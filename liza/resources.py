"""Linear resource obligations on normal control-flow exits.

Existing availability analysis also checks copyable values. This pass adds
explicit transfers and no implicit dropping of resource aggregates.
Loops must preserve outer obligations on every backedge; joins must agree.
"""
from .types import consumed_components
from .readonly import readonly_root, projection_root
from .frontend import CompileError, Conditional, While, LoopControl, Match, Update, Scope, Destructure


def check_resources(fn, types, match_types, structs, signatures):
    if fn.trusted_library:
        return  # Audited library adapters alone can handle invalid raw handles.

    readonly_names = {fn.params[i][0].text for i in fn.readonly_params}

    def resource(t):
        return t is not None and not structs.ensure(t)['copyable']

    def fail(token, message):
        raise CompileError(token, message)

    def discharged(state, names, token):
        live = sorted(n for n in names if state[n])
        if live:
            fail(token, 'resource must be closed or transferred before exit: '+', '.join(live))

    def merge(paths, token):
        paths = [p for p in paths if p is not None]
        if not paths:
            return None
        if any(p != paths[0] for p in paths[1:]):
            fail(token, 'resource ownership must agree on every continuing path')
        return paths[0].copy()

    def expr(node, state, active_borrows=frozenset(), active_readonly=frozenset()):
        t = types[id(node)]
        root = readonly_root(node, readonly_names)
        if node.kind == 'field' and root is not None:
            if resource(t):
                fail(node.token, 'readonly resource projection cannot become an owned value')
            return  # Copyable field snapshot; privacy and path types were checked.
        if node.kind == 'name' and resource(t):
            if root is not None:
                fail(node.token, 'readonly parameter cannot become an owned value')
            fail(node.token, 'resource transfer requires explicit move')
        if node.kind in ('copy','move') and readonly_root(node.args[0],readonly_names):
            if resource(types[id(node.args[0])]):
                fail(node.token, 'cannot copy or move a readonly resource')
        if node.kind == 'copy' and resource(t):
            fail(node.token, 'resource values cannot be copied')
        if node.kind == 'move' and resource(t):
            name = node.args[0].token.text
            if name in active_borrows:
                fail(node.token, 'cannot transfer resource while borrowed by an earlier argument')
            if not state.get(name, False):
                fail(node.token, 'use after move: resource is not available')
            state[name] = False
            return
        if node.kind == 'binary' and node.token.text in ('&&', '||'):
            expr(node.args[0], state, active_borrows, active_readonly)
            right = state.copy()
            expr(node.args[1], right, active_borrows, active_readonly)
            state.update(merge([state, right], node.token))
            return
        if node.kind == 'call' and node.token.text in signatures:
            signature = signatures[node.token.text]
            borrowed = set(signature.borrowed_params) | set(signature.readonly_params)
            observing = set(signature.readonly_params) | set(signature.readonly_borrowed_params)
            pending_borrows = set(active_borrows)
            pending_readonly = set(active_readonly)
            for i, arg in enumerate(node.args):
                if i in borrowed:
                    ro = readonly_root(arg,readonly_names)
                    name = projection_root(arg)
                    if arg.kind != 'name' and ro is None:
                        fail(arg.token, 'borrowed resource argument must be an available binding, without move')
                    if ro is not None and i not in observing:
                        fail(arg.token, 'operation has no readonly permission for this resource')
                    if name in pending_readonly and i not in observing:
                        fail(arg.token, 'cannot mutate resource while readonly borrow is active')
                    if ro is None and not state.get(name, False):
                        fail(arg.token, 'cannot borrow resource after move or close')
                    pending_borrows.add(name)
                    if i in observing:
                        pending_readonly.add(name)
                else:
                    expr(arg, state, pending_borrows, pending_readonly)
            return
        for arg in node.args:
            expr(arg, state, active_borrows, active_readonly)

    def scoped(body, state, keep, loops, token):
        result = statements(body, state.copy(), loops)
        if result is not None:
            discharged(result, result.keys()-keep, token)
            return {n:result[n] for n in keep}
        return None

    def statements(body, state, loops):
        for stmt in body:
            outer = set(state)
            if isinstance(stmt, Destructure):
                expr(stmt.expr, state)
                for token, t in zip(stmt.names, consumed_components(types[id(stmt.expr)], structs)):
                    if resource(t): state[token.text] = True
            elif isinstance(stmt, Scope):
                state = scoped(stmt.body, state, outer, loops, stmt.token)
            elif isinstance(stmt, Conditional):
                expr(stmt.condition, state)
                state = merge([scoped(stmt.then_body, state, outer, loops, stmt.token),
                               scoped(stmt.else_body, state, outer, loops, stmt.token)], stmt.token)
            elif isinstance(stmt, Match):
                expr(stmt.expr, state)
                cases = dict(structs.variants[match_types[id(stmt)]].cases)
                paths = []
                for arm in stmt.arms:
                    branch = state.copy()
                    payload = cases[arm.case.rsplit('.', 1)[-1]]
                    if resource(payload):
                        if arm.binding.text == '_':
                            fail(arm.token, 'resource payload cannot be discarded')
                        branch[arm.binding.text] = True
                    paths.append(scoped(arm.body, branch, outer, loops, arm.token))
                state = merge(paths, stmt.token)
            elif isinstance(stmt, While):
                entry = state.copy()
                condition = state.copy()
                expr(stmt.condition, condition)
                backs, breaks = [], []
                end = scoped(stmt.body, condition, outer,
                             loops+[(outer, backs, breaks)], stmt.token)
                if end is not None:
                    backs.append(end)
                if any(p != entry for p in backs):
                    fail(stmt.token, 'loop backedge must preserve resource ownership; close or restore the resource')
                always = stmt.condition.kind == 'bool' and stmt.condition.token.text == 'true'
                state = merge(breaks+([] if always else [condition]), stmt.token)
            elif isinstance(stmt, LoopControl):
                keep, backs, breaks = loops[-1]
                discharged(state, state.keys()-keep, stmt.token)
                (breaks if stmt.token.text == 'break' else backs).append({n:state[n] for n in keep})
                return None
            elif isinstance(stmt, Update):
                if stmt.token.text in readonly_names:
                    fail(stmt.token, 'cannot update readonly parameter')
                expr(stmt.target, state)
                expr(stmt.expr, state)
            else:
                expr(stmt.expr, state)
                if stmt.is_return:
                    discharged(state, state.keys(), stmt.token)
                    return None
                if resource(types[id(stmt.expr)]):
                    name = stmt.token.text
                    if state.get(name, False):
                        fail(stmt.token, 'cannot overwrite a live resource; close or transfer it first')
                    state[name] = True
            if state is None:
                return None
        return state

    initial = {p.text:True for i,(p,t) in enumerate(fn.params) if i not in fn.readonly_params and resource(t)}
    scoped(fn.body, initial, set(), [], fn.name)
