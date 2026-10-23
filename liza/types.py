"""Logical scalar types. No target ABI or LLVM representation belongs here."""
INTEGER_TYPES = tuple(f'{sign}{width}' for sign in ('u', 'i') for width in (8, 16, 32, 64))
SCALAR_TYPES = INTEGER_TYPES + ('bool',)


def width(type_name):
    return int(type_name[1:])


def signed(type_name):
    return type_name.startswith('i')


def bounds(type_name):
    bits = width(type_name)
    return (-(1 << (bits - 1)), (1 << (bits - 1)) - 1) if signed(type_name) else (0, (1 << bits) - 1)


def convert_integer(value, target, mode):
    """Mathematical conversion for compile-time integers, independent of LLVM."""
    low, high = bounds(target)
    if mode == 'wrap':
        modulus = 1 << width(target)
        result = value % modulus
        return result - modulus if signed(target) and result > high else result
    if mode == 'saturate':
        return max(low, min(high, value))
    if mode != 'checked':
        raise ValueError(f'unknown conversion mode: {mode}')
    if not low <= value <= high:
        raise ValueError(f'literal is outside {target} range')
    return value


def value_properties(type_name):
    """Semantic capabilities, independent of byte size and target layout."""
    if type_name == 'File':
        return {'copyable': False, 'implicit_copy': False}
    if type_name not in SCALAR_TYPES + ('Text',):
        raise ValueError(f'unknown value type: {type_name}')
    return {'copyable': True, 'implicit_copy': True}


def is_array(t):
    return t.startswith('[')


def is_view(t):
    return t.startswith('View<')


def element_type(t):
    return t[1:-1].rsplit(';', 1)[0] if is_array(t) else t[5:-1]


def array_length(t):
    return int(t[1:-1].rsplit(';', 1)[1])


def array_type(element, length):
    return f'[{element};{length}]'


def validate_type(t, structs, allow_view=True):
    if hasattr(structs, "ensure"):
        return structs.ensure(t, allow_view)
    if is_array(t):
        validate_type(element_type(t), structs, False)
    elif is_view(t):
        if not allow_view:
            raise ValueError('views cannot be stored in aggregates or returned')
        validate_type(element_type(t), structs, False)
    elif t not in SCALAR_TYPES and t not in structs:
        raise ValueError(f'unknown type {t!r}')


def generic_args(t):
    if not t.startswith(('Option<', 'Result<')):
        return None
    depth, start, args = 0, t.index('<')+1, []
    for i in range(start, len(t)-1):
        c = t[i]
        if c in '<[': depth += 1
        elif c in '>]': depth -= 1
        elif c == ',' and depth == 0:
            args.append(t[start:i]); start = i+1
    args.append(t[start:-1])
    return args


def type_application(t):
    """Split a named application, including user generics and capacity arguments."""
    if '<' not in t or t.startswith('['): return None
    head, tail = t.split('<',1)
    if not t.endswith('>'): return None
    depth, start, args = 0, 0, []
    for i,c in enumerate(tail[:-1]):
        if c in '<[': depth += 1
        elif c in '>]': depth -= 1
        elif c == ',' and depth == 0:
            args.append(tail[start:i]); start=i+1
    args.append(tail[start:-1])
    return head,args


def is_buffer(t):
    return t.startswith('memory.Buffer<')


def buffer_element(t):
    return t[len('memory.Buffer<'):-1]


def effects(contract):
    return set(contract.split(',')) - {'pure'}


def is_vec(t):
    return t.startswith('vec.Vec<')


def vec_element(t):
    return t[len('vec.Vec<'):-1]


def product_type(a, b):
    return '__liza_Product<'+a+','+b+'>'


def is_product(t):
    return t.startswith('__liza_Product<')


def product_args(t):
    return type_application(t)[1]
