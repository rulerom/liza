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
    """Names whose var storage must exist before an eventual mutable call.

    Names are not shadowed. Readonly calls can use immutable SSA snapshots;
    only explicit mutable arguments require a persistent local allocation.
    """
    result = set()
    def expr(node):
        if node.kind == 'borrow_mut':
            result.add(node.args[0].token.text)
        for arg in node.args:
            expr(arg)
    def visit(body):
        for stmt in body:
            if isinstance(stmt, Scope): visit(stmt.body)
            elif isinstance(stmt, Conditional):
                expr(stmt.condition);visit(stmt.then_body);visit(stmt.else_body)
            elif isinstance(stmt, While): expr(stmt.condition);visit(stmt.body)
            elif isinstance(stmt, Match):
                expr(stmt.expr)
                for arm in stmt.arms: visit(arm.body)
            elif not isinstance(stmt, LoopControl):
                expr(stmt.expr)
                if isinstance(stmt, Update): expr(stmt.target)
    visit(body)
    return result
