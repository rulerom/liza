"""Independent cutpoint and byte contracts. No compiler/helper execution."""
import z3
from .semantic import Memory, TOTAL

CAPACITY = 2048
ARRAY = z3.ArraySort(z3.IntSort(), z3.BitVecSort(8))


def valid(d):
    h, t, e, f = d
    return z3.And(0 <= h, h <= t, t <= CAPACITY, z3.Implies(f, z3.And(e, h == t)))


def equal(a, b):
    if isinstance(a, tuple): return z3.And(*[equal(x, y) for x, y in zip(a, b)])
    if isinstance(a, str): return z3.BoolVal(a == b)
    return a == b


def inputs(name):
    direction, operation = name.split('.')
    d = {}
    for side in ('forward', 'reverse'):
        h, t = z3.Ints(side + '_head ' + side + '_tail')
        e, f = z3.Bools(side + '_eof ' + side + '_fin')
        d[side] = (h, t, e, f)
    slot, cr, ur, n, outcome, wn, rn, p, j, local = z3.Ints('slot client_ready upstream_ready count outcome wlen rlen position other_direction local_position')
    failure = z3.Int('failure')
    alive, connected = z3.Bools('alive connected')
    B, R, W, data = z3.Consts('B R W data', ARRAY)
    pair = dict(d, connected=connected, client=('Some', 'client'), upstream=('Some', 'upstream'))
    values = dict(pair=pair, slot=slot, client_ready=cr, upstream_ready=ur, count=n,
                  outcome=outcome, alive=alive, data=data, failure=failure,
                  client='client', upstream='upstream', reactor='reactor')
    memory = Memory(B, R, W, rn, wn)
    base = 4096*slot + (0 if direction == 'forward' else CAPACITY)
    h, t, e, f = d[direction]
    flags = cr if direction == 'forward' else ur
    ready = z3.BV2Int(z3.Int2BV(flags, 32) & z3.BitVecVal(5, 32)) != 0
    if operation == 'read': enabled = z3.And(alive, z3.Not(e), t < CAPACITY, ready, connected if direction == 'reverse' else True)
    elif operation == 'write': enabled = z3.And(alive, connected, h < t)
    else: enabled = z3.And(alive, connected, e, h == t, z3.Not(f))
    requested = CAPACITY-t if operation == 'read' else t-h if operation == 'write' else z3.IntVal(0)
    domain = z3.And(valid(d['forward']), valid(d['reverse']), 0 <= slot, slot < 8,
                    0 <= cr, cr < 2**32, 0 <= ur, ur < 2**32,
                    0 <= failure, failure < 2**32,
                    0 <= n, n <= CAPACITY, 0 <= outcome, outcome <= 4, wn >= 0,
                    z3.Implies(enabled, outcome != 4),
                    n == 0 if operation == 'fin' else True,
                    rn == wn+t-h,
                    z3.Implies(outcome != 0, n == 0),
                    z3.Implies(z3.And(enabled, outcome == 0),
                               z3.And(n <= requested, n >= (1 if operation == 'write' else 0))),
                    z3.Implies(z3.And(0 <= p, p < rn),
                               z3.Select(R, p) == z3.If(p < wn, z3.Select(W, p), z3.Select(B, base+h+p-wn))))
    return values, memory, domain, dict(base=base, enabled=enabled, requested=requested,
                                       position=p, other=j, local=local, direction=direction, operation=operation)


def properties(values, before, context, pair, alive, after):
    direction, op = context['direction'], context['operation']
    h, t, e, f = values['pair'][direction]; n = values['count']; base = context['base']; p = context['position']
    call = after.call
    called = call is not None
    peer = ('client' if direction == 'forward' else 'upstream') if op == 'read' else ('upstream' if direction == 'forward' else 'client')
    binding = z3.BoolVal(True)
    if called:
        binding = z3.And(z3.BoolVal(call['connection'] == peer),
                         call['offset'] == (base + (t if op == 'read' else h) if op != 'fin' else 0),
                         call['requested'] == context['requested'])
        if op != 'fin': binding = z3.And(binding, call['offset'] >= base, call['requested'] > 0,
                                         call['offset']+call['requested'] <= base+CAPACITY,
                                         call['offset'] >= 0, call['offset']+call['requested'] <= TOTAL)
    result = {'call_binding_and_guard': z3.And(binding, z3.BoolVal(called) == context['enabled'])}
    if after.fatal:
        result['fatal_stops_direction'] = z3.Not(alive)
        return result
    success = z3.And(z3.BoolVal(called), values['outcome'] == 0)
    expected_d = (h, t, e, f)
    if op == 'read': expected_d = (h, z3.If(success, t+n, t), z3.If(success, n == 0, e), f)
    elif op == 'write':
        expected_d = (z3.If(success, z3.If(h+n == t, 0, h+n), h), z3.If(z3.And(success, h+n == t), 0, t), e, f)
    else: expected_d = (h, t, e, z3.If(success, True, f))
    other_side = 'reverse' if direction == 'forward' else 'forward'
    nh, nt, _, _ = pair[direction]
    result['state_and_count_binding'] = z3.And(equal(pair[direction], expected_d), valid(pair[direction]),
                                              equal(pair[other_side], values['pair'][other_side]),
                                              equal(pair['client'], values['pair']['client']), equal(pair['upstream'], values['pair']['upstream']),
                                              pair['connected'] == values['pair']['connected'], alive == values['alive'])
    result['byte_conservation'] = z3.And(after.rlen == after.wlen+nt-nh,
        z3.Implies(z3.And(0 <= p, p < after.rlen), z3.Select(after.R, p) ==
                   z3.If(p < after.wlen, z3.Select(after.W, p), z3.Select(after.B, base+nh+p-after.wlen))))
    changed = z3.And(success, z3.BoolVal(op == 'read'), base+t <= p, p < base+t+n)
    result['exact_buffer_frame'] = z3.Implies(z3.And(0 <= p, p < TOTAL),
        z3.Select(after.B, p) == z3.If(changed, z3.Select(values['data'], p-base-t), z3.Select(before.B, p)))
    j, local = context['other'], context['local']; address = CAPACITY*j+local
    result['other_directions_unchanged'] = z3.Implies(z3.And(0 <= j, j < 16, j != base/CAPACITY, 0 <= local, local < CAPACITY),
                                                    z3.Select(after.B, address) == z3.Select(before.B, address))
    expected_wlen = before.wlen + z3.If(z3.And(success, z3.BoolVal(op == 'write')), n, 0)
    expected_rlen = before.rlen + z3.If(z3.And(success, z3.BoolVal(op == 'read')), n, 0)
    result['exact_histories'] = z3.And(after.wlen == expected_wlen, after.rlen == expected_rlen,
        z3.Implies(z3.And(0 <= p, p < after.wlen), z3.Select(after.W, p) ==
                   z3.If(p < before.wlen, z3.Select(before.W, p), z3.Select(before.B, base+h+p-before.wlen))),
        z3.Implies(z3.And(0 <= p, p < after.rlen), z3.Select(after.R, p) ==
                   z3.If(p < before.rlen, z3.Select(before.R, p), z3.Select(values['data'], p-before.rlen))))
    if op == 'write':
        result['pending_suffix'] = z3.Implies(z3.And(success, 0 <= p, p < nt-nh),
                                             z3.Select(after.B, base+nh+p) == z3.Select(before.B, base+h+n+p))
    return result
