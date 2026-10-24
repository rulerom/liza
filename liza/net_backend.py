"""Scalar/pointer TCP ABI; buffer storage stays in its original region."""
from .types import product_args


def external(fn, lines, types):
    name=fn.name.text
    if name=='net.read':
        result=types[fn.result_type]
        status=types[product_args(fn.result_type)[1]]
        error=types['NetError']
        # Runtime codes 1..7 correspond to the seven NetError alternatives.
        lines.extend(['declare i64 @liza_rt_net_read(i64, ptr, i32)',
            f'define internal {result} @liza_net.read(i64 %handle, {{ ptr, i32 }} %buffer) {{',
            '  %p = extractvalue { ptr, i32 } %buffer, 0',
            '  %n = extractvalue { ptr, i32 } %buffer, 1',
            '  %raw = call i64 @liza_rt_net_read(i64 %handle, ptr %p, i32 %n)',
            '  %count = trunc i64 %raw to i32',
            '  %wide = lshr i64 %raw, 32', '  %code = trunc i64 %wide to i32',
            '  %failed = icmp ne i32 %code, 0', '  %tag = zext i1 %failed to i32',
            '  %errtag = sub i32 %code, 1',
            f'  %err = insertvalue {error} zeroinitializer, i32 %errtag, 0',
            f'  %s0 = insertvalue {status} zeroinitializer, i32 %tag, 0',
            f'  %s1 = insertvalue {status} %s0, i32 %count, 1',
            f'  %s2 = insertvalue {status} %s1, {error} %err, 2',
            f'  %r0 = insertvalue {result} zeroinitializer, {{ ptr, i32 }} %buffer, 0',
            f'  %r1 = insertvalue {result} %r0, {status} %s2, 1',
            f'  ret {result} %r1','}'])
    elif name in ('__liza_net_listen','__liza_net_accept'):
        operation=name.removeprefix('__liza_net_');arg='i16' if operation=='listen' else 'i64'
        result=types[fn.result_type]
        lines.extend([f'declare i32 @liza_rt_net_{operation}({arg}, ptr)',
            f'define internal {result} @liza_{name}({arg} %arg) {{',
            '  %slot = alloca i64',
            f'  %code = call i32 @liza_rt_net_{operation}({arg} %arg, ptr %slot)',
            '  %handle = load i64, ptr %slot',
            f'  %r0 = insertvalue {result} zeroinitializer, i64 %handle, 0',
            f'  %r1 = insertvalue {result} %r0, i32 %code, 1',f'  ret {result} %r1','}'])
    elif name in ('__liza_net_close_listener','__liza_net_close_stream','__liza_net_port'):
        symbol='liza_rt_net_port' if name.endswith('_port') else 'liza_rt_net_close'
        ret='i64' if name.endswith('_port') else 'i32'
        declaration=f'declare {ret} @{symbol}(i64)'
        if declaration not in lines:lines.append(declaration)
        lines.extend([f'define internal {ret} @liza_{name}(i64 %handle) {{',
            f'  %r = call {ret} @{symbol}(i64 %handle)',f'  ret {ret} %r','}'])
    elif name=='__liza_net_write':
        lines.extend(['declare i64 @liza_rt_net_write(i64, ptr, i32, i32, i32)',
            f'define internal i64 @liza_{name}(i64 %handle, {{ ptr, i32 }} %data, i32 %start, i32 %count) {{',
            '  %p = extractvalue { ptr, i32 } %data, 0',
            '  %n = extractvalue { ptr, i32 } %data, 1',
            '  %r = call i64 @liza_rt_net_write(i64 %handle, ptr %p, i32 %n, i32 %start, i32 %count)',
            '  ret i64 %r','}'])
    else:return False
    return True
