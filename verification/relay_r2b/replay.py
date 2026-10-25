"""Concrete actual-IR execution with socket-result mocks; no Z3 imports.

R1's separate concrete interpreter executes the actual Direction helper bodies.
No symbolic interpreter or reference transition computes actual results here.
"""
from verification.relay_r1.replay import run as pure_run
from .fragment import IO


def run(module, fragment, inputs, memory, budget=10000):
    functions = {f['name']: f for f in module['functions']}
    variants = {v['name']: [name for name, _ in v['cases']] for v in module['variants']}
    trace = []
    remaining = [budget]
    mem = dict(memory, B=memory['B'][:], R=memory['R'][:], W=memory['W'][:], call=None, fatal=False)

    class Trap(Exception): pass
    class Undefined(Exception): pass

    def runtime(operation, args):
        if mem['call'] is not None: raise ValueError('more than one I/O call')
        if args[0] != 'reactor': raise ValueError('reactor identity')
        if operation != 'fin' and args[2] != ('buffer' if operation == 'read' else 'view'):
            raise ValueError('buffer identity')
        offset, requested = args[3:] if operation != 'fin' else (0, 0)
        n, outcome = inputs['count'], inputs['outcome']
        mem['call'] = dict(operation=operation, connection=args[1], offset=offset, requested=requested)
        trace.append({'io': mem['call'], 'outcome': outcome, 'count': n})
        admissible = 0 <= offset < offset+requested <= len(mem['B'])
        if outcome == 4:
            if operation != 'read' or admissible: raise ValueError('inconsistent InvalidRange witness')
        elif operation != 'fin' and not admissible:
            raise ValueError('invalid range must not synthesize successful/temporary I/O')
        if outcome == 0:
            if operation != 'fin' and not (0 <= offset < offset+requested <= len(mem['B']) and
                                          (0 if operation == 'read' else 1) <= n <= requested):
                raise ValueError('I/O witness violates runtime count/range contract')
            if operation == 'read':
                data = inputs['data'][:n]
                if len(data) != n: raise ValueError('short mock input')
                mem['B'][offset:offset+n] = data; mem['R'].extend(data)
            elif operation == 'write': mem['W'].extend(mem['B'][offset:offset+n])
            result = ('Ok', n if operation != 'fin' else 0)
        else:
            if outcome not in (1, 2, 3, 4): raise ValueError('unsupported outcome')
            result = ('Err', ({1: 'WouldBlock', 2: 'Interrupted', 3: 'Other', 4: 'InvalidRange'}[outcome],))
            mem['fatal'] = outcome in (3, 4)
        return ('buffer', result) if operation == 'read' else result

    def execute(function, env, start, stop=None, entry=False):
        blocks = {b['name']: b for b in function['blocks']}
        label, predecessor = start, None
        while True:
            remaining[0] -= 1
            if remaining[0] < 0: raise ValueError('replay budget exhausted')
            b = blocks[label]; old = dict(env)
            trace.append({'function': function['name'], 'block': label, 'predecessor': predecessor})
            if not entry:
                for o in b['operations']:
                    if o['op'] == 'phi': env[o['result']] = old[o['args'][o['incoming_blocks'].index(predecessor)]]
            entry = False
            if label == stop: return env
            for o in b['operations']:
                op, raw = o['op'], o['args']
                if op == 'phi': continue
                if op == 'constant': value = raw[0]
                else:
                    a = [env[v] for v in raw]
                    if op == 'call':
                        callee = o['callee']
                        if callee in IO.values(): value = runtime(next(k for k, v in IO.items() if v == callee), a)
                        elif callee.startswith('relay.direction.'):
                            result = pure_run(module, callee, a)
                            trace.append({'helper': callee, 'arguments': a, 'execution': result})
                            if result['outcome'] == 'Trap': raise Trap()
                            value = result['value']
                        elif callee == 'liza_proxy.retry':
                            f = functions[callee]
                            value = execute(f, {p['name']: v for p, v in zip(f['params'], a)}, f['blocks'][0]['name'])
                        else: raise ValueError('unsupported concrete call')
                    elif op in ('move', 'copy', 'unpack.consume'): value = a[0]
                    elif op == 'buffer.view':
                        if a != ['buffer']: raise ValueError('view origin')
                        value = 'view'
                    elif op == 'unpack.component': value = a[0][int(o['field_name'])]
                    elif op == 'variant.tag': value = variants[o['source_type']].index(a[0][0])
                    elif op == 'variant.payload':
                        if a[0][0] != o['field_name']: raise ValueError('wrong variant')
                        value = a[0][1]
                    elif op == 'struct.field': value = a[0][o['field_name']] if isinstance(a[0], dict) else a[0][('head','tail','eof','fin').index(o['field_name'])]
                    elif op == 'struct.update': value = dict(a[0], **{o['field_name']: a[1]})
                    elif op == 'not': value = not a[0]
                    elif op == 'eq': value = a[0] == a[1]
                    elif op == 'ne': value = a[0] != a[1]
                    elif op == 'and': value = a[0] & a[1]
                    elif op == 'or': value = a[0] | a[1]
                    elif op in ('add', 'sub', 'mul'):
                        if o['overflow'] != 'trap': raise ValueError('unsupported arithmetic')
                        value = a[0]+a[1] if op == 'add' else a[0]-a[1] if op == 'sub' else a[0]*a[1]
                        if not 0 <= value < 2**32:
                            trace.append({'instruction': o['result'], 'trap_operands': a}); raise Trap()
                    else: raise ValueError('unsupported concrete instruction: ' + op)
                env[o['result']] = value
                trace.append({'instruction': o['result'], 'op': op, 'value': value})
            t = b['terminator']; a = t['args']
            if t['op'] == 'return': return env[a[0]]
            predecessor = label
            if t['op'] == 'jump': label = a[0]
            elif t['op'] == 'branch': label = a[1] if env[a[0]] else a[2]
            elif t['op'] == 'switch': label = dict(a[2:]).get(env[a[0]], a[1])
            elif t['op'] == 'unreachable': raise Undefined()
            else: raise ValueError('unsupported concrete terminator')
    try:
        env = execute(fragment.function, fragment.bindings(inputs), fragment.start, fragment.stop, True)
        return {'outcome': 'Return', 'pair': env[fragment.exit_pair], 'alive': env[fragment.exit_alive], 'memory': mem, 'trace': trace}
    except Trap: return {'outcome': 'Trap', 'memory': mem, 'trace': trace}
    except Undefined: return {'outcome': 'Undefined', 'memory': mem, 'trace': trace}


def violations(fragment, inputs, before, result):
    """Independent concrete observation contract, not a symbolic-model replay."""
    if result['outcome'] != 'Return': return [result['outcome']]
    side, op = fragment.direction, fragment.operation
    original = inputs['pair']; h, t, e, f = original[side]
    base = 4096*inputs['slot'] + (2048 if side == 'reverse' else 0)
    flags = inputs['client_ready'] if side == 'forward' else inputs['upstream_ready']
    if op == 'read': enabled = inputs['alive'] and not e and t < 2048 and bool(flags & 5) and (side == 'forward' or original['connected'])
    elif op == 'write': enabled = inputs['alive'] and original['connected'] and h < t
    else: enabled = inputs['alive'] and original['connected'] and e and h == t and not f
    after = result['memory']; call = after['call']; bad = []
    if bool(call) != bool(enabled): bad.append('call_guard')
    if call:
        peer = ('client' if side == 'forward' else 'upstream') if op == 'read' else ('upstream' if side == 'forward' else 'client')
        offset = base+(t if op == 'read' else h) if op != 'fin' else 0
        size = 2048-t if op == 'read' else t-h if op == 'write' else 0
        if call['connection'] != peer or call['offset'] != offset or call['requested'] != size: bad.append('call_binding')
        if op != 'fin' and not (base <= call['offset'] < call['offset']+call['requested'] <= base+2048): bad.append('slice_bounds')
    if after['fatal']:
        if result['alive']: bad.append('fatal_continues')
        return bad
    success = bool(call) and inputs['outcome'] == 0; n = inputs['count']
    expected = (h,t,e,f); B = before['B'][:]; R = before['R'][:]; W = before['W'][:]
    if success and op == 'read':
        expected = (h,t+n,n == 0,f); B[base+t:base+t+n] = inputs['data'][:n]; R += inputs['data'][:n]
    elif success and op == 'write':
        expected = (0,0,e,f) if h+n == t else (h+n,t,e,f); W += before['B'][base+h:base+h+n]
    elif success: expected = (h,t,e,True)
    pair = result['pair']; other = 'reverse' if side == 'forward' else 'forward'
    if pair[side] != expected or any(pair[key] != original[key] for key in (other,'client','upstream','connected')) or result['alive'] != inputs['alive']:
        bad.append('state_and_count_binding')
    nh, nt, _, _ = pair[side]
    if after['R'] != after['W'] + after['B'][base+nh:base+nt]: bad.append('byte_conservation')
    if after['B'] != B: bad.append('exact_buffer_frame')
    for index in range(16):
        if index != base//2048 and after['B'][index*2048:(index+1)*2048] != before['B'][index*2048:(index+1)*2048]:
            bad.append('other_directions_unchanged'); break
    if after['R'] != R or after['W'] != W: bad.append('exact_histories')
    return bad


def replay_record(module, fragment, record):
    """Restore JSON arrays/hex and replay a saved witness without the solver."""
    inputs = dict(record['inputs'], pair=dict(record['inputs']['pair']))
    for key in ('forward', 'reverse', 'client', 'upstream'):
        inputs['pair'][key] = tuple(inputs['pair'][key])
    before = {key: list(bytes.fromhex(value)) for key, value in record['before_hex'].items()}
    result = run(module, fragment, inputs, before)
    return result, violations(fragment, inputs, before, result)


def main():
    import argparse
    import json
    from pathlib import Path
    from .fragment import Fragment
    parser = argparse.ArgumentParser(description='Replay one saved R2-B results.json counterexample without Z3')
    parser.add_argument('--ir', required=True, type=Path)
    parser.add_argument('--cut', required=True)
    parser.add_argument('--witness', required=True, type=Path)
    args = parser.parse_args()
    module = json.loads(args.ir.read_text(encoding='utf-8'))
    rows = json.loads(args.witness.read_text(encoding='utf-8'))
    record = next(row['replay'] for row in rows if row.get('replay', {}).get('confirmed'))
    _, bad = replay_record(module, Fragment(module, args.cut), record)
    matched = bool(bad) and bad == record['violations']
    print(json.dumps({'replayed': matched, 'violations': bad}))
    return 0 if matched else 1


if __name__ == '__main__': raise SystemExit(main())
