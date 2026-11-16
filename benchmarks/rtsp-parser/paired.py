"""macOS whole-process A/B diagnostics against one unchanged RTSP camera.

Credentials remain in a temporary 0600 config. No media capture, code edits,
rebuilds or concurrent publishers occur during a series. Local sends are not
delivery counters; camera pacing is observed rather than controlled.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import statistics
import subprocess
import sys
import tempfile
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def parse(stdout, stderr):
    found = re.search(r'RTP received=(\d+) attempted=(\d+) succeeded=(\d+) gated=(\d+) discontinuities=(\d+)', stdout)
    usage = re.search(r'([\d.]+) real\s+([\d.]+) user\s+([\d.]+) sys', stderr)
    rss = re.search(r'(\d+)\s+maximum resident set size', stderr)
    if not found or not usage or not rss:
        raise ValueError('missing counters or native time statistics')
    row = dict(zip(('received', 'attempted', 'succeeded', 'gated', 'discontinuities'), map(int, found.groups())))
    row.update(zip(('wall_s', 'user_s', 'system_s'), map(float, usage.groups())))
    row['rss_bytes'] = int(rss[1])
    row['cpu_s'] = row['user_s'] + row['system_s']
    row['cpu_cores'] = row['cpu_s'] / row['wall_s']
    if row['received'] == 0 or row['succeeded'] == 0:
        raise ValueError('no media publication observed')
    row['input_pps'] = row['received'] / row['wall_s']
    row['cpu_us_per_input'] = 1e6 * row['cpu_s'] / row['received']
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--candidate', required=True, type=Path)
    p.add_argument('--config', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--duration-ms', type=int, default=60000)
    p.add_argument('--pairs', type=int, default=3)
    args = p.parse_args()
    if sys.platform != 'darwin' or not 1000 <= args.duration_ms <= 3600000 or not 1 <= args.pairs <= 20:
        p.error('requires macOS, duration 1000..3600000 ms and 1..20 pairs')
    binaries = {'baseline': args.baseline.resolve(), 'candidate': args.candidate.resolve()}
    hashes = {name: sha(path) for name, path in binaries.items()}
    config = json.loads(args.config.read_text())
    config['run_ms'] = args.duration_ms
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = {'platform': platform.platform(), 'machine': platform.machine(),
              'binary_sha256': hashes, 'harness_sha256': sha(__file__),
              'duration_ms': args.duration_ms, 'pairs': args.pairs, 'runs': []}
    with tempfile.TemporaryDirectory(prefix='liza-rtsp-paired-') as folder:
        private = Path(folder) / 'config.json'
        fd = os.open(private, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, 'w') as file:
            json.dump(config, file)
        for pair in range(args.pairs):
            for name in (('baseline', 'candidate') if pair % 2 == 0 else ('candidate', 'baseline')):
                if sha(binaries[name]) != hashes[name]:
                    raise ValueError('binary changed during the series')
                stem = output / f'{pair+1}-{name}'
                with stem.with_suffix('.stdout').open('wb') as out, stem.with_suffix('.stderr').open('wb') as err:
                    process = subprocess.Popen(['/usr/bin/time', '-l', str(binaries[name]), str(private)],
                                               stdout=out, stderr=err, start_new_session=True)
                    try:
                        code = process.wait(timeout=args.duration_ms / 1000 + 20)
                    except BaseException:
                        os.killpg(process.pid, signal.SIGTERM)
                        try:
                            process.wait(timeout=10)
                        except subprocess.TimeoutExpired:
                            os.killpg(process.pid, signal.SIGKILL)
                            process.wait()
                        raise
                if code != 0 or sha(binaries[name]) != hashes[name]:
                    raise ValueError(f'invalid trial: {pair+1}/{name}, exit={code}')
                row = parse(stem.with_suffix('.stdout').read_text(), stem.with_suffix('.stderr').read_text())
                row.update(pair=pair+1, variant=name)
                report['runs'].append(row)
                (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
                print(json.dumps(row), flush=True)
                time.sleep(1)
    report['medians'] = {name: {key: statistics.median(row[key] for row in report['runs'] if row['variant'] == name)
                               for key in ('cpu_cores', 'cpu_us_per_input', 'input_pps', 'rss_bytes')}
                         for name in binaries}
    (output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report['medians']), flush=True)


if __name__ == '__main__':
    main()
