"""Source -> AST. No backend semantics live here."""
from dataclasses import dataclass, field
import re
import json
from .types import SCALAR_TYPES, INTEGER_TYPES


@dataclass(frozen=True)
class Token:
    text: str
    line: int
    column: int
    source: str = ""


class CompileError(Exception):
    def __init__(self, token, message):
        self.source = token.source
        super().__init__(f"{token.source + ':' if token.source else ''}{token.line}:{token.column}: {message}")


def lex(source, filename=""):
    tokens = []
    pattern = re.compile(r'"(?:[^"\\\n]|\\[^\n])*"|//[^\n]*|[ \t\r]+|\n|0x[0-9a-fA-F]+|[0-9]+|[A-Za-z_][A-Za-z_0-9]*|\.\.|=>|->|==|!=|<<|>>|<=|>=|&&|\|\||[+*\-][%|]|[\[\]{}(),:=;+*\-!<>~&|^/%.]')
    pos, line, column = 0, 1, 1
    while pos < len(source):
        match = pattern.match(source, pos)
        if not match:
            raise CompileError(Token(source[pos], line, column, filename), f"unexpected character {source[pos]!r}")
        value = match.group()
        if not value.startswith('//') and not value.isspace() or value == '\n':
            tokens.append(Token(value, line, column, filename))
        if value == '\n':
            line, column = line + 1, 1
        else:
            column += len(value)
        pos = match.end()
    tokens.append(Token('<eof>', line, column, filename))
    return tokens


@dataclass
class Expr:
    token: Token
    kind: str
    args: list
    type_args: list = field(default_factory=list)


@dataclass
class Statement:
    token: Token
    expr: Expr
    is_return: bool
    annotation: str = ''
    is_var: bool = False


@dataclass
class Destructure:
    token: Token
    names: list
    expr: Expr


@dataclass
class Update:
    token: Token
    target: Expr
    expr: Expr


@dataclass
class Conditional:
    token: Token
    condition: Expr
    then_body: list
    else_body: list


@dataclass
class While:
    token: Token
    condition: Expr
    body: list


@dataclass
class MatchArm:
    token: Token
    case: str
    binding: object
    body: list


@dataclass
class Match:
    token: Token
    expr: Expr
    arms: list


@dataclass
class Enum:
    name: Token
    cases: list
    public: bool = False
    module: str = ""


@dataclass
class LoopControl:
    token: Token


@dataclass
class Scope:
    token: Token
    body: list


@dataclass
class GenericParameter:
    token: Token
    kind: str = "type"
    bound: str = ""


@dataclass
class Struct:
    name: Token
    fields: list
    public: bool = False
    public_fields: list = field(default_factory=list)
    module: str = ""
    generic_params: list = field(default_factory=list)
    instantiation_chain: list = field(default_factory=list)


class Program(list):
    def __init__(self):
        super().__init__()
        self.structs = []
        self.enums = []
        self.imports = []


@dataclass
class Function:
    name: Token
    params: list
    body: list
    result_type: str
    effect_contract: str = 'pure'
    borrowed_params: list = field(default_factory=list)
    trusted_library: bool = False
    public: bool = False
    module: str = ""
    generic_params: list = field(default_factory=list)
    instantiation_chain: list = field(default_factory=list)
    # Source readonly permissions are distinct from non-consuming runtime adapters.
    readonly_params: list = field(default_factory=list)
    readonly_borrowed_params: list = field(default_factory=list)


class Parser:
    def __init__(self, source, internal=False, filename=""):
        self.internal = internal
        self.tokens = lex(source, filename)
        self.index = 0
        self.generic_scope = {}
        self.enum_names = {self.tokens[i+1].text for i,t in enumerate(self.tokens[:-1]) if t.text == "enum"} | {"ReactorError", "FrameError", "NetError", "IoError", "FileError", "MemoryError", "FileCreateError", "FileWriteError", "Utf8ErrorKind", "Utf8StreamErrorKind", "JsonErrorKind"}

    @property
    def current(self):
        return self.tokens[self.index]

    def take(self, expected=None):
        token = self.current
        if expected is not None and token.text != expected:
            raise CompileError(token, f"expected {expected!r}, got {token.text!r}")
        if token.text == '<eof>':
            raise CompileError(token, 'unexpected end of file')
        self.index += 1
        return token

    def identifier(self):
        token = self.current
        if token.text.startswith('__liza_') and not self.internal:
            raise CompileError(token, 'reserved implementation name')
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token.text) or token.text in set(SCALAR_TYPES) | {'import', 'pub', 'fn', 'return', 'pure', 'io', 'Text', 'File', 'Arg', 'Path', 'true', 'false', 'if', 'else', 'var', 'while', 'break', 'continue', 'copy', 'move', 'borrow', 'struct', 'view', 'View', 'enum', 'match', 'Option', 'Result', 'Some', 'None', 'Ok', 'Err'}:
            raise CompileError(token, 'expected an identifier')
        return self.take()

    def separators(self):
        while self.current.text in ('\n', ';'):
            self.take()

    def close_angle(self):
        if self.current.text == '>>':
            t = self.current
            self.tokens[self.index:self.index+1] = [Token('>',t.line,t.column,t.source), Token('>',t.line,t.column+1,t.source)]
        self.take('>')

    def capacity(self):
        token = self.take()
        if re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', token.text):
            n = int(token.text,16 if token.text.startswith('0x') else 10)
            if n > 4294967295: raise CompileError(token,'capacity exceeds u32')
            return str(n)
        if self.generic_scope.get(token.text) == 'u32': return token.text
        raise CompileError(token,'capacity must be a u32 literal or capacity parameter')

    def generic_parameters(self):
        params = []
        if self.current.text != '<': return params
        self.take('<')
        while True:
            token = self.identifier(); kind, bound = 'type', ''
            if self.current.text == ':':
                self.take(':'); constraint = self.take()
                if constraint.text == 'u32': kind = 'u32'
                elif constraint.text in ('copyable','implicit_copy'): bound = constraint.text
                else: raise CompileError(constraint,'expected u32, copyable or implicit_copy')
            if token.text in self.generic_scope: raise CompileError(token,'duplicate generic parameter')
            self.generic_scope[token.text] = kind
            params.append(GenericParameter(token,kind,bound))
            if self.current.text != ',': break
            self.take(',')
        self.close_angle()
        return params

    def type_arguments(self):
        self.take('<'); args = []
        while True:
            if re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', self.current.text):
                args.append(self.capacity())
            else: args.append(self.type_name())
            if self.current.text != ',': break
            self.take(',')
        self.close_angle()
        return args

    def type_name(self):
        if self.current.text == '[':
            self.take('['); element = self.type_name(); self.take(';')
            length = self.capacity(); self.take(']')
            return f'[{element};{length}]'
        if self.current.text in ('View','Option','Result'):
            name = self.take().text
            args = self.type_arguments()
            if len(args) != (2 if name == 'Result' else 1):
                raise CompileError(self.current,'wrong number of type arguments')
            return name+'<'+','.join(args)+'>'
        if self.current.text in SCALAR_TYPES + ('Text','File','Arg','Path'):
            return self.take().text
        name = self.qualified_name().text
        if self.current.text == '<': name += '<'+','.join(self.type_arguments())+'>'
        return name

    def qualified_name(self):
        first = self.identifier()
        name = first.text
        while self.current.text == ".":
            self.take(".")
            name += "." + (self.take().text if name in ("memory", "vec") and self.current.text == "view" else self.identifier().text)
        return Token(name, first.line, first.column, first.source)

    def block(self):
        self.take('{')
        self.separators()
        body = []
        while self.current.text != '}':
            if self.current.text == '(':
                token = self.take('(')
                names = [self.identifier()]
                self.take(',')
                while self.current.text != ')':
                    names.append(self.identifier())
                    if self.current.text != ',': break
                    self.take(',')
                self.take(')')
                self.take('=')
                body.append(Destructure(token, names, self.expression()))
                if self.current.text not in ('\n', ';', '}'):
                    raise CompileError(self.current, 'expected statement separator')
            elif self.current.text == '{':
                body.append(Scope(self.current, self.block()))
            elif self.current.text == 'if':
                body.append(self.conditional())
            elif self.current.text == 'match':
                body.append(self.match_statement())
            elif self.current.text == 'while':
                token = self.take('while')
                condition = self.expression()
                body.append(While(token, condition, self.block()))
            elif self.current.text in ('break', 'continue'):
                body.append(LoopControl(self.take()))
                if self.current.text not in ('\n', ';', '}'):
                    raise CompileError(self.current, 'expected newline, semicolon, or closing brace')
            else:
                is_var = self.current.text == 'var'
                if is_var:
                    self.take('var')
                is_return = not is_var and self.current.text == 'return'
                token = self.take('return') if is_return else self.identifier()
                target = Expr(token, 'name', [])
                while not is_return and self.current.text in ('.', '['):
                    if is_var:
                        raise CompileError(token, 'var declares a binding, not a field or element')
                    if self.current.text == '.':
                        self.take('.')
                        target = Expr(self.identifier(), 'field', [target])
                    else:
                        bracket = self.take('[')
                        index = self.expression()
                        self.take(']')
                        target = Expr(bracket, 'index', [target, index])
                annotation = ''
                if not is_return:
                    if self.current.text == ':' and target.kind == 'name':
                        self.take(':')
                        annotation = self.type_name()
                    self.take('=')
                rhs = self.expression()
                body.append(Update(token, target, rhs) if target.kind != 'name' else
                            Statement(token, rhs, is_return, annotation, is_var))
                if self.current.text not in ('\n', ';', '}'):
                    raise CompileError(self.current, 'expected newline, semicolon, or closing brace')
            self.separators()
        self.take('}')
        return body

    def conditional(self):
        token = self.take('if')
        condition = self.expression()
        then_body = self.block()
        # Permit else on the next line, without consuming a statement separator.
        saved = self.index
        while self.current.text == '\n':
            self.take()
        else_body = []
        if self.current.text == 'else':
            self.take()
            else_body = [self.conditional()] if self.current.text == 'if' else self.block()
        else:
            self.index = saved
        return Conditional(token, condition, then_body, else_body)

    def structure(self):
        self.take('struct')
        name = self.qualified_name() if self.internal else self.identifier()
        self.generic_scope = {}
        generics = self.generic_parameters()
        self.take('{')
        fields = []
        public_fields = []
        self.separators()
        while self.current.text != '}':
            public = self.current.text == "pub"
            if public: self.take("pub")
            field = self.identifier()
            if public: public_fields.append(field.text)
            self.take(':')
            fields.append((field, self.type_name()))
            if self.current.text == ',':
                self.take(',')
            elif self.current.text not in ('\n', ';', '}'):
                raise CompileError(self.current, 'expected field separator or closing brace')
            self.separators()
        self.take('}')
        self.generic_scope = {}
        return Struct(name, fields, public_fields=public_fields, generic_params=generics)

    def enumeration(self):
        self.take('enum')
        name = self.identifier()
        self.take('{')
        self.separators()
        cases = []
        while self.current.text != '}':
            case = self.identifier()
            payload = None
            if self.current.text == '(':
                self.take('(')
                payload = self.type_name()
                self.take(')')
            cases.append((case, payload))
            if self.current.text == ',':
                self.take(',')
            elif self.current.text not in ('\n', ';', '}'):
                raise CompileError(self.current, 'expected case separator')
            self.separators()
        self.take('}')
        if not cases:
            raise CompileError(name, 'enum must have at least one alternative')
        return Enum(name, cases)

    def match_statement(self):
        token = self.take('match')
        value = self.expression()
        self.take('{')
        self.separators()
        arms = []
        while self.current.text != '}':
            case = self.take() if self.current.text in ('Some','None','Ok','Err') else self.identifier()
            label = case.text
            while self.current.text == '.':
                self.take('.')
                label += '.'+self.identifier().text
            binding = None
            if self.current.text == '(':
                self.take('(')
                binding = self.identifier()
                self.take(')')
            self.take('=>')
            arms.append(MatchArm(case, label, binding, self.block()))
            if self.current.text == ',':
                self.take(',')
            self.separators()
        self.take('}')
        return Match(token, value, arms)

    def parse(self):
        functions = Program()
        functions.uses_json = any(t.text in ('JsonState','JsonError','JsonErrorKind') or (t.text == 'json' and self.tokens[i+1].text == '.') for i,t in enumerate(self.tokens[:-1]))
        functions.uses_framing = any(t.text in ('FrameState','FrameStep','FrameError') or (t.text == 'framing' and self.tokens[i+1].text == '.') for i,t in enumerate(self.tokens[:-1]))
        functions.uses_net = any(t.text in ('NetError','ReactorError') or (t.text == 'net' and self.tokens[i+1].text == '.') for i,t in enumerate(self.tokens[:-1]))
        functions.uses_cli = any(t.text in ('Arg', 'Path') or (t.text == 'cli' and self.tokens[i+1].text == '.')
                                 for i,t in enumerate(self.tokens[:-1]))
        functions.uses_console = any(t.text in ('IoError', 'IoFailure') or
                                     (t.text == 'console' and self.tokens[i+1].text == '.')
                                     for i,t in enumerate(self.tokens[:-1]))
        functions.uses_file = any(t.text in ('File', 'FileError', 'FileFailure', 'FileBuffer', 'FileChunk', 'FileCreateError', 'FileWriteError', 'FileWriteFailure') or
                                  (t.text == 'file' and self.tokens[i+1].text == '.')
                                  for i,t in enumerate(self.tokens[:-1]))
        functions.uses_utf8_stream = any(t.text in ('Utf8StreamState', 'Utf8StreamError', 'Utf8StreamErrorKind') or
                                         (t.text == 'utf8_stream' and self.tokens[i+1].text == '.')
                                         for i,t in enumerate(self.tokens[:-1]))
        functions.uses_utf8 = any(t.text in ('Utf8ErrorKind', 'Utf8Error', 'Utf8Step', 'Utf8Range', 'Utf8Done') or
                                  (t.text == 'utf8' and self.tokens[i+1].text == '.')
                                  for i,t in enumerate(self.tokens[:-1]))
        functions.uses_vec = any(t.text == 'vec' and self.tokens[i+1].text == '.' for i,t in enumerate(self.tokens[:-1]))
        functions.uses_memory = any(t.text == 'MemoryError' or (t.text == 'memory' and self.tokens[i+1].text == '.')
                                    for i,t in enumerate(self.tokens[:-1]))
        self.separators()
        while self.current.text != '<eof>':
            if self.current.text == 'import':
                self.take('import')
                functions.imports.append(self.qualified_name())
                if self.current.text not in ('\n', ';', '<eof>'):
                    raise CompileError(self.current, 'expected import separator')
                self.separators()
                continue
            public = self.current.text == 'pub'
            if public: self.take('pub')
            if self.current.text == 'enum':
                functions.enums.append(self.enumeration())
                functions.enums[-1].public = public
                self.separators()
                continue
            if self.current.text == 'struct':
                functions.structs.append(self.structure())
                functions.structs[-1].public = public
                self.separators()
                continue
            self.take('fn')
            name = self.identifier()
            if self.internal and self.current.text == '.':
                self.take('.')
                name = Token(name.text+'.'+self.identifier().text, name.line, name.column)
            self.generic_scope = {}
            generics = self.generic_parameters()
            self.take('(')
            params = []
            readonly = []
            if self.current.text != ')':
                while True:
                    if self.current.text == 'borrow':
                        self.take('borrow');readonly.append(len(params))
                    param = self.identifier()
                    self.take(':')
                    params.append((param, self.type_name()))
                    if self.current.text != ',':
                        break
                    self.take(',')
            self.take(')')
            self.take('->')
            result_type = self.type_name()
            effect = 'pure'
            if self.current.text == ':':
                self.take(':')
                if self.current.text not in ('pure', 'io', 'alloc'):
                    raise CompileError(self.current, "expected 'pure', 'io' or 'alloc'")
                effect = self.take().text
                while self.current.text == ',':
                    self.take(',')
                    next_effect = self.take()
                    if next_effect.text not in ('io', 'alloc') or effect == 'pure' or next_effect.text in effect.split(','):
                        raise CompileError(next_effect, 'invalid or duplicate effect')
                    effect += ',' + next_effect.text
            body = self.block()
            functions.append(Function(name, params, body, result_type, effect, trusted_library=self.internal, public=public, generic_params=generics, readonly_params=readonly))
            self.generic_scope = {}
            self.separators()
        return functions

    def expression(self, minimum=0):
        token = self.current
        if token.text.startswith('"'):
            self.take()
            try:
                value = json.loads(token.text)
                value.encode('utf-8')
            except (ValueError, UnicodeError):
                raise CompileError(token, 'invalid UTF-8 text literal or escape') from None
            left = Expr(Token(value,token.line,token.column,token.source), 'text', [])
        elif token.text == '-' and re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', self.tokens[self.index + 1].text):
            self.take()
            number = self.take()
            left = Expr(Token('-' + number.text, token.line, token.column,token.source), 'literal', [])
        elif token.text in ('Some','None','Ok','Err') or (token.text in self.enum_names and self.tokens[self.index+1].text == '.'):
            self.take()
            name = token.text
            if name in self.enum_names:
                self.take('.')
                name += '.'+self.identifier().text
            args = []
            if self.current.text == '(':
                self.take('(')
                if self.current.text != ')':
                    args.append(self.expression())
                self.take(')')
            left = Expr(Token(name,token.line,token.column,token.source), 'variant', args)
        elif token.text == '[':
            self.take('[')
            elements = []
            count = None
            while self.current.text != ']':
                elements.append(self.expression())
                if self.current.text == ';' and len(elements)==1:
                    self.take(';'); count=self.capacity()
                    break
                if self.current.text != ',':
                    break
                self.take(',')
            self.take(']')
            left = Expr(token, 'array.repeat', elements, [count]) if count is not None else Expr(token, 'array', elements)
        elif token.text == 'view':
            self.take('view')
            owner = Expr(self.identifier(), 'name', [])
            self.take('[')
            start = self.expression()
            self.take('..')
            end = self.expression()
            self.take(']')
            left = Expr(token, 'view', [owner, start, end])
        elif token.text in ('copy', 'move'):
            left = Expr(self.take(), token.text, [self.expression(11)])
            if token.text == 'move' and left.args[0].kind != 'name':
                raise CompileError(token, 'move requires a binding name')
        elif token.text in ('!', '~', '-'):
            left = Expr(self.take(), {'!': 'not', '~': 'bit_not', '-': 'neg'}[token.text], [self.expression(11)])
        elif token.text in INTEGER_TYPES:
            target = self.take()
            mode = 'checked'
            if self.current.text == '.':
                self.take('.')
                mode = self.take().text
                if mode not in ('wrap', 'saturate'):
                    raise CompileError(target, 'expected wrap or saturate conversion')
            self.take('(')
            arg = self.expression()
            self.take(')')
            left = Expr(target, 'convert.' + mode, [arg])
        elif token.text in ('true', 'false'):
            left = Expr(self.take(), 'bool', [])
        elif token.text == '(':
            self.take('(')
            left = self.expression()
            self.take(')')
        elif re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', token.text):
            left = Expr(self.take(), 'literal', [])
        else:
            start = self.index
            name = self.qualified_name()
            type_args = []
            if self.current.text == '<':
                saved_index, saved_tokens = self.index, self.tokens[:]
                try:
                    type_args = self.type_arguments()
                    if self.current.text != '(': raise CompileError(self.current,'expected call')
                except CompileError:
                    self.index, self.tokens, type_args = saved_index, saved_tokens, []
            if self.current.text != '(':
                self.index = start
                name = self.identifier()
            if self.current.text == '(':
                self.take('(')
                args = []
                if self.current.text != ')':
                    while True:
                        args.append(self.expression())
                        if self.current.text != ',':
                            break
                        self.take(',')
                self.take(')')
                left = Expr(name, 'call', args, type_args)
            else:
                left = Expr(name, 'name', [])
        while self.current.text in ('.', '['):
            if self.current.text == '.':
                self.take('.')
                field = self.identifier()
                left = Expr(field, 'field', [left])
            else:
                token = self.take('[')
                index = self.expression()
                self.take(']')
                left = Expr(token, 'index', [left, index])
        precedence = {'||': 1, '&&': 2, '|': 3, '^': 4, '&': 5,
                      '==': 6, '!=': 6, '<': 7, '<=': 7, '>': 7, '>=': 7,
                      '<<': 8, '>>': 8, '+': 9, '-': 9, '+%': 9, '-%': 9, '+|': 9, '-|': 9,
                      '*': 10, '*%': 10, '*|': 10, '/': 10, '%': 10}
        while self.current.text in precedence and precedence[self.current.text] >= minimum:
            op = self.take()
            right = self.expression(precedence[op.text] + 1)
            left = Expr(op, 'binary', [left, right])
        return left
