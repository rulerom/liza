"""Compile actual proxy source mutations; never mutate the reference contract."""
MUTATIONS = (
    ('read_wrong_half', 'forward.read', 'i*4096+pair.forward.tail', 'i*4096+2048+pair.forward.tail'),
    ('read_base_off_by_one', 'forward.read', 'i*4096+pair.forward.tail', 'i*4096+1+pair.forward.tail'),
    ('write_from_tail', 'forward.write', 'i*4096+pair.forward.head', 'i*4096+pair.forward.tail'),
    ('consume_extra_byte', 'forward.write', 'relay.direction.write(pair.forward,count)', 'relay.direction.write(pair.forward,count+1)'),
    ('read_full_queue', 'forward.read', 'if alive && true && relay.direction.readable(pair.forward)!=0', 'if alive && true && relay.direction.readable(pair.forward)==0'),
    ('premature_fin', 'forward.fin', 'if alive && pair.connected && relay.direction.needs_fin(pair.forward)', 'if alive && pair.connected && relay.direction.valid(pair.forward)'),
    ('overwrite_other_direction', 'reverse.read', 'i*4096+2048+pair.reverse.tail', 'i*4096+pair.reverse.tail'),
    ('write_wrong_connection', 'forward.write', 'net.reactor_write(reactor,upstream,data,', 'net.reactor_write(reactor,client,data,'),
)

# Byte controls must demonstrate the byte-level defect after a successful mock
# transfer, not merely a mismatched call argument on a WouldBlock path.
TARGETS = {
    'read_wrong_half': ('other_directions_unchanged', 0),
    'read_base_off_by_one': ('exact_buffer_frame', 0),
    'write_from_tail': ('exact_histories', 0),
    'consume_extra_byte': ('byte_conservation', 0),
    'read_full_queue': ('call_binding_and_guard', 4),
    'premature_fin': ('call_binding_and_guard', 0),
    'overwrite_other_direction': ('other_directions_unchanged', 0),
    'write_wrong_connection': ('call_binding_and_guard', 0),
}


def mutate(source, control):
    name, _, old, new = control
    if source.count(old) != 1: raise ValueError('ambiguous mutation anchor: ' + name)
    return source.replace(old, new, 1)
