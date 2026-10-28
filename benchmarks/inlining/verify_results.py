#!/usr/bin/env python3
"""Check recorded gate decisions, actual fallback objects and growth control."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
from policy import decision


def verify(report,root):
    for unit,variants in report['builds'].items():
        for variant,metrics in variants.items():
            expected=decision(variants['default'],metrics)
            actual=report['gates'][unit][variant]
            for key in ('accepted','reasons','fallback'):
                if actual[key]!=expected[key]:raise ValueError('incorrect gate: '+unit+'/'+variant)
            selected=root/unit/variant/'selected.o'
            source=root/unit/(variant if expected['accepted'] else 'default')/'module.o'
            if selected.read_bytes()!=source.read_bytes():raise ValueError('fallback bytes differ')
            if hashlib.sha256(selected.read_bytes()).hexdigest()!=actual['selected_object_sha256']:raise ValueError('hash differs')
    if report['gates']['growth']['cost-3000']['accepted']:raise ValueError('growth control not rejected')
    if report['builds']['growth']['cost-3000']['text_bytes'] < 10*report['builds']['growth']['default']['text_bytes']:
        raise ValueError('stress did not exercise substantial growth')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('output',type=Path);a=p.parse_args()
    r=json.loads((a.output/'report.json').read_text());verify(r,a.output)
    mutant=copy.deepcopy(r);mutant['gates']['growth']['cost-3000']['accepted']=True
    try:verify(mutant,a.output)
    except ValueError:pass
    else:raise ValueError('disabled gate mutant escaped detection')
    print('All selected objects verified; growth and disabled-gate negative controls detected.')
