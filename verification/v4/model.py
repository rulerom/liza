"""Independent resource semantics and finite abstract reachability.

Compiler facts are checked, never used to select executable transitions.
Scalars are abstracted after arithmetic; resource identities remain distinct.
A closed reachable abstract graph is an inductive safety invariant, not a
termination proof. Unsupported transfers and exhausted budgets fail closed.
"""
from ast import literal_eval
from copy import deepcopy
from dataclasses import dataclass, field
import hashlib


class Unsupported(Exception): pass
class Violation(Exception): pass


@dataclass(frozen=True)
class Resource:
    kind: str
    identity: int


@dataclass(frozen=True)
class Variant:
    type: str
    case: str
    payload: object = None


@dataclass(frozen=True)
class Unknown:
    pass


UNKNOWN = Unknown()


def resources(value):
    if isinstance(value, Resource): return [value]
    if isinstance(value, Variant): return resources(value.payload)
    return []


@dataclass
class State:
    values: dict = field(default_factory=dict)
    regions: dict = field(default_factory=dict)
    buffers: dict = field(default_factory=dict)
    labels: dict = field(default_factory=dict)
    aliases: dict = field(default_factory=dict)
    lengths: dict = field(default_factory=dict)
    owned: set = field(default_factory=set)
    next_identity: int = 0
    trace: list = field(default_factory=list)
    coverage: list = field(default_factory=list)
    guards: list = field(default_factory=list)
    summaries: list = field(default_factory=list)
    choices: list = field(default_factory=list)
    visited: set = field(default_factory=set)

    def fresh(self):
        identity = self.next_identity
        self.next_identity += 1
        return identity

    def read(self, name):
        if name not in self.values: raise Violation(f'unavailable value {name}')
        return self.values[name]

    def take(self, name):
        value = self.read(name)
        if resources(value): del self.values[name]
        return value

    def region_guard(self, value):
        for resource in resources(value):
            if resource.kind == 'region' and resource.identity in self.buffers.values():
                raise Violation(f'forbidden region operation: live dependency on R{resource.identity}')

    def origin(self, resource):
        identity = resource.identity if resource.kind == 'region' else self.buffers[resource.identity]
        return self.labels[identity]


def origin_label(raw, audit):
    """Translate published names using the AST/SSA emission correspondence."""
    try:
        origin = literal_eval(raw) if isinstance(raw, str) else raw
        if origin[0] == 'parameter': return ('parameter', int(origin[1]), *origin[2:])
        if origin[0] != 'fresh' or len(origin) not in (3, 4): raise ValueError()
        fn, site = origin[1:3]
        operation = audit[fn]['sites'][site]
        if len(origin) == 3: return ('site', fn, operation)
        return ('call', fn, operation, origin_label(origin[3], audit))
    except (ValueError, SyntaxError, TypeError, KeyError, IndexError):
        raise Unsupported(f'unsupported static origin {raw}') from None


def audit_point(state, audit, operation, phase, function):
    point = audit[function]['points'].get(operation.result, {}).get(phase)
    if point is None:
        if operation.op not in {'variant.tag', 'variant.payload', 'phi'}:
            raise Unsupported(f'missing {phase} observation at {function}:{operation.result}')
        return
    static = {state.aliases.get(origin_label(raw,audit),origin_label(raw,audit))
              for raw in point['dependencies']}
    if phase == 'before' and operation.op in {'move', 'region.close'}:
        for resource in resources(state.read(operation.args[0])):
            if resource.kind == 'region' and state.origin(resource) in static:
                state.guards.append({'function': function, 'point': operation.result,
                                     'reason': 'accepted operation with static dependency'})
    real = {state.origin(r) for r in state.owned if r.kind == 'buffer'}
    if real - static:
        state.coverage.append({'function': function, 'point': operation.result,
                               'phase': phase, 'missing_origins': sorted(map(repr, real-static))})


def summary_check(state, value, description, fn, audit, path=()):
    """Check the selected returned shape, deriving actual origin from execution."""
    if isinstance(value, Variant):
        description = description.get('variants', {}).get(value.case, {})
        return summary_check(state, value.payload, description, fn, audit, path+(value.case,))
    for resource in resources(value):
        key = 'regions' if resource.kind == 'region' else 'depends_on'
        advertised = {state.aliases.get(origin_label(raw,audit),origin_label(raw,audit))
                      for raw in description.get(key, [])}
        if state.origin(resource) not in advertised:
            state.summaries.append({'function': fn, 'reason': 'return origin not covered',
                                    'actual': repr(state.origin(resource)), 'component': key,
                                    'return_path': list(path), 'advertised': sorted(map(repr,advertised))})


def fingerprint(state, block, predecessor):
    """Alpha-renaming live instances is bijective; same-site instances stay distinct."""
    ids = sorted(set(state.regions) | set(state.buffers))
    renaming = {identity: i for i, identity in enumerate(ids)}
    def val(v):
        if isinstance(v, Resource): return (v.kind, renaming.get(v.identity, ('dead', v.identity)))
        if isinstance(v, Variant): return ('variant', v.type, v.case, val(v.payload))
        if isinstance(v, Unknown): return ('scalar-top',)
        return ('scalar', v)
    return repr((block, predecessor, sorted((k, val(v)) for k,v in state.values.items()),
                 sorted((renaming[r], state.regions[r]) for r in state.regions),
                 sorted((renaming[b], renaming[r]) for b,r in state.buffers.items()),
                 sorted((renaming[r], repr(label)) for r,label in state.labels.items() if r in state.regions),
                 sorted(val(r) for r in state.owned)))


class Engine:
    def __init__(self, module, audit, budget, concrete=False, replay=None):
        self.module, self.audit = module, audit
        self.functions = {f.name:f for f in module}
        self.budget, self.concrete, self.replay = budget, concrete, replay
        self.states = 0
        self.unknown, self.violations = [], []
        self.coverage, self.guards, self.summaries = [], [], []
        self.closed_edges = 0
        self.graph = set()
        self.checked_functions = set()
        self.normal_paths = 0

    def collect(self, state):
        self.coverage.extend(state.coverage); state.coverage = []
        self.guards.extend(state.guards); state.guards = []
        self.summaries.extend(state.summaries); state.summaries = []

    def choose(self, state, options, kind):
        position = len(state.choices)
        if self.replay is not None:
            if position >= len(self.replay): raise Unsupported('replay choices exhausted')
            selected = self.replay[position]
            if selected['kind'] != kind or selected['value'] not in options:
                raise Unsupported('concrete replay contradicts abstract path')
            options = [selected['value']]
        for option in options:
            branch = deepcopy(state)
            branch.choices.append({'kind': kind, 'value': option})
            yield option, branch

    def tick(self):
        self.states += 1
        if self.states > self.budget: raise Unsupported('state budget exhausted')

    def operation(self, state, op, fn, stack):
        self.tick()
        supported = {'constant', 'region.create', 'region.alloc', 'move', 'copy',
                     'variant.tag', 'variant.payload', 'variant.construct', 'region.close',
                     'buffer.release', 'call', 'buffer.update', 'buffer.length',
                     'add', 'sub', 'mul', 'eq', 'ne', 'ult', 'ule', 'ugt', 'uge',
                     'slt', 'sle', 'sgt', 'sge'}
        if op.op not in supported: raise Unsupported(f'unsupported operation {op.op}')
        audit_point(state, self.audit, op, 'before', fn.name)
        state.trace.append({'function': fn.name, 'operation': op.op, 'value': op.result})
        args = op.args if op.op == 'constant' else [state.read(a) for a in op.args]
        successors = []
        value = None
        if op.op == 'constant': value = args[0]
        elif op.op in {'region.create', 'region.alloc'}:
            if op.op == 'region.alloc':
                r = args[0]
                if not isinstance(r,Resource) or r.kind != 'region' or r.identity not in state.regions:
                    raise Violation('allocation requires a live region')
            for success, branch in self.choose(state, [False,True], op.op):
                if success:
                    identity = branch.fresh()
                    kind = 'region' if op.op == 'region.create' else 'buffer'
                    payload = Resource(kind,identity)
                    branch.owned.add(payload)
                    if kind == 'region':
                        branch.regions[identity] = (fn.name, op.result)
                        branch.labels[identity] = ('site',fn.name,op.result)
                    else:
                        branch.buffers[identity] = args[0].identity
                        branch.lengths[identity] = args[1]
                else: payload = None
                branch.trace[-1]['outcome'] = 'Ok' if success else 'Err'
                branch.values[op.result] = Variant(op.type,'Ok' if success else 'Err',payload)
                successors.append(branch)
        elif op.op == 'move':
            state.region_guard(args[0]); value = state.take(op.args[0])
        elif op.op == 'copy':
            if resources(args[0]): raise Violation('copy of a linear resource')
            value = args[0]
        elif op.op == 'variant.construct':
            value = Variant(op.type,op.field_name,state.take(op.args[0]) if args else None)
        elif op.op == 'variant.tag':
            v=args[0]
            if not isinstance(v,Variant): raise Unsupported('tag of an unmodeled variant')
            value=next(i for i,(case,_) in enumerate(self.module.variants[v.type].cases) if case==v.case)
        elif op.op == 'variant.payload':
            v=args[0]
            if not isinstance(v,Variant) or v.case!=op.field_name: raise Violation('wrong variant payload')
            state.take(op.args[0]); value=v.payload
        elif op.op in {'region.close','buffer.release'}:
            resource=args[0];kind='region' if op.op=='region.close' else 'buffer'
            if not isinstance(resource,Resource) or resource.kind!=kind: raise Violation('wrong resource kind')
            state.region_guard(resource)
            heap=state.regions if kind=='region' else state.buffers
            if resource.identity not in heap: raise Violation('double close or release')
            del heap[resource.identity]
            if kind=='region': state.labels.pop(resource.identity,None)
            state.lengths.pop(resource.identity,None)
            state.owned.remove(resource);state.take(op.args[0]);value=0
        elif op.op == 'buffer.update':
            # Bounds may trap. Continuing with the same owner overapproximates
            # normal executions; this checker makes no arithmetic/content claim.
            if not isinstance(args[0],Resource) or args[0].kind!='buffer': raise Violation('wrong buffer')
            if self.concrete:
                length=state.lengths[args[0].identity]
                if isinstance(length,Unknown) or isinstance(args[1],Unknown):
                    raise Unsupported('unknown bounds in replay')
                if not 0<=args[1]<length: return []
            value=state.take(op.args[0])
        elif op.op == 'buffer.length':
            value=state.lengths[args[0].identity] if self.concrete else UNKNOWN
        elif op.op == 'call':
            if op.callee not in self.functions: raise Unsupported('external call')
            callee=self.functions[op.callee]
            if op.callee in stack: raise Unsupported('recursive resource call')
            if len(args)!=len(callee.params): raise Unsupported('call arity')
            if any(p.get('mode','value')!='value' for p in callee.params): raise Unsupported('borrowed user parameter')
            for argument in args: state.region_guard(argument)
            passed=[state.take(a) for a in op.args]
            moved={r for v in passed for r in resources(v)}
            state.owned-=moved
            caller_values, caller_owned, caller_labels=deepcopy(state.values),set(state.owned),dict(state.labels)
            caller_aliases=dict(state.aliases)
            child=deepcopy(state);child.values={p['name']:v for p,v in zip(callee.params,passed)}
            child.owned=moved;child.labels={};child.aliases={}
            def bind(v,path):
                if isinstance(v,Variant): bind(v.payload,path+(v.case,))
                for r in ([v] if isinstance(v,Resource) else []):
                    region=r.identity if r.kind=='region' else child.buffers[r.identity]
                    label=('parameter',*path)
                    # Multiple parameters may alias the same region. Track all
                    # parameter names via an independent entry alias map below.
                    canonical=child.labels.setdefault(region,label)
                    child.aliases[label]=canonical
            for i,v in enumerate(passed): bind(v,(i,))
            for returned, result in self.execute(callee,child,stack+(op.callee,)):
                returned_labels=dict(result.labels)
                result.aliases=dict(caller_aliases)
                result.values=deepcopy(caller_values);result.owned=set(caller_owned)|set(resources(returned))
                result.labels={r:l for r,l in caller_labels.items() if r in result.regions}
                for r,label in returned_labels.items():
                    if r in result.regions and r not in result.labels:
                        result.labels[r]=('call',fn.name,op.result,label)
                result.values[op.result]=returned
                successors.append(result)
        else:
            if not self.concrete: value=UNKNOWN
            elif any(isinstance(a,Unknown) for a in args): raise Unsupported('unknown scalar in replay')
            else:
                a,b=args
                opcode=op.op[1:] if op.op[0] in 'us' and op.op not in {'sub'} else op.op
                value={'add':lambda:a+b,'sub':lambda:a-b,'mul':lambda:a*b,
                       'eq':lambda:a==b,'ne':lambda:a!=b,'lt':lambda:a<b,
                       'le':lambda:a<=b,'gt':lambda:a>b,'ge':lambda:a>=b}[opcode]()
                if op.op in {'add','sub','mul'}:
                    width=int(op.type[1:]); signed=op.type.startswith('i')
                    lo=-(1<<(width-1)) if signed else 0;hi=(1<<(width-int(signed)))-1
                    if op.overflow!='trap': raise Unsupported('non-checked arithmetic replay')
                    if not lo<=value<=hi: return []  # trap: no normal successor
        if op.op not in {'region.create','region.alloc','call'}:
            state.values[op.result]=value;successors=[state]
        for successor in successors:
            audit_point(successor,self.audit,op,'after',fn.name)
        return successors

    def execute(self,fn,initial,stack):
        if fn.name not in self.audit: raise Unsupported('missing analyzer observations')
        self.checked_functions.add(fn.name)
        blocks={b.name:b for b in fn.blocks}
        pending=[(fn.blocks[0].name,None,initial)]
        seen=set()
        while pending:
            name,predecessor,state=pending.pop()
            try:
                self.tick()
                # Collect facts before quotienting states: a bad observation
                # must not disappear when the runtime resource state repeats.
                self.collect(state)
                key=fingerprint(state,name,predecessor)
                if self.concrete: key+=repr(sorted(state.lengths.items()))
                digest=hashlib.sha256((fn.name+key).encode()).hexdigest()
                self.graph.add(digest)
                if key in seen:
                    self.closed_edges+=1
                    continue
                seen.add(key)
                block=blocks[name]
                phis=[o for o in block.operations if o.op=='phi']
                selected={o.result:state.read(o.args[o.incoming_blocks.index(predecessor)]) for o in phis}
                consumed=[o.args[o.incoming_blocks.index(predecessor)] for o in phis]
                for source in consumed: state.take(source)
                state.values.update(selected)
                states=[state]
                for op in block.operations:
                    if op.op=='phi': continue
                    following=[]
                    for state in states: following.extend(self.operation(state,op,fn,stack))
                    states=following
                for state in states:
                    term=block.terminator
                    if term.op=='return':
                        value=state.read(term.args[0]);state.region_guard(value)
                        state.take(term.args[0]);state.owned-=set(resources(value))
                        summary_check(state,value,fn.storage_contract.get('returns',{}),fn.name,self.audit)
                        if state.owned: raise Violation('normal exit loses resource obligations')
                        self.collect(state);self.normal_paths+=1
                        yield value,state
                    elif term.op=='jump': pending.append((term.args[0],name,state))
                    elif term.op=='switch':
                        tag=state.read(term.args[0])
                        if isinstance(tag,Unknown): raise Unsupported('unmodeled variant tag')
                        pending.append((dict(term.args[2:]).get(tag,term.args[1]),name,state))
                    elif term.op=='branch':
                        condition=state.read(term.args[0])
                        options=[False,True] if isinstance(condition,Unknown) else [condition]
                        if any(type(x)!=bool for x in options): raise Unsupported('non-boolean condition')
                        for choice,branch in self.choose(state,options,'branch'):
                            pending.append((term.args[1 if choice else 2],name,branch))
                    else: raise Unsupported(f'unsupported terminator {term.op}')
            except (KeyError, IndexError, ValueError) as error:
                self.collect(state);self.unknown.append('malformed or unsupported IR: '+str(error))
            except Unsupported as error:
                self.collect(state);self.unknown.append(str(error))
            except Violation as error:
                self.collect(state)
                self.violations.append({'reason':str(error),'steps':state.trace,'choices':state.choices})


def check(module,audit,entry='main',max_states=10000,*,concrete=False,replay=None):
    report={'status':'unknown','scope':'resource-abstract-reachability','states':0,
            'normal_paths':0,'coverage_failures':[],'guard_failures':[],
            'summary_failures':[],'traces':[],
            'summary_scope': {
                'checked': ['returns provenance on reachable returns',
                            'normal-exit ownership obligations from execution'],
                'not_certified': ['requires', 'consumes', 'effects', 'parameters',
                                  'creation_sites', 'returned_buffer_storage',
                                  'normal_exit annotation', 'trap_cleanup']}}
    engine=Engine(module,audit,max_states,concrete,replay)
    if entry not in engine.functions or entry not in audit:
        report['reason']='missing entry or analyzer observations';return report
    fn=engine.functions[entry]
    if fn.params: report['reason']='entry parameters unsupported';return report
    try:
        for function in module:
            if function.name not in audit: continue
            operations={o.result:o for b in function.blocks for o in b.operations}
            for site in audit[function.name]['sites'].values():
                if site not in operations or operations[site].op not in {'region.create','call'}:
                    raise Unsupported('invalid creation-site correspondence')
        list(engine.execute(fn,State(),(entry,)))
    except Unsupported as error: engine.unknown.append(str(error))
    report.update(states=engine.states,normal_paths=engine.normal_paths,
                  coverage_failures=engine.coverage,guard_failures=engine.guards,
                  summary_failures=engine.summaries,traces=engine.violations,
                  unsupported=sorted(set(engine.unknown)),functions=sorted(engine.checked_functions),
                  closed_edges=engine.closed_edges,abstract_state_hashes=sorted(engine.graph))
    if engine.violations:
        report['status']='model_violation';report['reason']=engine.violations[0]['reason']
        if not concrete:
            reproduced=False
            for trace in report['traces']:
                replayed=check(module,audit,entry,max_states,concrete=True,replay=trace['choices'])
                matches=[t for t in replayed['traces'] if t['reason']==trace['reason']
                         and t['steps'][-1:]==trace['steps'][-1:]]
                trace['reproduced']=bool(matches)
                trace['replay_status']=replayed['status']
                trace['replay_reason']=replayed.get('reason','')
                reproduced |= bool(matches)
            if not reproduced:
                report['status']='unknown'
                report['reason']='abstract counterexample not reproduced concretely'

    elif engine.unknown: report['reason']='; '.join(sorted(set(engine.unknown)))
    elif engine.summaries: report['status']='summary_failure'
    elif engine.guards: report['status']='guard_failure'
    elif engine.coverage: report['status']='coverage_failure'
    else: report['status']='verified_fragment'
    return report
