"""Trusted library signatures and source; no source-level arbitrary externs."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from .frontend import Parser, Function, Token, Program, Expr


def attach(program):
    libraries = [name for name in ('console', 'file') if getattr(program, 'uses_'+name, False)]
    if not libraries:
        return program, []
    library = Parser('\n'.join((Path(__file__).parent/'stdlib'/ (name+'.liza')).read_text(encoding='utf-8')
                               for name in libraries), internal=True).parse()
    for fn in library:
        if fn.name.text == 'file.read_chunk':
            fn.borrowed_params = [0]
    combined = Program()
    combined.module_names = getattr(program,"module_names",[])
    combined.declarations = getattr(program,"declarations",[])
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
    externals.append(Function(Token('__liza_read_file',1,1), [(Token('path',1,1),'Text')], [], '__liza_FileRead', 'io'))
    externals.extend([
        Function(Token('__liza_file_open',1,1), [(Token('path',1,1),'Text')], [], '__liza_FileOpen', 'io'),
        Function(Token('__liza_file_close',1,1), [(Token('handle',1,1),'File')], [], 'u32', 'io'),
        Function(Token('__liza_read_chunk',1,1), [(Token('handle',1,1),'File')], [], '__liza_FileRead', 'io', borrowed_params=[0]),
    ])
    return combined, [fn for fn in externals if fn.name.text in needed]


def link_flags(module):
    memory_used = any(op.op.startswith(('region.','buffer.')) for fn in module for block in fn.blocks for op in block.operations)
    memory_files = [str(Path(__file__).parent/'runtime'/'memory.c')] if memory_used else []
    if not getattr(module,'externals',[]):
        return memory_files
    import sys
    suffix = 'windows' if sys.platform == 'win32' else 'posix'
    names = {fn.name.text for fn in module.externals}
    file_names = {'__liza_read_file','__liza_file_open','__liza_file_close','__liza_read_chunk'}
    libraries = (['console'] if names-file_names else []) + (['file'] if names & file_names else [])
    files = memory_files + [str(Path(__file__).parent/'runtime'/ (name+'_'+suffix+'.c')) for name in libraries]
    if sys.platform == 'win32':
        return files
    if sys.platform not in ('darwin','linux'):
        raise ValueError('console runtime currently supports Linux, macOS and Windows only')
    return files + ['-pthread']
