#!/usr/bin/env python3
"""Separate untimed macOS sample profiles, after run.py has finished."""
import argparse
import json
from pathlib import Path
import subprocess
from run import base

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--results', type=Path, required=True)
a = p.parse_args()
out = a.results.resolve()
r = json.loads((out/'report.json').read_text())
if r['status'] != 'measured':
    p.error('completed measurements required')
for label, exe in [('M0',out/'M0/O2'), ('rust',out/'reference/rust')]:
    target = out/(label+'.sample.txt')
    if target.exists():
        p.error('refusing to overwrite profile')
    corpus = next(c for c in r['commands'] if len(c)>3 and c[1]=='bench' and c[2].endswith('bench-ascii.json'))[2]
    cmd = [str(exe),'bench',corpus,'2048','16000']
    with (out/(label+'.profile-bench.json')).open('w') as f:
        process = subprocess.Popen(cmd, stdout=f)
        try:
            sample = ['sample',str(process.pid),'5','1','-file',str(target)]
            result = subprocess.run(sample, capture_output=True, text=True, timeout=30)
            (out/(label+'.sample-command.json')).write_text(json.dumps({'benchmark':cmd,'sample':sample,'stdout':result.stdout,'stderr':result.stderr,'returncode':result.returncode},indent=2)+'\n')
            code = process.wait(timeout=120)
            if result.returncode or code:
                raise RuntimeError((label,result.returncode,code))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
    measurement = json.loads((out/(label+'.profile-bench.json')).read_text())
    if measurement['status'] or measurement['checksum'] != 16001*Path(corpus).stat().st_size:
        raise ValueError('profile result mismatch')
manifest = {f.name:base.digest(f) for f in out.glob('*.sample*')}
manifest.update({f.name:base.digest(f) for f in out.glob('*.profile-bench.json')})
manifest['profile.py'] = base.digest(__file__)
(out/'profile-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
