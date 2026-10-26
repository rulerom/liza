#!/usr/bin/env python3
"""Independent raw-LLVM equivalence checks and native negative-control replay."""
import argparse,json,re,signal,subprocess,sys
from pathlib import Path
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.backend import llvm
from liza.target import resolve
from forward import forward
import symbolic as s

FIXTURE='''
struct Sample {position:u64;other:u64}
fn positive(s:Sample,flag:bool)->Sample {
 if s.position==18446744073709551615 {return s}
 var n=s
 if flag {n.other=7} else {n.other=8}
 n.position=n.position+1
 return n
}
fn changed(s:Sample,flag:bool)->Sample {
 if s.position==18446744073709551615 {return s}
 var n=s
 if flag {n.position=n.other} else {n.other=0}
 n.position=n.position+1
 return n
}
fn snapshots(s:Sample,flag:bool)->u32 {
 first=copy s;second=copy s
 current=positive(s,flag)
 third=copy current
 next=positive(current,!flag)
 if first.position!=s.position || second.other!=s.other {return 1}
 if third.position!=s.position+1 || next.position!=s.position+2 {return 2}
 return 0
}
fn increment(x:u64)->u64 {return x+1}
fn main()->u32 {return 0}
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--results',type=Path,required=True);p.add_argument('--clang',default='clang');p.add_argument('--z3',default='z3');a=p.parse_args()
 out=a.results/'proof';out.mkdir();report={'status':'incomplete','solver':subprocess.check_output([a.z3,'-version'],text=True),'checks':[],'replay':[]}
 def check(label,module,ir,name,expected,pinned=None):
  f=next(x for x in module['functions'] if x['name']==name);structs={x['name']:x['fields'] for x in module['structures']};m=s.SMT();args=s.inputs(m,f,structs)
  left=s.semantic(m,f,args,structs);right=s.llvm(m,ir,'liza_'+name,args)
  condition=s.mismatch(left,right)
  if pinned:
   bindings={n:s.S(n,w) for n,w in m.inputs}
   condition=s.conjunction(condition,*(s.equal(bindings[k],s.constant(v,bindings[k].width)) for k,v in pinned.items()))
  query=m.query(condition);path=out/(label+'.smt2');path.write_text(query)
  run=subprocess.run([a.z3,str(path)],text=True,capture_output=True,timeout=30,check=True)
  status=run.stdout.strip();(out/(label+'.solver.txt')).write_text(run.stdout+run.stderr)
  if status!=expected:raise AssertionError((label,status,expected))
  report['checks'].append({'name':label,'result':status,'concrete_input':pinned})
 try:
  emitted=a.results/'emitted';original=json.loads((emitted/'module.original.semantic.json').read_text())
  check('actual-utf8-baseline',original,(a.results/'default/module.ll').read_text(),'utf8_stream.feed_byte','unsat')
  check('actual-utf8-forward',original,(emitted/'module.ll').read_text(),'utf8_stream.feed_byte','unsat')
  (out/'fixture.liza').write_text(FIXTURE);module=lower(Parser(FIXTURE).parse());original=json.loads(dump(module));(out/'fixture.semantic.json').write_text(dump(module));target=resolve(a.clang)
  good,certs=forward(module);bad,badcerts=forward(module,unsafe=True)
  assert any(x['function']=='positive' for x in certs)
  assert not any(x['function']=='changed' and x['field']=='position' for x in certs)
  assert any(x['function']=='changed' and x['field']=='position' for x in badcerts)
  irs={'original':llvm(module,target),'forward':llvm(good,target),'wrong-field':llvm(bad,target)}
  for name in ('positive','changed','increment'):check('fixture-'+name,original,irs['forward'],name,'unsat')
  pinned={'p0_position':0,'p0_other':18446744073709551615,'p1':True}
  check('wrong-field',original,irs['wrong-field'],'changed','sat',pinned)
  # Separate negative control: an unconditional increment has no dominating guard.
  raw=irs['original'];match=re.search(r'(?ms)^define i64 @liza_increment.*?^}',raw);assert match
  fn,count=re.subn(r'br i1 %[^,]+, label %[^,]+, label %([^\n]+)',r'br label %\1',match[0]);assert count==1
  irs['deleted-trap']=raw[:match.start()]+fn+raw[match.end():]
  check('deleted-trap',original,irs['deleted-trap'],'increment','sat',{'p0':18446744073709551615})
  bridge='''
define i64 @replay_changed() {
entry:
 %s = insertvalue %struct.Sample zeroinitializer, i64 -1, 1
 %r = call %struct.Sample @liza_changed(%struct.Sample %s, i1 true)
 %v = extractvalue %struct.Sample %r, 0
 ret i64 %v
}
'''
  driver=out/'driver.c';driver.write_text('#include <stdint.h>\n#include <stdio.h>\nextern uint64_t replay_changed(void);extern uint64_t liza_increment(uint64_t);\nint main(int argc,char**argv){printf("%llu\\n",(unsigned long long)(argc>1?liza_increment(UINT64_MAX):replay_changed()));return 0;}\n')
  for label,ir in irs.items():
   path=out/(label+'.ll');path.write_text(ir.replace('define i32 @main()','define i32 @unused_main()')+bridge)
   for opt in (0,2):
    exe=out/(label+'-O'+str(opt));subprocess.run([a.clang,'-Wno-override-module','-O'+str(opt),str(path),str(driver),'-o',str(exe)],capture_output=True,check=True)
    for mode in ('changed','increment'):
     run=subprocess.run([str(exe)]+(['increment'] if mode=='increment' else []),capture_output=True,text=True,timeout=5)
     expected_output='1\n' if label=='wrong-field' and mode=='changed' else '0\n' if label=='deleted-trap' and mode=='increment' else None
     if expected_output is None:assert run.returncode in (-signal.SIGTRAP,-signal.SIGILL),(label,opt,mode,run)
     else:assert run.returncode==0 and run.stdout==expected_output,(label,opt,mode,run)
     report['replay'].append({'variant':label,'opt':opt,'case':mode,'returncode':run.returncode,'stdout':run.stdout})
  snapshot_bridge='\ndefine i32 @snapshot_probe(i1 %flag) {\nentry:\n %v = call i32 @liza_snapshots(%struct.Sample zeroinitializer, i1 %flag)\n ret i32 %v\n}\n'
  driver=out/'snapshot-driver.c'
  driver.write_text('#include <stdbool.h>\nextern unsigned snapshot_probe(bool);\nint main(void){return snapshot_probe(false)|snapshot_probe(true);}')
  for label in ('original','forward'):
   path=out/(label+'-snapshot.ll');path.write_text(irs[label].replace('define i32 @main()','define i32 @unused_main()')+snapshot_bridge)
   for opt in (0,2):
    exe=out/(label+'-snapshot-O'+str(opt));subprocess.run([a.clang,'-Wno-override-module','-O'+str(opt),str(path),str(driver),'-o',str(exe)],check=True,capture_output=True)
    run=subprocess.run([str(exe)],capture_output=True,text=True,timeout=5);assert run.returncode==0
    report['replay'].append({'variant':label,'opt':opt,'case':'snapshots-both-branches','returncode':run.returncode})
  report['status']='passed'
 finally:(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 print(json.dumps(report,indent=2))
if __name__=='__main__':main()
