"""Observe one existing macOS RTSP process; never signal or restart it.

RTP counters are unavailable live in the frozen binary. Kernel byte counters
are recorded separately and must not be interpreted as packet delivery.
"""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def seconds(value):
    days, clock = value.split('-', 1) if '-' in value else ('0', value)
    parts = list(map(float, clock.split(':')))
    return int(days) * 86400 + sum(n * 60**i for i, n in enumerate(reversed(parts)))


def parse_ps(value):
    parts = value.strip().split(None, 11)
    if not parts:
        return None
    if len(parts) != 12:
        raise ValueError('unexpected ps fields')
    return {'pid': int(parts[0]), 'uptime_s': seconds(parts[1]),
            'cpu_s': seconds(parts[2]), 'cpu_recent_percent': float(parts[3]),
            'rss_bytes': int(parts[4]) * 1024, 'process_state': parts[5],
            'start_identity': ' '.join(parts[6:11]), 'command_identity': parts[11]}


def parse_sockets(value):
    return {'open_fds': sum(bool(line[1:].isdigit()) for line in value.splitlines() if line.startswith('f')),
            'tcp_sockets': value.splitlines().count('PTCP'),
            'tcp_established': value.splitlines().count('TST=ESTABLISHED'),
            'udp_sockets': value.splitlines().count('PUDP')}


def parse_network(value, pid):
    for row in csv.reader(io.StringIO(value)):
        if len(row) >= 3 and row[0].endswith('.' + str(pid)):
            return {'bytes_in': int(row[1]), 'bytes_out': int(row[2])}
    raise ValueError('nettop did not report the target PID')


def run(*args):
    result = subprocess.run(args, env=dict(os.environ, LC_ALL='C', TZ='UTC'),
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(args[0] + ' failed')
    return result.stdout


def process(pid):
    result = subprocess.run(['ps', '-p', str(pid), '-o',
                             'pid=,etime=,time=,pcpu=,rss=,state=,lstart=,command='],
                            env=dict(os.environ, LC_ALL='C', TZ='UTC'),
                            capture_output=True, text=True, timeout=5)
    if result.returncode and not result.stdout.strip():
        return None
    if result.returncode:
        raise RuntimeError('ps failed')
    return parse_ps(result.stdout)


def same_process(first, current):
    return current is not None and all(first[key] == current[key]
        for key in ('pid', 'start_identity', 'command_identity'))


def interval_metrics(previous, current):
    gap = current['sample_epoch_s'] - previous['sample_epoch_s']
    if gap <= 0:
        return {'interval_valid': False}
    cpu = current['cpu_s'] - previous['cpu_s']
    if cpu < 0:
        return {'interval_valid': False}
    result = {'interval_valid': True, 'interval_s': gap, 'cpu_interval_cores': cpu / gap}
    for key in ('bytes_in', 'bytes_out'):
        a, b = previous.get(key), current.get(key)
        if a is not None and b is not None and b >= a:
            result[key + '_per_s'] = (b - a) / gap
    return result


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, indent=2) + '\n')
    temporary.replace(path)


def observe(pid, binary, output, target_uptime_s=86400, interval_s=300, once=False):
    output.mkdir(parents=True, exist_ok=False)
    first = process(pid)
    if first is None:
        raise ValueError('target process is not running')
    if not (first['command_identity'] == str(binary) or first['command_identity'].startswith(str(binary) + ' ')):
        raise ValueError('target command does not match the selected binary')
    metadata = {'observer_pid': os.getpid(), 'target_pid': pid,
                'binary_name': binary.name, 'binary_sha256': hashlib.sha256(binary.read_bytes()).hexdigest(),
                'process_start_utc': first['start_identity'], 'target_uptime_s': target_uptime_s,
                'interval_s': interval_s, 'monitor_started_at_uptime_s': first['uptime_s'],
                'rtp_counters': 'unavailable until normal application shutdown',
                'behavior': 'read only; never signals, stops or restarts the connector'}
    write_json(output / 'metadata.json', metadata)
    summary = dict(metadata, status='observing', samples=0, observed_rss_min_bytes=None,
                   observed_rss_max_bytes=None, max_sample_gap_s=0)
    previous = None
    try:
        while True:
            current = process(pid)
            if current is None:
                summary['status'] = 'process_no_longer_observed'
                break
            if not same_process(first, current):
                summary['status'] = 'process_identity_changed'
                break
            current.pop('command_identity')
            current.pop('start_identity')
            current.update(sample_epoch_s=time.time(), sampled_at_utc=datetime.now(timezone.utc).isoformat(),
                           rtp_received=None, rtp_succeeded=None, rtp_sequence_discontinuities=None, errors=[])
            for action in ('sockets', 'network'):
                try:
                    values = (parse_sockets(run('lsof', '-nP', '-p', str(pid), '-F', 'fPT'))
                              if action == 'sockets' else
                              parse_network(run('nettop', '-P', '-L', '1', '-p', str(pid), '-J', 'bytes_in,bytes_out'), pid))
                    current.update(values)
                except (ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
                    current['errors'].append(action + ': ' + str(error))
            # Do not publish a mixed sample if the process exited/reused its PID
            # while the kernel tools were collecting their individual snapshots.
            if not same_process(first, process(pid)):
                summary['status'] = 'process_changed_during_sample'
                break
            if previous is not None:
                current.update(interval_metrics(previous, current))
                summary['max_sample_gap_s'] = max(summary['max_sample_gap_s'], current.get('interval_s', 0))
            with (output / 'samples.jsonl').open('a') as file:
                file.write(json.dumps(current) + '\n')
            summary['samples'] += 1
            summary.setdefault('first_sample', current)
            summary['last_sample'] = current
            summary['observed_rss_min_bytes'] = min(summary['observed_rss_min_bytes'] or current['rss_bytes'], current['rss_bytes'])
            summary['observed_rss_max_bytes'] = max(summary['observed_rss_max_bytes'] or 0, current['rss_bytes'])
            if current['uptime_s'] >= target_uptime_s:
                summary['status'] = 'target_uptime_reached'
            write_json(output / 'summary.json', summary)
            if once or summary['status'] == 'target_uptime_reached':
                break
            previous = current
            time.sleep(min(interval_s, max(1, target_uptime_s - current['uptime_s'])))
    except KeyboardInterrupt:
        summary['status'] = 'observer_stopped'
    except Exception as error:
        summary['status'] = 'observer_error'
        summary['error'] = str(error)
        raise
    finally:
        write_json(output / 'summary.json', summary)
    return summary


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--target-uptime-seconds', type=int, default=86400)
    parser.add_argument('--interval-seconds', type=int, default=300)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin' or args.pid <= 0 or args.interval_seconds < 5 or args.target_uptime_seconds <= 0:
        parser.error('requires macOS, positive PID/target uptime, and interval >= 5 seconds')
    result = observe(args.pid, args.binary.resolve(), args.output, args.target_uptime_seconds,
                     args.interval_seconds, args.once)
    print(json.dumps({'status': result['status'], 'samples': result['samples']}))
