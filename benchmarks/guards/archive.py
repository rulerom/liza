#!/usr/bin/env python3
"""Verify a saved P3 evidence archive without executing or extracting its contents."""
import argparse,hashlib,json,tarfile
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);a=p.parse_args()
m=json.loads((a.directory/'manifest.json').read_text());archive=a.directory/'evidence.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()==m['archive_sha256']
seen=set()
with tarfile.open(archive,'r:gz') as tar:
 for member in tar:
  if not member.isfile():raise ValueError('non-regular archive member')
  name=member.name
  if name in seen or name not in m['files']:raise ValueError('unexpected archive member: '+name)
  data=tar.extractfile(member).read();assert hashlib.sha256(data).hexdigest()==m['files'][name],name;seen.add(name)
assert seen==set(m['files'])
assert hashlib.sha256((a.directory/'report.json').read_bytes()).hexdigest()==m['files']['report.json']
print(f'{len(seen)} evidence hashes verified.')
