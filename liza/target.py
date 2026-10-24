"""Resolve a concrete LLVM environment before emitting a Liza module.

The selected Clang is the authority for its ABI. The probe has no headers or
runtime dependencies and does not execute target code (cross targets work).
"""
from dataclasses import dataclass, asdict
import re
import subprocess

PROBE = r'''
const unsigned liza_pointer_bits = sizeof(void *) * 8;
const unsigned liza_pointer_align = _Alignof(void *);
const unsigned liza_i64_align = _Alignof(long long);
const unsigned liza_i32_align = _Alignof(int);
const unsigned liza_little_endian = __BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__;
'''


@dataclass(frozen=True)
class Target:
    triple: str
    data_layout: str
    flags: tuple
    pointer_bits: int
    pointer_align: int
    i64_align: int
    i32_align: int
    little_endian: int

    def __post_init__(self):
        for field in (self.triple, self.data_layout):
            if not field or not re.fullmatch(r'[A-Za-z0-9_.:+-]+', field):
                raise ValueError('invalid LLVM target metadata')
        if self.pointer_bits != 64 or not self.little_endian:
            raise ValueError('Liza currently supports 64-bit little-endian targets only')

    def metadata(self):
        return asdict(self)


def probe(clang, flags):
    cmd = [clang, *flags, '-x', 'c', '-std=c11', '-S', '-emit-llvm', '-', '-o', '-']
    p = subprocess.run(cmd, input=PROBE, text=True, capture_output=True)
    if p.returncode:
        raise ValueError('cannot resolve LLVM target: ' + p.stderr.strip())
    def directive(name):
        m = re.search(r'^target '+name+r' = "([^"]+)"', p.stdout, re.M)
        if not m:
            raise ValueError('Clang omitted target ' + name)
        return m[1]
    values = {}
    for name in ('pointer_bits', 'pointer_align', 'i64_align', 'i32_align', 'little_endian'):
        m = re.search(r'@liza_'+name+r' = .*?constant i32 (\d+)', p.stdout)
        if not m:
            raise ValueError('Clang omitted ABI probe ' + name)
        values[name] = int(m[1])
    return directive('triple'), directive('datalayout'), values


def resolve(clang='clang', triple=None):
    first, _, _ = probe(clang, ('--target='+triple,) if triple else ())
    arch = first.split('-')[0]
    if arch in ('arm64', 'aarch64'):
        cpu = '-mcpu=generic'
    elif arch in ('x86_64', 'amd64'):
        cpu = '-march=x86-64'
    else:
        raise ValueError('unsupported Liza target architecture: ' + arch)
    # Canonicalize with Clang itself, then explicitly select exactly that target
    # and the same baseline CPU for generation and all subsequent compilation.
    flags = ('--target='+first, cpu)
    canonical, layout, abi = probe(clang, flags)
    flags = ('--target='+canonical, cpu)
    again, same_layout, same_abi = probe(clang, flags)
    if (again, same_layout, same_abi) != (canonical, layout, abi):
        raise ValueError('Clang target environment is not stable')
    return Target(canonical, layout, flags, **abi)
