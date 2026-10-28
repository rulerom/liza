"""A2 research-only acyclic local-slot reuse; not the production optimizer."""
from liza.storage import Analysis, Plan, acyclic, references

def caller_plan(fn, structs, large, variants):
    a=Analysis(fn,structs,large);plan=Plan()
    physical={}
    def root(n):
        while n in physical: n=physical[n]
        return n
    # Calls only. Ordinary updates retain the conservative immutable lowering;
    # owned callee variants contain separately verified destructive transactions.
    for b in fn.blocks:
        for o in b.operations:
            if o.op!='call' or o.callee not in variants: continue
            parameter_index, _=variants[o.callee]
            source=o.args[parameter_index]
            allocation=a.prefix(source)
            if allocation is None: continue
            allocation=root(allocation)
            if allocation in a.params: continue  # borrowed immutable ABI input
            allocation_op=a.ops.get(allocation)
            if allocation_op is None or allocation_op.op not in ('call','phi','struct.construct','array.repeat','array.construct','variant.construct','struct.update','array.update'): continue
            observers=set().union(*(a.roots.get(n,set()) for n in a.after[o.result]-{o.result}))
            if any(root(n)==allocation for n in observers): continue
            # A second argument may observe the same allocation during the call.
            other=set().union(*(a.roots.get(v,set()) for i,v in enumerate(o.args) if i!=parameter_index))
            if any(root(n)==allocation for n in other): continue
            plan.aliases[o.result]=source
            plan.calls[o.result]='__liza_owned_'+o.callee
            physical[o.result]=allocation
            plan.reserve.setdefault(allocation,set()).add(o.type)
    # First local-reuse slice: keep loop and owned-call composition separate.
    # Neither a source-level move nor a dead parameter grants writable storage.
    if acyclic(fn) and not plan.calls:
        physical = {}
        allocations = {'call', 'struct.construct', 'array.repeat', 'array.construct',
                       'variant.construct', 'struct.update', 'array.update'}
        for chain in a.transactions():
            end = chain[-1]
            allocation = a.prefix(end.args[0])
            if allocation is None:
                continue
            allocation = root(allocation)
            if allocation in a.params:
                continue
            source_op = a.ops.get(allocation)
            if source_op is None or source_op.op not in allocations:
                continue
            produced = {o.result for o in chain}
            observers = set().union(*(a.roots.get(n, set())
                                      for n in a.after[end.result] - produced))
            if any(root(n) == allocation for n in observers):
                continue
            for op in chain:
                plan.aliases[op.result] = op.args[0]
                plan.inplace.add(op.result)
                physical[op.result] = allocation
            plan.rebuilt.update(op.result for op in chain[1:])
        # Distinct SSA allocations may share an entry-block slot only when their
        # backing roots never coexist, including during copies and calls. Phi
        # slots and owned-call reserves are deliberately outside this first slice.
        candidates = {o.result for o in a.ops.values()
                      if large(o.type) and o.op in allocations and o.result not in plan.aliases}
        interference = {n: set() for n in candidates}
        for op in a.ops.values():
            live = (a.after[op.result] - {op.result}) | references(op, set(a.types)) | {op.result}
            roots = {root(r) for n in live for r in a.roots.get(n, set())} & candidates
            for n in roots:
                interference[n].update(roots - {n})
        slots = []
        for name in sorted(candidates):
            for owner, members in slots:
                if a.types[name] == a.types[owner] and not (interference[name] & members):
                    plan.aliases[name] = owner
                    members.add(name)
                    break
            else:
                slots.append((name, {name}))
    return plan
