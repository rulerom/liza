"""Vector library signatures with explicit region-local growth. Calls use ordinary argument evaluation."""
from dataclasses import replace
import hashlib
from .frontend import Function, Token, CompileError, Struct, Enum
from .types import is_vec, vec_element, product_type


def declarations():
    return (Struct(Token('vec.Done', 1, 1), []),
            Enum(Token('vec.Error', 1, 1), [(Token(n, 1, 1), None) for n in ('Full', 'OutOfBounds')]))


def signature(node, actuals, mono):
    operation = node.token.text.removeprefix('vec.')
    if operation not in ('with_capacity', 'push', 'pop', 'get', 'set', 'len', 'capacity', 'view', 'release', 'reserve'):
        raise CompileError(node.token, 'unknown vec operation')
    if operation == 'with_capacity':
        if len(node.type_args) != 1:
            raise CompileError(node.token, 'vec.with_capacity requires one explicit element type')
        element = mono.concrete_type(node.type_args[0], node.token)
        if not mono.structs.ensure(element)['copyable']:
            raise CompileError(node.token, 'vectors require copyable elements')
    else:
        if node.type_args:
            raise CompileError(node.token, 'only vec.with_capacity accepts explicit type arguments')
        if not actuals or actuals[0] is None: return None
        if not is_vec(actuals[0]): raise CompileError(node.token, 'expected vec.Vec<T>')
        element = vec_element(actuals[0])
    vector = 'vec.Vec<'+element+'>'
    status = 'Result<vec.Done,vec.Error>'
    parameters, result, borrowed, effect = {
        'with_capacity': (['memory.Region', 'u32'], 'Result<'+vector+',MemoryError>', [0], 'alloc'),
        'reserve': ([vector, 'memory.Region', 'u32'], product_type(vector, 'Result<vec.Done,MemoryError>'), [1], 'alloc'),
        'push': ([vector, element], product_type(vector, status), [], 'pure'),
        'pop': ([vector], product_type(vector, 'Option<'+element+'>'), [], 'pure'),
        'get': ([vector, 'u32'], 'Option<'+element+'>', [0], 'pure'),
        'set': ([vector, 'u32', element], product_type(vector, status), [], 'pure'),
        'len': ([vector], 'u32', [0], 'pure'),
        'capacity': ([vector], 'u32', [0], 'pure'),
        'view': ([vector], 'View<'+element+'>', [0], 'pure'),
        'release': ([vector], 'u32', [], 'pure'),
    }[operation]
    if len(actuals) != len(parameters):
        raise CompileError(node.token, 'wrong number of vec operation arguments')
    symbol = 'vec$'+operation+'$'+hashlib.sha256(element.encode()).hexdigest()
    fn = Function(replace(node.token, text=symbol), [(Token('p'+str(i),1,1),t) for i,t in enumerate(parameters)], [], result, effect, borrowed_params=borrowed)
    fn.memory_operation = 'vec.'+('create' if operation == 'with_capacity' else operation)
    fn.memory_element = element
    mono.signatures[symbol] = fn
    mono.structs.ensure(result)
    return fn
