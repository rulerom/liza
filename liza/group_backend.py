"""SG3 adapters expose role operations without a source-level Reactor pointer."""

def external(fn, lines, types, module):
    name = fn.name.text
    if not name.startswith(('__liza_group_', 'groups.')):
        return False
    if name == '__liza_group_run':
        producer, consumer = module.group_entries
        raw = types['__liza_GroupRaw']
        params = [f'i64 %p{i}' for i in range(5)] + [f'i32 %p{i}' for i in range(5,9)]
        abi = ['i64']*5+['i32']*4+['ptr']*6
        lines.extend([f'declare i32 @liza_rt_group_run({", ".join(abi)})',
                      f'define internal {raw} @liza_{name}({", ".join(params)}) {{'])
        for i in range(4): lines.append(f'  %out{i} = alloca i32')
        args = params+[f'ptr @liza_{producer}',f'ptr @liza_{consumer}']+[f'ptr %out{i}' for i in range(4)]
        lines.append(f'  %code = call i32 @liza_rt_group_run({", ".join(args)})')
        for i in range(4):
            lines.append(f'  %v{i} = load i32, ptr %out{i}')
            base = 'zeroinitializer' if i == 0 else f'%r{i-1}'
            lines.append(f'  %r{i} = insertvalue {raw} {base}, i32 %v{i}, {i}')
        lines.extend([f'  %r4 = insertvalue {raw} %r3, i32 %code, 4', f'  ret {raw} %r4', '}'])
        return True
    operation = name.removeprefix('__liza_group_').removeprefix('groups.')
    if operation in ('send','listen','next','stop','stopping','busy'):
        params=[f'{types[t]} %p{i}' for i,(_,t) in enumerate(fn.params)]
        abi=[types[t] for _,t in fn.params]
        ret=types[fn.result_type]
        lines.extend([f'declare {ret} @liza_rt_group_{operation}({", ".join(abi)})',
                      f'define internal {ret} @liza_{name}({", ".join(params)}) {{',
                      f'  %result = call {ret} @liza_rt_group_{operation}({", ".join(params)})',
                      f'  ret {ret} %result', '}'])
        return True
    from .reactor_backend import external as reactor_external
    generated=[]
    reactor_external(fn, generated, types)
    for line in generated:
        if not line.startswith('declare ') or line not in lines: lines.append(line)
    return True
