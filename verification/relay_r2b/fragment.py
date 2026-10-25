"""Explicit cutpoint contract for the current proxy IR, not loop verification.

Entry phi results are assumed cutpoint inputs; exit phi nodes are executed.
Block labels are deliberate fixture selectors. Changed CFG/live-ins fail closed.
No compiler storage/effect summary supplies a state transition.
"""
class Unsupported(ValueError):
    pass


def require(condition, message):
    if not condition: raise Unsupported(message)

PAIR = 'liza_proxy.Pair'
DIRECTION = 'relay.direction.Direction'
BUFFER = 'memory.Buffer<u8>'
CUTS = {
    'forward.read': ('b91', 'b114'),
    'forward.write': ('b114', 'b134'),
    'forward.fin': ('b134', 'b154'),
    'reverse.read': ('b154', 'b177'),
    'reverse.write': ('b177', 'b197'),
    'reverse.fin': ('b197', 'b217'),
}
IO = {'read': 'net.reactor_read', 'write': 'net.reactor_write', 'fin': 'net.reactor_shutdown_write'}
ROOTS = {'v127': 'slot', 'v136': 'client', 'v141': 'upstream',
         'v154': 'client_ready', 'v163': 'upstream_ready', 'p0': 'reactor'}
OPS = {'constant', 'phi', 'struct.field', 'struct.update', 'call', 'move', 'copy',
       'buffer.view', 'unpack.consume', 'unpack.component', 'variant.tag',
       'variant.payload', 'add', 'mul', 'sub', 'not', 'and', 'or', 'eq', 'ne'}


def successors(block):
    t = block['terminator']; a = t['args']
    if t['op'] == 'jump': return a
    if t['op'] == 'branch': return a[1:]
    if t['op'] == 'switch': return [a[1]] + [c[1] for c in a[2:]]
    if t['op'] == 'unreachable': return []
    raise Unsupported('fragment terminator: ' + t['op'])


class Fragment:
    def __init__(self, module, name):
        require(module['version'] == 20, 'Semantic IR version')
        self.name = name
        self.direction, self.operation = name.split('.')
        self.start, self.stop = CUTS[name]
        self.function = next(f for f in module['functions'] if f['name'] == 'liza_proxy.exchange')
        self.blocks = {b['name']: b for b in self.function['blocks']}
        require(len(self.blocks) == len(self.function['blocks']), 'duplicate blocks')
        self.defs = {o['result']: o for b in self.function['blocks'] for o in b['operations']}
        require(len(self.defs) == sum(len(b['operations']) for b in self.function['blocks']), 'duplicate SSA definition')
        require(any(p['name'] == 'p0' and p['type'] == 'net.Reactor' for p in self.function['params']), 'reactor parameter')
        structures = {s['name']: s['fields'] for s in module['structures']}
        require(structures.get(PAIR) == [['client', 'Option<net.Connection>'], ['upstream', 'Option<net.Connection>'],
                                         ['connected', 'bool'], ['forward', DIRECTION], ['reverse', DIRECTION]], 'Pair layout')
        # Check the manifest's external names against actual defining operations.
        require(self.defs['v127']['op'] == 'phi' and self.defs['v127']['type'] == 'u32', 'slot root')
        require(self.defs['v133']['op'] == 'copy', 'pair copy root')
        array_read = self.defs[self.defs['v133']['args'][0]]
        require(array_read['op'] == 'array.read' and array_read['args'][1] == 'v127', 'slot provenance')
        for value, field in [('v136', 'client'), ('v141', 'upstream')]:
            o = self.defs[value]
            require(o['op'] == 'variant.payload' and o['field_name'] == 'Some', 'connection payload')
            origin = self.defs[o['args'][0]]
            require(origin['op'] == 'struct.field' and origin['field_name'] == field and origin['args'] == ['v133'], 'connection provenance')
        for value in ('v154', 'v163'):
            require(self.defs[value]['op'] == 'phi' and self.defs[value]['type'] == 'u32', 'readiness root')
        self.entry = self.blocks[self.start]['operations']
        require(all(o['op'] == 'phi' for o in self.entry), 'entry must contain only cut phi nodes')
        types = [o['type'] for o in self.entry]
        require(sorted(types) in (sorted([PAIR, 'bool', 'u32']), sorted([BUFFER, PAIR, 'bool', 'u32'])), 'entry parameter schema')
        self.entry_pair = self.unique(self.entry, PAIR)
        self.entry_alive = self.unique(self.entry, 'bool')
        require(self.blocks[self.start]['terminator']['args'][0] == self.entry_alive, 'alive guard boundary')
        self.exit = self.blocks[self.stop]['operations']
        require(all(o['op'] == 'phi' for o in self.exit), 'exit must contain only phi nodes')
        self.exit_pair = self.unique(self.exit, PAIR)
        self.exit_alive = self.unique(self.exit, 'bool')
        self.selected = set()
        def visit(label, seen):
            require(label not in seen, 'backedge inside cut')
            self.selected.add(label)
            if label == self.stop: return
            for target in successors(self.blocks[label]): visit(target, seen | {label})
        visit(self.start, set())
        definitions = set()
        used = set()
        calls = []
        for label in self.selected:
            b = self.blocks[label]
            for o in b['operations']:
                require(o['op'] in OPS, 'unsupported operation: ' + o['op'])
                definitions.add(o['result'])
                if label == self.start: continue
                if o['op'] != 'constant': used.update(o['args'])
                if o['op'] == 'call':
                    callee = o['callee']
                    require(callee.startswith('relay.direction.') or callee == 'liza_proxy.retry' or callee in IO.values(), 'unsupported call: ' + callee)
                    if callee in IO.values(): calls.append((label, o['result'], callee))
            if label != self.stop and b['terminator']['op'] in ('branch', 'switch'):
                used.add(b['terminator']['args'][0])
        require(len(calls) == 1 and calls[0][2] == IO[self.operation], 'one declared I/O call per cut')
        self.call = calls[0]
        self.live = used - definitions
        self.buffer_inputs = [v for v in self.live if self.defs.get(v, {}).get('type') == BUFFER]
        require(len(self.buffer_inputs) + types.count(BUFFER) <= 1, 'ambiguous buffer live-in')
        require(self.live <= set(ROOTS) | set(self.buffer_inputs), 'unknown live-ins: ' + str(self.live - set(ROOTS) - set(self.buffer_inputs)))

    @staticmethod
    def unique(operations, typ):
        found = [o['result'] for o in operations if o['type'] == typ]
        require(len(found) == 1, 'cut binding type: ' + typ)
        return found[0]

    def bindings(self, inputs):
        env = {key: inputs[role] for key, role in ROOTS.items() if key in self.live}
        env.update({key: 'buffer' for key in self.buffer_inputs})
        for o in self.entry:
            if o['type'] == PAIR: env[o['result']] = inputs['pair']
            elif o['type'] == 'bool': env[o['result']] = inputs['alive']
            elif o['type'] == BUFFER: env[o['result']] = 'buffer'
            elif o['type'] == 'u32': env[o['result']] = inputs['failure']
            else: raise Unsupported('entry type')
        return env

    def manifest(self):
        return {'entry_after_phi': self.start, 'exit_after_phi': self.stop,
                'blocks': sorted(self.selected, key=lambda b: int(b[1:])),
                'entry_bindings': self.entry, 'live_ins': sorted(self.live),
                'io': self.call, 'exit_pair': self.exit_pair, 'exit_alive': self.exit_alive}
