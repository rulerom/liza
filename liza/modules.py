"""Root-confined source modules, nominal names and visibility before lowering.

Modules are loaded once, then merged into one program. No runtime initialization,
separate-compilation ABI, module globals, or changes to value semantics.
"""
from dataclasses import replace
from pathlib import Path
from .frontend import (Parser, Program, CompileError, Token, Expr, Statement,
                       Update, Conditional, While, Match, LoopControl, Scope, Destructure, Struct, Enum)
from .types import SCALAR_TYPES, is_array, is_view, element_type, array_length, generic_args, type_application

BUILTINS = set(SCALAR_TYPES) | {'FrameState','FrameStep','FrameError','net.Address','net.Listener','net.Stream','net.DatagramSocket','net.Reactor','net.Connection','ReactorError','NetError','UdpError','Text','File','Arg','Path','IoError','IoFailure','FileError',
    'FileFailure','FileBuffer','FileChunk','FileCreateError','FileWriteError','FileWriteFailure','memory.Region','MemoryError','vec.Done','vec.Error',
    'Utf8ErrorKind','Utf8Error','Utf8Step','Utf8Range','Utf8Done',
    'Utf8StreamState','Utf8StreamError','Utf8StreamErrorKind','JsonState','JsonError','JsonErrorKind'}
RESERVED = {'console','file','memory','vec','utf8','utf8_stream','cli','net','framing','json','workers'}


def load_program(source, project_root=None):
    source = Path(source).absolute()
    root = Path(project_root).absolute() if project_root is not None else source.parent
    try:
        relative = source.relative_to(root)
    except ValueError:
        raise ValueError('entry source must be inside project root') from None
    root = root.resolve()
    if relative.suffix != '.liza':
        raise ValueError('module source must have .liza extension')
    entry_parts = relative.with_suffix('').parts
    if any(not part.isascii() or not part.isidentifier() for part in entry_parts):
        raise ValueError('entry path components must be module identifiers')
    entry = '.'.join(entry_parts)
    loaded, active, symbols = {}, [], {}

    def path_for(name, token):
        parts = name.split('.')
        if parts[0] in RESERVED or parts[0] in BUILTINS:
            raise CompileError(token,'reserved standard-library namespace')
        if any(not p.isascii() or not p.isidentifier() or p.startswith('__liza_') for p in parts):
            raise CompileError(token,'invalid module path')
        path = root
        for part in parts[:-1] + [parts[-1]+'.liza']:
            # Reject case aliases and symlinks even on case-insensitive hosts.
            if not path.is_dir() or part not in {p.name for p in path.iterdir()}:
                raise CompileError(token,f'module {name!r} not found under project root')
            path = path / part
            if path.is_symlink():
                raise CompileError(token,'symlink module paths are not supported')
        if not path.is_file():
            raise CompileError(token,'module path must name a source file')
        return path

    def visit(name, token):
        if name in active:
            raise CompileError(token,'cyclic import: '+' -> '.join(active+[name]))
        if name in loaded: return
        path = path_for(name,token)
        active.append(name)
        program = Parser(path.read_text(encoding='utf-8'), filename=str(path)).parse()
        declared = {}
        for decl in list(program)+program.structs+program.enums:
            if decl.name.text in RESERVED:
                raise CompileError(decl.name,'reserved standard-library namespace')
            if decl.name.text in declared:
                raise CompileError(decl.name,'duplicate declaration')
            declared[decl.name.text] = decl
        imports = {}
        for imported in program.imports:
            head = imported.text.split('.')[0]
            if head in RESERVED or head in BUILTINS:
                raise CompileError(imported,'reserved standard-library namespace')
            if head in declared:
                raise CompileError(imported,'import namespace conflicts with declaration')
            if imported.text in imports:
                raise CompileError(imported,'duplicate import')
            imports[imported.text] = imported
            visit(imported.text,imported)
        loaded[name] = (program,declared,imports)
        for local,decl in declared.items():
            canonical = 'main' if name == entry and local == 'main' and decl in program else name+'.'+local
            symbols[name+'.'+local] = canonical
        active.pop()

    visit(entry,Token(entry,1,1,str(source)))
    for name in loaded:
        if name in symbols:
            raise CompileError(Token(name,1,1), "module namespace conflicts with declaration "+name)
    combined = Program()
    combined.module_names = sorted(loaded)
    combined.source_paths = [root.joinpath(*name.split(".")).with_suffix(".liza").resolve() for name in loaded]
    combined.declarations = []

    for module,(program,declared,imports) in loaded.items():
        heads = {n.split('.')[0] for n in imports}
        parameters = {}
        def resolve(name, token):
            # A qualified name is visible only through an explicit import.
            if name in declared:
                return symbols[module+'.'+name],declared[name]
            for imported in sorted(imports,key=len,reverse=True):
                prefix = imported+'.'
                if name.startswith(prefix):
                    local = name[len(prefix):]
                    other = loaded[imported][1]
                    if local in other:
                        decl = other[local]
                        if not decl.public:
                            raise CompileError(token,f'{name} is private')
                        return symbols[imported+'.'+local],decl
            if name in BUILTINS: return name,None
            raise CompileError(token,f'unknown or unimported declaration {name!r}')

        def type_name(t, token, exported=False, allow_capacity=False):
            if t in parameters:
                if parameters[t].kind == "u32" and not allow_capacity:
                    raise CompileError(token,"capacity parameter is not a type")
                return t
            if t.isdigit():
                if not allow_capacity: raise CompileError(token,"capacity value is not a type")
                return t
            if is_array(t):
                return '['+type_name(element_type(t),token,exported)+';'+t[1:-1].rsplit(';',1)[1]+']'
            if is_view(t): return 'View<'+type_name(element_type(t),token,exported)+'>'
            application = type_application(t)
            if application is not None:
                base,args = application
                if base in ('Option','Result','memory.Buffer','vec.Vec','__liza_Product'):
                    return base+'<'+','.join(type_name(a,token,exported) for a in args)+'>'
                canonical,decl = resolve(base,token)
                if not isinstance(decl,Struct) or not decl.generic_params:
                    raise CompileError(token,'expected generic structure')
                if exported and not decl.public: raise CompileError(token,'public interface exposes private type '+base)
                if len(args)!=len(decl.generic_params): raise CompileError(token,'wrong number of generic arguments')
                return canonical+'<'+','.join(type_name(a,token,exported,p.kind=='u32') for a,p in zip(args,decl.generic_params))+'>'
            canonical,decl = resolve(t,token)
            if decl is not None and not isinstance(decl,(Struct,Enum)):
                raise CompileError(token,'expected type declaration')
            if exported and decl is not None and not decl.public:
                raise CompileError(token,'public interface exposes private type '+t)
            return canonical

        def variant(name,token):
            if '.' not in name: return name
            owner,case=name.rsplit('.',1)
            canonical,decl=resolve(owner,token)
            if decl is not None and not isinstance(decl,Enum):
                raise CompileError(token,'expected enum type')
            return canonical+'.'+case

        def chain(node):
            if node.kind=='name': return node.token.text
            if node.kind=='field':
                parent=chain(node.args[0])
                if parent is not None:return parent+'.'+node.token.text
            return None

        def expression(node):
            if node.kind=='field':
                path=chain(node)
                # Imported enum constants have no call parentheses.
                if path and path.split('.')[0] in heads:
                    qualified=variant(path,node.token)
                    return Expr(replace(node.token,text=qualified),'variant',[])
            node.args=[expression(a) for a in node.args]
            if node.kind=='call':
                name=node.token.text
                if name.split('.')[0] in RESERVED:
                    node.type_args=[type_name(t,node.token,allow_capacity=True) for t in node.type_args]
                    return node
                owner = name.rsplit('.',1)[0] if '.' in name else ''
                enum_decl = declared.get(owner)
                for imported in sorted(imports,key=len,reverse=True):
                    if owner.startswith(imported+'.'):
                        enum_decl = loaded[imported][1].get(owner[len(imported)+1:])
                        break
                if isinstance(enum_decl,Enum):
                    canonical=variant(name,node.token);node.kind='variant'
                else:
                    canonical,decl=resolve(name,node.token)
                node.type_args=[type_name(t,node.token,allow_capacity=True) for t in node.type_args]
                node.token=replace(node.token,text=canonical)
            elif node.kind=='variant':
                node.token=replace(node.token,text=variant(node.token.text,node.token))
            return node

        def binding(token):
            if token.text in heads or token.text in RESERVED or token.text in parameters:
                raise CompileError(token,'binding conflicts with module namespace')

        def statements(body):
            for stmt in body:
                if isinstance(stmt,Destructure):
                    for name in stmt.names: binding(name)
                    stmt.expr=expression(stmt.expr)
                elif isinstance(stmt,Scope):
                    statements(stmt.body)
                elif isinstance(stmt,Conditional):
                    stmt.condition=expression(stmt.condition)
                    statements(stmt.then_body);statements(stmt.else_body)
                elif isinstance(stmt,While):
                    stmt.condition=expression(stmt.condition);statements(stmt.body)
                elif isinstance(stmt,Match):
                    stmt.expr=expression(stmt.expr)
                    for arm in stmt.arms:
                        arm.case=variant(arm.case,stmt.expr.token)
                        if arm.binding:binding(arm.binding)
                        statements(arm.body)
                elif isinstance(stmt,Update):
                    stmt.target=expression(stmt.target);stmt.expr=expression(stmt.expr)
                elif isinstance(stmt,Statement):
                    if not stmt.is_return:binding(stmt.token)
                    if stmt.annotation:stmt.annotation=type_name(stmt.annotation,stmt.token)
                    stmt.expr=expression(stmt.expr)
                elif not isinstance(stmt,LoopControl):raise AssertionError(type(stmt))

        for decl in program.structs:
            parameters={p.token.text:p for p in decl.generic_params}
            if set(parameters) & (set(declared)|heads|RESERVED):
                raise CompileError(decl.name,"generic parameter conflicts with declaration or namespace")
            decl.fields=[(tok,type_name(t,tok,decl.public and tok.text in decl.public_fields)) for tok,t in decl.fields]
        for decl in program.enums:
            parameters={}
            decl.cases=[(tok,type_name(t,tok,decl.public) if t else None) for tok,t in decl.cases]
        for fn in program:
            parameters={p.token.text:p for p in fn.generic_params}
            if set(parameters) & (set(declared)|heads|RESERVED):
                raise CompileError(fn.name,"generic parameter conflicts with declaration or namespace")
            for token,_ in fn.params: binding(token)
            fn.params=[(token,type_name(t,token,fn.public)) for token,t in fn.params]
            fn.result_type=type_name(fn.result_type,fn.name,fn.public)
            statements(fn.body)
        for local,decl in declared.items():
            canonical=symbols[module+'.'+local]
            combined.declarations.append({'id':module+'.'+local,'symbol':canonical,'module':module,
                                          'public':decl.public})
            decl.module=module
            decl.name=replace(decl.name,text=canonical)
        combined.extend(program)
        combined.structs.extend(program.structs);combined.enums.extend(program.enums)
    for name in RESERVED:
        setattr(combined,'uses_'+name,any(getattr(p,'uses_'+name,False) for p,_,_ in loaded.values()))
    return combined
