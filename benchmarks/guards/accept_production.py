"""Production O0/O2 correctness and exact P3 code comparison; no new timing."""
import argparse,importlib.util,json,sys,hashlib,subprocess,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--reference',type=Path,required=True);p.add_argument('--p3',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
out=a.output.resolve();ref=a.reference.resolve();p3=a.p3.resolve();out.mkdir(parents=True)
clang=shutil.which('clang')
subprocess.run([sys.executable,root/'benchmarks/mutable/emit.py',out/'module.ll',clang],cwd=root,check=True,env={**__import__('os').environ,'PYTHONPATH':str(root)})
sys.path.insert(0,str(root/'benchmarks/json'))
spec=importlib.util.spec_from_file_location('base',root/'benchmarks/json/run.py');base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
flags=json.loads((out/'module.target.json').read_text())['flags'];exes={};commands=[]
def run(args):commands.append([str(a) for a in args]);return subprocess.check_output(args,stderr=subprocess.STDOUT)
for opt in (0,2):
 obj=out/f'O{opt}.o';exe=out/f'O{opt}'
 run([clang,*flags,f'-O{opt}','-fstack-usage','-c',out/'module.ll','-o',obj]);run([clang,*flags,ref/'baseline/driver.o',obj,'-o',exe]);exes[f'production-O{opt}']=exe
run([clang,*flags,'-O2','-S','-emit-llvm',out/'module.ll','-o',out/'optimized.ll'])
run([clang,*flags,'-O2','-S',out/'module.ll','-o',out/'module.s'])
exes['rust']=ref/'baseline/rust';r=base.correctness(exes,ref/'baseline/liza-json',out);r['cli_cases']=r['documents']*(len(exes)+1)
sys.path.insert(0,str(root/'benchmarks/state'));from inspect_objects import text_section
same=text_section(out/'O2.o')==text_section(p3/'forward/O2.o')
assert same
assert (out/'module.ll').read_bytes()==(p3/'forward/module.ll').read_bytes()
report={'correctness':r,'commands':commands,'clang':run([clang,'--version']).decode(),'p3_raw_llvm_identical':(out/'module.ll').read_bytes()==(p3/'forward/module.ll').read_bytes(),'p3_machine_text_identical':same,'text_sha256':hashlib.sha256(text_section(out/'O2.o')).hexdigest(),'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((root/'liza').rglob('*.py'))}}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('JSON production O0/O2 agreement passed; raw LLVM and machine text identical to P3.')
