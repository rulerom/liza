#!/usr/bin/env python3
"""Verify R0 archived or extracted evidence; never execute packaged binaries."""
import argparse,hashlib,json,tarfile
from pathlib import Path

def sha(data):return hashlib.sha256(data).hexdigest()
def verify(root):
 manifest=root/'manifest.json'
 if manifest.exists():
  m=json.loads(manifest.read_text());archive=root/'evidence.tar.gz'
  if sha(archive.read_bytes())!=m['archive_sha256']:raise ValueError('archive hash differs')
  seen=set()
  with tarfile.open(archive) as tar:
   for member in tar:
    if not member.isfile() or member.name in seen or member.name not in m['files']:raise ValueError('unexpected member')
    if sha(tar.extractfile(member).read())!=m['files'][member.name]:raise ValueError('member hash differs')
    seen.add(member.name)
  if seen!=set(m['files']):raise ValueError('missing members')
  if sha((root/'report.json').read_bytes())!=m['files']['report.json']:raise ValueError('public report differs')
  print(len(seen),'archive members verified');return
 r=json.loads((root/'report.json').read_text())
 if r['status']!='functional_reproduction_passed':raise ValueError('run incomplete')
 for name,h in r['artifacts'].items():
  path=(root/name).resolve()
  if not path.is_relative_to(root.resolve()) or sha(path.read_bytes())!=h:raise ValueError('artifact differs: '+name)
 seen=set()
 with tarfile.open(root/'source.tar') as tar:
  for member in tar:
   if member.isdir():continue
   if not member.isfile() or member.name in seen or member.name not in r['source_hashes']:raise ValueError('unexpected source member')
   if sha(tar.extractfile(member).read())!=r['source_hashes'][member.name]:raise ValueError('archived source differs: '+member.name)
   seen.add(member.name)
 if seen!=set(r['source_hashes']):raise ValueError('missing source files')
 if (root/'source').exists():
  for name,h in r['source_hashes'].items():
   path=(root/'source'/name).resolve()
   if not path.is_relative_to((root/'source').resolve()) or sha(path.read_bytes())!=h:raise ValueError('source differs: '+name)
 print(len(r['artifacts']),'artifacts and',len(r['source_hashes']),'source files verified')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);verify(p.parse_args().directory)
