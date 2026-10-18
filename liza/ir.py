"""Typed value graph; arithmetic policy is preserved until backend lowering."""
from dataclasses import dataclass, asdict
import json
from .frontend import CompileError, Token


@dataclass
class Operation:
    result: str
    op: str
    args: list
    type: str = 'u32'
    overflow: str = 'none'
    callee: str = ''


@dataclass
class FunctionIR:
    name: str
    params: list
    operations: list
    returns: str
    result_type: str = 'u32'
    effect_contract: str = 'pure'


def lower(functions):
    signatures = {}
    for fn in functions:
        if fn.name.text in signatures:
            raise CompileError(fn.name, 'duplicate function')
        signatures[fn.name.text] = fn
    if 'main' not in signatures:
        raise CompileError(Token('', 1, 1), 'missing fn main() -> u32')
    if signatures['main'].params:
        raise CompileError(signatures['main'].name, 'main must have no parameters')
    result = []
    for fn in functions:
        names, ops, params = {}, [], []
        for i, param in enumerate(fn.params):
            if param.text in names:
                raise CompileError(param, 'duplicate parameter')
            names[param.text] = f'p{i}'
            params.append(f'p{i}')

        def emit(op, args, **kwargs):
            name = f'v{len(ops)}'
            ops.append(Operation(name, op, args, **kwargs))
            return name

        def expression(expr):
            text = expr.token.text
            if expr.kind == 'literal':
                try:
                    value = int(text, 16 if text.startswith('0x') else 10)
                except ValueError:
                    raise CompileError(expr.token, 'invalid u32 literal') from None
                if value > 0xffffffff:
                    raise CompileError(expr.token, 'literal is outside u32 range')
                return emit('constant', [value])
            if expr.kind == 'name':
                if text not in names:
                    raise CompileError(expr.token, f'unknown value {text!r}')
                return names[text]
            if expr.kind == 'call':
                if text not in signatures:
                    raise CompileError(expr.token, f'unknown function {text!r}')
                if len(expr.args) != len(signatures[text].params):
                    raise CompileError(expr.token, f'wrong number of arguments for {text!r}')
                return emit('call', [expression(arg) for arg in expr.args], callee=text)
            args = [expression(arg) for arg in expr.args]
            return emit({'+': 'add', '-': 'sub', '*': 'mul'}[text[0]], args,
                        overflow='wrap' if text.endswith('%') else 'trap')

        returned = None
        for stmt in fn.body:
            if returned is not None:
                raise CompileError(stmt.token, 'unreachable statement after return')
            if stmt.is_return:
                returned = expression(stmt.expr)
            else:
                if stmt.token.text in names:
                    raise CompileError(stmt.token, 'values are immutable; duplicate binding')
                names[stmt.token.text] = expression(stmt.expr)
        if returned is None:
            raise CompileError(fn.name, 'function must return a u32 value')
        result.append(FunctionIR(fn.name.text, params, ops, returned))
    return result


def dump(module):
    return json.dumps({'version': 1, 'functions': [asdict(fn) for fn in module]}, indent=2) + '\n'
