"""Definite availability of bindings, checked after typing and before backend.

True means available on every incoming path. Loop headers use the greatest
fixed point below their entry state. Source scopes are already validated by
lowering; this pass never guesses reachability from constant expressions.
"""
from .frontend import CompileError, Conditional, While, LoopControl


def merge(scope, paths):
    paths = [path for path in paths if path is not None]
    if not paths:
        return None
    return {name: all(path[name] for path in paths) for name in scope}


def expression(expr, state):
    if expr.kind == 'name':
        if not state[expr.token.text]:
            raise CompileError(expr.token, f'use after move: {expr.token.text!r} is not available on every path')
        return
    if expr.kind == 'binary' and expr.token.text in ('&&', '||'):
        expression(expr.args[0], state)
        right = state.copy()
        expression(expr.args[1], right)
        state.update(merge(state, [state, right]))
        return
    for arg in expr.args:
        expression(arg, state)
    if expr.kind == 'move':
        state[expr.args[0].token.text] = False


def statements(body, state, loops):
    for stmt in body:
        if isinstance(stmt, Conditional):
            expression(stmt.condition, state)
            left = statements(stmt.then_body, state.copy(), loops)
            right = statements(stmt.else_body, state.copy(), loops)
            state = merge(state, [left, right])
        elif isinstance(stmt, While):
            entry = state.copy()
            header = entry.copy()
            while True:
                condition = header.copy()
                expression(stmt.condition, condition)
                backs, breaks = [], []
                end = statements(stmt.body, condition.copy(), loops + [(backs, breaks)])
                if end is not None:
                    backs.append(end)
                next_header = merge(entry, [entry] + backs)
                if next_header == header:
                    break
                header = next_header
            always_true = stmt.condition.kind == 'bool' and stmt.condition.token.text == 'true'
            state = merge(entry, breaks + ([] if always_true else [condition]))
        elif isinstance(stmt, LoopControl):
            backs, breaks = loops[-1]
            (breaks if stmt.token.text == 'break' else backs).append(state.copy())
            return None
        else:
            expression(stmt.expr, state)
            if stmt.is_return:
                return None
            # The RHS is checked before restoring a mutable binding.
            state[stmt.token.text] = True
        if state is None:
            return None
    return state


def check_ownership(fn):
    statements(fn.body, {param.text: True for param, _ in fn.params}, [])
