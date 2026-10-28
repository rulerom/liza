#!/usr/bin/env python3
"""Non-JSON applications: sites, exact text comparison and compilation cost."""
import argparse,hashlib,json,random,statistics,subprocess,sys,time
from pathlib import Path
from liza.modules import load_program
from liza.ir import lower,dump
from liza.backend import llvm
from liza.target import resolve
from forward import forward
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'state'))
from inspect_objects import text_section
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--results',type=Path,required=True);p.add_argument('--clang',default='clang');a=p.parse_args()
out=a.results/'controls';out.mkdir();target=resolve(a.clang);report={'applications':{},'compilation_samples':[]}
for label,source in [('rtp','examples/rtp_result.liza'),('relay','examples/apps/liza_proxy.liza')]:
 folder=out/label;folder.mkdir();module=lower(load_program(ROOT/source));changed,sites=forward(module)
 report['applications'][label]={'source':source,'certificates':sites,'variants':{}}
 for variant,m in [('default',module),('forward',changed)]:
  path=folder/(variant+'.ll');path.write_text(llvm(m,target));path.with_suffix('.semantic.json').write_text(dump(m))
  obj=folder/(variant+'.o');subprocess.run([a.clang,*target.flags,'-O2','-fstack-usage','-c',str(path),'-o',str(obj)],check=True,capture_output=True)
  text=text_section(obj);report['applications'][label]['variants'][variant]={'text_bytes':len(text),'text_sha256':hashlib.sha256(text).hexdigest(),'stack':obj.with_suffix('.su').read_text().splitlines()}
 report['applications'][label]['identical_text']=report['applications'][label]['variants']['default']['text_sha256']==report['applications'][label]['variants']['forward']['text_sha256']
for repeat in range(5):
 schedule=['default','forward'];random.Random(311+repeat).shuffle(schedule)
 for label in schedule:
  start=time.monotonic();subprocess.run([a.clang,*target.flags,'-O2','-c',str(a.results/label/'module.ll'),'-o',str(out/(label+'-timed.o'))],check=True,capture_output=True)
  report['compilation_samples'].append({'variant':label,'repeat':repeat,'seconds':time.monotonic()-start})
report['compile_median_seconds']={v:statistics.median(x['seconds'] for x in report['compilation_samples'] if x['variant']==v) for v in ('default','forward')}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
