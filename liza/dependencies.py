"""Storage provenance, separate from availability and linear obligations.

Origins denote abstract instances, not source binding names. A creation site may
be reused only after iteration-local obligations end; loop-carried provenance
must remain invariant. Call sites freshen factory origins. Variant payloads
retain conditional dependencies until match refines the selected alternative.
"""
from dataclasses import dataclass, field
from .frontend import CompileError, Conditional, While, LoopControl, Match, Update, Scope, Destructure
from .types import is_buffer, is_view, is_vec, is_product, product_args


@dataclass(eq=True)
class Value:
    regions: frozenset = frozenset()
    buffers: frozenset = frozenset()
    cases: dict = field(default_factory=dict)
    components: tuple = ()

    def __post_init__(self):
        if self.cases and not any(v.all_regions() or v.all_buffers() for v in self.cases.values()):
            self.cases = {}

    def all_regions(self):
        return self.regions | frozenset(o for v in list(self.cases.values())+list(self.components) for o in v.all_regions())

    def all_buffers(self):
        return self.buffers | frozenset(o for v in list(self.cases.values())+list(self.components) for o in v.all_buffers())

    def map(self, substitution):
        return Value(frozenset(x for o in self.regions for x in [substitution(o)] if x is not None),
                     frozenset(x for o in self.buffers for x in [substitution(o)] if x is not None),
                     {k:v.map(substitution) for k,v in self.cases.items()},
                     tuple(v.map(substitution) for v in self.components))

    def describe(self):
        return {'regions':sorted(map(str,self.regions)), 'depends_on':sorted(map(str,self.buffers)),
                'variants':{k:v.describe() for k,v in self.cases.items()},
                'components':[v.describe() for v in self.components]}


EMPTY = Value()


def check_dependencies(records, structs, signatures, audit=None, expression_maps=None):
    """Analyze records; optional audit publishes facts at expression checkpoints.

    records maps function names to (AST, expression types, match types, IR).
    expression_maps supplies the lowering correspondence only when auditing.
    Audit data is evidence for a separate checker, never input to decisions.
    """
    summaries, active = {}, set()

    def shape(t, origin):
        if t == 'memory.Region': return Value(regions=frozenset([origin]))
        if is_product(t): return Value(components=tuple(shape(c,origin+(i,)) for i,c in enumerate(product_args(t))))
        if is_buffer(t) or is_vec(t): return Value(buffers=frozenset([origin]))
        if t in structs and not structs[t].properties['copyable']:
            return Value(components=tuple(shape(c,origin+(i,)) for i,(_,c) in enumerate(structs[t].fields)))
        if t in structs.variants:
            return Value(cases={k:shape(v,origin+(k,)) if v else EMPTY
                                for k,v in structs.variants[t].cases})
        return EMPTY

    def join_value(values, token):
        if not values: return EMPTY
        first=values[0]
        if first.components:
            if any(len(v.components) != len(first.components) for v in values):
                raise CompileError(token, 'incompatible product dependency shapes')
            return Value(components=tuple(join_value([v.components[i] for v in values],token) for i in range(len(first.components))))
        if any(v != first for v in values[1:]):
            # Empty/nonempty alternatives are represented within the variant,
            # not by guessing equality of unrelated origins at a phi.
            if all(not v.regions and not v.buffers for v in values):
                keys=set().union(*(v.cases for v in values))
                return Value(cases={k:join_value([v.cases[k] for v in values if k in v.cases],token) for k in keys})
            raise CompileError(token,'ambiguous storage origin at control-flow join')
        return first

    def analyze(name):
        try:
            return analyze_body(name)
        except CompileError as error:
            chain=records[name][0].instantiation_chain if name in records else []
            raise signatures.monomorphizer.trace(error,chain) from None

    def analyze_body(name):
        if name in summaries: return summaries[name]
        if name not in records: return EMPTY
        fn,types,match_types,ir=records[name]
        initial={p.text:shape(t,('parameter',str(i))) for i,(p,t) in enumerate(fn.params)}
        if name in active:
            if any(v.all_regions() or v.all_buffers() for v in initial.values()) or shape(fn.result_type,('return',)).all_regions() or shape(fn.result_type,('return',)).all_buffers():
                raise CompileError(fn.name,'recursive storage dependency summaries are not supported yet')
            return EMPTY
        active.add(name)
        returned=[]
        origins=[]
        sites={}
        observation = {'points': {}, 'sites': {}}
        if audit is not None:
            audit[name] = observation
        def capture(node, phase, state, temporary=(), result=None):
            if audit is None or node.kind == 'name': return
            value_id = expression_maps[name].get(id(node))
            if value_id is None: return
            values = list(state.values()) + list(temporary)
            if result is not None: values.append(result)
            observation['points'].setdefault(value_id, {})[phase] = {
                'dependencies': sorted({str(o) for v in values for o in v.all_buffers()}),
                'result': result.describe() if result is not None else None}

        def site(node):
            if id(node) not in sites: sites[id(node)] = str(len(sites))
            if audit is not None:
                observation['sites'][sites[id(node)]] = expression_maps[name][id(node)]
            return sites[id(node)]

        def expression(node,state,temporary=()):
            result = expression_impl(node,state,temporary)
            capture(node, 'after', state, temporary, result)
            return result

        def expression_impl(node,state,temporary=()):
            if node.kind=='name': return state.get(node.token.text,EMPTY)
            if node.kind=='move':
                capture(node, 'before', state, temporary)
                value=state.get(node.args[0].token.text,EMPTY)
                dependencies=frozenset(o for v in list(state.values())+list(temporary) for o in v.all_buffers())
                if value.all_regions() & dependencies:
                    raise CompileError(node.token,'cannot move or close region while dependent buffer or Result is live')
                state[node.args[0].token.text]=EMPTY
                return value
            if node.kind=='binary' and node.token.text in ('&&','||'):
                expression(node.args[0],state,temporary)
                right=state.copy();expression(node.args[1],right,temporary)
                state.update(join_states([state,right],set(state),node.token))
                return EMPTY
            arguments=[]
            for arg in node.args:
                arguments.append(expression(arg,state,tuple(temporary)+tuple(arguments)))
            capture(node, 'before', state, tuple(temporary)+tuple(arguments))
            if node.kind=='field' and types[id(node.args[0])] in structs:
                source=structs[types[id(node.args[0])]]
                if not source.properties['copyable']:
                    index=next(i for i,(f,_) in enumerate(source.fields) if f==node.token.text)
                    return arguments[0].components[index] if arguments[0].components else EMPTY
            if node.kind=='variant':
                return Value(cases={node.token.text.rsplit('.',1)[-1]:arguments[0] if arguments else EMPTY})
            if node.kind=='call':
                if node.token.text in structs and not structs[node.token.text].properties['copyable']:
                    return Value(components=tuple(arguments))
                signature=signatures[node.token.text] if node.token.text in signatures else None
                operation=getattr(signature,'memory_operation','')
                if operation=='region.create':
                    origin=('fresh',name,site(node))
                    origins.append({'site':site(node),'kind':'region.create','source':str(node.token)})
                    return Value(cases={'Ok':Value(regions=frozenset([origin])),'Err':EMPTY})
                if operation in ('region.alloc','vec.create'):
                    region=arguments[0].all_regions()
                    if len(region)!=1: raise CompileError(node.token,'allocation requires one proven region origin')
                    return Value(cases={'Ok':Value(buffers=region),'Err':EMPTY})
                if operation == 'vec.reserve':
                    origin = arguments[0].all_buffers()
                    if len(origin) != 1 or origin != arguments[1].all_regions():
                        raise CompileError(node.token, 'vec.reserve requires the vector original region')
                    return Value(components=(arguments[0], EMPTY))
                if operation in ('vec.push','vec.pop','vec.set'): return Value(components=(arguments[0],EMPTY))
                if operation.startswith('vec.'): return EMPTY
                if operation=='buffer.update': return arguments[0]
                if operation in ('region.close','buffer.release','buffer.length','buffer.view'): return EMPTY
                # Audited I/O boundary returns the exact consumed buffer, on Ok and Err.
                # The stream has no region origin; the status contains no resource.
                if node.token.text=='net.read': return Value(components=(arguments[1],EMPTY))
                if node.token.text=='net.reactor_read': return Value(components=(arguments[2],EMPTY))
                result=analyze(node.token.text)
                def substitute(origin):
                    if origin[0]=='parameter':
                        value=arguments[int(origin[1])]
                        for case in origin[2:]:
                            value=value.components[case] if isinstance(case,int) else value.cases.get(case,EMPTY)
                        ids=value.all_regions()|value.all_buffers()
                        if not ids: return None
                        if len(ids)!=1: raise CompileError(node.token,'cannot establish function result storage origin')
                        return next(iter(ids))
                    return ('fresh',name,site(node),repr(origin))
                return result.map(substitute)
            if node.kind=='copy': return arguments[0]
            return EMPTY

        def join_states(paths,keep,token):
            paths=[p for p in paths if p is not None]
            if not paths:return None
            return {k:join_value([p.get(k,EMPTY) for p in paths],token) for k in keep}

        def scoped(body,state,keep,loops):
            end=statements(body,state.copy(),loops)
            return None if end is None else {k:end.get(k,EMPTY) for k in keep}

        def statements(body,state,loops):
            for stmt in body:
                keep=set(state)
                if isinstance(stmt,Destructure):
                    value=expression(stmt.expr,state)
                    for i,token in enumerate(stmt.names):
                        state[token.text]=value.components[i] if value.components else EMPTY
                elif isinstance(stmt,Scope):
                    state=scoped(stmt.body,state,keep,loops)
                elif isinstance(stmt,Conditional):
                    expression(stmt.condition,state)
                    state=join_states([scoped(stmt.then_body,state,keep,loops),scoped(stmt.else_body,state,keep,loops)],keep,stmt.token)
                elif isinstance(stmt,Match):
                    value=expression(stmt.expr,state)
                    paths=[]
                    for arm in stmt.arms:
                        branch=state.copy()
                        if arm.binding and arm.binding.text!='_':
                            branch[arm.binding.text]=value.cases.get(arm.case.rsplit('.',1)[-1],EMPTY)
                        paths.append(scoped(arm.body,branch,keep,loops))
                    state=join_states(paths,keep,stmt.token)
                elif isinstance(stmt,While):
                    entry=state.copy();expression(stmt.condition,state)
                    backs,breaks=[],[]
                    end=scoped(stmt.body,state,keep,loops+[(keep,backs,breaks)])
                    if end is not None:backs.append(end)
                    if any(p != entry for p in backs):
                        raise CompileError(stmt.token,'loop backedge must preserve storage origins; iteration-local regions cannot escape')
                    always=stmt.condition.kind=='bool' and stmt.condition.token.text=='true'
                    state=join_states(breaks+([] if always else [state]),keep,stmt.token)
                elif isinstance(stmt,LoopControl):
                    keep,backs,breaks=loops[-1]
                    (breaks if stmt.token.text=='break' else backs).append({k:state.get(k,EMPTY) for k in keep})
                    return None
                elif isinstance(stmt,Update):
                    expression(stmt.target,state);expression(stmt.expr,state)
                else:
                    value=expression(stmt.expr,state)
                    if stmt.is_return:
                        if any(o[0]!='parameter' for o in value.all_buffers()):
                            raise CompileError(stmt.token,'buffer cannot escape its locally owned region')
                        returned.append(value)
                        return None
                    state[stmt.token.text]=value
                if state is None:return None
            return state

        statements(fn.body,initial.copy(),[])
        result=join_value(returned,fn.name)
        summaries[name]=result
        active.remove(name)
        storage_effects = sorted({op.op for block in ir.blocks for op in block.operations if op.op.startswith(('region.','buffer.','vec.'))})
        ir.storage_contract={'requires':['available owned arguments', 'no readonly loans on consumed buffers', 'no dependent values on consumed regions'],
                             'consumes':[p.text for i,(p,t) in enumerate(fn.params) if i not in fn.readonly_params and (shape(t,('p',)).all_regions() or shape(t,('p',)).all_buffers())],
                             'effects':storage_effects,
                             'returned_buffer_storage':'preserved',
                             'parameters':{k:v.describe() for k,v in initial.items()},
                             'returns':result.describe(),'creation_sites':origins,
                             'normal_exit':'all resource obligations discharged',
                             'trap_cleanup':'not guaranteed'}
        if fn.mutable_params:
            ir.storage_contract['mutable_parameters']=[fn.params[i][0].text for i in fn.mutable_params]
            ir.storage_contract['requires'].append('exclusive call-scoped access to each mutable parameter storage')
        if fn.readonly_params:
            ir.storage_contract['requires'][0]='available arguments with their declared access modes'
            ir.storage_contract['requires'].append('readonly access to each readonly parameter and its reachable storage')
            ir.storage_contract['readonly_parameters']=[fn.params[i][0].text for i in fn.readonly_params]
        return result

    for name in records:analyze(name)
    changed=True
    while changed:
        changed=False
        for _,_,_,ir in records.values():
            effects=set(ir.storage_contract['effects'])
            for block in ir.blocks:
                for op in block.operations:
                    if op.op=='call' and op.callee in records:
                        effects.update(records[op.callee][3].storage_contract['effects'])
            if effects != set(ir.storage_contract['effects']):
                ir.storage_contract['effects']=sorted(effects);changed=True

    for _,_,_,ir in records.values():
        if 'vec.reserve' in ir.storage_contract['effects']:
            ir.storage_contract['returned_buffer_storage'] = 'may_relocate_within_origin'
