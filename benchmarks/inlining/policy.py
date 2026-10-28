"""Research-only policies; no library names and no production backend changes."""
import json
import re

MAX_TEXT_GROWTH = 1.25
MAX_FRAME_GROWTH = 2
MIN_FRAME_BUDGET = 256
STRATEGIES = {'default': [], **{f'cost-{n}': ['-mllvm', f'-inline-threshold={n}', '-mllvm', '-inline-max-stacksize=256'] for n in (400,600,3000)},
              'guided': ['-mllvm','-inlinehint-threshold=600','-mllvm','-inline-max-stacksize=256'],
              'excessive': ['-mllvm','-inline-threshold=50000']}


def acyclic(blocks):
    def flatten(items):
        for item in items:
            if isinstance(item,list): yield from flatten(item)
            else: yield item
    edges = {b['name']: list(flatten(b['terminator']['args'])) for b in blocks}
    active, done = set(), set()
    def visit(n):
        if n in active: return False
        if n in done: return True
        active.add(n)
        for target in edges[n]:
            if isinstance(target,str) and target in edges and not visit(target): return False
        active.remove(n); done.add(n)
        return True
    return all(visit(n) for n in edges)


def guided(ir, semantic):
    """Hint small pure acyclic functions; LLVM still chooses whether to inline."""
    selected = []
    called = {o["callee"] for f in semantic["functions"] for b in f["blocks"] for o in b["operations"] if o["op"]=="call"}
    for f in semantic['functions']:
        if f['name'] not in called: continue
        ops = [o for b in f['blocks'] for o in b['operations']]
        if f['effect_contract'] != 'pure' or len(ops)>160 or len(f['blocks'])>64 or not acyclic(f['blocks']): continue
        # Exclude direct or indirect recursion conservatively through call closure.
        functions = {x['name']:x for x in semantic['functions']}
        def reaches(name, seen):
            if name==f['name']: return True
            if name in seen or name not in functions: return False
            seen.add(name)
            return any(reaches(o['callee'],seen) for b in functions[name]['blocks'] for o in b['operations'] if o['op']=='call')
        if any(reaches(o['callee'],set()) for o in ops if o['op']=='call'): continue
        name = 'liza_'+f['name']
        pattern = r'(?m)^(define [^\n]*@'+re.escape(name)+r'\([^\n]*) \{$'
        ir, count = re.subn(pattern,r'\1 inlinehint {',ir)
        if count != 1: raise ValueError('missing/ambiguous LLVM definition: '+name)
        selected.append(name)
    return ir,selected


def decision(default, candidate):
    reasons=[]
    if candidate['text_bytes'] > default['text_bytes']*MAX_TEXT_GROWTH:
        reasons.append('text_growth')
    # Compare every frame by identity, not just the largest frame in the module.
    for name,size in candidate['frames'].items():
        if size>max(MIN_FRAME_BUDGET,MAX_FRAME_GROWTH*default['frames'].get(name,0)):
            reasons.append('stack_growth:'+name)
    return {'accepted':not reasons,'reasons':reasons,'fallback':'default' if reasons else None}
