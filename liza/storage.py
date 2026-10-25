"""Conservative storage reuse proofs over typed SSA, independent of LLVM layout.

No source move is treated as a uniqueness assertion. Projections/copies/views
keep their backing roots live; phi uses belong to predecessor edges. Owned
callee variants are restricted to acyclic value transformations returning the
input value directly or in the first field of a result record. Direct variants
compose only through already-proven direct callees. Other shapes use the normal
immutable ABI.
"""
from dataclasses import dataclass, field


def successors(block):
    t = block.terminator
    if t.op in ('return', 'unreachable'): return []
    if t.op == 'jump': return [t.args[0]]
    if t.op == 'branch': return t.args[1:]
    if t.op == 'switch': return [t.args[1]] + [x[1] for x in t.args[2:]]
    raise ValueError(t.op)


def references(op, names):
    if op.op in ('constant', 'text.literal'): return set()
    return {a for a in op.args if isinstance(a, str) and a in names}


def liveness(fn):
    """Live SSA names after each instruction, with edge-sensitive phi inputs."""
    names = {p['name'] for p in fn.params} | {o.result for b in fn.blocks for o in b.operations}
    blocks = {b.name:b for b in fn.blocks}
    phis = {b.name:[o for o in b.operations if o.op == 'phi'] for b in fn.blocks}
    live_in = {b.name:set() for b in fn.blocks}
    live_out = {b.name:set() for b in fn.blocks}
    after = {}
    changed = True
    while changed:
        changed = False
        for b in reversed(fn.blocks):
            live = set()
            for target in successors(b):
                live.update(live_in[target] - {o.result for o in phis[target]})
                for op in phis[target]:
                    live.add(op.args[op.incoming_blocks.index(b.name)])
            live_out[b.name] = live.copy()
            t = b.terminator
            if t.op in ('return','branch','switch'):
                live.add(t.args[0])
            for op in reversed(b.operations):
                after[op.result] = live.copy()
                live.discard(op.result)
                if op.op != 'phi': live.update(references(op,names))
            if live != live_in[b.name]:
                live_in[b.name] = live
                changed = True
    return after


def acyclic(fn):
    blocks={b.name:b for b in fn.blocks}; active=set(); done=set()
    def visit(name):
        if name in active: return False
        if name in done: return True
        active.add(name)
        if not all(visit(n) for n in successors(blocks[name])): return False
        active.remove(name); done.add(name)
        return True
    return visit(fn.blocks[0].name)


@dataclass
class Plan:
    # SSA result -> an existing SSA address, or '$return' for an owned variant.
    aliases: dict = field(default_factory=dict)
    inplace: set = field(default_factory=set)
    rebuilt: set = field(default_factory=set)
    calls: dict = field(default_factory=dict)
    reserve: dict = field(default_factory=dict)
    owned_parameter: str = ''
    direct: bool = False


class Analysis:
    def __init__(self, fn, structs, large):
        self.fn, self.structs, self.large = fn, structs, large
        self.ops={o.result:o for b in fn.blocks for o in b.operations}
        self.types={p['name']:p['type'] for p in fn.params}
        self.types.update({o.result:o.type for o in self.ops.values()})
        self.after=liveness(fn)
        self.roots={p['name']:{p['name']} for p in fn.params if large(p['type']) or p['type'].startswith('View<')}
        # Baseline memory roots. Small loaded values are independent; a view or
        # a large projection retains access to the backing root.
        changed=True
        while changed:
            changed=False
            for b in fn.blocks:
                for o in b.operations:
                    roots=set()
                    if o.op in ('copy','move','unpack.consume'):
                        roots=self.roots.get(o.args[0],set()).copy()
                    elif o.op in ('struct.field','variant.payload','array.read','unpack.component') and large(o.type):
                        roots=self.roots.get(o.args[0],set()).copy()
                    elif o.op=='view.create':
                        roots=self.roots.get(o.args[0],set()).copy()
                    elif o.op=='phi' and o.type.startswith('View<'):
                        roots=set().union(*(self.roots.get(a,set()) for a in o.args))
                    elif large(o.type): roots={o.result}
                    if roots != self.roots.get(o.result,set()):
                        self.roots[o.result]=roots;changed=True
        self.params={p['name'] for p in fn.params}

    def canonical(self, name):
        while name in self.ops and self.ops[name].op in ('copy','move','unpack.consume'):
            name=self.ops[name].args[0]
        return name

    def projection(self, name):
        """Address path, used only for equality (never arithmetic on an address)."""
        name=self.canonical(name)
        o=self.ops.get(name)
        if o and o.op=='struct.field' and self.large(o.type):
            root,path=self.projection(o.args[0])
            return root,path+(('field',o.field_name),)
        if o and o.op=='array.read' and self.large(o.type):
            root,path=self.projection(o.args[0])
            return root,path+(('index',self.canonical(o.args[1])),)
        return name,()

    def prefix(self, name):
        """Return the baseline allocation if a value starts at its first byte."""
        name=self.canonical(name);o=self.ops.get(name)
        if o and o.op=='struct.field' and self.large(o.type):
            if self.structs[o.source_type].fields[0][0]!=o.field_name: return None
            return self.prefix(o.args[0])
        if o and o.op in ('array.read','view.read','variant.payload','unpack.component'): return None
        return name

    def transactions(self):
        """Contiguous nested updates form one root-value replacement.

        Rebuilding the parent after writing its child is not an observation of
        the replaced child. Any other interleaved instruction prevents folding.
        """
        for b in self.fn.blocks:
            ops=b.operations;i=0
            while i<len(ops):
                o=ops[i]
                if o.op not in ('struct.update','array.update') or not self.large(o.type):
                    i+=1;continue
                chain=[o];j=i+1
                while j<len(ops):
                    parent=ops[j];child=chain[-1]
                    if parent.op not in ('struct.update','array.update') or not self.large(parent.type): break
                    replacement=parent.args[-1]
                    if self.canonical(replacement)!=child.result: break
                    root,path=self.projection(parent.args[0])
                    step=('field',parent.field_name) if parent.op=='struct.update' else ('index',self.canonical(parent.args[1]))
                    if self.projection(child.args[0]) != (root,path+(step,)): break
                    chain.append(parent);j+=1
                yield chain
                i=j

    def lineage(self, name, parameter, active=None):
        """Whole-value versions derived from the owned parameter, not projections."""
        name=self.canonical(name)
        if name==parameter: return True
        active=set() if active is None else active
        if name in active: return False
        o=self.ops.get(name)
        if o is None: return False
        if o.op in ('struct.update','array.update'):
            return self.lineage(o.args[0],parameter,active|{name})
        if o.op=='phi':
            return all(self.lineage(a,parameter,active|{name}) for a in o.args)
        return False


def owned_variant(fn, structs, large):
    """Prove an acyclic owned variant can return/update its one large argument."""
    params=[p for p in fn.params if large(p['type'])]
    if len(params)!=1 or fn.result_type not in structs or not acyclic(fn): return None
    p=params[0]
    if p.get("mode") == "readonly": return None
    fields=structs[fn.result_type].fields
    if not fields or fields[0][1]!=p['type'] or any(large(t) for _,t in fields[1:]): return None
    if any(x['type'].startswith('View<') for x in fn.params): return None
    a=Analysis(fn,structs,large);plan=Plan(owned_parameter=p['name'])
    returns=[]
    for b in fn.blocks:
        if b.terminator.op!='return': continue
        o=a.ops.get(a.canonical(b.terminator.args[0]))
        if o is None or o.op!='struct.construct' or o.type!=fn.result_type: return None
        if not a.lineage(o.args[0],p['name']): return None
        if o not in b.operations: return None
        tail=b.operations[b.operations.index(o)+1:]
        if any(x.op not in ('copy','move') or a.canonical(x.result)!=o.result for x in tail): return None
        returns.append(o)
    if not returns: return None
    # Parameter-derived whole versions, including phi joins, share the owned
    # allocation only if each destructive transaction has no old observer.
    versions={n for n,t in a.types.items() if t==p['type'] and a.lineage(n,p['name'])}
    version_roots=set().union(*(a.roots.get(n,set()) for n in versions))
    for chain in a.transactions():
        end=chain[-1]
        if not a.lineage(end.args[0],p['name']): return None
        produced={o.result for o in chain}
        old_roots=version_roots-produced
        if any(a.roots.get(n,set()) & old_roots for n in a.after[end.result]): return None
        for o in chain:
            plan.aliases[o.result]=o.args[0]
            plan.inplace.add(o.result)
        plan.rebuilt.update(o.result for o in chain[1:])
    # All nontrivial large operations must belong to this proof or be an output
    # wrapper/projection. Unrelated materialization/calls use the ordinary ABI.
    output_names={o.result for o in returns}
    for o in a.ops.values():
        if large(o.type) and o.op in ('call','array.repeat','array.construct','struct.construct','variant.construct') and o.result not in output_names:
            return None
    for n in versions:
        plan.aliases[n]='$return'
    for o in returns: plan.aliases[o.result]='$return'
    plan.aliases[p['name']]='$return'
    return plan


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
    return plan


def direct_owned_variant(fn, structs, large, variants):
    """Acyclic whole-value transform, composed only with proven owned callees.

    The caller must supply exclusive writable storage. The public immutable ABI
    remains available for parameters, snapshots, projections and other observers.
    """
    params = [p for p in fn.params if large(p['type'])]
    if len(params) != 1 or not acyclic(fn):
        return None
    p = params[0]
    if p.get('mode') == 'readonly' or fn.result_type != p['type']:
        return None
    if any(x['type'].startswith('View<') for x in fn.params):
        return None
    a = Analysis(fn, structs, large)

    def lineage(name, active=frozenset()):
        name = a.canonical(name)
        if name == p['name']:
            return True
        if name in active:
            return False
        op = a.ops.get(name)
        if op is None:
            return False
        active = active | {name}
        if op.op in ('struct.update', 'array.update'):
            return lineage(op.args[0], active)
        if op.op == 'phi':
            return all(lineage(n, active) for n in op.args)
        if op.op == 'call' and op.callee in variants:
            index, child = variants[op.callee]
            return child.direct and lineage(op.args[index], active)
        return False

    returns = [b.terminator.args[0] for b in fn.blocks if b.terminator.op == 'return']
    if not returns or not all(lineage(n) for n in returns):
        return None
    versions = {n for n, t in a.types.items() if t == p['type'] and lineage(n)}
    version_roots = set().union(*(a.roots.get(n, set()) for n in versions))
    plan = Plan(owned_parameter=p['name'], direct=True)

    def observed_after(result, produced):
        old = version_roots - produced
        return any(a.roots.get(n, set()) & old for n in a.after[result])

    for chain in a.transactions():
        end = chain[-1]
        if not lineage(end.args[0]):
            return None
        if observed_after(end.result, {o.result for o in chain}):
            return None
        for op in chain:
            plan.aliases[op.result] = op.args[0]
            plan.inplace.add(op.result)
        plan.rebuilt.update(o.result for o in chain[1:])

    for op in a.ops.values():
        if not large(op.type):
            continue
        if op.op == 'call':
            if not lineage(op.result) or observed_after(op.result, {op.result}):
                return None
            index, _ = variants[op.callee]
            # A second argument can observe a projection even if it is dead
            # after the call. It may not alias the destructively updated root.
            if any(a.roots.get(n, set()) & version_roots
                   for i, n in enumerate(op.args) if i != index):
                return None
            plan.calls[op.result] = '__liza_owned_' + op.callee
        elif op.op in ('array.repeat', 'array.construct', 'struct.construct', 'variant.construct'):
            return None
    for name in versions:
        plan.aliases[name] = '$return'
    plan.aliases[p['name']] = '$return'
    return plan
