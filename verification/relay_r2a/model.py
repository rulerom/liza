"""R2-A mathematical buffer model; no Liza/compiler/runtime imports.

A sequence is (length, Int -> BV8). Equality is length equality plus equality
at every in-range position. Obligations leave the position free: UNSAT proves
the property for all positions, not a finite sample. Buffer addresses are 0..2047.
"""
from dataclasses import dataclass, replace
import z3

CAPACITY = 2048
BYTE_ARRAY = z3.ArraySort(z3.IntSort(), z3.BitVecSort(8))
OPERATIONS = ('read', 'write', 'would_block', 'eof', 'fin')
MUTATIONS = {
    'read_offset_plus_one': 'read',
    'read_overwrites_queue': 'read',
    'read_corrupts_byte': 'read',
    'read_when_full': 'read',
    'write_from_tail': 'write',
    'write_swaps_bytes': 'write',
    'write_consumes_extra': 'write',
    'write_reset_keeps_tail': 'write',
    'would_block_changes_buffer': 'would_block',
    'eof_discards_queue': 'eof',
    'premature_fin': 'fin',
}


@dataclass(frozen=True)
class State:
    R: object
    W: object
    B: object
    rlen: object
    wlen: object
    head: object
    tail: object
    eof: object
    fin: object


@dataclass(frozen=True)
class Step:
    state: State
    # Exact physical buffer footprint used by the model operation, not a proof
    # annotation inferred from expected head/tail after the transition.
    accesses: tuple = ()


def symbolic():
    R, W, B, data = z3.Consts('R W B data', BYTE_ARRAY)
    rlen, wlen, head, tail, count, position = z3.Ints('rlen wlen head tail count position')
    eof, fin = z3.Bools('eof fin')
    return State(R, W, B, rlen, wlen, head, tail, eof, fin), data, count, position


def scalars(s):
    return z3.And(0 <= s.head, s.head <= s.tail, s.tail <= CAPACITY,
                  0 <= s.wlen, s.rlen == s.wlen + s.tail - s.head,
                  z3.Implies(s.fin, z3.And(s.eof, s.head == s.tail)))


def byte_at(s, i):
    return z3.Implies(z3.And(0 <= i, i < s.rlen),
                      z3.Select(s.R, i) == z3.If(i < s.wlen, z3.Select(s.W, i),
                                               z3.Select(s.B, s.head + i - s.wlen)))


def eligible(s, operation, n, mutation=''):
    if operation == 'read':
        if mutation == 'read_when_full':
            return z3.And(z3.Not(s.eof), 0 < n, n <= z3.If(s.tail == CAPACITY, 1, CAPACITY-s.tail))
        return z3.And(z3.Not(s.eof), 0 < n, n <= CAPACITY-s.tail)
    if operation == 'write': return z3.And(0 < n, n <= s.tail-s.head)
    if operation == 'would_block': return z3.BoolVal(True)
    if operation == 'eof': return z3.And(z3.Not(s.eof), s.tail < CAPACITY)
    if operation == 'fin':
        return z3.And(s.eof, z3.Not(s.fin), z3.BoolVal(True) if mutation == 'premature_fin' else s.head == s.tail)
    raise ValueError(operation)


def splice(destination, start, source, source_start, n, corrupt=False):
    i = z3.Int('splice_index')
    byte = z3.Select(source, source_start+i-start)
    if corrupt: byte = byte ^ z3.BitVecVal(1, 8)
    return z3.Lambda(i, z3.If(z3.And(start <= i, i < start+n), byte, z3.Select(destination, i)))


def transition(s, operation, data, n, mutation=''):
    if operation == 'read':
        start = s.tail+1 if mutation == 'read_offset_plus_one' else s.head if mutation == 'read_overwrites_queue' else s.tail
        return Step(replace(s, R=splice(s.R, s.rlen, data, 0, n), rlen=s.rlen+n,
                            B=splice(s.B, start, data, 0, n, mutation == 'read_corrupts_byte'), tail=s.tail+n), ((start, n),))
    if operation == 'write':
        start = s.tail if mutation == 'write_from_tail' else s.head
        output = splice(s.W, s.wlen, s.B, start, n)
        if mutation == 'write_swaps_bytes':
            i = z3.Int('swap_index')
            output = z3.Lambda(i, z3.If(z3.And(n >= 2, i == s.wlen), z3.Select(s.B, s.head+1),
                                     z3.If(z3.And(n >= 2, i == s.wlen+1), z3.Select(s.B, s.head), z3.Select(output, i))))
        advance = n+1 if mutation == 'write_consumes_extra' else n
        drained = s.head+advance == s.tail
        return Step(replace(s, W=output, wlen=s.wlen+n,
                            head=z3.If(drained, 0, s.head+advance),
                            tail=s.tail if mutation == 'write_reset_keeps_tail' else z3.If(drained, 0, s.tail)), ((start, n),))
    if operation == 'would_block':
        return Step(replace(s, B=z3.Store(s.B, s.head, z3.Select(s.B, s.head) ^ z3.BitVecVal(1, 8))), ((s.head, 1),)) if mutation else Step(s)
    if operation == 'eof': return Step(replace(s, eof=z3.BoolVal(True), tail=s.head if mutation else s.tail))
    if operation == 'fin': return Step(replace(s, fin=z3.BoolVal(True)))
    raise ValueError(operation)


def contracts(old, new, operation, data, n, i):
    """Observable postconditions, separate from transition construction."""
    B, R, W = (z3.Select(a, i) for a in (old.B, old.R, old.W))
    expected_B, expected_R, expected_W = B, R, W
    h, t, e, f = old.head, old.tail, old.eof, old.fin
    rn, wn = old.rlen, old.wlen
    if operation == 'read':
        expected_B = z3.If(z3.And(old.tail <= i, i < old.tail+n), z3.Select(data, i-old.tail), B)
        expected_R = z3.If(i >= old.rlen, z3.Select(data, i-old.rlen), R)
        t, rn = old.tail+n, old.rlen+n
    elif operation == 'write':
        expected_W = z3.If(i >= old.wlen, z3.Select(old.B, old.head+i-old.wlen), W)
        h = z3.If(n == old.tail-old.head, 0, old.head+n)
        t = z3.If(n == old.tail-old.head, 0, old.tail)
        wn = old.wlen+n
    elif operation == 'eof': e = z3.BoolVal(True)
    elif operation == 'fin': f = z3.BoolVal(True)
    return {
        'state': z3.And(scalars(new), new.head == h, new.tail == t,
                        new.eof == e, new.fin == f, new.rlen == rn, new.wlen == wn),
        'conservation': byte_at(new, i),
        'buffer_frame_and_bytes': z3.Implies(z3.And(0 <= i, i < CAPACITY), z3.Select(new.B, i) == expected_B),
        'read_history': z3.Implies(z3.And(0 <= i, i < new.rlen), z3.Select(new.R, i) == expected_R),
        'write_history': z3.Implies(z3.And(0 <= i, i < new.wlen), z3.Select(new.W, i) == expected_W),
    }


def queries(operation, mutation=''):
    s, data, n, i = symbolic()
    step = transition(s, operation, data, n, mutation)
    # Universal old byte invariant is instantiated at the arbitrary observation
    # index. This is a WEAKER precondition; UNSAT still implies preservation for
    # every valid state. SAT must be replayed after constructing a fully valid R.
    pre = z3.And(scalars(s), 0 <= n, n < 2**32, eligible(s, operation, n, mutation), byte_at(s, i))
    post = contracts(s, step.state, operation, data, n, i)
    post['access_bounds'] = z3.And(*[z3.And(0 <= start, 0 < size, start+size <= CAPACITY) for start, size in step.accesses])
    return s, data, n, i, pre, post


def endpoints():
    s, _, _, i = symbolic()
    initial = replace(s, rlen=z3.IntVal(0), wlen=z3.IntVal(0), head=z3.IntVal(0), tail=z3.IntVal(0),
                      eof=z3.BoolVal(False), fin=z3.BoolVal(False))
    yield 'initial.state', z3.BoolVal(True), scalars(initial)
    yield 'initial.conservation', z3.BoolVal(True), byte_at(initial, i)
    pre = z3.And(scalars(s), byte_at(s, i), s.fin)
    yield 'completed.lengths', pre, s.rlen == s.wlen
    yield 'completed.bytes', pre, z3.Implies(z3.And(0 <= i, i < s.rlen), z3.Select(s.R, i) == z3.Select(s.W, i))
