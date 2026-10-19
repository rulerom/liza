"""Trusted library signatures and source; no source-level arbitrary externs."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from .frontend import Parser, Function, Token, Program, Expr


def attach(program):
    if not getattr(program, 'uses_console', False):
        return program, []
    library = Parser((Path(__file__).parent/'stdlib/console.liza').read_text(), internal=True).parse()
    combined = Program()
    combined.extend(program)
    def calls(node):
        if isinstance(node, Expr) and node.kind == 'call':
            yield node.token.text
        if isinstance(node, list):
            for item in node:
                yield from calls(item)
        elif is_dataclass(node):
            for f in fields(node):
                yield from calls(getattr(node, f.name))
    definitions = {fn.name.text: fn for fn in library}
    needed = set(calls(list(program)))
    pending = list(needed)
    while pending:
        name = pending.pop()
        if name in definitions:
            for callee in calls(definitions[name].body):
                if callee not in needed:
                    needed.add(callee)
                    pending.append(callee)
    combined.extend(fn for fn in library if fn.name.text in needed)
    combined.structs = program.structs + library.structs
    combined.enums = program.enums + library.enums
    externals = [Function(Token(name,1,1), [(Token('value',1,1),t)], [], 'u64', 'io')
                 for name,t in [('__liza_write_text','Text'), ('__liza_write_bytes','View<u8>'),
                                ('__liza_print_u64','u64'), ('__liza_print_i64','i64')]]
    return combined, [fn for fn in externals if fn.name.text in needed]


def link_flags(module):
    if not getattr(module,'externals',[]):
        return []
    import sys
    if sys.platform == 'win32':
        return [str(Path(__file__).parent/'runtime/console_windows.c')]
    if sys.platform not in ('darwin','linux'):
        raise ValueError('console runtime currently supports Linux, macOS and Windows only')
    return [str(Path(__file__).parent/'runtime/console_posix.c'), '-pthread']
