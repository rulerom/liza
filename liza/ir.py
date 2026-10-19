"""Typed value graph with explicit control flow and arithmetic policy."""
from dataclasses import dataclass, asdict, field
import json
from typing import Optional
from .frontend import CompileError, Token, Conditional, While, LoopControl
from .typecheck import infer_expression
from .types import signed, SCALAR_TYPES, value_properties
from .ownership import check_ownership


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
    source_type: str = ''
    field_name: str = ''
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
    termination_contract: str = 'may_diverge'


@dataclass
class StructIR:
    name: str
    fields: list
    properties: dict


class ModuleIR(list):
    def __init__(self, functions, structs):
        super().__init__(functions)
        self.structs = structs


def structure_types(program):
    declarations, result, visiting = {}, {}, set()
    for decl in getattr(program, 'structs', []):
        if decl.name.text in declarations:
            raise CompileError(decl.name, 'duplicate structure')
        declarations[decl.name.text] = decl

    def resolve(name):
        if name in result:
            return result[name]
        decl = declarations[name]
        if name in visiting:
            raise CompileError(decl.name, 'recursive by-value structure is not allowed')
        visiting.add(name)
        fields, properties = [], {'copyable': True, 'implicit_copy': True}
        seen = set()
        for field, type_name in decl.fields:
            if field.text in seen:
                raise CompileError(field, 'duplicate field')
            seen.add(field.text)
            if type_name in SCALAR_TYPES:
                member = value_properties(type_name)
            elif type_name in declarations:
                member = resolve(type_name).properties
            else:
                raise CompileError(field, f'unknown type {type_name!r}')
            fields.append((field.text, type_name))
            for key in properties:
                properties[key] = properties[key] and member[key]
        visiting.remove(name)
        result[name] = StructIR(name, fields, properties)
        return result[name]

    for name in declarations:
        resolve(name)
    return result


@dataclass
class LoopContext:
    header: Block
    exit: Block
    backedges: list = field(default_factory=list)
    breaks: list = field(default_factory=list)


class Lowerer:
    def __init__(self, fn, signatures, structs):
        self.fn = fn
        self.signatures = signatures
        self.structs = structs
        self.blocks = []
        self.current = self.new_block()
        self.types = {}
        self.counter = 0
        self.loops = []

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
        may_trap = op == 'convert.checked' or any(kwargs.get(policy) == 'trap'
                       for policy in ('overflow', 'shift_policy', 'division_policy'))
        self.current.operations.append(Operation(
            name, op, args, type, may_trap=may_trap, **kwargs))
        self.types[name] = type
        return name

    def expression(self, expr, names, expected=None):
        if expected and expected not in SCALAR_TYPES and expected not in self.structs:
            raise CompileError(expr.token, f'unknown type {expected!r}')
        inferred = infer_expression(expr, names, self.types, self.signatures, expected, self.structs)
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
            if text in self.structs:
                return self.emit('struct.construct', args, type=type_name)
            return self.emit('call', args, type=type_name, callee=text)
        if expr.kind == 'field':
            value = self.emit_expression(expr.args[0], names, inferred)
            return self.emit('struct.field', [value], type=type_name,
                             source_type=self.types[value], field_name=text)
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
        if expr.kind.startswith('convert.'):
            return self.emit(expr.kind, args, type=type_name, source_type=self.types[args[0]])
        if expr.kind in ('copy', 'move', 'not', 'bit_not'):
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
                         type=type_name, overflow='wrap' if text.endswith('%') else 'saturate' if text.endswith('|') else 'trap')

    def merge_names(self, names, mutable, edges):
        # Only bindings visible before a construct survive its local scopes.
        for name in names:
            if name not in mutable or not edges:
                continue
            values = [env[name] for _, env in edges]
            if all(value == values[0] for value in values):
                names[name] = values[0]
            else:
                names[name] = self.emit('phi', values, type=self.types[names[name]],
                                        incoming_blocks=[block.name for block, _ in edges])

    def while_loop(self, stmt, names, mutable):
        entry = self.current
        header, body, exit_block = self.new_block(), self.new_block(), self.new_block()
        entry.terminator = Terminator('jump', [header.name])
        self.current = header
        header_names, phis = names.copy(), {}
        # Create loop-carried SSA values before lowering the condition/body.
        # Fill backedges only after all continue and fallthrough paths are known.
        for name in names:
            if name in mutable:
                header_names[name] = self.emit('phi', [names[name]], type=self.types[names[name]],
                                               incoming_blocks=[entry.name])
                phis[name] = header.operations[-1]
        condition = self.expression(stmt.condition, header_names, 'bool')
        condition_end = self.current
        always_true = stmt.condition.kind == 'bool' and stmt.condition.token.text == 'true'
        if always_true:
            condition_end.terminator = Terminator('jump', [body.name])
        else:
            condition_end.terminator = Terminator('branch', [condition, body.name, exit_block.name])
        context = LoopContext(header, exit_block)
        self.loops.append(context)
        self.current = body
        body_names = header_names.copy()
        self.statements(stmt.body, body_names, mutable.copy())
        if self.current is not None:
            context.backedges.append((self.current, body_names.copy()))
            self.current.terminator = Terminator('jump', [header.name])
        self.loops.pop()
        for name, phi in phis.items():
            for block, env in context.backedges:
                phi.args.append(env[name])
                phi.incoming_blocks.append(block.name)
        exits = ([] if always_true else [(condition_end, header_names)]) + context.breaks
        self.current = exit_block
        if exits:
            self.merge_names(names, mutable, exits)
        else:
            # No CFG edge reaches this reserved break target.
            exit_block.terminator = Terminator('unreachable', [])
            self.current = None

    def statements(self, statements, names, mutable):
        for stmt in statements:
            if self.current is None:
                raise CompileError(stmt.token, 'unreachable statement after control transfer')
            if isinstance(stmt, Conditional):
                condition = self.expression(stmt.condition, names, 'bool')
                self.expect(condition, 'bool', stmt.condition.token)
                then_block, else_block = self.new_block(), self.new_block()
                self.current.terminator = Terminator('branch', [condition, then_block.name, else_block.name])
                then_names, else_names = names.copy(), names.copy()
                self.current = then_block
                self.statements(stmt.then_body, then_names, mutable.copy())
                then_end = self.current
                self.current = else_block
                self.statements(stmt.else_body, else_names, mutable.copy())
                else_end = self.current
                ends = [(block, env) for block, env in
                        ((then_end, then_names), (else_end, else_names)) if block is not None]
                self.current = self.new_block() if ends else None
                for block, _ in ends:
                    block.terminator = Terminator('jump', [self.current.name])
                # Returned, broken and continued paths do not reach this join.
                self.merge_names(names, mutable, ends)
            elif isinstance(stmt, While):
                self.while_loop(stmt, names, mutable)
            elif isinstance(stmt, LoopControl):
                if not self.loops:
                    raise CompileError(stmt.token, f'{stmt.token.text} outside a loop')
                context = self.loops[-1]
                if stmt.token.text == 'break':
                    context.breaks.append((self.current, names.copy()))
                    target = context.exit
                else:
                    context.backedges.append((self.current, names.copy()))
                    target = context.header
                self.current.terminator = Terminator('jump', [target.name])
                self.current = None
            elif stmt.is_return:
                value = self.expression(stmt.expr, names, self.fn.result_type)
                self.expect(value, self.fn.result_type, stmt.expr.token)
                self.current.terminator = Terminator('return', [value])
                self.current = None
            else:
                name = stmt.token.text
                if name in names:
                    if stmt.is_var or stmt.annotation:
                        raise CompileError(stmt.token, 'duplicate binding; shadowing is not allowed')
                    if name not in mutable:
                        raise CompileError(stmt.token, 'values are immutable; assignment requires var')
                    expected = self.types[names[name]]
                else:
                    expected = stmt.annotation or None
                # Evaluate using the old environment, then rebind to a new SSA value.
                value = self.expression(stmt.expr, names, expected)
                names[name] = value
                if stmt.is_var:
                    mutable.add(name)

    def lower(self):
        names, params = {}, []
        for i, (param, type_name) in enumerate(self.fn.params):
            if param.text in names:
                raise CompileError(param, 'duplicate parameter')
            name = f'p{i}'
            names[param.text] = name
            self.types[name] = type_name
            params.append({'name': name, 'type': type_name})
        self.statements(self.fn.body, names, set())
        if self.current is not None:
            raise CompileError(self.fn.name, f'function must return a {self.fn.result_type} value on every path')
        return FunctionIR(self.fn.name.text, params, self.blocks, self.fn.result_type)


def lower(functions):
    structs = structure_types(functions)
    signatures = {}
    for fn in functions:
        if fn.name.text in structs:
            raise CompileError(fn.name, 'function and structure names must be distinct')
        for token, type_name in fn.params + [(fn.name, fn.result_type)]:
            if type_name not in SCALAR_TYPES and type_name not in structs:
                raise CompileError(token, f'unknown type {type_name!r}')
        if fn.name.text in signatures:
            raise CompileError(fn.name, 'duplicate function')
        signatures[fn.name.text] = fn
    if 'main' not in signatures:
        raise CompileError(Token('', 1, 1), 'missing fn main() -> u32')
    if signatures['main'].params:
        raise CompileError(signatures['main'].name, 'main must have no parameters')
    if signatures['main'].result_type != 'u32':
        raise CompileError(signatures['main'].name, 'main must return u32')
    module = ModuleIR([Lowerer(fn, signatures, structs).lower() for fn in functions], structs)
    for fn in functions:
        check_ownership(fn)
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
            op.may_trap = (op.op == 'convert.checked' and op.source_type != 'integer') or op.overflow == 'trap' or op.shift_policy == 'trap' or op.division_policy == 'trap'
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
    structs = getattr(module, 'structs', {})
    properties = {t: value_properties(t) for t in SCALAR_TYPES}
    properties.update({name: struct.properties for name, struct in structs.items()})
    return json.dumps({'version': 9, 'type_properties': properties,
                       'structures': [asdict(s) for s in structs.values()],
                       'functions': [asdict(fn) for fn in module]}, indent=2) + '\n'
