"""Infer literal contexts without emitting or reordering executable operations."""
from .frontend import CompileError
from .types import INTEGER_TYPES, SCALAR_TYPES, bounds, signed, convert_integer, is_array, is_view, element_type, array_type, array_length, validate_type, generic_args


class TypeVariable:
    def __init__(self):
        self.parent = self
        self.type = None

    def root(self):
        if self.parent is not self:
            self.parent = self.parent.root()
        return self.parent


def infer_expression(expr, names, value_types, signatures, expected=None, structs=None, access_module=""):
    if structs is None:
        structs = {}
    variants = getattr(structs, "variants", {})
    constructors = []
    variables, integers, signed_operands, literals = {}, [], [], []
    scalars, arrays, projections, derived, empty_elements = [], [], [], [], []

    def bind(var, type_name, token):
        root = var.root()
        if root.type and root.type != type_name:
            raise CompileError(token, f'expected {type_name}, got {root.type}')
        root.type = type_name

    def unify(left, right, token):
        left, right = left.root(), right.root()
        if left is right:
            return
        if left.type and right.type and left.type != right.type:
            raise CompileError(token, f'expected {left.type}, got {right.type}')
        left.type = left.type or right.type
        right.parent = left

    def visit(node):
        var = TypeVariable()
        variables[id(node)] = var
        token = node.token
        if node.kind == 'text':
            bind(var, 'Text', token)
        elif node.kind == 'literal':
            integers.append((var, token))
            literals.append((var, token))
        elif node.kind.startswith('convert.'):
            bind(var, token.text, token)
            arg = node.args[0]
            if arg.kind == 'literal':
                literal_var = TypeVariable()
                literal_var.type = 'integer'
                variables[id(arg)] = literal_var
                try:
                    value = int(arg.token.text, 16 if arg.token.text.lstrip('-').startswith('0x') else 10)
                    convert_integer(value, token.text, node.kind.split('.')[1])
                except ValueError as error:
                    raise CompileError(arg.token, str(error)) from None
            else:
                integers.append((visit(arg), arg.token))
        elif node.kind in ('copy', 'move'):
            unify(var, visit(node.args[0]), token)
        elif node.kind == 'bool':
            bind(var, 'bool', token)
        elif node.kind == 'name':
            if token.text not in names:
                raise CompileError(token, f'unknown value {token.text!r}')
            bind(var, value_types[names[token.text]], token)
        elif node.kind == 'variant':
            if '.' in token.text:
                type_name, case = token.text.rsplit('.',1)
                bind(var, type_name, token)
            constructors.append((node, var, [visit(arg) for arg in node.args]))
            derived.append(var)
        elif node.kind == 'array':
            element = TypeVariable()
            for arg in node.args:
                unify(element, visit(arg), arg.token)
            arrays.append((var, element, len(node.args), token))
            derived.append(var)
            if not node.args:
                empty_elements.append(element)
        elif node.kind in ('index', 'view', 'field'):
            source = visit(node.args[0])
            for arg in node.args[1:]:
                bind(visit(arg), 'u32', arg.token)
            projections.append((node.kind, var, source, token))
            derived.append(var)
        elif node.kind == 'call' and token.text in structs:
            structure = structs[token.text]
            visibility = getattr(structs, "visibility", {}).get(token.text)
            if visibility and visibility[0] != access_module and any(f not in visibility[1] for f,_ in structure.fields):
                raise CompileError(token, "constructor contains private fields: "+token.text)
            if len(node.args) != len(structure.fields):
                raise CompileError(token, f'wrong number of constructor arguments for {token.text!r}')
            for arg, (_, type_name) in zip(node.args, structure.fields):
                bind(visit(arg), type_name, arg.token)
            bind(var, token.text, token)
        elif node.kind == 'call':
            if token.text not in signatures:
                raise CompileError(token, f'unknown function {token.text!r}')
            fn = signatures[token.text]
            if len(node.args) != len(fn.params):
                raise CompileError(token, f'wrong number of arguments for {token.text!r}')
            for arg, (_, type_name) in zip(node.args, fn.params):
                bind(visit(arg), type_name, arg.token)
            bind(var, fn.result_type, token)
        else:
            args = [visit(arg) for arg in node.args]
            if node.kind == 'not' or token.text in ('&&', '||'):
                bind(var, 'bool', token)
                for arg in args:
                    bind(arg, 'bool', token)
            elif token.text in ('==', '!=', '<', '<=', '>', '>='):
                bind(var, 'bool', token)
                unify(args[0], args[1], token)
                if token.text not in ('==', '!='):
                    integers.append((args[0], token))
                else:
                    scalars.append((args[0], token))
            elif token.text in ('<<', '>>'):
                unify(var, args[0], token)
                integers.append((var, token))
                bind(args[1], 'u32', node.args[1].token)
            else:
                integers.append((var, token))
                for arg in args:
                    unify(var, arg, token)
                if node.kind == 'neg':
                    signed_operands.append((var, token))
        return var

    root = visit(expr)
    if expected:
        bind(root, expected, expr.token)
    # Composite constraints propagate context both into literals and out of
    # typed elements. Do not default a composite or an empty element to u32.
    def solve():
        changed = True
        while changed:
            before = tuple(v.root().type for v in list(variables.values()) + [e for _, e, _, _ in arrays])
            for node, result, payloads in constructors:
                case = node.token.text.rsplit('.',1)[-1]
                t = result.root().type
                if t is None and case == 'Some' and len(payloads)==1 and payloads[0].root().type:
                    t = 'Option<'+payloads[0].root().type+'>'
                    bind(result, t, node.token)
                if t is None:
                    continue
                try:
                    validate_type(t, structs, False)
                except ValueError as error:
                    raise CompileError(node.token, str(error)) from None
                if t not in variants or case not in dict(variants[t].cases):
                    raise CompileError(node.token, 'constructor does not belong to expected variant type')
                if '.' not in node.token.text and generic_args(t) is None:
                    raise CompileError(node.token, 'user variant constructors require Type.Alternative')
                payload = dict(variants[t].cases)[case]
                if len(payloads) != (0 if payload is None else 1):
                    raise CompileError(node.token, 'wrong number of variant payload arguments')
                if payload is not None:
                    bind(payloads[0], payload, node.token)
            for aggregate, element, count, token in arrays:
                t = aggregate.root().type
                if t:
                    if not is_array(t) or array_length(t) != count:
                        raise CompileError(token, 'array literal length/type mismatch')
                    bind(element, element_type(t), token)
                if element.root().type:
                    if is_view(element.root().type):
                        raise CompileError(token, 'views cannot be stored in arrays')
                    bind(aggregate, array_type(element.root().type, count), token)
            for kind, result, source, token in projections:
                t = source.root().type
                if not t:
                    if kind == 'index' and result.root().type:
                        for aggregate, element, _, _ in arrays:
                            if aggregate.root() is source.root():
                                bind(element, result.root().type, token)
                    continue
                if kind == 'field':
                    if token.text == 'len' and (is_array(t) or is_view(t) or t == 'Text'):
                        bind(result, 'u32', token)
                        continue
                    if t not in structs:
                        raise CompileError(token, 'field access requires a structure value')
                    fields = dict(structs[t].fields)
                    if token.text not in fields:
                        raise CompileError(token, f'unknown field {token.text!r} in {t}')
                    visibility = getattr(structs, "visibility", {}).get(t)
                    if visibility and visibility[0] != access_module and token.text not in visibility[1]:
                        raise CompileError(token, f"private field {t}.{token.text}")
                    bind(result, fields[token.text], token)
                else:
                    if not is_array(t) and not (kind == 'index' and is_view(t)):
                        raise CompileError(token, 'view requires an array binding' if kind == 'view' else 'index requires array or view')
                    target = element_type(t)
                    bind(result, f'View<{target}>' if kind == 'view' else target, token)
            after = tuple(v.root().type for v in list(variables.values()) + [e for _, e, _, _ in arrays])
            changed = before != after
    solve()
    excluded = {v.root() for v in derived + empty_elements}
    for var in variables.values():
        if var.root().type is None and var.root() not in excluded:
            var.root().type = 'u32'
    solve()
    if any(v.root().type is None for v in variables.values()):
        raise CompileError(expr.token, 'cannot infer composite type; provide a type annotation')
    for var, token in integers:
        if var.root().type not in INTEGER_TYPES:
            raise CompileError(token, f'expected integer, got {var.root().type}')
    for var, token in scalars:
        if var.root().type not in SCALAR_TYPES:
            raise CompileError(token, 'equality is only defined for scalar types')
    for var, token in signed_operands:
        if not signed(var.root().type):
            raise CompileError(token, 'negation requires a signed integer')
    for var, token in literals:
        type_name = var.root().type
        try:
            value = int(token.text, 16 if token.text.lstrip('-').startswith('0x') else 10)
        except ValueError:
            raise CompileError(token, f'invalid {type_name} literal') from None
        low, high = bounds(type_name)
        if not low <= value <= high:
            raise CompileError(token, f'literal is outside {type_name} range')
    return {key: var.root().type for key, var in variables.items()}
