"""M0's deliberately restricted addressable value types and source discovery."""
from .types import SCALAR_TYPES, is_array, element_type
from .frontend import Conditional, While, Match, Scope, LoopControl, Update, Destructure


def plain_value(t, structs):
    if t in SCALAR_TYPES:
        return True
    if is_array(t):
        return plain_value(element_type(t), structs)
    return t in structs and structs[t].properties['copyable'] and all(
        plain_value(member, structs) for _, member in structs[t].fields)


def addressable_bindings(body):
    """Declaration IDs of vars used as explicit mutable call arguments.

    Resolve names lexically; sibling declarations with identical spelling are
    unrelated. The same AST declaration has one stable ID across loop visits.
    """
    result = set()
    def expr(node, env):
        if node.kind == 'borrow_mut':
            target = env.get(node.args[0].token.text)
            if target is not None and getattr(target, 'is_var', False):
                result.add(id(target))
        for arg in node.args:
            expr(arg, env)
    def visit(body, env):
        for stmt in body:
            if isinstance(stmt, Scope): visit(stmt.body, env.copy())
            elif isinstance(stmt, Conditional):
                expr(stmt.condition, env)
                visit(stmt.then_body, env.copy());visit(stmt.else_body, env.copy())
            elif isinstance(stmt, While):
                expr(stmt.condition, env);visit(stmt.body, env.copy())
            elif isinstance(stmt, Match):
                expr(stmt.expr, env)
                for arm in stmt.arms:
                    branch = env.copy()
                    if arm.binding: branch[arm.binding.text] = None
                    visit(arm.body, branch)
            elif not isinstance(stmt, LoopControl):
                expr(stmt.expr, env)
                if isinstance(stmt, Update): expr(stmt.target, env)
                elif isinstance(stmt, Destructure):
                    for token in stmt.names: env[token.text] = None
                elif not stmt.is_return and stmt.token.text not in env:
                    env[stmt.token.text] = stmt
    visit(body, {})
    return result
