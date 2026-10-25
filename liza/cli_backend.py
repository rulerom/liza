"""Private process-argument adapters. No source-level pointer or integer casts."""
import sys


def external(fn, lines):
    name=fn.name.text
    if name in ('__liza_cli_arg','__liza_cli_path'):
        lines.extend([f'define internal i32 @liza_{name}(i32 %index) {{',
                      '  ret i32 %index','}'])
    elif name=='__liza_cli_count':
        lines.extend(['declare i32 @liza_rt_cli_count()',
                      'define internal i32 @liza___liza_cli_count() {',
                      '  %n = call i32 @liza_rt_cli_count()', '  ret i32 %n','}'])
    elif name=='__liza_cli_ascii_at':
        lines.extend(['declare i32 @liza_rt_cli_ascii_at(i32, i32)',
                      'define internal i32 @liza___liza_cli_ascii_at(i32 %arg, i32 %index) {',
                      '  %r = call i32 @liza_rt_cli_ascii_at(i32 %arg, i32 %index)',
                      '  ret i32 %r', '}'])
    elif name=='__liza_cli_equals':
        lines.extend(['declare i32 @liza_rt_cli_equals(i32, ptr, i32)',
                      'define internal i1 @liza___liza_cli_equals(i32 %arg, { ptr, i32 } %text) {',
                      '  %p = extractvalue { ptr, i32 } %text, 0',
                      '  %n = extractvalue { ptr, i32 } %text, 1',
                      '  %r = call i32 @liza_rt_cli_equals(i32 %arg, ptr %p, i32 %n)',
                      '  %b = icmp ne i32 %r, 0', '  ret i1 %b','}'])
    elif name in ('__liza_file_open_path', '__liza_file_create_path'):
        operation='create' if name=='__liza_file_create_path' else 'open'
        if 'declare ptr @liza_rt_cli_path(i32)' not in lines:
            lines.append('declare ptr @liza_rt_cli_path(i32)')
        lines.extend([f'declare i32 @liza_rt_file_{operation}_native(ptr, ptr)',
                      f'define internal %struct.__liza_FileOpen @liza_{name}(i32 %index) {{',
                      '  %p = call ptr @liza_rt_cli_path(i32 %index)',
                      '  %slot = alloca i64',
                      f'  %error = call i32 @liza_rt_file_{operation}_native(ptr %p, ptr %slot)',
                      '  %handle = load i64, ptr %slot',
                      '  %base = insertvalue %struct.__liza_FileOpen zeroinitializer, i64 %handle, 0',
                      '  %r = insertvalue %struct.__liza_FileOpen %base, i32 %error, 1',
                      '  ret %struct.__liza_FileOpen %r','}'])
    elif name=='__liza_file_write':
        lines.extend(['declare i64 @liza_rt_file_write(i64, ptr, i32)',
                      'define internal i64 @liza___liza_file_write(i64 %handle, { ptr, i32 } %view) {',
                      '  %p = extractvalue { ptr, i32 } %view, 0',
                      '  %n = extractvalue { ptr, i32 } %view, 1',
                      '  %r = call i64 @liza_rt_file_write(i64 %handle, ptr %p, i32 %n)',
                      '  ret i64 %r','}'])
    elif name=='__liza_file_flush':
        lines.extend(['declare i32 @liza_rt_file_flush(i64)',
                      'define internal i32 @liza___liza_file_flush(i64 %handle) {',
                      '  %r = call i32 @liza_rt_file_flush(i64 %handle)', '  ret i32 %r','}'])
    else:return False
    return True


def entry(module):
    names={f.name.text for f in getattr(module,'externals',[])}
    if any(n.startswith('__liza_cli_') or n in ('__liza_file_open_path','__liza_file_create_path') for n in names):
        symbol='wmain' if sys.platform=='win32' else 'main'
        return ['declare void @liza_rt_cli_init(i32, ptr)',
                f'define i32 @{symbol}(i32 %argc, ptr %argv) {{','entry:',
                '  call void @liza_rt_cli_init(i32 %argc, ptr %argv)',
                '  %result = call i32 @liza_main()', '  ret i32 %result','}']
    return ['define i32 @main() {','entry:','  %result = call i32 @liza_main()',
            '  ret i32 %result','}']
