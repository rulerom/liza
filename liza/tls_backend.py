"""Optional TLS backend. C receives only scalars/pointers and an explicit output array."""
from pathlib import Path
import os
import subprocess
import sys
from .types import product_args


def link_flags():
    prefix = os.environ.get('LIZA_OPENSSL_PREFIX')
    if not prefix and sys.platform == 'darwin':
        prefix = subprocess.check_output(['brew', '--prefix', 'openssl@3'], text=True).strip()
    if prefix:
        root = Path(prefix)
        if sys.platform == 'win32':
            flags = ['-I'+str(root/'include'), str(root/'lib/libssl.lib'), str(root/'lib/libcrypto.lib')]
        else:
            flags = ['-I'+str(root/'include'), '-L'+str(root/'lib'), '-Wl,-rpath,'+str(root/'lib'), '-lssl', '-lcrypto']
    else:
        flags = subprocess.check_output(['pkg-config', '--cflags', '--libs', 'openssl'], text=True).split()
    if sys.platform == 'darwin': flags += ['-framework', 'Security', '-framework', 'CoreFoundation']
    if sys.platform == 'win32':
        # O0 preserves bounded aggregate snapshots in native protocol callers.
        # The default PE reserve (1 MiB) is insufficient for their call chains.
        # This is an executable main-stack reserve, not TLS managed memory;
        # pages commit on demand. Explicit SG2 stack budgets remain separate;
        # legacy native threads using the PE default inherit this reserve.
        flags += ['-lcrypt32', '-Wl,/STACK:8388608']
    return flags


def external(fn, lines, types):
    name = fn.name.text
    if name == '__liza_crypto_hmac_sha256':
        result=types[fn.result_type]
        lines.extend(['declare i32 @liza_rt_hmac_sha256(ptr, i32, ptr, i32, ptr)',
            f'define internal {result} @liza_{name}({{ ptr, i32 }} %key, {{ ptr, i32 }} %data) {{',
            '  %kp = extractvalue { ptr, i32 } %key, 0','  %kn = extractvalue { ptr, i32 } %key, 1',
            '  %dp = extractvalue { ptr, i32 } %data, 0','  %dn = extractvalue { ptr, i32 } %data, 1',
            '  %out = alloca [32 x i8]','  store [32 x i8] zeroinitializer, ptr %out',
            '  %code = call i32 @liza_rt_hmac_sha256(ptr %kp, i32 %kn, ptr %dp, i32 %dn, ptr %out)',
            '  %bytes = load [32 x i8], ptr %out',
            f'  %r0 = insertvalue {result} zeroinitializer, [32 x i8] %bytes, 0',
            f'  %r1 = insertvalue {result} %r0, i32 %code, 1',f'  ret {result} %r1','}'])
        return True
    if name == 'tls.managed_bytes':
        lines.extend(['declare i64 @liza_rt_tls_bytes()', 'define internal i64 @liza_tls.managed_bytes() {',
                      '  %r = call i64 @liza_rt_tls_bytes()', '  ret i64 %r', '}'])
        return True
    if not name.startswith('__liza_tls_'): return False
    result = types[fn.result_type]
    if name == '__liza_tls_destroy':
        lines.extend(['declare i32 @liza_tls_destroy(ptr)',
                      'define internal i32 @liza___liza_tls_destroy(ptr %s) {',
                      '  %r = call i32 @liza_tls_destroy(ptr %s)', '  ret i32 %r', '}'])
        return True
    if name == '__liza_tls_create':
        lines.extend(['declare i32 @liza_rt_tls_create(ptr, i32, ptr, i32, i32, i64, i64, i64, ptr)',
            f'define internal {result} @liza_{name}({{ ptr, i32 }} %peer, {{ ptr, i32 }} %ca, i32 %mode, i64 %budget, i64 %now, i64 %deadline) {{',
            '  %p = extractvalue { ptr, i32 } %peer, 0', '  %pn = extractvalue { ptr, i32 } %peer, 1',
            '  %c = extractvalue { ptr, i32 } %ca, 0', '  %cn = extractvalue { ptr, i32 } %ca, 1',
            '  %out = alloca ptr', '  store ptr null, ptr %out',
            '  %code = call i32 @liza_rt_tls_create(ptr %p, i32 %pn, ptr %c, i32 %cn, i32 %mode, i64 %budget, i64 %now, i64 %deadline, ptr %out)',
            '  %s = load ptr, ptr %out', f'  %r0 = insertvalue {result} zeroinitializer, ptr %s, 0',
            f'  %r1 = insertvalue {result} %r0, i32 %code, 1', f'  ret {result} %r1', '}'])
        return True
    read = name in ('__liza_tls_read','__liza_tls_drain')
    raw_type = types[product_args(fn.result_type)[1]] if read else result
    declaration = 'declare void @liza_rt_tls_step(i32, ptr, ptr, i32, i32, i32, i64, ptr)'
    if declaration not in lines: lines.append(declaration)
    params = ('ptr %s, { ptr, i32 } %data, i32 %start, i32 %count, i64 %now' if read else
              'i32 %op, ptr %s, { ptr, i32 } %data, i32 %start, i32 %count, i64 %now')
    op = ('2' if name == '__liza_tls_read' else '5') if read else '%op'
    lines.extend([f'define internal {result} @liza_{name}({params}) {{',
        '  %p = extractvalue { ptr, i32 } %data, 0', '  %n = extractvalue { ptr, i32 } %data, 1',
        '  %out = alloca [6 x i64]', '  store [6 x i64] zeroinitializer, ptr %out',
        f'  call void @liza_rt_tls_step(i32 {op}, ptr %s, ptr %p, i32 %n, i32 %start, i32 %count, i64 %now, ptr %out)'])
    for i in range(6):
        lines.extend([f'  %p{i} = getelementptr [6 x i64], ptr %out, i32 0, i32 {i}',
                      f'  %v{i} = load i64, ptr %p{i}',
                      f'  %r{i} = insertvalue {raw_type} '+('zeroinitializer' if i==0 else '%r'+str(i-1))+f', i64 %v{i}, {i}'])
    if read:
        lines.extend([f'  %b = insertvalue {result} zeroinitializer, {{ ptr, i32 }} %data, 0',
                      f'  %all = insertvalue {result} %b, {raw_type} %r5, 1', f'  ret {result} %all', '}'])
    else: lines.extend([f'  ret {result} %r5', '}'])
    return True
