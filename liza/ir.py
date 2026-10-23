"""Typed value graph with explicit control flow and arithmetic policy."""
from dataclasses import dataclass, asdict, field
import json
from typing import Optional
from .frontend import CompileError, Token, Conditional, While, LoopControl, Match, Update
from .typecheck import infer_expression
from .types import signed, SCALAR_TYPES, value_properties, is_array, is_view, element_type, array_length, validate_type, generic_args
from .ownership import check_ownership
from .borrowing import check_borrows
from .resources import check_resources


@dataclass
class Operation:
    result: str
    op: str
    args: list
    type: str = 'u32'
    overflow: str = 'none'
    callee: str = ''
    effect_contract: str = 'pure'
    parameter_modes: list = field(default_factory=list)
    may_trap: bool = False
    shift_policy: str = 'none'
    division_policy: str = 'none'
    source_type: str = ''
    field_name: str = ''
    bounds_policy: str = 'none'
    owner_binding: str = ''
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
        self.variants = structs.variants


@dataclass
class VariantIR:
    name: str
    cases: list
    properties: dict


class TypeTable(dict):
    def __init__(self):
        super().__init__()
        self.variants = {}


def structure_types(program):
    declarations, result, visiting = {}, TypeTable(), set()
    result.visibility = {d.name.text:(d.module,set(d.public_fields)) for d in getattr(program,"structs",[]) if d.module}
    for decl in list(getattr(program, 'structs', [])) + list(getattr(program, 'enums', [])):
        if decl.name.text in declarations:
            raise CompileError(decl.name, 'duplicate structure or enum')
        declarations[decl.name.text] = decl

    def resolve(name, allow_view=True):
        if is_array(name):
            member = resolve(element_type(name), False)
            if not member['copyable']:
                raise ValueError('resource values cannot be stored in arrays yet')
            return member
        if is_view(name):
            if not allow_view:
                raise ValueError('views cannot be stored in aggregates or returned')
            if not resolve(element_type(name), False)['copyable']:
                raise ValueError('views of resource values are not supported')
            return {'copyable': True, 'implicit_copy': True}
        if name in SCALAR_TYPES + ('Text', 'File'):
            return value_properties(name)
        if name in result:
            return result[name].properties
        if name in result.variants:
            return result.variants[name].properties
        if name in visiting:
            raise ValueError('recursive by-value structure or variant is not allowed')
        args = generic_args(name)
        if args is not None:
            entries = [('Some', args[0]), ('None', None)] if name.startswith('Option<') else [('Ok',args[0]),('Err',args[1])]
            decl, variant = None, True
        elif name in declarations:
            decl = declarations[name]
            variant = hasattr(decl, 'cases')
            entries = [(t.text, ty) for t, ty in (decl.cases if variant else decl.fields)]
        else:
            raise ValueError(f'unknown type {name!r}')
        visiting.add(name)
        properties = {'copyable': True, 'implicit_copy': True}
        seen = set()
        for field_name, type_name in entries:
            if field_name in seen:
                raise ValueError('duplicate alternative' if variant else 'duplicate field')
            seen.add(field_name)
            if type_name is not None:
                member = resolve(type_name, False)
                if not variant and not name.startswith('__liza_') and not member['copyable']:
                    raise ValueError('resource fields require destructuring, which is not supported yet')
                for key in properties:
                    properties[key] = properties[key] and member[key]
        visiting.remove(name)
        if variant:
            result.variants[name] = VariantIR(name, entries, properties)
        else:
            result[name] = StructIR(name, entries, properties)
        return properties

    result.ensure = resolve
    for name, decl in declarations.items():
        try:
            resolve(name)
        except ValueError as error:
            raise CompileError(decl.name, str(error)) from None
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
        self.expression_types = {}
        self.match_types = {}

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
                       for policy in ('overflow', 'shift_policy', 'division_policy', 'bounds_policy'))
        self.current.operations.append(Operation(
            name, op, args, type, may_trap=may_trap, **kwargs))
        self.types[name] = type
        return name

    def expression(self, expr, names, expected=None):
        if expected:
            try:
                validate_type(expected, self.structs)
            except ValueError as error:
                raise CompileError(expr.token, str(error)) from None
        inferred = infer_expression(expr, names, self.types, self.signatures, expected, self.structs, self.fn.module)
        for type_name in set(inferred.values()) - {'integer'}:
            try:
                validate_type(type_name, self.structs)
            except ValueError as error:
                raise CompileError(expr.token, str(error)) from None
        self.expression_types.update(inferred)
        return self.emit_expression(expr, names, inferred)

    def emit_expression(self, expr, names, inferred):
        text, type_name = expr.token.text, inferred[id(expr)]
        if expr.kind == 'text':
            if len(text.encode('utf-8')) > 4294967295:
                raise CompileError(expr.token, 'text literal exceeds u32 bytes')
            return self.emit('text.literal', [text], type='Text')
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
            effect = self.signatures[text].effect_contract
            if effect == 'io' and self.fn.effect_contract != 'io':
                raise CompileError(expr.token, 'pure function cannot call io function '+text)
            return self.emit('call', args, type=type_name, callee=text, effect_contract=effect,
                             parameter_modes=['borrow' if i in self.signatures[text].borrowed_params else 'value'
                                              for i in range(len(args))])
        if expr.kind in ('array', 'index', 'view'):
            args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
            if expr.kind == 'array':
                return self.emit('array.construct', args, type=type_name)
            source = self.types[args[0]]
            op = 'view.create' if expr.kind == 'view' else 'view.read' if is_view(source) else 'array.read'
            return self.emit(op, args, type=type_name, source_type=source,
                             bounds_policy='trap',
                             owner_binding=expr.args[0].token.text if expr.kind == 'view' else '')
        if expr.kind == 'variant':
            args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
            case = text.rsplit('.',1)[-1]
            return self.emit('variant.construct', args, type=type_name, field_name=case)
        if expr.kind == 'field':
            value = self.emit_expression(expr.args[0], names, inferred)
            if text == 'len' and (is_array(self.types[value]) or is_view(self.types[value]) or self.types[value] == 'Text'):
                return self.emit('sequence.length', [value], type='u32', source_type=self.types[value])
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

    def match_statement(self, stmt, names, mutable):
        value = self.expression(stmt.expr, names)
        type_name = self.types[value]
        if type_name not in self.structs.variants:
            raise CompileError(stmt.token, 'match requires a variant value')
        cases = self.structs.variants[type_name].cases
        expected = {case for case, _ in cases}
        seen, arm_info = set(), []
        for arm in stmt.arms:
            if '.' in arm.case:
                qualifier, case = arm.case.rsplit('.',1)
                if qualifier != type_name:
                    raise CompileError(arm.token, 'pattern belongs to a different variant type')
            else:
                case = arm.case
                if generic_args(type_name) is None:
                    raise CompileError(arm.token, 'user variant patterns require Type.Alternative')
            if case not in expected:
                raise CompileError(arm.token, 'unknown alternative')
            if case in seen:
                raise CompileError(arm.token, 'duplicate match alternative')
            seen.add(case)
            payload = dict(cases)[case]
            if (payload is None) != (arm.binding is None):
                raise CompileError(arm.token, 'pattern payload binding does not match alternative')
            if arm.binding and arm.binding.text != '_' and arm.binding.text in names:
                raise CompileError(arm.binding, 'duplicate binding; shadowing is not allowed')
            arm_info.append((arm, case, payload))
        if seen != expected:
            raise CompileError(stmt.token, 'non-exhaustive match; missing '+', '.join(sorted(expected-seen)))
        self.match_types[id(stmt)] = type_name
        tag = self.emit('variant.tag', [value], type='u32', source_type=type_name)
        dispatch = self.current
        invalid = self.new_block()
        invalid.terminator = Terminator('unreachable', [])
        targets, ends = [], []
        for arm, case, payload in arm_info:
            block = self.new_block()
            targets.append([next(i for i,(c,_) in enumerate(cases) if c==case), block.name])
            self.current = block
            env = names.copy()
            if payload is not None and arm.binding.text != '_':
                env[arm.binding.text] = self.emit('variant.payload', [value], type=payload,
                                                source_type=type_name, field_name=case)
            self.statements(arm.body, env, mutable.copy())
            if self.current is not None:
                ends.append((self.current, env))
        dispatch.terminator = Terminator('switch', [tag, invalid.name] + targets)
        self.current = self.new_block() if ends else None
        for block, _ in ends:
            block.terminator = Terminator('jump', [self.current.name])
        self.merge_names(names, mutable, ends)

    def update(self, stmt, names, mutable):
        name = stmt.token.text
        if name not in names:
            raise CompileError(stmt.token, 'unknown binding '+name)
        if name not in mutable:
            raise CompileError(stmt.token, 'values are immutable; assignment requires var')
        # Type the complete path once, then evaluate each projection once. Reads
        # preserve bounds traps before the RHS, including the final projection.
        inferred = infer_expression(stmt.target, names, self.types, self.signatures, None, self.structs, self.fn.module)
        for type_name in set(inferred.values()) - {'integer'}:
            try:
                validate_type(type_name, self.structs)
            except ValueError as error:
                raise CompileError(stmt.token, str(error)) from None
        self.expression_types.update(inferred)
        path = []
        node = stmt.target
        while node.kind != 'name':
            path.append(node)
            node = node.args[0]
        value = names[name]
        parents = []
        for node in reversed(path):
            source = self.types[value]
            if node.kind == 'field':
                if source not in self.structs:
                    raise CompileError(node.token, 'only structure fields can be updated')
                parents.append((node, value, None))
                value = self.emit('struct.field', [value], type=inferred[id(node)],
                                  source_type=source, field_name=node.token.text)
            else:
                if not is_array(source):
                    raise CompileError(node.token, 'only owned array elements can be updated')
                index = self.emit_expression(node.args[1], names, inferred)
                parents.append((node, value, index))
                value = self.emit('array.read', [value, index], type=inferred[id(node)],
                                  source_type=source, bounds_policy='trap')
        replacement = self.expression(stmt.expr, names, self.types[value])
        self.expect(replacement, self.types[value], stmt.expr.token)
        for node, parent, index in reversed(parents):
            source = self.types[parent]
            if node.kind == 'field':
                replacement = self.emit('struct.update', [parent, replacement], type=source,
                                        field_name=node.token.text)
            else:
                replacement = self.emit('array.update', [parent, index, replacement], type=source,
                                        bounds_policy='trap')
        names[name] = replacement

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
            elif isinstance(stmt, Match):
                self.match_statement(stmt, names, mutable)
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
            elif isinstance(stmt, Update):
                self.update(stmt, names, mutable)
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
            params.append({'name': name, 'type': type_name,
                           'mode': 'borrow' if i in self.fn.borrowed_params else 'value'})
        self.statements(self.fn.body, names, set())
        if self.current is not None:
            raise CompileError(self.fn.name, f'function must return a {self.fn.result_type} value on every path')
        check_resources(self.fn, self.expression_types, self.match_types, self.structs, self.signatures)
        check_borrows(self.fn, self.expression_types, self.match_types, self.structs.variants)
        return FunctionIR(self.fn.name.text, params, self.blocks, self.fn.result_type, self.fn.effect_contract)


def lower(functions):
    if getattr(functions,"imports",[]):
        raise CompileError(functions.imports[0], "imports require file-based module loading")
    from .stdlib import attach
    functions, externals = attach(functions)
    structs = structure_types(functions)
    signatures = {f.name.text: f for f in externals}
    for fn in functions:
        if fn.name.text in structs or fn.name.text in structs.variants:
            raise CompileError(fn.name, 'function and structure names must be distinct')
        for token, type_name in fn.params + [(fn.name, fn.result_type)]:
            try:
                validate_type(type_name, structs, token is not fn.name)
            except ValueError as error:
                raise CompileError(token, str(error)) from None
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
    module.externals = externals
    module.modules = getattr(functions,"module_names",[])
    module.declarations = getattr(functions,"declarations",[])
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
            op.may_trap = (op.op == 'convert.checked' and op.source_type != 'integer') or op.overflow == 'trap' or op.shift_policy == 'trap' or op.division_policy == 'trap' or op.bounds_policy == 'trap'
        fn.may_trap = any(op.may_trap for op in operations[fn.name])
    changed = True
    while changed:
        changed = False
        for fn in module:
            for op in operations[fn.name]:
                if op.op == 'call':
                    op.may_trap = functions[op.callee].may_trap if op.callee in functions else False
            summary = any(op.may_trap for op in operations[fn.name])
            if summary != fn.may_trap:
                fn.may_trap = summary
                changed = True


def dump(module):
    structs = getattr(module, 'structs', {})
    properties = {t: value_properties(t) for t in SCALAR_TYPES + ('Text', 'File')}
    properties.update({name: struct.properties for name, struct in structs.items()})
    variants = getattr(module, 'variants', {})
    properties.update({name: v.properties for name, v in variants.items()})
    def describe(t):
        if t in properties or t == 'integer':
            return
        if is_array(t) or is_view(t):
            describe(element_type(t))
            properties[t] = dict(properties[element_type(t)]) if is_array(t) else {'copyable': True, 'implicit_copy': True}
    for struct in structs.values():
        for _, t in struct.fields:
            describe(t)
    for variant in variants.values():
        for _, t in variant.cases:
            if t is not None:
                describe(t)
    for fn in module:
        describe(fn.result_type)
        for param in fn.params:
            describe(param['type'])
        for block in fn.blocks:
            for op in block.operations:
                describe(op.type)
    return json.dumps({'version': 15, 'type_properties': properties,
                       'modules': getattr(module,'modules',[]),
                       'declarations': getattr(module,'declarations',[]),
                       'structures': [asdict(s) for s in structs.values()],
                       'variants': [asdict(v) for v in variants.values()],
                       'externals': [asdict(fn) for fn in getattr(module, 'externals', [])],
                       'functions': [asdict(fn) for fn in module]}, indent=2) + '\n'
