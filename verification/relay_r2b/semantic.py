"""Execute selected actual proxy CFG with explicit abstract socket contracts.

Pure Direction bodies use the unchanged R1 IR interpreter, not R1's report or
specification. Runtime effects use actual call arguments; logical offsets are
never substituted for the program's computed offsets.
"""
from dataclasses import dataclass, replace
import z3
from verification.relay_r1.semantic import Executor as PureExecutor
from .fragment import IO, Unsupported, require

TOTAL = 32768
FIELDS = ('head', 'tail', 'eof', 'fin')


def splice(array, start, source, source_start, count):
    p = z3.Int('byte_index')
    return z3.Lambda(p, z3.If(z3.And(start <= p, p < start+count),
                             z3.Select(source, source_start+p-start), z3.Select(array, p)))


@dataclass(frozen=True)
class Memory:
    B: object
    R: object
    W: object
    rlen: object
    wlen: object
    call: object = None
    fatal: bool = False


def shape(v):
    if isinstance(v, tuple): return tuple(shape(x) for x in v)
    if isinstance(v, str): return v
    return str(v.sort())


def choose(cond, a, b):
    if isinstance(a, tuple): return tuple(choose(cond, x, y) for x, y in zip(a, b))
    if isinstance(a, str):
        require(a == b, 'incompatible helper payload'); return a
    return z3.If(cond, a, b)


def group_returns(outcomes):
    groups = {}
    for path, kind, value in outcomes:
        if kind == 'Trap': yield path, kind, value; continue
        groups.setdefault(shape(value), []).append((path, value))
    for group in groups.values():
        value = group[0][1]
        for path, candidate in group[1:]: value = choose(path, candidate, value)
        yield z3.Or(*[p for p, _ in group]), 'Return', value


class Executor:
    def __init__(self, module, fragment, inputs):
        self.fragment = fragment; self.inputs = inputs
        self.functions = {f['name']: f for f in module['functions']}
        self.variants = {v['name']: [name for name, _ in v['cases']] for v in module['variants']}
        self.pure = PureExecutor(module)
        self.exits = []

    def retry(self, variant):
        # The actual retry body is a closed enum switch with constant returns.
        f = self.functions['liza_proxy.retry']; blocks = {b['name']: b for b in f['blocks']}
        require(f['effect_contract'] == 'pure' and len(f['params']) == 1, 'retry signature')
        b = f['blocks'][0]; ops = b['operations']; t = b['terminator']
        require(len(ops) == 1 and ops[0]['op'] == 'variant.tag' and ops[0]['args'] == [f['params'][0]['name']], 'retry tag')
        require(t['op'] == 'switch' and t['args'][0] == ops[0]['result'], 'retry switch')
        tag = self.variants['ReactorError'].index(variant[0])
        targets = [target for case, target in t['args'][2:] if case == tag]
        require(len(targets) == 1, 'retry case')
        target = blocks[targets[0]]; out = target['operations']
        require(len(out) == 1 and out[0]['op'] == 'constant' and type(out[0]['args'][0]) is bool
                and target['terminator'] == {'op': 'return', 'args': [out[0]['result']]}, 'retry return')
        return z3.BoolVal(out[0]['args'][0])

    def runtime(self, operation, args, memory):
        require(memory.call is None, 'multiple I/O events inside a cut')
        expected_arity = 2 if operation == 'fin' else 5
        require(len(args) == expected_arity and args[0] == 'reactor', 'runtime receiver')
        if operation != 'fin': require(args[2] == ('buffer' if operation == 'read' else 'view'), 'buffer provenance')
        call = {'operation': operation, 'connection': args[1],
                'offset': args[3] if operation != 'fin' else z3.IntVal(0),
                'requested': args[4] if operation != 'fin' else z3.IntVal(0)}
        n = self.inputs['count']; kind = self.inputs['outcome']; data = self.inputs['data']
        for tag, error in [(0, None), (1, 'WouldBlock'), (2, 'Interrupted'), (3, 'Other'), (4, 'InvalidRange')]:
            path = kind == tag; new = replace(memory, call=call, fatal=tag in (3, 4))
            offset, requested = call['offset'], call['requested']
            admissible = z3.And(offset >= 0, requested > 0, offset+requested <= TOTAL)
            if tag == 4:
                # Explicit read range validation precedes recv for a valid
                # connected stream. This outcome is used by the full-buffer
                # source control; it must not synthesize WouldBlock for count=0.
                path = z3.And(path, z3.BoolVal(operation == 'read'), z3.Not(admissible))
            elif operation != 'fin':
                path = z3.And(path, admissible)
            if tag == 0:
                if operation != 'fin':
                    path = z3.And(path, offset >= 0, requested > 0, offset+requested <= TOTAL,
                                  n >= (0 if operation == 'read' else 1), n <= requested)
                if operation == 'read':
                    new = replace(new, B=splice(memory.B, offset, data, 0, n),
                                  R=splice(memory.R, memory.rlen, data, 0, n), rlen=memory.rlen+n)
                elif operation == 'write':
                    new = replace(new, W=splice(memory.W, memory.wlen, memory.B, offset, n), wlen=memory.wlen+n)
                result = ('Ok', n if operation != 'fin' else z3.IntVal(0))
            else:
                # Fatal memory effects are intentionally NOT certified. No later
                # byte property is asserted on this branch; only alive=false.
                result = ('Err', (error,))
            yield path, (('buffer', result) if operation == 'read' else result), new

    def execute(self, memory):
        fragment = self.fragment
        env = fragment.bindings(self.inputs)
        self.walk(fragment.start, None, env, memory, z3.BoolVal(True), 0, True)
        return self.exits

    def walk(self, label, previous, env, memory, path, position=0, entry=False):
        path = z3.simplify(path)
        if z3.is_false(path): return
        b = self.fragment.blocks[label]; values = dict(env)
        if position == 0:
            if not entry:
                for o in b['operations']:
                    if o['op'] != 'phi': continue
                    incoming = o['incoming_blocks']
                    require(len(incoming) == len(o['args']) and incoming.count(previous) == 1, 'phi predecessor')
                    values[o['result']] = env[o['args'][incoming.index(previous)]]
            if label == self.fragment.stop:
                self.exits.append((path, 'Return', values[self.fragment.exit_pair], values[self.fragment.exit_alive], memory))
                return
        for index in range(position, len(b['operations'])):
            o = b['operations'][index]; op = o['op']; raw = o['args']
            if op == 'phi': continue
            if op == 'constant':
                require(len(raw) == 1 and o['type'] in ('u32', 'bool'), 'constant type')
                if o['type'] == 'bool': require(type(raw[0]) is bool, 'bool literal'); value = z3.BoolVal(raw[0])
                else: require(type(raw[0]) is int and 0 <= raw[0] < 2**32, 'u32 literal'); value = z3.IntVal(raw[0])
            else:
                a = [values[v] for v in raw]
                if op == 'call':
                    callee = o['callee']
                    if callee in IO.values():
                        operation = next(k for k, v in IO.items() if v == callee)
                        for guard, value, new in self.runtime(operation, a, memory):
                            self.walk(label, previous, dict(values, **{o['result']: value}), new, z3.And(path, guard), index+1)
                        return
                    if callee == 'liza_proxy.retry': value = self.retry(a[0])
                    elif callee.startswith('relay.direction.'):
                        require(o['effect_contract'] == 'pure', 'effectful helper')
                        for guard, kind, value in group_returns(self.pure.execute(callee, a)):
                            if kind == 'Trap': self.exits.append((z3.And(path, guard), 'Trap', None, None, memory))
                            else: self.walk(label, previous, dict(values, **{o['result']: value}), memory, z3.And(path, guard), index+1)
                        return
                    else: raise Unsupported(callee)
                elif op in ('copy', 'move', 'unpack.consume'):
                    require(len(a) == 1, 'unary arity'); value = a[0]
                elif op == 'buffer.view':
                    require(a == ['buffer'], 'view owner'); value = 'view'
                elif op == 'unpack.component': value = a[0][int(o['field_name'])]
                elif op == 'variant.tag': value = z3.IntVal(self.variants[o['source_type']].index(a[0][0]))
                elif op == 'variant.payload':
                    require(a[0][0] == o['field_name'] and len(a[0]) == 2, 'variant payload'); value = a[0][1]
                elif op == 'struct.field':
                    value = a[0][o['field_name']] if isinstance(a[0], dict) else a[0][FIELDS.index(o['field_name'])]
                elif op == 'struct.update':
                    require(isinstance(a[0], dict) and o['field_name'] in a[0], 'Pair update')
                    value = dict(a[0], **{o['field_name']: a[1]})
                elif op == 'not': value = z3.Not(a[0])
                elif op in ('eq', 'ne'): value = (a[0] == a[1]) if op == 'eq' else (a[0] != a[1])
                elif op in ('and', 'or'):
                    require(o['type'] == 'u32', 'bit operation type')
                    x, y = z3.Int2BV(a[0], 32), z3.Int2BV(a[1], 32)
                    value = z3.BV2Int(x & y if op == 'and' else x | y)
                elif op in ('add', 'sub', 'mul'):
                    require(o['type'] == 'u32' and o['overflow'] == 'trap', 'checked arithmetic policy')
                    value = a[0]+a[1] if op == 'add' else a[0]-a[1] if op == 'sub' else a[0]*a[1]
                    safe = z3.And(value >= 0, value < 2**32)
                    self.exits.append((z3.And(path, z3.Not(safe)), 'Trap', None, None, memory))
                    path = z3.And(path, safe)
                else: raise Unsupported(op)
            values[o['result']] = value
        t = b['terminator']; a = t['args']
        if t['op'] == 'jump': self.walk(a[0], label, values, memory, path)
        elif t['op'] == 'branch':
            self.walk(a[1], label, values, memory, z3.And(path, values[a[0]]))
            self.walk(a[2], label, values, memory, z3.And(path, z3.Not(values[a[0]])))
        elif t['op'] == 'switch':
            conditions = []
            for tag, target in a[2:]:
                condition = values[a[0]] == tag; conditions.append(condition)
                self.walk(target, label, values, memory, z3.And(path, condition))
            self.walk(a[1], label, values, memory, z3.And(path, z3.Not(z3.Or(*conditions))))
        elif t['op'] == 'unreachable': self.exits.append((path, 'Undefined', None, None, memory))
        else: raise Unsupported('terminator')
