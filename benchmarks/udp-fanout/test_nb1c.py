"""Small cross-process native-collector regression."""
from pathlib import Path
import subprocess,sys,tempfile,unittest
import nb1b_build,nb1c
ROOT=Path(__file__).resolve().parents[2]

@unittest.skipIf(sys.platform=='win32','POSIX-only experimental collector')
class NativeCollector(unittest.TestCase):
    def test_clock_accounting_and_byte_delivery(self):
        with tempfile.TemporaryDirectory(prefix='liza-nb1c-test-') as d:
            tmp=Path(d);collector=tmp/'collector';exe=tmp/'liza';folder=tmp/'run';folder.mkdir()
            subprocess.run(['clang','-std=c11','-O2','-Wall','-Wextra','-Werror',str(ROOT/'benchmarks/udp-fanout/nb1c_collector.c'),'-o',str(collector)],check=True)
            nb1b_build.build(ROOT,exe)
            row=nb1c.trial(exe,collector,2,20,100,.1,folder)
            self.assertEqual(row['generator_sent'],20);self.assertEqual(row['fanout']['received'],20)
            self.assertEqual(row['collector_unique'],40);self.assertEqual(row['collector_missing_from_successful_send'],0)
            self.assertEqual(row['collector_invalid'],0);self.assertEqual(row['collector_duplicates'],0)
            self.assertLessEqual(row['generator_finished_ns'],row['phase_command_ns'])
            self.assertLessEqual(row['phase_command_ns'],row['phase_ack_ns'])
            self.assertLessEqual(row['phase_ack_ns'],row['stop_command_ns'])
            self.assertLess(row['latency_percentiles_upper_ms']['p99'],10000)
            self.assertEqual(sum(row['latency_histogram_100us'].values()),40)
            self.assertEqual(len(row['collector_socket_receive_buffers']),2)

if __name__=='__main__':unittest.main()
