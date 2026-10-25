"""Private scalar ABI for a bounded owner and opaque connection identities."""
from .types import product_args


def external(fn, lines, types):
    name = fn.name.text
    if name == 'net.connection_slot':
        lines.extend(['define internal i32 @liza_net.connection_slot([3 x i64] %id) {',
                      '  %slot = extractvalue [3 x i64] %id, 2',
                      '  %r = trunc i64 %slot to i32', '  ret i32 %r', '}'])
        return True
    if not name.startswith('__liza_reactor_') and name != 'net.reactor_read':
        return False
    operation = 'read' if name == 'net.reactor_read' else name.removeprefix('__liza_reactor_')
    result = types[fn.result_type]
    if operation in ('create', 'accept'):
        create = operation == 'create'
        params = 'i16 %port, i32 %capacity' if create else 'ptr %r'
        abi = 'i16, i32, ptr' if create else 'ptr, ptr'
        args = 'i16 %port, i32 %capacity, ptr %out' if create else 'ptr %r, ptr %out'
        handle = 'ptr' if create else '[3 x i64]'
        lines.extend([f'declare i32 @liza_rt_reactor_{operation}({abi})',
                      f'define internal {result} @liza_{name}({params}) {{',
                      f'  %out = alloca {handle}',
                      f'  %code = call i32 @liza_rt_reactor_{operation}({args})',
                      f'  %value = load {handle}, ptr %out',
                      f'  %r0 = insertvalue {result} zeroinitializer, {handle} %value, 0',
                      f'  %r1 = insertvalue {result} %r0, i32 %code, 1',
                      f'  ret {result} %r1', '}'])
        return True
    params=['ptr %r'];abi=['ptr'];args=['ptr %r'];body=[]
    if operation in ('read','write','interest','ready','disconnect'):
        params.append('[3 x i64] %id')
        for i in range(3):
            body.append(f'  %id{i} = extractvalue [3 x i64] %id, {i}')
            abi.append('i64');args.append(f'i64 %id{i}')
    if operation in ('read','write'):
        params.append('{ ptr, i32 } %data')
        body.extend(['  %p = extractvalue { ptr, i32 } %data, 0',
                     '  %n = extractvalue { ptr, i32 } %data, 1'])
        abi.extend(['ptr','i32']);args.extend(['ptr %p','i32 %n'])
    extras = {'poll':['timeout'], 'interest':['flags'], 'read':['start','count'], 'write':['start','count']}.get(operation,[])
    for arg in extras:
        params.append(f'i32 %{arg}');abi.append('i32');args.append(f'i32 %{arg}')
    ret='i32' if operation=='close' else 'i64'
    lines.extend([f'declare {ret} @liza_rt_reactor_{operation}({", ".join(abi)})',
                  f'define internal {result} @liza_{name}({", ".join(params)}) {{',*body,
                  f'  %raw = call {ret} @liza_rt_reactor_{operation}({", ".join(args)})'])
    if operation=='read':
        status=types[product_args(fn.result_type)[1]];error=types['ReactorError']
        lines.extend(['  %count_read = trunc i64 %raw to i32',
                      '  %wide = lshr i64 %raw, 32','  %code = trunc i64 %wide to i32',
                      '  %failed = icmp ne i32 %code, 0','  %tag = zext i1 %failed to i32',
                      '  %errtag = sub i32 %code, 1',
                      f'  %err = insertvalue {error} zeroinitializer, i32 %errtag, 0',
                      f'  %s0 = insertvalue {status} zeroinitializer, i32 %tag, 0',
                      f'  %s1 = insertvalue {status} %s0, i32 %count_read, 1',
                      f'  %s2 = insertvalue {status} %s1, {error} %err, 2',
                      f'  %r0 = insertvalue {result} zeroinitializer, {{ ptr, i32 }} %data, 0',
                      f'  %r1 = insertvalue {result} %r0, {status} %s2, 1',
                      f'  ret {result} %r1','}'])
    else:
        lines.extend([f'  ret {ret} %raw','}'])
    return True
