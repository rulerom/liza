"""Independent acyclic Semantic IR executor. Integers model checked u32 exactly.

There is no precondition that an input Direction is valid. Compiler summaries,
including may_trap and storage_contract, are not used as semantic axioms.
"""
import z3

DIRECTION = 'relay.direction.Direction'
ERROR = 'relay.direction.Error'
RESULT = 'Result<' + DIRECTION + ',' + ERROR + '>'
FIELDS = ('head', 'tail', 'eof', 'fin')
OPS = ('constant', 'struct.construct', 'struct.field', 'variant.construct',
       'phi', 'call', 'not', 'eq', 'ule', 'ugt', 'add', 'sub')


class Unsupported(ValueError):
    pass


def require(condition, message):
    if not condition: raise Unsupported(message)


def equal(a, b):
    if isinstance(a, tuple) or isinstance(b, tuple):
        if not isinstance(a, tuple) or not isinstance(b, tuple) or len(a) != len(b):
            return z3.BoolVal(False)
        return z3.And(*[equal(x, y) for x, y in zip(a, b)])
    if isinstance(a, str) or isinstance(b, str): return z3.BoolVal(a == b)
    return a == b


def typed(value, typ):
    if typ == 'u32': require(z3.is_int(value), 'expected integer u32')
    elif typ == 'bool': require(z3.is_bool(value), 'expected bool')
    elif typ == DIRECTION:
        require(isinstance(value, tuple) and len(value) == 4, 'Direction shape')
        for v, t in zip(value, ('u32', 'u32', 'bool', 'bool')): typed(v, t)
    elif typ == ERROR: require(value == ('InvalidTransition',), 'Error shape')
    elif typ == RESULT:
        require(isinstance(value, tuple) and len(value) == 2 and value[0] in ('Ok', 'Err'), 'Result shape')
        typed(value[1], DIRECTION if value[0] == 'Ok' else ERROR)
    else: raise Unsupported('type: ' + typ)
    return value


class Executor:
    def __init__(self, module):
        require(module['version'] == 20, 'unsupported Semantic IR version')
        self.functions = {f['name']: f for f in module['functions']}
        require(len(self.functions) == len(module['functions']), 'duplicate function')
        structures = {s['name']: s['fields'] for s in module['structures']}
        require(structures.get(DIRECTION) == [[n, t] for n, t in zip(FIELDS, ('u32', 'u32', 'bool', 'bool'))], 'Direction declaration')
        variants = {v['name']: v['cases'] for v in module['variants']}
        require(variants.get(ERROR) == [['InvalidTransition', None]], 'Error declaration')
        require(variants.get(RESULT) == [['Ok', DIRECTION], ['Err', ERROR]], 'Result declaration')
        self.visited = set()

    def validate(self, name, stack=()):
        require(name not in stack, 'recursive calls')
        f = self.functions[name]
        require(f['effect_contract'] == 'pure', 'effectful function')
        require(all(p['mode'] == 'value' for p in f['params']), 'resource parameter')
        blocks = {b['name']: b for b in f['blocks']}
        require(len(blocks) == len(f['blocks']) and bool(blocks), 'block names')
        def visit(label, ancestors):
            require(label not in ancestors, 'cyclic CFG')
            b = blocks[label]
            for o in b['operations']:
                require(o['op'] in OPS, 'instruction: ' + o['op'])
                require(o['effect_contract'] == 'pure', 'effectful operation')
                if o['op'] in ('add', 'sub'):
                    require(o['type'] == 'u32' and o['overflow'] == 'trap', 'arithmetic policy')
                if o['op'] == 'call':
                    require(o['parameter_modes'] == ['value'] * len(o['args']), 'call modes')
                    self.validate(o['callee'], stack + (name,))
            term = b['terminator']; op = term['op']; a = term['args']
            require(op in ('return', 'branch', 'jump'), 'terminator: ' + op)
            require(len(a) == (3 if op == 'branch' else 1), 'terminator arity')
            for target in (a[1:] if op == 'branch' else a if op == 'jump' else []):
                visit(target, ancestors + (label,))
        visit(f['blocks'][0]['name'], ())
        self.visited.add(name)

    def execute(self, name, arguments):
        if name not in self.visited: self.validate(name)
        f = self.functions[name]
        require(len(arguments) == len(f['params']), 'argument count')
        env = {p['name']: typed(v, p['type']) for p, v in zip(f['params'], arguments)}
        blocks = {b['name']: b for b in f['blocks']}
        exits = []
        def walk(label, previous, values, path):
            path = z3.simplify(path)
            if z3.is_false(path): return
            old = values; values = dict(values); b = blocks[label]
            for o in b['operations']:
                op = o['op']; raw = o['args']; typ = o['type']
                if op == 'phi':
                    incoming = o['incoming_blocks']
                    require(len(incoming) == len(raw) and incoming.count(previous) == 1, 'phi predecessor')
                    value = old[raw[incoming.index(previous)]]
                elif op == 'constant':
                    require(len(raw) == 1, 'constant arity')
                    if typ == 'bool':
                        require(type(raw[0]) is bool, 'boolean literal')
                        value = z3.BoolVal(raw[0])
                    else:
                        require(typ == 'u32' and type(raw[0]) is int and 0 <= raw[0] < 2**32, 'u32 literal')
                        value = z3.IntVal(raw[0])
                else:
                    a = [values[x] for x in raw]
                    if op == 'call':
                        require(typ == self.functions[o['callee']]['result_type'], 'call result type')
                        outcomes = self.execute(o['callee'], a)
                        # Actual helpers return scalars. Aggregate-returning calls are outside R1.
                        require(typ in ('bool', 'u32'), 'aggregate call result')
                        value = z3.BoolVal(False) if typ == 'bool' else z3.IntVal(0)
                        returned = []
                        for cond, kind, result in outcomes:
                            if kind == 'Trap': exits.append((z3.And(path, cond), 'Trap', None))
                            else:
                                returned.append(cond); value = z3.If(cond, result, value)
                        # Coverage is preserved, not assumed: missing callee paths remain missing.
                        path = z3.And(path, z3.Or(*returned))
                    elif op == 'struct.construct':
                        require(typ == DIRECTION, 'struct constructor type'); value = tuple(a)
                    elif op == 'struct.field':
                        require(len(a) == 1 and o['source_type'] == DIRECTION, 'field source')
                        typed(a[0], DIRECTION)
                        value = a[0][FIELDS.index(o['field_name'])]
                    elif op == 'variant.construct':
                        value = (o['field_name'], *a)
                    elif op == 'not':
                        require(len(a) == 1, 'not arity'); value = z3.Not(typed(a[0], 'bool'))
                    else:
                        require(len(a) == 2, 'binary arity')
                        x, y = a
                        if op == 'eq':
                            require((z3.is_int(x) and z3.is_int(y)) or (z3.is_bool(x) and z3.is_bool(y)), 'equality operands')
                            value = x == y
                        else:
                            typed(x, 'u32'); typed(y, 'u32')
                            if op == 'ule': value = x <= y
                            elif op == 'ugt': value = x > y
                            elif op in ('add', 'sub'):
                                value = x+y if op == 'add' else x-y
                                safe = z3.And(value >= 0, value < 2**32)
                                exits.append((z3.And(path, z3.Not(safe)), 'Trap', None))
                                path = z3.And(path, safe)
                            else: raise Unsupported(op)
                values[o['result']] = typed(value, typ)
            term = b['terminator']; a = term['args']
            if term['op'] == 'return': exits.append((path, 'Return', typed(values[a[0]], f['result_type'])))
            elif term['op'] == 'jump': walk(a[0], label, values, path)
            else:
                condition = typed(values[a[0]], 'bool')
                walk(a[1], label, values, z3.And(path, condition))
                walk(a[2], label, values, z3.And(path, z3.Not(condition)))
        walk(f['blocks'][0]['name'], None, env, z3.BoolVal(True))
        return exits
