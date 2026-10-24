"""Trusted library signatures and source; no source-level arbitrary externs."""
from pathlib import Path
from dataclasses import fields, is_dataclass
from .frontend import Parser, Function, Token, Program, Expr


def attach(program):
    libraries = [name for name in ('console', 'file', 'utf8', 'utf8_stream', 'cli', 'net') if getattr(program, 'uses_'+name, False)]
    if not libraries:
        return program, []
    library = Parser('\n'.join((Path(__file__).parent/'stdlib'/ (name+'.liza')).read_text(encoding='utf-8')
                               for name in libraries), internal=True).parse()
    for structure in library.structs:
        if structure.name.text == 'Utf8StreamState':
            structure.module = '__liza_utf8_stream'
    for fn in library:
        if fn.name.text.startswith(('utf8_stream.', '__liza_stream_')):
            fn.module = '__liza_utf8_stream'
        if fn.name.text in ('net.accept','net.local_port','net.write','file.read_chunk', 'file.write_chunk', 'file.flush'):
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
    externals.extend(Function(Token(name,1,1), [(Token('value',1,1),t)], [], 'u64', 'io')
                     for name,t in [('__liza_err_text','Text'),('__liza_err_bytes','View<u8>'),
                                    ('__liza_err_print_u64','u64'),('__liza_err_print_i64','i64')])
    externals.append(Function(Token('__liza_read_file',1,1), [(Token('path',1,1),'Text')], [], '__liza_FileRead', 'io'))
    externals.extend([
        Function(Token('__liza_file_open',1,1), [(Token('path',1,1),'Text')], [], '__liza_FileOpen', 'io'),
        Function(Token('__liza_file_close',1,1), [(Token('handle',1,1),'File')], [], 'u32', 'io'),
        Function(Token('__liza_read_chunk',1,1), [(Token('handle',1,1),'File')], [], '__liza_FileRead', 'io', borrowed_params=[0]),
    ])
    externals.extend([
        Function(Token('__liza_cli_count',1,1), [], [], 'u32', 'io'),
        Function(Token('__liza_cli_arg',1,1), [(Token('index',1,1),'u32')], [], 'Arg', 'io'),
        Function(Token('__liza_cli_path',1,1), [(Token('index',1,1),'u32')], [], 'Path', 'io'),
        Function(Token('__liza_cli_equals',1,1), [(Token('arg',1,1),'Arg'),(Token('text',1,1),'Text')], [], 'bool', 'pure'),
        Function(Token('__liza_file_create_path',1,1), [(Token('path',1,1),'Path')], [], '__liza_FileOpen', 'io'),
        Function(Token('__liza_file_write',1,1), [(Token('handle',1,1),'File'),(Token('data',1,1),'View<u8>')], [], 'u64', 'io', borrowed_params=[0]),
        Function(Token('__liza_file_flush',1,1), [(Token('handle',1,1),'File')], [], 'u32', 'io', borrowed_params=[0]),
        Function(Token('__liza_file_open_path',1,1), [(Token('path',1,1),'Path')], [], '__liza_FileOpen', 'io'),
    ])
    from .types import product_type
    net_externals = [
        ('__liza_net_listen',['u16'],'__liza_NetListener',[]),
        ('__liza_net_accept',['net.Listener'],'__liza_NetStream',[0]),
        ('__liza_net_port',['net.Listener'],'u64',[0]),
        ('__liza_net_close_listener',['net.Listener'],'u32',[]),
        ('__liza_net_close_stream',['net.Stream'],'u32',[]),
        ('__liza_net_write',['net.Stream','View<u8>','u32','u32'],'u64',[0]),
        ('net.read',['net.Stream','memory.Buffer<u8>'],product_type('memory.Buffer<u8>','Result<u32,NetError>'),[0]),
    ]
    externals.extend(Function(Token(n,1,1),[(Token('p'+str(i),1,1),t) for i,t in enumerate(params)],[],result,'io',borrowed_params=borrowed)
                     for n,params,result,borrowed in net_externals)
    return combined, [fn for fn in externals if fn.name.text in needed]


def link_flags(module):
    memory_used = any(op.op.startswith(('region.','buffer.','vec.')) for fn in module for block in fn.blocks for op in block.operations)
    memory_files = [str(Path(__file__).parent/'runtime'/'memory.c')] if memory_used else []
    if not getattr(module,'externals',[]):
        return memory_files
    import sys
    suffix = 'windows' if sys.platform == 'win32' else 'posix'
    names = {fn.name.text for fn in module.externals}
    file_names = {'__liza_read_file','__liza_file_open','__liza_file_close','__liza_read_chunk','__liza_file_open_path','__liza_file_create_path','__liza_file_write','__liza_file_flush'}
    net_names = {n for n in names if n.startswith('__liza_net_') or n=='net.read'}
    cli_names = {n for n in names if n.startswith('__liza_cli_')}
    libraries = (['console'] if names-file_names-cli_names-net_names else []) + (['file'] if names & file_names else [])
    if net_names: libraries.append('net')
    if cli_names or names & {'__liza_file_open_path','__liza_file_create_path'}: libraries.append('cli')
    files = memory_files + [str(Path(__file__).parent/'runtime'/ (name+'_'+suffix+'.c')) for name in libraries]
    if sys.platform == 'win32':
        return files + (['ws2_32.lib'] if net_names else [])
    if sys.platform not in ('darwin','linux'):
        raise ValueError('console runtime currently supports Linux, macOS and Windows only')
    return files + ['-pthread']
