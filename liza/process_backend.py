"""Child and filesystem adapters: scalar/pointer ABI; no C aggregate ABI."""
def external(fn, lines):
    name=fn.name.text
    if not name.startswith(('__liza_process_', '__liza_fs_')):return False
    if name in ('__liza_process_spawn','__liza_fs_stat','__liza_fs_op'):
        if 'declare ptr @liza_rt_cli_path(i32)' not in lines:
            lines.append('declare ptr @liza_rt_cli_path(i32)')
    if name=='__liza_process_spawn':
        raw='%struct.__liza_ProcessChild'
        lines.extend(['declare ptr @liza_rt_process_spawn(ptr, i32, ptr, i32, ptr, i32, ptr)',
            f'define internal {raw} @liza_{name}(i32 %path, i1 %inherit, {{ptr,i32}} %args, {{ptr,i32}} %env) {{',
            '  %p = call ptr @liza_rt_cli_path(i32 %path)',
            '  %a = extractvalue {ptr,i32} %args, 0', '  %an = extractvalue {ptr,i32} %args, 1',
            '  %e = extractvalue {ptr,i32} %env, 0', '  %en = extractvalue {ptr,i32} %env, 1',
            '  %i = zext i1 %inherit to i32', '  %error = alloca i32',
            '  %c = call ptr @liza_rt_process_spawn(ptr %p, i32 %i, ptr %a, i32 %an, ptr %e, i32 %en, ptr %error)',
            '  %err = load i32, ptr %error',f'  %r0 = insertvalue {raw} zeroinitializer, ptr %c, 0',
            f'  %r = insertvalue {raw} %r0, i32 %err, 1',f'  ret {raw} %r','}'])
    elif name=='__liza_process_poll':
        raw='%struct.__liza_ProcessPoll'
        lines.extend(['declare i32 @liza_rt_process_poll(ptr, i32, ptr, ptr)',
            f'define internal {raw} @liza_{name}(ptr %child, i1 %block) {{',
            '  %kind = alloca i32','  %code = alloca i32','  %b = zext i1 %block to i32',
            '  %err = call i32 @liza_rt_process_poll(ptr %child, i32 %b, ptr %kind, ptr %code)',
            '  %k = load i32, ptr %kind','  %c = load i32, ptr %code',
            f'  %r0 = insertvalue {raw} zeroinitializer, i32 %err, 0',
            f'  %r1 = insertvalue {raw} %r0, i32 %k, 1',f'  %r = insertvalue {raw} %r1, i32 %c, 2',f'  ret {raw} %r','}'])
    elif name in ('__liza_process_op','__liza_process_close'):
        symbol='liza_rt_process_op' if name.endswith('_op') else 'liza_rt_process_close'
        args='ptr %child, i32 %op' if name.endswith('_op') else 'ptr %child'
        decl='ptr, i32' if name.endswith('_op') else 'ptr'
        lines.extend([f'declare i32 @{symbol}({decl})',f'define internal i32 @liza_{name}({args}) {{',f'  %r = call i32 @{symbol}({args})','  ret i32 %r','}'])
    elif name.startswith('__liza_fs_utf8_'):
        if name.endswith('_stat'):
            raw='%struct.__liza_FileInfo'
            lines.extend(['declare i32 @liza_rt_fs_utf8_stat(ptr, i32, ptr, ptr)',f'define internal {raw} @liza_{name}({{ptr,i32}} %path) {{',
                '  %p = extractvalue {ptr,i32} %path, 0','  %n = extractvalue {ptr,i32} %path, 1',
                '  %kind = alloca i32','  %size = alloca i64',
                '  %err = call i32 @liza_rt_fs_utf8_stat(ptr %p, i32 %n, ptr %kind, ptr %size)',
                '  %k = load i32, ptr %kind','  %s = load i64, ptr %size',
                f'  %r0 = insertvalue {raw} zeroinitializer, i32 %err, 0',f'  %r1 = insertvalue {raw} %r0, i32 %k, 1',
                f'  %r = insertvalue {raw} %r1, i64 %s, 2',f'  ret {raw} %r','}'])
        elif name.endswith('_op'):
            lines.extend(['declare i32 @liza_rt_fs_utf8_op(ptr, i32, i32)',f'define internal i32 @liza_{name}({{ptr,i32}} %path, i32 %op) {{',
                '  %p = extractvalue {ptr,i32} %path, 0','  %n = extractvalue {ptr,i32} %path, 1',
                '  %r = call i32 @liza_rt_fs_utf8_op(ptr %p, i32 %n, i32 %op)','  ret i32 %r','}'])
        else:
            raw='%struct.__liza_FileOpen'
            lines.extend(['declare i32 @liza_rt_fs_utf8_file(ptr, i32, i32, ptr)',f'define internal {raw} @liza_{name}({{ptr,i32}} %path, i1 %create) {{',
                '  %p = extractvalue {ptr,i32} %path, 0','  %n = extractvalue {ptr,i32} %path, 1','  %c = zext i1 %create to i32',
                '  %slot = alloca i64','  %err = call i32 @liza_rt_fs_utf8_file(ptr %p, i32 %n, i32 %c, ptr %slot)',
                '  %handle = load i64, ptr %slot',f'  %r0 = insertvalue {raw} zeroinitializer, i64 %handle, 0',
                f'  %r = insertvalue {raw} %r0, i32 %err, 1',f'  ret {raw} %r','}'])
    elif name=='__liza_fs_op':
        lines.extend(['declare i32 @liza_rt_fs_op(ptr, i32)',f'define internal i32 @liza_{name}(i32 %path, i32 %op) {{',
            '  %p = call ptr @liza_rt_cli_path(i32 %path)','  %r = call i32 @liza_rt_fs_op(ptr %p, i32 %op)','  ret i32 %r','}'])
    elif name=='__liza_fs_stat':
        raw='%struct.__liza_FileInfo'
        lines.extend(['declare i32 @liza_rt_fs_stat(ptr, ptr, ptr)',f'define internal {raw} @liza_{name}(i32 %path) {{',
            '  %p = call ptr @liza_rt_cli_path(i32 %path)','  %kind = alloca i32','  %size = alloca i64',
            '  %err = call i32 @liza_rt_fs_stat(ptr %p, ptr %kind, ptr %size)',
            '  %k = load i32, ptr %kind','  %s = load i64, ptr %size',
            f'  %r0 = insertvalue {raw} zeroinitializer, i32 %err, 0',f'  %r1 = insertvalue {raw} %r0, i32 %k, 1',
            f'  %r = insertvalue {raw} %r1, i64 %s, 2',f'  ret {raw} %r','}'])
    else:return False
    return True
