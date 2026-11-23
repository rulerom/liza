"""Anomaly diagnostics against captured RTP clock steps and controlled time."""
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
from test_httpws import build, array

ROOT = Path(__file__).resolve().parents[1]



@unittest.skipUnless(shutil.which('clang'), 'Clang required')
class RtspMonitor(unittest.TestCase):
    def test_clock_wrap_pause_source_and_bounded_reporting(self):
        source = '''import rtsp.monitor
import rtsp.bridge
fn main()->u32:io {
var m=rtsp.monitor.create();var bridge=rtsp.bridge.create(96,1041,1)
'''
        counter = 0

        def feed(seq, timestamp, at, ssrc=777, valid=True, idr=False):
            nonlocal source, counter
            data = struct.pack('!BBHII', 128, 224, seq, timestamp, ssrc) + b'\x65'
            source += f'p{counter}:[u8;13]={array(data)}\n'
            source += f'r{counter}=rtsp.monitor.packet(borrow mut m,{at},view p{counter}[0..13],{str(valid).lower()},{str(idr).lower()},bridge)\n'
            counter += 1

        # Natural sequence/timestamp wraps and small backward presentation steps.
        feed(65535, 4294965000, 1000, idr=True)
        feed(0, 1304, 1040)
        feed(1, 1000, 1080)
        source += 'if m.clock_jumps!=0||m.sequence_events!=0 {return 1}\n'
        # A genuine two-second source pause is not a discontinuous media clock.
        feed(2, 181000, 3080)
        source += 'if m.clock_jumps!=0||m.packet_pauses!=1||m.frame_pauses!=1 {return 2}\n'
        source += 'm=rtsp.monitor.create()\n'
        # Exact header values observed on the camera: adjacent seq, 42 ms apart.
        feed(36917, 2377562238, 1000)
        feed(36918, 4293749047, 1042)
        source += 'if m.clock_jumps!=1||m.sequence_events!=0 {return 3}\n'
        # Repeated jumps continue counting while event lines are suppressed.
        for i in range(10):
            feed(36919+i, 2377562238 if i % 2 == 0 else 4293749047, 1043+i)
        source += 'if m.clock_jumps!=11||m.suppressed!=10 {return 4}\n'
        feed(7, 42, 1055, ssrc=888)
        source += 'if m.source_changes!=1||m.sequence_events!=0||m.clock_jumps!=11 {return 5}\n'
        source += 'bridge.rejected=1;bridge.send_errors=1\n'
        feed(9, 43, 1100, ssrc=888, valid=False)
        source += 'if m.sequence!=7||m.rejected!=1||m.send_errors!=1 {return 6}\n'
        feed(9, 3642, 1200, ssrc=888)
        source += '''if m.sequence_events!=1 {return 7}
a=rtsp.monitor.tick(borrow mut m,1000);b=rtsp.monitor.tick(borrow mut m,2000)
if m.loop_stalls!=1||m.max_loop_gap!=1000 {return 8}
s=rtsp.monitor.summary(m,bridge,0)
return 0
}'''
        with tempfile.TemporaryDirectory(prefix='liza-rtsp-monitor-') as folder:
            root = Path(folder)
            shutil.copytree(ROOT/'examples', root/'project')
            entry = root/'project/probe.liza'
            entry.write_text(source)
            for opt in ('0', '2'):
                with self.subTest(opt=opt):
                    out = root/opt
                    out.mkdir()
                    exe = build(entry, out, opt, root/'project')
                    result = subprocess.run([str(exe)], capture_output=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    log = result.stderr
                    self.assertEqual(log.count(b'clock_jump '), 1, log)
                    self.assertIn(b'delta_ticks=1916186809', log)
                    self.assertIn(b'prev_ts=2377562238', log)
                    self.assertIn(b'rejected_packet send_error', log)
                    self.assertIn(b'clock_jumps=11 source_changes=1', log)
                    self.assertLess(len(log), 2500)
