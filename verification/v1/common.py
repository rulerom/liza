import z3 as z


class Unsupported(ValueError):
    pass


def bit(condition):
    return z.If(condition,z.BitVecVal(1,1),z.BitVecVal(0,1))


def collect(exits, violations=()):
    return {'trap':z.Or(*[p for kind,p,v in exits if kind=='Trap']),
            'undefined':z.Or(*[p for kind,p,v in exits if kind=='Undefined']),
            'returns':[(p,v) for kind,p,v in exits if kind=='Return'],
            'covered':z.Or(*[p for kind,p,v in exits]),
            'violations':list(violations)}


def scalar(value,width):
    if not z.is_bv(value) or value.size()!=width:raise Unsupported('scalar type mismatch')
    return value
