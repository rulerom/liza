"""Run unchanged V0–V4 against a captured source tree and retain their evidence."""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import signal
import subprocess
import sys
import time
from .reports import STAGES, COVERAGE, validate, observations
from .artifacts import verify

ROOT=Path(__file__).resolve().parents[2]
SOURCE_SUFFIXES={'.py','.liza','.json','.txt','.sh','.md','.ll','.c','.h'}


def sha(path):
    digest=hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()


def write(path,value):
    path.write_bytes((json.dumps(value,indent=2,ensure_ascii=False,sort_keys=True)+'\n').encode('utf-8'))


def inventory(root):
    return {p.relative_to(root).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size}
            for p in sorted(root.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}


def snapshot(root,destination):
    destination.mkdir()
    for directory in ('liza','verification','docs'):
        for path in sorted((root/directory).rglob('*')):
            if '__pycache__' in path.parts or path.suffix not in SOURCE_SUFFIXES or not path.is_file():continue
            if path.is_symlink():raise ValueError('source symlink not supported: '+str(path))
            target=destination/path.relative_to(root)
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(path,target)
    return inventory(destination)


def execute(command,cwd,logs,timeout):
    logs.mkdir(parents=True,exist_ok=True)
    start=time.monotonic()
    result={'command':command,'cwd':str(cwd),'timeout_seconds':timeout}
    env=os.environ.copy()
    # Replays use the snapshot rather than user import overrides. Do not save
    # the whole environment: it may contain credentials unrelated to proofs.
    env.pop('PYTHONPATH',None);env.pop('PYTHONHOME',None)
    env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONUTF8']='1';env['PYTHONHASHSEED']='0'
    result['environment_overrides']={k:env[k] for k in ('PYTHONDONTWRITEBYTECODE','PYTHONUTF8','PYTHONHASHSEED')}
    with (logs/'stdout.log').open('wb') as out,(logs/'stderr.log').open('wb') as err:
        try:
            process=subprocess.Popen(command,cwd=cwd,stdout=out,stderr=err,env=env,
                                     start_new_session=os.name!='nt')
            try:result['returncode']=process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if os.name=='nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=err,stderr=err,check=False)
                    process.kill()
                else:os.killpg(process.pid,signal.SIGKILL)
                process.wait()
                result.update(returncode=None,error='stage timeout')
        except OSError as error:result.update(returncode=None,error=str(error))
    result['elapsed_seconds']=round(time.monotonic()-start,3)
    return result


def commands(args,source,stage,output):
    if stage=='v4':return [sys.executable,'-m','verification.v4.check','--output',str(output)]
    script='verification/check.py' if stage=='v0' else f'verification/{stage}/check.py'
    cmd=[sys.executable,str(source/script),'--output',str(output),'--clang',args.v3_clang if stage=='v3' else args.clang]
    if stage!='v3':return cmd+['--timeout-ms',str(args.solver_timeout_ms)]
    if not all((args.alive_tv,args.alive_source,args.llvm_revision)):
        raise ValueError('V3 requires --alive-tv, --alive-source and --llvm-revision; it is not skipped')
    cmd+=['--actual','--alive-tv',args.alive_tv,'--alive-source',args.alive_source,
          '--llvm-revision',args.llvm_revision,'--llvm-config',args.llvm_config,
          '--opt',args.opt,'--z3',args.z3,'--timeout',str(args.alive_timeout)]
    if args.toolchain_lock:cmd+=['--toolchain-lock',args.toolchain_lock]
    return cmd


def tool_metadata(args):
    result={'python':{'version':sys.version,'executable':sys.executable,'sha256':sha(Path(sys.executable))}}
    for name in ('clang','v3_clang','alive_tv','llvm_config','opt','z3'):
        requested=getattr(args,name)
        executable=shutil.which(requested) if requested else None
        result[name]={'requested':requested,'resolved':executable,
                      'sha256':sha(Path(executable)) if executable else None}
    return result


def aggregate(stages):
    selected=[s for s in stages.values() if s['status']!='not_selected']
    if any(s['status']!='passed' for s in selected):return 'incomplete'
    return 'passed' if len(selected)==len(STAGES) else 'partial'


def run(args):
    output=Path(args.output).resolve()
    for protected in (ROOT/'liza',ROOT/'verification',ROOT/'docs',ROOT/'.git'):
        if output==protected or protected in output.parents:raise ValueError('output must be outside source directories')
    if output.exists() and any(output.iterdir()):raise ValueError('output directory must be new or empty; stale reports are not reused')
    output.mkdir(parents=True,exist_ok=True)
    source=output/'source'
    sources=snapshot(ROOT,source)
    args=copy.copy(args)
    if args.toolchain_lock:
        lock=source/'pipeline-inputs/toolchain-lock.json'
        lock.parent.mkdir()
        shutil.copyfile(args.toolchain_lock,lock)
        args.toolchain_lock=str(lock)
        sources=inventory(source)
    write(output/'source-manifest.json',sources)
    tools_before=tool_metadata(args)
    report={'schema_version':1,'purpose':'orchestration of selected fixed experiments; no new proof scope',
            'certificate':'none; this report and its hashes are not a proof certificate',
            'machine_code_verified':False,'arbitrary_user_programs_verified':False,
            'started_at':datetime.now(timezone.utc).isoformat(),'host':platform.platform(),
            'selected_stages':args.stages,'required_stages':list(STAGES),'tools':tools_before,
            'trusted_base':['unchanged experiment models, specifications and solvers',
                            'pipeline adapters, snapshotting and hash collection','Python and host environment'],
            'reproducibility_limits':['tool binaries/libraries, SDK and OS are not bundled',
                                      'hashes identify artifacts, not correctness',
                                      'reports retain original model assumptions; no composed end-to-end proof'],
            'stages':{},'source_manifest':'source-manifest.json'}
    try:
        report['git']={'head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                       'dirty':bool(subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True))}
    except (OSError,subprocess.CalledProcessError):report['git']={'unavailable':True}
    for stage in STAGES:
        if stage not in args.stages:
            report['stages'][stage]={'status':'not_selected','reason':'explicit partial run; no claim for this experiment'}
            continue
        directory=output/'stages'/stage
        directory.mkdir(parents=True)
        child_output=directory/'artifacts'
        item={'status':'unknown','coverage_contract':COVERAGE[stage],'raw_report':f'stages/{stage}/artifacts/report.json',
              'specification':('source/docs/verified.md' if stage=='v0' else f'source/docs/verified-{stage}.md')}
        try:
            cmd=commands(args,source,stage,child_output)
            item['execution']=execute(cmd,source,directory,args.stage_timeout)
            raw_path=child_output/'report.json'
            if raw_path.is_file():
                raw=json.loads(raw_path.read_text(encoding='utf-8'))
                item['raw_report_sha256']=sha(raw_path)
                item['observations']=observations(raw,stage)
                item['scope']={k:raw[k] for k in ('scope','assumptions','memory_assumptions',
                    'trusted_base','exclusions','certificate','summary_scope') if k in raw}
                item.update(validate(stage,raw))
                if item['status']=='passed':
                    verify(stage,raw,child_output,source)
                    item['declared_artifacts_verified']=True
            else:item['reason']='child did not produce a report'
            if item['execution']['returncode']!=0:
                item.update(status='unknown' if 'error' in item['execution'] else 'failed',
                            reason='child execution did not succeed; raw report retained if present')
        except (OSError,ValueError,KeyError,TypeError) as error:item.update(status='unknown',reason=str(error))
        item['artifacts']=inventory(directory)
        report['stages'][stage]=item
        report['status']=aggregate(report['stages'])
        write(output/'report.json',report)
        print(stage,item['status'],flush=True)
    report['source_unchanged']=inventory(source)==sources
    report['tools_unchanged']=tool_metadata(args)==tools_before
    report['status']=aggregate(report['stages'])
    if not report['source_unchanged'] or not report['tools_unchanged']:report['status']='incomplete'
    report['finished_at']=datetime.now(timezone.utc).isoformat()
    write(output/'report.json',report)
    # Report is included in the manifest; the manifest cannot hash itself.
    write(output/'manifest.json',inventory(output))
    return report


def verify_bundle(path):
    root=Path(path).resolve()
    manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    actual=inventory(root)
    actual.pop('manifest.json',None)
    if actual!=manifest:raise ValueError('bundle integrity mismatch: missing, changed or extra artifacts')
    return json.loads((root/'report.json').read_text(encoding='utf-8'))['status']


def parser():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output')
    p.add_argument('--check-bundle',help='check saved bundle integrity only; does not rerun proofs')
    p.add_argument('--stages',nargs='+',choices=STAGES,default=list(STAGES))
    p.add_argument('--clang',default='clang')
    p.add_argument('--v3-clang',default='clang',help='separate compiler compatible with the pinned Alive2/LLVM toolchain')
    p.add_argument('--alive-tv');p.add_argument('--alive-source');p.add_argument('--llvm-revision')
    p.add_argument('--llvm-config',default='llvm-config');p.add_argument('--opt',default='opt');p.add_argument('--z3',default='z3')
    p.add_argument('--toolchain-lock')
    p.add_argument('--solver-timeout-ms',type=int,default=10000)
    p.add_argument('--alive-timeout',type=int,default=120)
    p.add_argument('--stage-timeout',type=int,default=1800)
    return p


def main(argv=None):
    p=parser();args=p.parse_args(argv)
    if args.check_bundle:
        if args.output:p.error('--check-bundle cannot be combined with --output')
        try:status=verify_bundle(args.check_bundle)
        except (OSError,ValueError,KeyError) as error:print(str(error),file=sys.stderr);return 1
        print('bundle integrity verified; recorded experiment status:',status)
        return 0
    if not args.output:p.error('--output is required for a run')
    if len(set(args.stages))!=len(args.stages):p.error('duplicate stages')
    if min(args.solver_timeout_ms,args.alive_timeout,args.stage_timeout)<=0:p.error('timeouts must be positive')
    for name in ('alive_source','toolchain_lock'):
        if getattr(args,name):setattr(args,name,str(Path(getattr(args,name)).resolve()))
    for name in ('clang','v3_clang','alive_tv','llvm_config','opt','z3'):
        value=getattr(args,name)
        if value and shutil.which(value):setattr(args,name,str(Path(shutil.which(value)).absolute()))
    try:report=run(args)
    except (OSError,ValueError) as error:print(str(error),file=sys.stderr);return 1
    print('pipeline:',report['status'])
    return {'passed':0,'partial':2,'incomplete':1}[report['status']]


if __name__=='__main__':raise SystemExit(main())
