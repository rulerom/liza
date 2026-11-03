"""One immutable generated configuration and binary pair per invocation."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
WARMUP=200
MAX_PACKETS=600000

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def build(folder,ports,inject_send_failure=False):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    config=['import rtp.receivers','pub fn setup(borrow mut table:rtp.receivers.Receivers)->u32 {']
    for i,port in enumerate(ports):
        config += [f' a{i}=rtp.receivers.add(borrow mut table,{i})',f' b{i}=rtp.receivers.learn(borrow mut table,{i},rtp.receivers.Endpoint(2130706433,{port}))']
    config+=['return 0','}'];(folder/'config.liza').write_text('\n'.join(config)+'\n')
    (folder/'config.h').write_text(f'#define RECEIVERS {len(ports)}\n#define WARMUP {WARMUP}\n#define MAX_PACKETS {MAX_PACKETS}\nstatic const unsigned short ports[RECEIVERS]={{'+','.join(map(str,ports))+'};\n')
    shutil.copyfile(HERE/'fanout.liza',folder/'fanout.liza')
    shutil.copytree(ROOT/'examples/apps/rtp',folder/'rtp',dirs_exist_ok=True)
    commands=[]
    def run(cmd):
        commands.append(list(map(str,cmd)));subprocess.run(commands[-1],cwd=ROOT,check=True,capture_output=True,text=True,timeout=120)
    ir=folder/'fanout.ll';run([sys.executable,'-m','liza','emit-llvm',folder/'fanout.liza','-o',ir])
    runtime=ROOT/'liza/runtime'
    common=['clang','-std=c11','-O2','-g','-I'+str(runtime),'-I'+str(folder)]
    net=folder/'net.o';run(common+['-Dliza_rt_net_udp_bind=bench_net_bind_original','-c',runtime/'net_posix.c','-o',net])
    adapter=folder/'adapter.o';run(common+(['-DBENCH_TEST_SEND_FAIL'] if inject_send_failure else [])+['-Wall','-Wextra','-Werror','-c',HERE/'adapter.c','-o',adapter])
    objects=[]
    for name in ('reactor_posix','scoped_channel_core','memory'):
        obj=folder/(name+'.o');run(common+['-c',runtime/(name+'.c'),'-o',obj]);objects.append(obj)
    binaries={}
    for variant,source in [('liza',ir),('c',HERE/'fanout.c')]:
        binary=folder/variant
        run(common+['-Wno-override-module',source,adapter,net,*objects,'-pthread','-o',binary]);binaries[variant]=binary
    collector=folder/'collector';run(common+[HERE/'collector.c','-o',collector]);binaries['collector']=collector
    sources=[*HERE.glob('*.c'),*HERE.glob('*.h'),*HERE.glob('*.py'),HERE/'fanout.liza',folder/'config.h',folder/'config.liza',folder/'fanout.ll',*sorted(runtime.glob('*')),*(folder/'rtp').glob('*.liza')]
    hashes={str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else p.name:sha(p) for p in sources if p.is_file()}
    return binaries,{'commands':commands,'source_sha256':hashes,'binary_sha256':{k:sha(v) for k,v in binaries.items()},'ports':ports}
