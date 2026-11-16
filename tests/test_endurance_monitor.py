"""External observer: PID reuse and clock/counter resets must not fake evidence."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools import monitor_rtsp_endurance as monitor


class EnduranceMonitor(unittest.TestCase):
    def snapshot(self):
        return monitor.parse_ps('26472 07:00:45 89:35.90 20.8 6944 S+ '
                                'Mon Nov 16 12:15:33 2026 /tmp/connector /tmp/private.json')

    def test_kernel_formats(self):
        self.assertEqual(monitor.seconds('1-00:00:01'), 86401)
        data = self.snapshot()
        self.assertEqual(data['uptime_s'], 25245)
        self.assertAlmostEqual(data['cpu_s'], 5375.90)
        sockets = monitor.parse_sockets('p26472\nfcwd\nftxt\nf0\nf1\nf2\nf3\nPUDP\nf4\nPTCP\nTST=ESTABLISHED\n')
        self.assertEqual(sockets, dict(open_fds=5, tcp_sockets=1, tcp_established=1, udp_sockets=1))
        self.assertEqual(monitor.parse_network('connector.264720,9,9\nconnector.26472,123,456\n', 26472),
                         dict(bytes_in=123, bytes_out=456))

    def test_clock_and_counter_resets(self):
        previous = dict(sample_epoch_s=100, cpu_s=10, bytes_in=900, bytes_out=200)
        current = dict(sample_epoch_s=110, cpu_s=12, bytes_in=100, bytes_out=400)
        result = monitor.interval_metrics(previous, current)
        self.assertAlmostEqual(result['cpu_interval_cores'], .2)
        self.assertNotIn('bytes_in_per_s', result)
        self.assertEqual(result['bytes_out_per_s'], 20)
        self.assertFalse(monitor.interval_metrics(current, previous)['interval_valid'])

    def test_reused_pid_during_collection_discards_sample(self):
        first = self.snapshot()
        replacement = dict(first, start_identity='Tue Nov 17 12:15:33 2026')
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'connector'
            binary.write_bytes(b'fixture')
            first['command_identity'] = str(binary) + ' /tmp/private.json'
            replacement['command_identity'] = first['command_identity']
            output = Path(directory) / 'observation'
            with patch.object(monitor, 'process', side_effect=[dict(first), dict(first), replacement]), \
                 patch.object(monitor, 'run', side_effect=['f0\n', 'connector.26472,123,456\n']), \
                 patch.object(monitor.time, 'sleep') as sleep:
                summary = monitor.observe(26472, binary, output)
            self.assertEqual(summary['status'], 'process_changed_during_sample')
            self.assertEqual(summary['samples'], 0)
            self.assertFalse((output / 'samples.jsonl').exists())
            sleep.assert_not_called()

    def test_target_uptime_finishes_observer_without_stopping_target(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / 'connector'
            binary.write_bytes(b'fixture')
            first = dict(self.snapshot(), command_identity=str(binary))
            with patch.object(monitor, 'process', side_effect=lambda pid: dict(first)), \
                 patch.object(monitor, 'run', side_effect=['f0\n', 'connector.26472,123,456\n']), \
                 patch.object(monitor.time, 'sleep') as sleep, \
                 patch.object(monitor.os, 'kill') as kill:
                output = Path(directory) / 'observation'
                summary = monitor.observe(26472, binary, output, target_uptime_s=first['uptime_s'])
            self.assertEqual(summary['status'], 'target_uptime_reached')
            self.assertEqual(summary['samples'], 1)
            self.assertIsNone(summary['last_sample']['rtp_received'])
            self.assertNotIn('command_identity', summary['last_sample'])
            sleep.assert_not_called()
            kill.assert_not_called()
