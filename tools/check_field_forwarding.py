#!/usr/bin/env python3
"""Independently compare original SIR with production raw LLVM on selected CFGs.

Uses P3's separate fail-closed semantic interpreters, not forwarding certificates.
This checks selected unsigned, acyclic functions, not universal pass soundness.
"""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'benchmarks/guards'))
import symbolic as s
from liza import backend
from liza.frontend import Parser
from liza.ir import lower,dump
from liza.field_forwarding import analyze


def run(output,z3=None,python_z3=False):
 output=Path(output);output.mkdir(parents=True,exist_ok=True);rows=[]
 command=None if python_z3 else z3 or shutil.which('z3')
 if command:version=subprocess.check_output([command,'-version'],text=True).strip()
 else:
  import z3 as solver
  version=solver.get_version_string()
 def check(label,m,ir,name,expected,pinned=None):
  data=json.loads(dump(m));f=next(f for f in data['functions'] if f['name']==name)
  smt=s.SMT();structs={x['name']:x['fields'] for x in data['structures']};args=s.inputs(smt,f,structs)
  left=s.semantic(smt,f,args,structs);right=s.llvm(smt,ir,'liza_'+name,args)
  condition=s.mismatch(left,right)
  for key,value in (pinned or {}).items():
   width=dict(smt.inputs)[key];condition=s.conjunction(condition,s.equal(s.S(key,width),s.constant(value,width)))
  query=smt.query(condition);(output/(label+'.smt2')).write_text(query)
  if command:
   result=subprocess.run([command,'-in'],input=query,text=True,capture_output=True,check=True,timeout=30).stdout.strip()
  else:
   engine=solver.Solver();engine.set(timeout=15000);engine.from_string(query);result=str(engine.check())
  rows.append({'name':label,'result':result,'expected':expected,'input':pinned})
  if result!=expected:raise AssertionError(rows[-1])
 def save(label,source):
  m=lower(Parser(source).parse());ir=backend.llvm(m)
  (output/(label+'.liza')).write_text(source);(output/(label+'.semantic.json')).write_text(dump(m));(output/(label+'.ll')).write_text(ir)
  facts={f.name:{'roots':p.roots,'certificates':p.certificates,'facts':{str(k):{n:asdict(v) for n,v in facts.items()} for k,facts in p.facts.items()},'visits':p.visits} for f in m for p in [analyze(f,m.structs,lambda t:False)] if p.roots}
  (output/(label+'.analysis.json')).write_text(json.dumps(facts,indent=2)+'\n')
  return m,ir
 try:
  m,ir=save('utf8','fn feed(s:Utf8StreamState,b:u8)->Utf8StreamState{return utf8_stream.feed_byte(s,b)} fn main()->u32{return 0}')
  check('utf8-all-input-bits',m,ir,'utf8_stream.feed_byte','unsat')
  m,ir=save('fixture',(ROOT/'tests/fixtures/field_forwarding.liza').read_text())
  for name in ('nested','remote_change','increment','other_field_trap'):check(name,m,ir,name,'unsat')
  for changed_at in (None,0,6,11):
   body='\n'.join(f'if b{i} {{n.'+('x=s.y' if i==changed_at else 'y=1')+'} else {n.y=2}' for i in range(12))
   source='struct S {x:u64;y:u64} fn graph(s:S,'+','.join(f'b{i}:bool' for i in range(12))+')->u64 {var n=s;'+body+';return n.x+1} fn main()->u32{return 0}'
   label='graph-'+str(changed_at);gm,gir=save(label,source);check(label,gm,gir,'graph','unsat')
  def unsafe(fn,structs,large):
   p=analyze(fn,structs,large)
   if fn.name=='remote_change':
    for b in fn.blocks:
     for op in b.operations:
      if op.op=='struct.field' and op.field_name=='sequence':p.roots[op.result]='p0'
   return p
  with patch.object(backend,'field_forwarding',side_effect=unsafe):bad=backend.llvm(m)
  (output/'wrong-field.ll').write_text(bad)
  check('wrong-field',m,bad,'remote_change','sat',{'p0_sequence':0,'p0_tag':2**64-1,'p1':True,'p2':True,'p3':True})
  match=re.search(r'(?ms)^define i64 @liza_increment.*?^}',ir)
  body,count=re.subn(r'br i1 %[^,]+, label %[^,]+, label %([^\n]+)',r'br label %\1',match[0]);assert count==1
  bad=ir[:match.start()]+body+ir[match.end():];(output/'deleted-trap.ll').write_text(bad)
  check('deleted-trap',m,bad,'increment','sat',{'p0':2**64-1})
 finally:(output/'report.json').write_text(json.dumps({'solver':version,'checks':rows},indent=2)+'\n')
 print(f'{len(rows)-2} UNSAT equivalence checks; 2 SAT negative controls; solver {version}')

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',default='build/field-forwarding');p.add_argument('--z3');p.add_argument('--python-z3',action='store_true');a=p.parse_args();run(a.output,a.z3,a.python_z3)
