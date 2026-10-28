#!/usr/bin/env python3
"""Read Mach-O64 object text bytes; distinguish code changes from timing noise."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def text_section(path):
    data=Path(path).read_bytes()
    if struct.unpack_from('<I',data)[0]!=0xfeedfacf:raise ValueError('expected little-endian Mach-O64')
    n=struct.unpack_from('<I',data,16)[0];offset=32
    for _ in range(n):
        cmd,length=struct.unpack_from('<II',data,offset)
        if length<8 or offset+length>len(data):raise ValueError('invalid load command')
        if cmd==0x19:
            count=struct.unpack_from('<I',data,offset+64)[0]
            for i in range(count):
                section=offset+72+80*i
                if section+80>offset+length:raise ValueError('invalid section table')
                if data[section:section+16].rstrip(b'\0')==b'__text' and data[section+16:section+32].rstrip(b'\0')==b'__TEXT':
                    size=struct.unpack_from('<Q',data,section+40)[0];start=struct.unpack_from('<I',data,section+48)[0]
                    if start+size>len(data):raise ValueError('section outside file')
                    return data[start:start+size]
        offset+=length
    raise ValueError('text section missing')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('results',type=Path);a=p.parse_args()
    report=json.loads((a.results/'report.json').read_text());rows={}
    for variant in report['variants']:
        data=text_section(a.results/variant/'O2.o')
        if len(data)!=report['variants'][variant]['text_bytes']:raise ValueError('size disagrees with native size tool')
        rows[variant]={'text_bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
    result={'objects':rows,'inspection_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'alias_matches_default':rows['alias']==rows['default'],
            'alias_cost400_matches_cost400':rows['alias-cost400']==rows['cost400']}
    (a.results/'object-comparison.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
