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
