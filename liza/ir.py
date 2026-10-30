"""Typed value graph with explicit control flow and arithmetic policy."""
from .readonly import readonly_root, parameter_modes
from .mutable import plain_value, addressable_bindings
from .types import is_vec, vec_element, is_product, product_args, consumed_components
from dataclasses import dataclass, asdict, field
import json
from typing import Optional
from .frontend import CompileError, Token, Conditional, While, LoopControl, Match, Update, Scope, Destructure
from .typecheck import infer_expression
from .types import signed, SCALAR_TYPES, value_properties, is_array, is_view, element_type, array_length, validate_type, generic_args, is_buffer, buffer_element, effects
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
    storage_relation: str = ''


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
    storage_contract: dict = field(default_factory=dict)


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
        if name == "memory.Region":
            return {"copyable": False, "implicit_copy": False}
        if is_product(name):
            for component in product_args(name): resolve(component, False)
            return {'copyable': False, 'implicit_copy': False}
        if is_vec(name):
            element = vec_element(name)
            if resolve(element, False).get('process_borrow'):
                raise ValueError('process arguments and paths cannot be stored in vectors')
            if not resolve(element, False)['copyable']:
                raise ValueError('vectors require copyable elements')
            from .memory import validate_element_layout
            validate_element_layout(element, result)
            return {'copyable': False, 'implicit_copy': False}
        if is_buffer(name):
            if resolve(buffer_element(name), False).get('process_borrow'):
                raise ValueError('process arguments and paths cannot be stored in buffers')
            if not resolve(buffer_element(name), False)["copyable"]:
                raise ValueError("region buffers require copyable elements")
            from .memory import validate_element_layout
            validate_element_layout(buffer_element(name), result)
            return {"copyable": False, "implicit_copy": False}
        if is_array(name):
            member = resolve(element_type(name), False)
            if member.get('process_borrow'):
                raise ValueError('process arguments and paths cannot be stored in arrays')
            if not member['copyable']:
                raise ValueError('resource values cannot be stored in arrays yet')
            return member
        if is_view(name):
            if resolve(element_type(name), False).get('process_borrow'):
                raise ValueError('process arguments and paths cannot be view elements')
            if not allow_view:
                raise ValueError('views cannot be stored in aggregates or returned')
            if not resolve(element_type(name), False)['copyable']:
                raise ValueError('views of resource values are not supported')
            return {'copyable': True, 'implicit_copy': True}
        if name in SCALAR_TYPES + ('Text', 'File', 'Arg', 'Path', 'net.Listener', 'net.Stream', 'net.DatagramSocket', 'net.Reactor', 'net.Connection'):
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
                if is_product(type_name):
                    raise ValueError('linear products cannot be stored in aggregates')
                member = resolve(type_name, False)
                if member.get('process_borrow'):
                    if decl is not None:
                        raise ValueError('process arguments and paths cannot be stored in user aggregates')
                    properties['process_borrow'] = True
                for key in ('copyable', 'implicit_copy'):
                    properties[key] = properties[key] and member[key]
        visiting.remove(name)
        if variant:
            result.variants[name] = VariantIR(name, entries, properties)
        else:
            result[name] = StructIR(name, entries, properties)
        return properties

    def register(decl):
        declarations[decl.name.text] = decl
        if decl.module:
            result.visibility[decl.name.text] = (decl.module, set(decl.public_fields))
    result.register = register
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
    def __init__(self, fn, signatures, structs, record_expressions=False):
        self.fn = fn
        self.readonly_names = {fn.params[i][0].text for i in fn.readonly_params}
        self.mutable_names = {fn.params[i][0].text for i in fn.mutable_params}
        self.storage_names = self.mutable_names | {fn.params[i][0].text for i in fn.readonly_params
                                                  if structs[fn.params[i][1]].properties['copyable']}
        self.storage_values = set()
        self.address_candidates = addressable_bindings(fn.body)
        self.signatures = signatures
        self.structs = structs
        self.blocks = []
        self.current = self.new_block()
        self.types = {}
        self.counter = 0
        self.loops = []
        self.expression_types = {}
        self.match_types = {}
        self.expression_values = {} if record_expressions else None

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
        inferred = infer_expression(expr, names, self.types, self.signatures, expected, self.structs, self.fn.module, self.readonly_names)
        for type_name in set(inferred.values()) - {'integer'}:
            try:
                validate_type(type_name, self.structs)
            except ValueError as error:
                raise CompileError(expr.token, str(error)) from None
        self.expression_types.update(inferred)
        return self.emit_expression(expr, names, inferred)

    def emit_expression(self, expr, names, inferred):
        result = self._emit_expression(expr, names, inferred)
        if self.expression_values is not None:
            self.expression_values[id(expr)] = result
        return result

    @staticmethod
    def storage_root(node):
        while node.kind in ('field', 'index'):
            node = node.args[0]
        return node.token.text if node.kind == 'name' else None

    def storage_address(self, node, names, inferred):
        if node.kind == 'name':
            return names[node.token.text]
        parent = self.storage_address(node.args[0], names, inferred)
        source = self.types[parent]
        root = names[self.storage_root(node)]
        if node.kind == 'field':
            # .len is a value, never an addressable field.
            if source not in self.structs:
                raise CompileError(node.token, 'only structure fields are addressable')
            return self.emit('storage.field', [parent], type=inferred[id(node)],
                             source_type=source, field_name=node.token.text, owner_binding=root)
        if not is_array(source):
            raise CompileError(node.token, 'only fixed array elements are addressable')
        index = self.emit_expression(node.args[1], names, inferred)
        return self.emit('storage.index', [parent, index], type=inferred[id(node)],
                         source_type=source, bounds_policy='trap', owner_binding=root)

    def _emit_expression(self, expr, names, inferred):
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
        addressable = names.get(self.storage_root(expr)) in self.storage_values
        if addressable and expr.kind == 'field' and text == 'len' and is_array(inferred[id(expr.args[0])]):
            pointer = self.storage_address(expr.args[0], names, inferred)
            return self.emit('sequence.length', [pointer], type='u32', source_type=self.types[pointer])
        if addressable and expr.kind in ('name', 'field', 'index'):
            pointer = self.storage_address(expr, names, inferred)
            return self.emit('storage.read', [pointer], type=type_name,
                             owner_binding=names[self.storage_root(expr)], storage_relation='independent_snapshot')
        if expr.kind == 'borrow_mut':
            raise CompileError(expr.token, 'borrow mut is only allowed for a mutable call argument')
        if expr.kind == 'name':
            return names[text]
        if expr.kind == 'call':
            args, loans = [], []
            signature = self.signatures.get(text)
            for i, arg in enumerate(expr.args):
                mutable_arg = signature is not None and i in signature.mutable_params
                readonly_value = (signature is not None and i in signature.readonly_params
                                  and signature.params[i][1] in self.structs
                                  and self.structs[signature.params[i][1]].properties['copyable'])
                if mutable_arg:
                    if arg.kind != 'borrow_mut':
                        raise CompileError(arg.token, 'mutable argument requires explicit borrow mut')
                    root = arg.args[0].token.text
                    if names[root] not in self.storage_values or root in self.readonly_names:
                        raise CompileError(arg.token, 'mutable borrow requires a var or mutable parameter')
                    value = names[root]
                elif readonly_value and arg.kind == 'name' and names[arg.token.text] in self.storage_values:
                    value = names[arg.token.text]
                else:
                    value = self.emit_expression(arg, names, inferred)
                    if readonly_value:
                        value = self.emit('storage.local', [value], type=inferred[id(arg)], storage_relation='readonly_temporary')
                if mutable_arg or readonly_value:
                    loan = self.emit('loan.begin', [value], type=self.types[value], owner_binding=value,
                                     storage_relation='mutable' if mutable_arg else 'readonly')
                    loans.append(loan);value=loan
                args.append(value)
            if text in self.structs:
                return self.emit('struct.construct', args, type=type_name)
            effect = self.signatures[text].effect_contract
            if effects(effect) - effects(self.fn.effect_contract):
                missing = ','.join(sorted(effects(effect) - effects(self.fn.effect_contract)))
                raise CompileError(expr.token, 'pure function cannot call '+missing+' function '+text)
            if hasattr(self.signatures[text], 'memory_operation'):
                fn = self.signatures[text]
                relations = {
                    'region.create': 'fresh_instance', 'region.alloc': 'depends_on_argument_0',
                    'buffer.update': 'preserve_argument_0', 'buffer.view': 'borrow_argument_0',
                    'buffer.length': 'read_argument_0', 'buffer.release': 'end_dependency_0',
                    'region.close': 'end_origin_0', 'vec.create': 'depends_on_argument_0',
                    'vec.reserve': 'preserve_origin_0_may_relocate_component_0',
                    'vec.push': 'preserve_argument_0_in_component_0',
                    'vec.pop': 'preserve_argument_0_in_component_0',
                    'vec.set': 'preserve_argument_0_in_component_0',
                    'vec.get': 'independent_element_snapshot', 'vec.view': 'borrow_argument_0',
                    'vec.len': 'read_argument_0', 'vec.capacity': 'read_argument_0',
                    'vec.release': 'end_dependency_0',
                }
                return self.emit(fn.memory_operation, args, type=type_name, source_type=fn.memory_element,
                                 storage_relation=relations[fn.memory_operation],
                                 **({"owner_binding":names[readonly_root(expr.args[0],self.readonly_names)]} if expr.args and readonly_root(expr.args[0],self.readonly_names) else {}),
                                 effect_contract=effect, bounds_policy='trap' if fn.memory_operation == 'buffer.update' else 'none',
                                 parameter_modes=parameter_modes(fn, expr.args, self.readonly_names))
            result = self.emit('call', args, type=type_name, callee=text, effect_contract=effect,
                               parameter_modes=parameter_modes(self.signatures[text], expr.args, self.readonly_names))
            for loan in reversed(loans):
                self.emit('loan.end', [loan], owner_binding=loan)
            return result
        if expr.kind in ('array', 'array.repeat', 'index', 'view'):
            args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
            if expr.kind in ('array', 'array.repeat'):
                return self.emit('array.repeat' if expr.kind == 'array.repeat' else 'array.construct', args, type=type_name)
            source = self.types[args[0]]
            op = 'view.create' if expr.kind == 'view' else 'view.read' if is_view(source) else 'array.read'
            return self.emit(op, args, type=type_name, source_type=source,
                             bounds_policy='trap',
                             owner_binding=(args[0] if is_view(source) else expr.args[0].token.text) if expr.kind == 'view' else '',
                             storage_relation='borrow_argument_0' if expr.kind == 'view' and is_view(source) else '')
        if expr.kind == 'variant':
            args = [self.emit_expression(arg, names, inferred) for arg in expr.args]
            case = text.rsplit('.',1)[-1]
            return self.emit('variant.construct', args, type=type_name, field_name=case)
        if expr.kind == 'field':
            value = self.emit_expression(expr.args[0], names, inferred)
            if text == 'len' and (is_array(self.types[value]) or is_view(self.types[value]) or self.types[value] == 'Text'):
                return self.emit('sequence.length', [value], type='u32', source_type=self.types[value])
            return self.emit('struct.field', [value], type=type_name,
                             source_type=self.types[value], field_name=text,
                             **({'storage_relation':'readonly_projection', 'owner_binding':names[readonly_root(expr,self.readonly_names)]}
                                if readonly_root(expr,self.readonly_names) else {}))
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
            if name in mutable and names[name] not in self.storage_values:
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
        inferred = infer_expression(stmt.target, names, self.types, self.signatures, None, self.structs, self.fn.module, self.readonly_names)
        for type_name in set(inferred.values()) - {'integer'}:
            try:
                validate_type(type_name, self.structs)
            except ValueError as error:
                raise CompileError(stmt.token, str(error)) from None
        self.expression_types.update(inferred)
        if names.get(name) in self.storage_values:
            pointer = self.storage_address(stmt.target, names, inferred)
            replacement = self.expression(stmt.expr, names, self.types[pointer])
            self.expect(replacement, self.types[pointer], stmt.expr.token)
            self.emit('storage.write', [pointer, replacement], source_type=self.types[pointer], owner_binding=names[name])
            return
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
            if isinstance(stmt, Destructure):
                if len({n.text for n in stmt.names}) != len(stmt.names) or any(n.text in names or n.text == '_' for n in stmt.names):
                    raise CompileError(stmt.token, 'unpack requires distinct new bindings, without discards')
                value = self.expression(stmt.expr, names)
                t = self.types[value]
                try:
                    components = consumed_components(t, self.structs)
                except ValueError as error:
                    raise CompileError(stmt.token, str(error)) from None
                if len(stmt.names) != len(components):
                    raise CompileError(stmt.token, 'unpack must bind every component exactly once')
                visibility = self.structs.visibility.get(t)
                if visibility and visibility[0] != self.fn.module and any(f not in visibility[1] for f,_ in self.structs[t].fields):
                    raise CompileError(stmt.token, 'unpack contains private fields')
                consumed = self.emit('unpack.consume', [value], type=t)
                for index, (token, component) in enumerate(zip(stmt.names, components)):
                    names[token.text] = self.emit('unpack.component', [consumed], type=component, source_type=t, field_name=str(index))
            elif isinstance(stmt, Scope):
                inner = names.copy()
                self.statements(stmt.body, inner, mutable.copy())
                for name in names:
                    names[name] = inner[name]
            elif isinstance(stmt, Conditional):
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
                if names.get(name) in self.storage_values:
                    self.emit('storage.write', [names[name], value], source_type=self.types[value], owner_binding=names[name])
                elif stmt.is_var and id(stmt) in self.address_candidates:
                    if self.types[value] not in self.structs or not plain_value(self.types[value], self.structs):
                        raise CompileError(stmt.token, 'mutable borrow requires a resource-free copyable structure')
                    names[name] = self.emit('storage.local', [value], type=self.types[value], storage_relation='local_owner')
                    self.storage_values.add(names[name])
                else:
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
            if param.text in self.storage_names: self.storage_values.add(name)
            params.append({'name': name, 'type': type_name,
                           'mode': 'mutable' if i in self.fn.mutable_params else 'readonly' if i in self.fn.readonly_params else 'borrow' if i in self.fn.borrowed_params else 'value'})
        self.statements(self.fn.body, names, set(self.mutable_names))
        if self.current is not None:
            raise CompileError(self.fn.name, f'function must return a {self.fn.result_type} value on every path')
        check_resources(self.fn, self.expression_types, self.match_types, self.structs, self.signatures)
        check_borrows(self.fn, self.expression_types, self.match_types, self.structs.variants, self.structs, self.signatures)
        return FunctionIR(self.fn.name.text, params, self.blocks, self.fn.result_type, self.fn.effect_contract)


def lower(functions, dependency_audit=None):
    if getattr(functions,"imports",[]):
        raise CompileError(functions.imports[0], "imports require file-based module loading")
    from .memory import error_declaration
    if getattr(functions, 'uses_vec', False):
        from .vectors import declarations
        done, error = declarations()
        functions.structs.append(done)
        functions.enums.append(error)
    if getattr(functions, 'uses_memory', False) or getattr(functions, 'uses_vec', False):
        functions.enums.append(error_declaration())
    from .stdlib import attach
    functions, externals = attach(functions)
    from .generics import Monomorphizer, Signatures
    mono = Monomorphizer(functions)
    structs = structure_types(functions)
    mono.structs = structs
    mono.check_bounds()
    signatures = Signatures({f.name.text: f for f in externals})
    signatures.monomorphizer = mono
    mono.signatures = signatures
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
    worker_symbol = None
    if any(f.name.text == 'workers.run' for f in externals):
        main_module = signatures['main'].module
        worker_symbol = (main_module + '.' if main_module else '') + 'worker'
        worker = signatures.get(worker_symbol)
        if worker is None or worker.generic_params or [t for _, t in worker.params] != ['u32'] or worker.result_type != 'u32' or worker.readonly_params or worker.mutable_params or worker.borrowed_params:
            raise CompileError(signatures['main'].name, 'workers.run requires fn worker(id:u32)->u32 with value parameter in the entry module')
    lowered = []
    dependency_records = {}
    expression_maps = {}
    index = 0
    while index < len(mono.functions):
        fn = mono.functions[index]
        mono.current_chain = fn.instantiation_chain
        try:
            for token, type_name in fn.params + [(fn.name, fn.result_type)]:
                validate_type(type_name, structs, token is not fn.name)
            for i in fn.readonly_params:
                token,t = fn.params[i]
                if t not in structs or (structs[t].properties['copyable'] and not plain_value(t, structs)):
                    raise CompileError(token, 'borrow requires a concrete resource structure or plain copyable structure')
            for i in fn.mutable_params:
                token,t = fn.params[i]
                if t not in structs or not plain_value(t, structs):
                    raise CompileError(token, 'borrow mut requires a resource-free copyable structure')
            if (fn.readonly_params or fn.mutable_params) and not structs.ensure(fn.result_type)['copyable']:
                raise CompileError(fn.name, 'readonly function must return an independent copyable value')
            lowerer = Lowerer(fn, signatures, structs, record_expressions=dependency_audit is not None)
            lowered.append(lowerer.lower())
            dependency_records[fn.name.text] = (fn, lowerer.expression_types, lowerer.match_types, lowered[-1])
            expression_maps[fn.name.text] = lowerer.expression_values
            check_ownership(fn)
        except ValueError as error:
            raise mono.trace(CompileError(fn.name, str(error))) from None
        except CompileError as error:
            raise mono.trace(error) from None
        index += 1
    # The scalar boundary alone does not prove thread-safety. Inspect the
    # complete reachable call graph and allow only audited runtime adapters.
    if worker_symbol:
        by_name = {fn.name: fn for fn in lowered}
        allowed = {
            '__liza_reactor_clock', '__liza_reactor_connect_at', '__liza_reactor_create_at',
            '__liza_reactor_connect', '__liza_reactor_finish_connect', '__liza_reactor_shutdown_write',
            '__liza_reactor_create', '__liza_reactor_accept', '__liza_reactor_port',
            '__liza_reactor_stop_accepting', '__liza_reactor_poll', '__liza_reactor_interest',
            '__liza_reactor_ready', '__liza_reactor_disconnect', '__liza_reactor_close',
            '__liza_reactor_write', 'net.reactor_read', 'net.connection_slot',
        }
        pending, seen = [worker_symbol], set()
        while pending:
            name = pending.pop()
            if name in seen: continue
            seen.add(name)
            fn = by_name.get(name)
            if fn is None:
                if name not in allowed:
                    raise CompileError(signatures[worker_symbol].name, 'worker cannot call unaudited external '+name)
                continue
            for block in fn.blocks:
                for op in block.operations:
                    if op.op == 'call': pending.append(op.callee)
    from .dependencies import check_dependencies
    check_dependencies(dependency_records, structs, signatures, audit=dependency_audit, expression_maps=expression_maps)
    module = ModuleIR(lowered, structs)
    module.specializations = mono.instances
    module.externals = externals
    module.worker_symbol = worker_symbol
    module.modules = getattr(functions,"module_names",[])
    module.declarations = getattr(functions,"declarations",[])
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
    properties = {t: value_properties(t) for t in SCALAR_TYPES + ('Text', 'File', 'Arg', 'Path')}
    properties.update({name: struct.properties for name, struct in structs.items()})
    variants = getattr(module, 'variants', {})
    properties.update({name: v.properties for name, v in variants.items()})
    def describe(t):
        if t in properties or t == 'integer':
            return
        if t in ('memory.Region','net.Listener','net.Stream','net.DatagramSocket','net.Reactor'):
            properties[t] = {'copyable': False, 'implicit_copy': False}
        elif t == 'net.Connection':
            properties[t] = value_properties(t)
        elif is_product(t):
            for component in product_args(t): describe(component)
            properties[t] = {'copyable': False, 'implicit_copy': False}
        elif is_vec(t):
            describe(vec_element(t))
            properties[t] = {'copyable': False, 'implicit_copy': False}
        elif is_buffer(t):
            describe(buffer_element(t))
            properties[t] = {'copyable': False, 'implicit_copy': False}
        elif is_array(t) or is_view(t):
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
    return json.dumps({'version': 20, **({'worker_entry': module.worker_symbol} if getattr(module, 'worker_symbol', None) else {}), 'type_properties': properties,
                       'modules': getattr(module,'modules',[]),
                       'specializations': getattr(module,'specializations',[]),
                       'declarations': getattr(module,'declarations',[]),
                       'structures': [asdict(s) for s in structs.values()],
                       'variants': [asdict(v) for v in variants.values()],
                       'externals': [asdict(fn) for fn in getattr(module, 'externals', [])],
                       'functions': [asdict(fn) for fn in module]}, indent=2) + '\n'
