"""Independent mathematical contract. No compiler or subject-module imports."""
import z3

SUBJECTS = ('empty', 'valid', 'readable', 'queued', 'read', 'write', 'needs_fin', 'shutdown')
FIELDS = ('head', 'tail', 'eof', 'fin')
ERR = ('Err', ('InvalidTransition',))


def cases(name, d, n):
    """Disjoint, exhaustive expected outcomes over mathematical integers."""
    h, t, e, f = d
    valid = z3.And(0 <= h, h <= t, t <= 2048, z3.Implies(f, z3.And(e, h == t)))
    ready = z3.And(valid, e, h == t, z3.Not(f))
    yes = z3.BoolVal(True)
    if name == 'empty': return [(yes, (0, 0, False, False))]
    if name == 'valid': return [(yes, valid)]
    if name == 'readable': return [(yes, z3.If(z3.And(valid, z3.Not(e)), 2048-t, 0))]
    if name == 'queued': return [(yes, z3.If(valid, t-h, 0))]
    if name == 'needs_fin': return [(yes, ready)]
    if name == 'shutdown':
        return [(ready, ('Ok', (h, t, True, True))), (z3.Not(ready), ERR)]
    if name == 'read':
        allowed = z3.And(valid, z3.Not(e), t < 2048, n <= 2048-t)
        return [(z3.Not(allowed), ERR),
                (z3.And(allowed, n == 0), ('Ok', (h, t, True, False))),
                (z3.And(allowed, n > 0), ('Ok', (h, t+n, False, False)))]
    if name == 'write':
        allowed = z3.And(valid, n > 0, n <= t-h)
        return [(z3.Not(allowed), ERR),
                (z3.And(allowed, h+n == t), ('Ok', (0, 0, e, f))),
                (z3.And(allowed, h+n != t), ('Ok', (h+n, t, e, f)))]
    raise ValueError(name)


def concrete(name, d, n):
    """Concrete oracle, independent of either IR executor."""
    h, t, e, f = d
    valid = 0 <= h <= t <= 2048 and (not f or (e and h == t))
    ready = valid and e and h == t and not f
    if name == 'empty': return (0, 0, False, False)
    if name == 'valid': return valid
    if name == 'readable': return 2048-t if valid and not e else 0
    if name == 'queued': return t-h if valid else 0
    if name == 'needs_fin': return ready
    if name == 'shutdown': return ('Ok', (h, t, True, True)) if ready else ERR
    if name == 'read':
        if not valid or e or t == 2048 or n > 2048-t: return ERR
        return ('Ok', (h, t, True, False) if n == 0 else (h, t+n, False, False))
    if name == 'write':
        if not valid or n == 0 or n > t-h: return ERR
        return ('Ok', (0, 0, e, f) if h+n == t else (h+n, t, e, f))
    raise ValueError(name)
