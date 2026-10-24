"""Run V4 resource graph validation: python -m verification.v4.check --output DIR."""
import argparse
from contextlib import contextmanager
import hashlib
import json
import platform
from pathlib import Path
import types
from unittest.mock import patch

from liza import dependencies
from liza.frontend import Parser, CompileError
from liza.ir import lower, dump
from .model import check

SAFE = '''fn main()->u32:alloc {
    match memory.create(64) {
        Err(e)=>{return 1}
        Ok(region)=>{
            allocation=memory.alloc<u8>(region,4,0)
            match move allocation {
                Err(e)=>{}
                Ok(buffer)=>{released=memory.release(move buffer)}
            }
            closed=memory.close(move region)
            return 0
        }
    }
}
'''
UNSAFE = SAFE.replace('            match move allocation',
                      '            closed=memory.close(move region)\n            match move allocation').replace(
                          '            closed=memory.close(move region)\n            return 0', '            return 0')
MUTATIONS = {
    'lose_ok_payload': (
        "branch[arm.binding.text]=value.cases.get(arm.case.rsplit('.',1)[-1],EMPTY)",
        "branch[arm.binding.text]=value.cases.get(arm.case.rsplit('.',1)[-1],EMPTY)\n                            if branch[arm.binding.text].all_buffers(): branch[arm.binding.text]=EMPTY"),
    'wrong_call_origin': (
        'return next(iter(ids))', "return ('parameter','999')"),
    'lose_phi_dependency': (
        'return {k:join_value([p.get(k,EMPTY) for p in paths],token) for k in keep}',
        'return {k:(EMPTY if any(p.get(k,EMPTY).all_buffers() for p in paths) else join_value([p.get(k,EMPTY) for p in paths],token)) for k in keep}'),
    'conflate_regions': (
        'region=arguments[0].all_regions()',
        'region=next((v.all_regions() for v in reversed(list(state.values())) if v.all_regions()),arguments[0].all_regions())'),
    'forget_backedge_origins': (
        'if any(p != entry for p in backs):',
        'if False and any(p != entry for p in backs):'),
    'lose_unresolved_result': (
        'list(self.cases.values())+list(self.components) for o in v.all_buffers()',
        'list(self.components) for o in v.all_buffers()'),
    'bypass_region_guard': (
        'if value.all_regions() & dependencies:',
        'if False and value.all_regions() & dependencies:'),
}


def compile_source(source):
    audit = {}
    module = lower(Parser(source).parse(), dependency_audit=audit)
    return module, audit


@contextmanager
def mutant(name):
    original = Path(dependencies.__file__).read_text(encoding='utf-8')
    old, new = MUTATIONS[name]
    if original.count(old) != 1:
        raise RuntimeError('mutation anchor changed; recalibration required')
    source = original.replace(old, new)
    isolated = types.ModuleType('liza._v4_mutant')
    isolated.__package__ = 'liza'
    exec(compile(source, '<V4 mutated analyzer>', 'exec'), isolated.__dict__)
    with patch.object(dependencies, 'check_dependencies', isolated.check_dependencies):
        yield source


def run(output):
    output.mkdir(parents=True, exist_ok=True)
    reports = {}

    def save(name, source, module, audit):
        ir = dump(module)
        artifacts = {'source.liza': source, 'semantic-ir.json': ir,
                     'audit.json': json.dumps(audit, indent=2, sort_keys=True)}
        directory = output / name
        directory.mkdir(exist_ok=True)
        hashes = {}
        for filename, contents in artifacts.items():
            data = contents.encode()
            (directory / filename).write_bytes(data)
            hashes[filename] = hashlib.sha256(data).hexdigest()
        result = check(module, audit)
        result['artifacts'] = hashes
        return result

    from . import fixtures
    positive = {'safe':SAFE, **{name.lower():getattr(fixtures,name) for name in
                               ['CALL','RESULT_CALL','UPDATE','FACTORY','CFG','LOOP','LIVE_LOOP',
                                'WRAP','TWO_BUFFERS','TWO_REGIONS_SAFE']}}
    for name,source in positive.items():
        module,audit=compile_source(source)
        reports[name]=save(name,source,module,audit)
    negative = {'lose_unresolved_result':UNSAFE,'bypass_region_guard':UNSAFE,
                'lose_ok_payload':fixtures.RESOLVED_UNSAFE,
                'wrong_call_origin':fixtures.CALL_UNSAFE,
                'lose_phi_dependency':fixtures.CFG_UNSAFE,
                'conflate_regions':fixtures.TWO_REGIONS,
                'forget_backedge_origins':fixtures.LOOP_UNSAFE}
    for name in MUTATIONS:
        source=negative[name]
        try:
            compile_source(source)
        except CompileError as error:
            rejection=str(error)
        else:
            raise RuntimeError('unmodified analyzer accepted negative control '+name)
        with mutant(name) as analyzer:
            module, audit = compile_source(source)
        reports[name] = save(name, source, module, audit)
        reports[name]['original_rejection'] = rejection
        reports[name]['mutated_analyzer_accepts'] = True
        (output / name / 'dependencies-mutant.py').write_bytes(analyzer.encode('utf-8'))
        reports[name]['artifacts']['dependencies-mutant.py'] = hashlib.sha256(analyzer.encode()).hexdigest()
    from .summary_controls import CONTROLS, understate
    for name,(source,mutation) in CONTROLS.items():
        module,audit=compile_source(source)
        baseline=check(module,audit)
        original_ir=dump(module)
        function=understate(module,mutation)
        reports[name]=save(name,source,module,audit)
        concrete=check(module,audit,concrete=True)
        reports[name].update(baseline_status=baseline['status'],
                             mutated_function=function, concrete_status=concrete['status'],
                             concrete_summary_failures=concrete['summary_failures'])
        original_bytes=original_ir.encode('utf-8')
        (output/name/'original-semantic-ir.json').write_bytes(original_bytes)
        reports[name]['artifacts']['original-semantic-ir.json']=hashlib.sha256(original_bytes).hexdigest()
    root = Path(__file__).resolve().parents[2]
    tool_files = ['liza/dependencies.py', 'liza/ir.py',
                  'verification/v4/model.py', 'verification/v4/check.py',
                  'verification/v4/fixtures.py', 'verification/v4/summary_controls.py']
    result = {'stage': 'V4 resource graph: functions, CFG and inductive closure',
              'python': platform.python_version(), 'platform': platform.platform(),
              'positive_cases':list(positive), 'summary_controls':list(CONTROLS), 'tools': {name: hashlib.sha256((root/name).read_bytes()).hexdigest()
                        for name in tool_files}, 'results': reports}
    (output / 'report.json').write_bytes((json.dumps(result, indent=2, sort_keys=True)+'\n').encode('utf-8'))
    return result


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = run(args.output)
    print(json.dumps({k:v['status'] for k,v in report['results'].items()}, indent=2))
    results = report['results']
    return 0 if (all(results[n]['status']=='verified_fragment' for n in report['positive_cases']) and
                 all(results[n]['status'] == 'model_violation' and
                     any(t.get('reproduced') for t in results[n]['traces']) for n in MUTATIONS) and
                 all(results[n]['baseline_status']=='verified_fragment' and
                     results[n]['status']=='summary_failure' and
                     results[n]['concrete_status']=='summary_failure'
                     for n in report['summary_controls']) and
                 results['lose_unresolved_result']['coverage_failures'] and
                 not results['bypass_region_guard']['coverage_failures']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
