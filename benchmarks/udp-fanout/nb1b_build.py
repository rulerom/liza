"""Generate a controlled Liza benchmark from the production experiment.

The test-only POSIX runtime adapter uses UdpError.Interrupted and WouldBlock for
D/S control-pipe events, while retrying those actual socket errors. This shim is
not a proposed Liza runtime contract. Input data is otherwise unchanged.
"""
from pathlib import Path
import shutil
import subprocess
import sys

def build(root,output,opt=2):
    root=Path(root).resolve();output=Path(output).resolve();tmp=output.parent
    src=(root/'examples/apps/rtp_fanout.liza').read_text()
    src=src.replace('    var stop=false','    var stop=false\n    var phase_rx:u64=0\n    var phase_valid:u64=0\n    var phase_seen=false')
    src=src.replace('UdpError.Interrupted=>{status=3}', 'UdpError.Interrupted=>{if phase_seen {status=3} else {phase_seen=true;phase_rx=rx;phase_valid=valid;ack=console.write("PHASE\\n")}}')
    src=src.replace('UdpError.WouldBlock=>{status=3}', 'UdpError.WouldBlock=>{if !phase_seen {status=3} else {stop=true;reason=1}}')
    src=src.replace('if is_stop(packet) {','if false {')
    src=src.replace('            if !metric("stop_reason=",reason) {status=3}', '''            if !metric("stop_reason=",reason) {status=3}
            if !metric("phase_received=",phase_rx) {status=3}
            if !metric("phase_valid=",phase_valid) {status=3}
            if !metric("phase_seen=",u64(phase_seen)) {status=3}''')
    # u64(bool) is not a supported conversion; use a conditional scalar.
    src=src.replace('            if !metric("phase_seen=",u64(phase_seen)) {status=3}', '            var phase_flag:u64=0\n            if phase_seen {phase_flag=1}\n            if !metric("phase_seen=",phase_flag) {status=3}')
    if 'UdpError.Interrupted=>{status=3}' in src or 'if is_stop(packet)' in src:raise RuntimeError('unsupported source shape')
    app=tmp/'rtp_controlled.liza';app.write_text(src)
    shutil.copytree(root/'examples/apps/rtp',tmp/'rtp')
    ir=tmp/'controlled.ll'
    subprocess.run([sys.executable,'-m','liza','emit-llvm',str(app),'-o',str(ir)],cwd=root,check=True)
    cmd=['clang','-O'+str(opt),'-Wno-override-module',str(ir),str(root/'benchmarks/udp-fanout/controlled_runtime.c'),str(root/'liza/runtime/memory.c'),str(root/'liza/runtime/cli_posix.c'),str(root/'liza/runtime/console_posix.c'),'-pthread','-o',str(output)]
    subprocess.run(cmd,cwd=root,check=True)
    return cmd
