"""Typed value graph with explicit control flow and arithmetic policy."""
from dataclasses import dataclass, asdict, field
import json
from typing import Optional
from .frontend import CompileError, Token, Conditional
from .typecheck import infer_expression
from .types import signed


@dataclass
class Operation:
    result: str
    op: str
    args: list
    type: str = 'u32'
    overflow: str = 'none'
    callee: str = ''
    may_trap: bool = False
    shift_policy: str = 'none'
    division_policy: str = 'none'
    incoming_blocks: list = field(default_factory=list)


@dataclass
class Terminator:
    op: str
    args: list


@dataclass
class Block:
    name: str
    operations: list = field(default_factory=list)
    terminator: Optional[Terminator] = None


@dataclass
class FunctionIR:
    name: str
    params: list
    blocks: list
    result_type: str
    effect_contract: str = 'pure'
    may_trap: bool = False


class Lowerer:
    def __init__(self, fn, signatures):
        self.fn = fn
        self.signatures = signatures
        self.blocks = []
        self.current = self.new_block()
        self.types = {}
        self.counter = 0

    def new_block(self):
        block = Block(f'b{len(self.blocks)}')
        self.blocks.append(block)
        return block

    def expect(self, value, expected, token):
        actual = self.types[value]
        if actual != expected:
            raise CompileError(token, f'expected {expected}, got {actual}')

    def emit(self, op, args, type='u32', **kwargs):
        name = f'v{self.counter}'
        self.counter += 1
        may_trap = any(kwargs.get(policy) == 'trap'
                       for policy in ('overflow', 'shift_policy', 'division_policy'))
        self.current.operations.append(Operation(
            name, op, args, type, may_trap=may_trap, **kwargs))
        self.types[name] = type
        return name

    def expression(self, expr, names, expected=None):
        inferred = infer_expression(expr, names, self.types, self.signatures, expected)
        return self.emit_expression(expr, names, inferred)

    def emit_expression(self, expr, names, inferred):
        text, type_name = expr.token.text, inferred[id(expr)]
        if expr.kind == 'bool':
            return self.emit('constant', [text == 'true'], type='bool')
        if expr.kind == 'literal':
            value = int(text, 16 if text.lstrip('-').startswith('0x') else 10)
            return self.emit('constant', [value], type=type_name)
        if expr.kind == 'name':
            return names[text]
        if expr.kind == 'call':
            args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
            return self.emit('call', args, type=type_name, callee=text)
        if text in ('&&', '||'):
            left = self.emit_expression(expr.args[0], names, inferred)
            rhs, short = self.new_block(), self.new_block()
            targets = [rhs.name, short.name] if text == '&&' else [short.name, rhs.name]
            self.current.terminator = Terminator('branch', [left] + targets)
            self.current = short
            short_value = self.emit('constant', [text == '||'], type='bool')
            self.current = rhs
            right = self.emit_expression(expr.args[1], names, inferred)
            right_end = self.current
            join = self.new_block()
            short.terminator = Terminator('jump', [join.name])
            right_end.terminator = Terminator('jump', [join.name])
            self.current = join
            return self.emit('phi', [short_value, right], type='bool',
                             incoming_blocks=[short.name, right_end.name])
        args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
        if expr.kind in ('not', 'bit_not'):
            return self.emit(expr.kind, args, type=type_name)
        if expr.kind == 'neg':
            zero = self.emit('constant', [0], type=type_name)
            return self.emit('sub', [zero, args[0]], type=type_name, overflow='trap')
        comparisons = {'==': 'eq', '!=': 'ne', '<': 'lt', '<=': 'le', '>': 'gt', '>=': 'ge'}
        if text in comparisons:
            op = comparisons[text]
            if op not in ('eq', 'ne'):
                op = ('s' if signed(self.types[args[0]]) else 'u') + op
            return self.emit(op, args, type='bool')
        if text in ('<<', '>>'):
            return self.emit('shl' if text == '<<' else 'shr', args,
                             type=type_name, shift_policy='trap')
        if text in ('/', '%'):
            return self.emit('div' if text == '/' else 'rem', args,
                             type=type_name, division_policy='trap')
        if text in ('&', '|', '^'):
            return self.emit({'&': 'and', '|': 'or', '^': 'xor'}[text], args, type=type_name)
        return self.emit({'+': 'add', '-': 'sub', '*': 'mul'}[text[0]], args,
                         type=type_name, overflow='wrap' if text.endswith('%') else 'trap')

    def statements(self, statements, names):
        for stmt in statements:
            if self.current is None:
                raise CompileError(stmt.token, 'unreachable statement after return')
            if isinstance(stmt, Conditional):
                condition = self.expression(stmt.condition, names, 'bool')
                self.expect(condition, 'bool', stmt.condition.token)
                then_block, else_block = self.new_block(), self.new_block()
                self.current.terminator = Terminator('branch', [condition, then_block.name, else_block.name])
                self.current = then_block
                self.statements(stmt.then_body, names.copy())
                then_end = self.current
                self.current = else_block
                self.statements(stmt.else_body, names.copy())
                else_end = self.current
                ends = [block for block in (then_end, else_end) if block is not None]
                self.current = self.new_block() if ends else None
                for block in ends:
                    block.terminator = Terminator('jump', [self.current.name])
            elif stmt.is_return:
                value = self.expression(stmt.expr, names, self.fn.result_type)
                self.expect(value, self.fn.result_type, stmt.expr.token)
                self.current.terminator = Terminator('return', [value])
                self.current = None
            else:
                if stmt.token.text in names:
                    raise CompileError(stmt.token, 'values are immutable; duplicate binding')
                value = self.expression(stmt.expr, names, stmt.annotation or None)
                if stmt.annotation:
                    self.expect(value, stmt.annotation, stmt.token)
                names[stmt.token.text] = value

    def lower(self):
        names, params = {}, []
        for i, (param, type_name) in enumerate(self.fn.params):
            if param.text in names:
                raise CompileError(param, 'duplicate parameter')
            name = f'p{i}'
            names[param.text] = name
            self.types[name] = type_name
            params.append({'name': name, 'type': type_name})
        self.statements(self.fn.body, names)
        if self.current is not None:
            raise CompileError(self.fn.name, f'function must return a {self.fn.result_type} value on every path')
        return FunctionIR(self.fn.name.text, params, self.blocks, self.fn.result_type)


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
    if signatures['main'].result_type != 'u32':
        raise CompileError(signatures['main'].name, 'main must return u32')
    module = [Lowerer(fn, signatures).lower() for fn in functions]
    annotate_traps(module)
    return module


def annotate_traps(module):
    """Conservative, transitive trap summaries, including recursive call graphs.

    This is not a termination proof. False only excludes language-level traps
    from the operations currently in the function, not stack exhaustion.
    Recompute after any future IR transformation that changes operations/calls.
    """
    functions = {fn.name: fn for fn in module}
    operations = {fn.name: [op for block in fn.blocks for op in block.operations]
                  for fn in module}
    for fn in module:
        for op in operations[fn.name]:
            op.may_trap = op.overflow == 'trap' or op.shift_policy == 'trap' or op.division_policy == 'trap'
        fn.may_trap = any(op.may_trap for op in operations[fn.name])
    changed = True
    while changed:
        changed = False
        for fn in module:
            for op in operations[fn.name]:
                if op.op == 'call':
                    op.may_trap = functions[op.callee].may_trap
            summary = any(op.may_trap for op in operations[fn.name])
            if summary != fn.may_trap:
                fn.may_trap = summary
                changed = True


def dump(module):
    return json.dumps({'version': 5, 'functions': [asdict(fn) for fn in module]}, indent=2) + '\n'
