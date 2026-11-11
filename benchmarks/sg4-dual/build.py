"""Immutable Liza single/dual builds and SSRC-specific diagnostic collectors."""
import hashlib,ipaddress,json,platform,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'sg4-fanout'
WARMUP=200
MAX_PACKETS=600000
SSRC=(0x10203040,0x50607080)
CONFIG='GroupConfig(65536,65536,1048576,1048576,65536,2,2,10000,3000)'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def build(folder,ports,binds=('127.0.0.1','127.0.0.1')):
    folder=Path(folder).resolve();folder.mkdir(parents=True,exist_ok=False)
    if len(ports)!=2 or any(not 1<=len(p)<=64 for p in ports) or len(set(sum(ports,[])))!=sum(map(len,ports)):raise ValueError('distinct bounded receiver endpoints')
    addresses=[ipaddress.IPv4Address(v) for v in binds]
    lines=['import rtp.receivers','pub fn setup(borrow mut table:rtp.receivers.Receivers,stream:u32)->u32 {']
    for stream,group in enumerate(ports):
        lines.append(f' if stream=={stream} {{')
        for i,port in enumerate(group):
            if not 0<port<65536:raise ValueError('port')
            lines.extend([f' a{i}=rtp.receivers.add(borrow mut table,{i})',f' b{i}=rtp.receivers.learn(borrow mut table,{i},rtp.receivers.Endpoint(2130706433,{port}))'])
        lines.append(' }')
    lines+=['return 0','}','pub fn bind_address(owner:u32)->net.Address {']
    for owner,addr in enumerate(addresses):
        lines.append(f'if owner=={owner} {{return net.ipv4('+','.join(map(str,addr.packed))+',0)}')
    lines+=['return net.ipv4('+','.join(map(str,addresses[0].packed))+',0)','}']
    (folder/'config.liza').write_text('\n'.join(lines)+'\n')
    header=[f'#define WARMUP {WARMUP}',f'#define MAX_PACKETS {MAX_PACKETS}',f'#define SSRC_A {SSRC[0]}u',f'#define SSRC_B {SSRC[1]}u']
    for i in range(2):
        header.extend([f'#if COLLECTOR_STREAM=={i}',f'#define RECEIVERS {len(ports[i])}',f'#define EXPECTED_SSRC {SSRC[i]}u','static const unsigned short ports[RECEIVERS]={'+','.join(map(str,ports[i]))+'};','#endif'])
    # Adapter does not use the collector-only ports array.
    header.insert(0,'#ifdef COLLECTOR_STREAM');header.append('#endif')
    header += [f'#ifndef MAX_PACKETS\n#define MAX_PACKETS {MAX_PACKETS}\n#define WARMUP {WARMUP}\n#define SSRC_A {SSRC[0]}u\n#define SSRC_B {SSRC[1]}u\n#endif']
    (folder/'config.h').write_text('\n'.join(header)+'\n')
    shutil.copyfile(HERE/'owner.liza',folder/'owner.liza');shutil.copytree(ROOT/'examples/apps/rtp',folder/'rtp')
    single='''import owner
fn producer()->u32:io {return owner.publish()}
fn consumer()->u32:io,alloc {return owner.consume_both()}
fn main()->u32:io,alloc {
 match groups.run(CONFIG) {Ok(r)=>{return 0} Err(e)=>{match e {GroupError.Faulted(r)=>{return 0} GroupError.Busy=>{return 1} GroupError.InvalidConfig=>{return 2} GroupError.StartupFailed=>{return 3}}}}
}
'''.replace('CONFIG',CONFIG)
    dual='''import owner
fn producer_a()->u32:io {return owner.publish()}
fn producer_b()->u32:io {return owner.publish()}
fn consumer_a()->u32:io,alloc {return owner.consume_a()}
fn consumer_b()->u32:io,alloc {return owner.consume_b()}
fn main()->u32:io,alloc {
 pair=groups.run_pair(CONFIG,CONFIG)
 match pair.first {Ok(r)=>{} Err(e)=>{match e {GroupError.Faulted(r)=>{} GroupError.Busy=>{return 1} GroupError.InvalidConfig=>{return 2} GroupError.StartupFailed=>{return 3}}}}
 match pair.second {Ok(r)=>{} Err(e)=>{match e {GroupError.Faulted(r)=>{} GroupError.Busy=>{return 4} GroupError.InvalidConfig=>{return 5} GroupError.StartupFailed=>{return 6}}}}
 return 0
}
'''.replace('CONFIG',CONFIG)
    # Export only application helpers; producer/consumer capabilities remain in IR.
    text=(folder/'owner.liza').read_text()
    for fn in ('publish','consume_a','consume_b','consume_both'):text=text.replace('fn '+fn+'(', 'pub fn '+fn+'(')
    (folder/'owner.liza').write_text(text)
    for variant,text in [('single',single),('dual',dual)]:(folder/(variant+'.liza')).write_text(text)
    collector=(BASE/'collector_ab.c').read_text();needle='be32(data+8)!=0x10203040u'
    if collector.count(needle)!=1:raise RuntimeError('upstream collector validation changed; audit adaptation')
    (folder/'collector.c').write_text('/* B2 generated SSRC adaptation of A2 collector_ab.c; all other validation preserved. */\n'+collector.replace(needle,'be32(data+8)!=EXPECTED_SSRC'))
    runtime=ROOT/'liza/runtime';commands=[]
    def run(cmd):
        commands.append(list(map(str,cmd)));p=subprocess.run(commands[-1],cwd=ROOT,capture_output=True,text=True,timeout=180)
        if p.returncode:raise RuntimeError(p.stdout+p.stderr)
    common=['clang','-std=c11','-O2','-g','-I'+str(runtime),'-I'+str(folder),'-I'+str(BASE)]
    if sys.platform.startswith('linux'):common+=['-D_GNU_SOURCE']
    net=folder/'net.o';run(common+['-Dliza_rt_net_udp_bind=b2_net_bind_original','-c',runtime/'net_posix.c','-o',net])
    objects=[net]
    for name in ('reactor_posix','scoped_channel_core','memory'):
        obj=folder/(name+'.o');run(common+['-c',runtime/(name+'.c'),'-o',obj]);objects.append(obj)
    bins={}
    for variant in ('single','dual'):
        ir=folder/(variant+'.ll');run([sys.executable,'-m','liza','emit-llvm',folder/(variant+'.liza'),'-o',ir])
        obj=folder/(variant+'_adapter.o');run(common+['-Wall','-Wextra','-Werror','-DLIZA_SG2_TESTING','-DB2_SINGLE='+str(int(variant=='single')),'-c',HERE/'adapter.c','-o',obj])
        binary=folder/variant;run(common+['-Wno-override-module',ir,obj,*objects,'-pthread','-o',binary]);bins[variant]=binary
    for stream in range(2):
        binary=folder/f'collector{stream}';run(common+[f'-DCOLLECTOR_STREAM={stream}',folder/'collector.c','-o',binary]);bins[f'collector{stream}']=binary
    sources=[*HERE.glob('*'),*BASE.glob('*.c'),*BASE.glob('*.h'),*BASE.glob('*.py'),*runtime.glob('*'),*folder.glob('*.liza'),folder/'collector.c',folder/'config.h',*folder.glob('*.ll'),*(folder/'rtp').glob('*.liza')]
    manifest={'commands':commands,'ports':ports,'binds':list(map(str,addresses)),'platform':platform.platform(),'source_sha256':{str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p.relative_to(folder)):sha(p) for p in sources if p.is_file()},'binary_sha256':{k:sha(v) for k,v in bins.items()},'llvm_version':subprocess.check_output(['clang','--version'],text=True),'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()}
    return bins,manifest
