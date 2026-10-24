"""Independent fixed mathematical contracts; no compiler imports.

16 bits represent every mathematical add/sub/mul result of two signed i8s.
For u8 subtraction, signed 17 bits also represent negative results and 65025.
No arithmetic in this specification overflows its widened representation.
"""
import z3 as z

SUBJECTS = tuple(f'{op}_{ty}' for ty in ('u8', 'i8')
                 for op in ('add', 'sub', 'mul', 'sequence', 'branch'))


def inputs(name):
    op, ty = name.split('_')
    args = [z.BitVec('x', 8)]
    if op in ('add', 'sub', 'mul'):
        args.append(z.BitVec('y', 8))
    elif op == 'branch':
        args.append(z.BitVec('take', 1))
    return args


def specification(name, args):
    op, ty = name.split('_')
    extend = z.SignExt if ty == 'i8' else z.ZeroExt
    x = extend(9, args[0])
    lo, hi = (-128, 127) if ty == 'i8' else (0, 255)
    if op in ('sequence', 'branch'):
        wide = x + 1
        trap = wide > hi
        if op == 'sequence':
            return trap, args[0]
        take = args[1] == 1
        return z.And(take, trap), z.If(take, z.Extract(7, 0, wide), args[0])
    y = extend(9, args[1])
    wide = {'add': lambda: x+y, 'sub': lambda: x-y, 'mul': lambda: x*y}[op]()
    return z.Or(wide < lo, wide > hi), z.Extract(7, 0, wide)


def concrete(name, values):
    """Ordinary unbounded Python integers: independent replay of counterexamples."""
    op, ty = name.split('_')
    values = list(values)
    if ty == 'i8':
        values[0] = values[0] if values[0] < 128 else values[0]-256
        if op in ('add', 'sub', 'mul'):
            values[1] = values[1] if values[1] < 128 else values[1]-256
    x = values[0]
    lo, hi = (-128, 127) if ty == 'i8' else (0, 255)
    if op == 'branch' and not values[1]:
        return False, x % 256
    if op in ('sequence', 'branch'):
        v = x+1
    else:
        y = values[1]
        v = {'add': lambda: x+y, 'sub': lambda: x-y, 'mul': lambda: x*y}[op]()
    trap = not lo <= v <= hi
    return trap, (x if op == 'sequence' else v) % 256
