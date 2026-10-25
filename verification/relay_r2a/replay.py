"""Concrete byte-list replay of mathematical controls; NOT IR execution."""
from copy import deepcopy

CAPACITY = 2048


def valid(s):
    h, t = s['head'], s['tail']
    return (len(s['B']) == CAPACITY and 0 <= h <= t <= CAPACITY
            and all(type(b) is int and 0 <= b <= 255 for field in ('B', 'R', 'W') for b in s[field])
            and s['R'] == s['W'] + s['B'][h:t]
            and (not s['fin'] or (s['eof'] and h == t)))


def eligible(s, op, n, mutation=''):
    h, t = s['head'], s['tail']
    if op == 'read': return not s['eof'] and 0 < n <= (1 if mutation == 'read_when_full' and t == CAPACITY else CAPACITY-t)
    if op == 'write': return 0 < n <= t-h
    if op == 'eof': return not s['eof'] and t < CAPACITY
    if op == 'fin': return s['eof'] and not s['fin'] and (mutation == 'premature_fin' or h == t)
    if op == 'would_block': return True
    raise ValueError(op)


def execute(s, op, n, data, mutation=''):
    out = deepcopy(s); h, t = s['head'], s['tail']
    def check(start, count):
        if not 0 <= start < start+count <= CAPACITY:
            raise ValueError('access_bounds')
    if op == 'read':
        start = t+1 if mutation == 'read_offset_plus_one' else h if mutation == 'read_overwrites_queue' else t
        check(start, n)
        if len(data) != n: raise ValueError('data length')
        out['B'][start:start+n] = [b ^ 1 for b in data] if mutation == 'read_corrupts_byte' else data
        out['R'].extend(data); out['tail'] += n
    elif op == 'write':
        start = t if mutation == 'write_from_tail' else h
        check(start, n)
        sent = s['B'][start:start+n]
        if mutation == 'write_swaps_bytes' and n >= 2: sent[0], sent[1] = sent[1], sent[0]
        out['W'].extend(sent)
        out['head'] += n+1 if mutation == 'write_consumes_extra' else n
        if out['head'] == t:
            out['head'] = 0
            if mutation != 'write_reset_keeps_tail': out['tail'] = 0
    elif op == 'would_block':
        if mutation:
            check(h, 1); out['B'][h] ^= 1
    elif op == 'eof':
        out['eof'] = True
        if mutation == 'eof_discards_queue': out['tail'] = h
    elif op == 'fin': out['fin'] = True
    else: raise ValueError(op)
    return out


def confirm(before, operation, n, data, mutation):
    if type(n) is not int or not 0 <= n < 2**32 or any(type(b) is not int or not 0 <= b <= 255 for b in data):
        return {'confirmed': False, 'reason': 'invalid concrete byte or count'}
    if not valid(before) or not eligible(before, operation, n, mutation):
        return {'confirmed': False, 'reason': 'invalid concrete pre-state or disabled transition'}
    violations = []
    if not eligible(before, operation, n): violations.append('guard')
    try:
        after = execute(before, operation, n, data, mutation)
    except ValueError as error:
        if str(error) != 'access_bounds': raise
        return {'confirmed': True, 'violations': violations + ['access_bounds'],
                'before': before, 'count': n, 'data': data, 'after': None}
    h, t = before['head'], before['tail']
    expected_B = before['B'][:]
    expected_R = before['R'][:]; expected_W = before['W'][:]
    eh, et, ee, ef = h, t, before['eof'], before['fin']
    if operation == 'read':
        expected_B[t:t+n] = data; expected_R += data; et = t+n
    elif operation == 'write':
        expected_W += before['B'][h:h+n]
        eh, et = (0, 0) if h+n == t else (h+n, t)
    elif operation == 'eof': ee = True
    elif operation == 'fin': ef = True
    if (after['head'], after['tail'], after['eof'], after['fin']) != (eh, et, ee, ef) or not valid(after): violations.append('state')
    if after['R'] != after['W'] + after['B'][after['head']:after['tail']]: violations.append('conservation')
    if after['B'] != expected_B: violations.append('buffer_frame_and_bytes')
    if after['R'] != expected_R: violations.append('read_history')
    if after['W'] != expected_W: violations.append('write_history')
    return {'confirmed': bool(violations), 'violations': violations, 'before': before,
            'count': n, 'data': data, 'after': after}
