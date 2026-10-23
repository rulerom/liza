"""Conservative lexical readonly loans, separate from value availability.

Loans survive moving/copying/reassigning a view until their lexical scope ends.
Assigning a view into an outer binding extends the loan to that binding's scope;
its owner must live at least that long. No view can escape a function.
"""
from .frontend import CompileError, Conditional, While, LoopControl, Match, Update, Scope
from .types import is_view


def check_borrows(fn, types, match_types=None, variants=None):
    loans = [set()]
    # name -> (type, declaration depth, possible owner names)
    initial = {p.text: (t, 0, set()) for p, t in fn.params}

    def locked(name):
        return any(name in scope for scope in loans)

    def expr(node, env):
        if node.kind == 'name':
            return set(env[node.token.text][2])
        if node.kind == 'move' and locked(node.args[0].token.text):
            raise CompileError(node.token, 'cannot move owner while readonly view is live')
        if node.kind == 'view' or (node.kind == 'call' and node.token.text.startswith('memory$view$')):
            owner = node.args[0].token.text
            loans[-1].add(owner)
            for arg in node.args[1:]:
                expr(arg, env)
            return {owner}
        owners = set()
        for arg in node.args:
            owners.update(expr(arg, env))
        return owners if is_view(types[id(node)]) else set()

    def join(env, paths):
        paths = [p for p in paths if p is not None]
        if not paths:
            return None
        return {name: (t, depth, set().union(*(p[name][2] for p in paths)))
                for name, (t, depth, _) in env.items()}

    def scoped(body, env):
        loans.append(set())
        result = statements(body, env.copy())
        loans.pop()
        return result

    def statements(body, env):
        for stmt in body:
            if isinstance(stmt, Scope):
                env = join(env, [scoped(stmt.body, env)])
            elif isinstance(stmt, Conditional):
                expr(stmt.condition, env)
                env = join(env, [scoped(stmt.then_body, env), scoped(stmt.else_body, env)])
            elif isinstance(stmt, Match):
                expr(stmt.expr, env)
                cases = dict(variants[match_types[id(stmt)]].cases)
                paths = []
                for arm in stmt.arms:
                    branch = env.copy()
                    if arm.binding and arm.binding.text != '_':
                        branch[arm.binding.text] = (cases[arm.case.rsplit('.',1)[-1]], len(loans), set())
                    paths.append(scoped(arm.body, branch))
                env = join(env, paths)
            elif isinstance(stmt, While):
                # Outer-scope loans may be acquired by an assignment in the
                # body. Revisit until they stabilize to check the next iteration.
                while True:
                    before = [set(s) for s in loans]
                    expr(stmt.condition, env)
                    end = scoped(stmt.body, env)
                    merged = join(env, [env, end])
                    changed = before != loans or merged != env
                    env = merged
                    if not changed:
                        break
            elif isinstance(stmt, LoopControl):
                return env
            elif isinstance(stmt, Update):
                if locked(stmt.token.text):
                    raise CompileError(stmt.token, 'cannot update owner while readonly view is live')
                expr(stmt.target, env)
                expr(stmt.expr, env)
                if locked(stmt.token.text):
                    raise CompileError(stmt.token, 'cannot update owner while readonly view is live')
            else:
                owners = expr(stmt.expr, env)
                if stmt.is_return:
                    return None
                name = stmt.token.text
                if name in env and locked(name):
                    raise CompileError(stmt.token, 'cannot reassign owner while readonly view is live')
                t = types[id(stmt.expr)]
                depth = env[name][1] if name in env else len(loans)-1
                if is_view(t):
                    if any(env[owner][1] > depth for owner in owners):
                        raise CompileError(stmt.token, 'view escapes owner lifetime')
                    loans[depth].update(owners)
                env[name] = (t, depth, owners)
            if env is None:
                return None
        return env

    statements(fn.body, initial)
