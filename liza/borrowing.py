"""Conservative lexical readonly loans, separate from value availability.

Loans survive moving/copying/reassigning a view until their lexical scope ends.
Assigning a view into an outer binding extends the loan to that binding's scope;
its owner must live at least that long. No view can escape a function.
"""
from dataclasses import dataclass, replace
from .types import consumed_components
from .readonly import projection_root
from .frontend import CompileError, Conditional, While, LoopControl, Match, Update, Scope, Destructure
from .types import is_view


@dataclass(frozen=True)
class Binding:
    type: str
    depth: int
    owners: frozenset
    identity: int
    writable: bool = False
    mode: str = 'value'


def declaration(token, type_name, depth, writable=False, mode='value'):
    # AST declaration objects remain stable while a loop fixed point is visited.
    # IDs are local analysis identities, never serialized or runtime addresses.
    return Binding(type_name, depth, frozenset(), id(token), writable, mode)


def check_borrows(fn, types, match_types=None, variants=None, structs=None, signatures=None):
    loans = [set()]
    signatures = signatures or {}
    active_readers, active_writers = set(), set()
    # Text names only resolve the current lexical environment. Every permission,
    # active loan and retained view root below uses declaration identity.
    initial = {}
    for i, (token, type_name) in enumerate(fn.params):
        mode = 'mutable' if i in fn.mutable_params else 'readonly' if i in fn.readonly_params else 'value'
        binding = declaration(token, type_name, 0, mode=='mutable', mode)
        if is_view(type_name):
            # The external backing is distinct from the movable descriptor.
            binding = replace(binding, owners=frozenset({('view_parameter', binding.identity)}))
        initial[token.text] = binding
    depths = {b.identity:b.depth for b in initial.values()}
    for binding in initial.values():
        for owner in binding.owners:
            depths[owner] = 0

    def locked(identity):
        return any(identity in scope for scope in loans)

    def expr(node, env):
        if node.kind == 'borrow_mut':
            raise CompileError(node.token, 'borrow mut is only allowed for a mutable call argument')
        if node.kind == 'name':
            if env[node.token.text].identity in active_writers:
                raise CompileError(node.token, 'cannot access owner while mutable borrow is active')
            return set(env[node.token.text].owners)
        if node.kind == 'move' and env[node.args[0].token.text].mode in ('mutable', 'readonly'):
            raise CompileError(node.token, 'cannot move a borrowed parameter')
        if node.kind == 'move' and env[node.args[0].token.text].identity in active_readers:
            raise CompileError(node.token, 'cannot move owner while readonly borrow is active')
        if node.kind == 'call' and node.token.text in signatures and not node.token.text.startswith(('memory$view$', 'vec$view$')):
            signature = signatures[node.token.text]
            saved_readers, saved_writers = set(active_readers), set(active_writers)
            try:
                for i, arg in enumerate(node.args):
                    if i in signature.mutable_params:
                        if arg.kind != 'borrow_mut':
                            raise CompileError(arg.token, 'mutable argument requires explicit borrow mut')
                        binding = env[arg.args[0].token.text]
                        identity = binding.identity
                        if not binding.writable or binding.mode == 'readonly':
                            raise CompileError(arg.token, 'mutable borrow requires a var or mutable parameter')
                        if locked(identity) or identity in active_readers or identity in active_writers:
                            raise CompileError(arg.token, 'conflicting mutable borrow')
                        expr(arg.args[0], env)
                        active_writers.add(identity)
                    else:
                        expr(arg, env)
                        if i in signature.readonly_params:
                            root = projection_root(arg)
                            if root is not None: active_readers.add(env[root].identity)
            finally:
                active_readers.clear();active_readers.update(saved_readers)
                active_writers.clear();active_writers.update(saved_writers)
            return set()
        if node.kind == 'move' and locked(env[node.args[0].token.text].identity):
            raise CompileError(node.token, 'cannot move owner while readonly view is live')
        if node.kind == 'view' or (node.kind == 'call' and node.token.text.startswith(('memory$view$', 'vec$view$'))):
            owner = projection_root(node.args[0])
            if owner is None:
                raise CompileError(node.token, 'view requires a binding root')
            binding = env[owner]
            # A descriptor is not a new storage owner. Parameter views borrow
            # external storage for this call; locally created views retain all
            # possible roots across assignments and CFG joins.
            owners = set(binding.owners) if is_view(binding.type) else {binding.identity}
            if not owners:
                owners = {binding.identity}
            if owners & active_writers or binding.identity in active_writers:
                raise CompileError(node.token, 'cannot create view while mutable borrow is active')
            loans[-1].update(owners)
            for arg in node.args[1:]:
                expr(arg, env)
            return owners
        owners = set()
        for arg in node.args:
            owners.update(expr(arg, env))
        return owners if is_view(types[id(node)]) else set()

    def join(env, paths):
        paths = [p for p in paths if p is not None]
        if not paths:
            return None
        return {name: replace(binding, owners=frozenset().union(*(p[name].owners for p in paths)))
                for name, binding in env.items()}

    def scoped(body, env):
        loans.append(set())
        result = statements(body, env.copy())
        loans.pop()
        return result

    def statements(body, env):
        for stmt in body:
            if isinstance(stmt, Destructure):
                expr(stmt.expr, env)
                for token, t in zip(stmt.names, consumed_components(types[id(stmt.expr)], structs)):
                    env[token.text] = declaration(token, t, len(loans)-1)
                    depths[env[token.text].identity] = len(loans)-1
            elif isinstance(stmt, Scope):
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
                        branch[arm.binding.text] = declaration(arm.binding, cases[arm.case.rsplit('.',1)[-1]], len(loans))
                        depths[branch[arm.binding.text].identity] = len(loans)
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
                if locked(env[stmt.token.text].identity):
                    raise CompileError(stmt.token, 'cannot update owner while readonly view is live')
                expr(stmt.target, env)
                expr(stmt.expr, env)
                if locked(env[stmt.token.text].identity):
                    raise CompileError(stmt.token, 'cannot update owner while readonly view is live')
            else:
                owners = expr(stmt.expr, env)
                if stmt.is_return:
                    return None
                name = stmt.token.text
                if name in env and locked(env[name].identity):
                    raise CompileError(stmt.token, 'cannot reassign owner while readonly view is live')
                t = types[id(stmt.expr)]
                binding = env.get(name) or declaration(stmt.token, t, len(loans)-1, stmt.is_var)
                depth = binding.depth
                depths[binding.identity] = depth
                if is_view(t):
                    if any(depths[owner] > depth for owner in owners):
                        raise CompileError(stmt.token, 'view escapes owner lifetime')
                    loans[depth].update(owners)
                env[name] = replace(binding, type=t, owners=frozenset(owners))
            if env is None:
                return None
        return env

    statements(fn.body, initial)
