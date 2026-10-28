"""Unchanged scalar fields across acyclic value phis (no guard elimination).

Facts describe SSA values, never mutable storage. A fact is rooted in an immutable
by-value parameter and depends only on updates of other fields and agreeing phis.
Every requested (struct, field) walks the CFG once; shared diamonds are not expanded.
"""
from collections import deque
from dataclasses import dataclass, field
from .types import INTEGER_TYPES


@dataclass(frozen=True)
class Fact:
    root: str
    through_phi: bool
    inputs: tuple = ()


@dataclass
class Forwarding:
    roots: dict = field(default_factory=dict)  # projection SSA result -> parameter
    certificates: dict = field(default_factory=dict)  # result -> (type, field, source)
    facts: dict = field(default_factory=dict)  # (type, field) -> value -> Fact
    visits: int = 0


def acyclic_order(fn):
    blocks = {b.name: b for b in fn.blocks}
    successors = {}; incoming = {name: 0 for name in blocks}
    for b in fn.blocks:
        t = b.terminator
        if t is None: return None
        if t.op == 'branch': targets = t.args[1:]
        elif t.op == 'jump': targets = t.args
        elif t.op == 'return': targets = []
        else: return None
        successors[b.name] = set(targets)
        for target in successors[b.name]:
            if target not in blocks: return None
            incoming[target] += 1
    ready = deque(n for n in blocks if incoming[n] == 0); order = []
    while ready:
        name = ready.popleft(); order.append(blocks[name])
        for target in sorted(successors[name]):
            incoming[target] -= 1
            if incoming[target] == 0: ready.append(target)
    return order if len(order) == len(blocks) else None


def analyze(fn, structs, large):
    result = Forwarding()
    if fn.effect_contract != 'pure': return result
    scalars = set(INTEGER_TYPES) | {'bool'}
    eligible = {name for name, s in structs.items()
                if s.properties.get('copyable') and 0 < len(s.fields) <= 64
                and all(t in scalars for _, t in s.fields) and not large(name)}
    parameters = {p['name']: p['type'] for p in fn.params
                  if p['type'] in eligible and p.get('mode', 'value') == 'value'}
    if not parameters: return result
    queries = {}
    for b in fn.blocks:
        for op in b.operations:
            if (op.op == 'struct.field' and op.source_type in parameters.values()
                    and dict(structs[op.source_type].fields).get(op.field_name) == op.type):
                queries.setdefault((op.source_type, op.field_name), []).append(op)
    if not queries: return result
    blocks = acyclic_order(fn)
    if blocks is None: return result
    for (ty, field_name), projections in queries.items():
        facts = {name: Fact(name, False) for name, t in parameters.items() if t == ty}
        for b in blocks:
            for op in b.operations:
                result.visits += 1
                if op.type != ty: continue
                if op.op == 'struct.update' and op.field_name != field_name and op.args[0] in facts:
                    parent = facts[op.args[0]]
                    facts[op.result] = Fact(parent.root, parent.through_phi, (op.args[0],))
                elif op.op == 'phi' and op.args and all(a in facts for a in op.args):
                    roots = {facts[a].root for a in op.args}
                    if len(roots) == 1:
                        facts[op.result] = Fact(next(iter(roots)), True, tuple(op.args))
        result.facts[ty, field_name] = facts
        for op in projections:
            source = op.args[0]; fact = facts.get(source)
            if fact is not None and fact.through_phi:
                result.roots[op.result] = fact.root
                result.certificates[op.result] = (ty, field_name, source)
    return result
