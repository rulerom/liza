"""Every negative control changes compiled Liza source, not the specification."""
MUTATIONS = (
    ('missing_capacity_bound', 'valid', ' && d.tail<=2048', ''),
    ('wrong_readable', 'readable', 'return 2048-d.tail', 'return 2047-d.tail'),
    ('wrong_queued', 'queued', 'return d.tail-d.head', 'return d.tail'),
    ('unchecked_read_count', 'read', ' || count>readable(d)', ''),
    ('missing_eof', 'read', 'Ok(Direction(d.head,d.tail,true,false))', 'Ok(Direction(d.head,d.tail,false,false))'),
    ('no_write_progress', 'write', 'next=d.head+count', 'next=d.head'),
    ('no_empty_reset', 'write', 'Ok(Direction(0,0,d.eof,d.fin))', 'Ok(Direction(next,d.tail,d.eof,d.fin))'),
    ('premature_fin', 'shutdown', 'if !needs_fin(d)', 'if !valid(d) || !d.eof || d.fin'),
)


def mutate(source, control):
    _, _, old, new = control
    if source.count(old) != 1: raise ValueError('mutation anchor is not unique: ' + control[0])
    return source.replace(old, new, 1)
