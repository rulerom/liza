"""Linear resource obligations on normal control-flow exits.

Existing availability analysis also checks copyable values. This pass adds
explicit transfers and no implicit dropping of File-containing variants.
Loops must preserve outer obligations on every backedge; joins must agree.
"""
from .frontend import CompileError, Conditional, While, LoopControl, Match


def check_resources(fn, types, match_types, structs, signatures):
    if fn.trusted_library:
        return  # Audited library adapters alone can handle invalid raw handles.

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

    def expr(node, state):
        t = types[id(node)]
        if node.kind == 'name' and resource(t):
            fail(node.token, 'resource transfer requires explicit move')
        if node.kind == 'copy' and resource(t):
            fail(node.token, 'resource values cannot be copied')
        if node.kind == 'move' and resource(t):
            name = node.args[0].token.text
            if not state.get(name, False):
                fail(node.token, 'use after move: resource is not available')
            state[name] = False
            return
        if node.kind == 'binary' and node.token.text in ('&&', '||'):
            expr(node.args[0], state)
            right = state.copy()
            expr(node.args[1], right)
            state.update(merge([state, right], node.token))
            return
        if node.kind == 'call' and node.token.text in signatures:
            borrowed = signatures[node.token.text].borrowed_params
            for i, arg in enumerate(node.args):
                if i in borrowed:
                    if arg.kind != 'name':
                        fail(arg.token, 'borrowed resource argument must be an available binding, without move')
                    if not state.get(arg.token.text, False):
                        fail(arg.token, 'cannot borrow resource after move or close')
                else:
                    expr(arg, state)
            return
        for arg in node.args:
            expr(arg, state)

    def scoped(body, state, keep, loops, token):
        result = statements(body, state.copy(), loops)
        if result is not None:
            discharged(result, result.keys()-keep, token)
            return {n:result[n] for n in keep}
        return None

    def statements(body, state, loops):
        for stmt in body:
            outer = set(state)
            if isinstance(stmt, Conditional):
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

    initial = {p.text:True for p,t in fn.params if resource(t)}
    scoped(fn.body, initial, set(), [], fn.name)
