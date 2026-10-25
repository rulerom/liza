"""Concrete IR execution with Python values; no Z3 or symbolic executor imports."""


def run(module, name, arguments, budget=10000):
    functions = {f['name']: f for f in module['functions']}
    trace = []
    remaining = [budget]

    class Trap(Exception): pass

    def call(name, arguments):
        f = functions[name]
        env = dict(zip((p['name'] for p in f['params']), arguments))
        blocks = {b['name']: b for b in f['blocks']}
        label, predecessor = f['blocks'][0]['name'], None
        while True:
            remaining[0] -= 1
            if remaining[0] < 0: raise ValueError('concrete replay budget exhausted')
            trace.append({'function': name, 'block': label, 'predecessor': predecessor})
            block = blocks[label]; before = dict(env)
            for o in block['operations']:
                op, raw = o['op'], o['args']
                if op == 'constant': value = raw[0]
                elif op == 'phi': value = before[raw[o['incoming_blocks'].index(predecessor)]]
                else:
                    a = [env[x] for x in raw]
                    if op == 'call': value = call(o['callee'], a)
                    elif op == 'struct.construct': value = tuple(a)
                    elif op == 'struct.field': value = a[0][['head', 'tail', 'eof', 'fin'].index(o['field_name'])]
                    elif op == 'variant.construct': value = (o['field_name'], *a)
                    elif op == 'not': value = not a[0]
                    elif op == 'eq': value = a[0] == a[1]
                    elif op == 'ule': value = a[0] <= a[1]
                    elif op == 'ugt': value = a[0] > a[1]
                    elif op in ('add', 'sub'):
                        if o['overflow'] != 'trap': raise ValueError('unsupported overflow')
                        value = a[0]+a[1] if op == 'add' else a[0]-a[1]
                        if not 0 <= value <= 4294967295:
                            trace.append({'instruction': o['result'], 'outcome': 'Trap', 'operands': a})
                            raise Trap()
                    else: raise ValueError('unsupported concrete operation: ' + op)
                env[o['result']] = value
                trace.append({'instruction': o['result'], 'value': value})
            t = block['terminator']; a = t['args']
            if t['op'] == 'return': return env[a[0]]
            predecessor = label
            if t['op'] == 'jump': label = a[0]
            elif t['op'] == 'branch': label = a[1] if env[a[0]] else a[2]
            else: raise ValueError('unsupported concrete terminator')
    try:
        value = call(name, arguments)
        return {'outcome': 'Return', 'value': value, 'trace': trace}
    except Trap:
        return {'outcome': 'Trap', 'value': None, 'trace': trace}
