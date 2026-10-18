"""Infer literal contexts without emitting or reordering executable operations."""
from .frontend import CompileError
from .types import INTEGER_TYPES, bounds, signed, convert_integer


class TypeVariable:
    def __init__(self):
        self.parent = self
        self.type = None

    def root(self):
        if self.parent is not self:
            self.parent = self.parent.root()
        return self.parent


def infer_expression(expr, names, value_types, signatures, expected=None):
    variables, integers, signed_operands, literals = {}, [], [], []

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
        if node.kind == 'literal':
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
        elif node.kind == 'bool':
            bind(var, 'bool', token)
        elif node.kind == 'name':
            if token.text not in names:
                raise CompileError(token, f'unknown value {token.text!r}')
            bind(var, value_types[names[token.text]], token)
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
    for var in variables.values():
        if var.root().type is None:
            var.root().type = 'u32'
    for var, token in integers:
        if var.root().type not in INTEGER_TYPES:
            raise CompileError(token, f'expected integer, got {var.root().type}')
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
