"""Source -> AST. No backend semantics live here."""
from dataclasses import dataclass
import re
import json
from .types import SCALAR_TYPES, INTEGER_TYPES


@dataclass(frozen=True)
class Token:
    text: str
    line: int
    column: int


class CompileError(Exception):
    def __init__(self, token, message):
        super().__init__(f"{token.line}:{token.column}: {message}")


def lex(source):
    tokens = []
    pattern = re.compile(r'"(?:[^"\\\n]|\\[^\n])*"|//[^\n]*|[ \t\r]+|\n|0x[0-9a-fA-F]+|[0-9]+|[A-Za-z_][A-Za-z_0-9]*|\.\.|=>|->|==|!=|<<|>>|<=|>=|&&|\|\||[+*\-][%|]|[\[\]{}(),:=;+*\-!<>~&|^/%.]')
    pos, line, column = 0, 1, 1
    while pos < len(source):
        match = pattern.match(source, pos)
        if not match:
            raise CompileError(Token(source[pos], line, column), f"unexpected character {source[pos]!r}")
        value = match.group()
        if not value.startswith('//') and not value.isspace() or value == '\n':
            tokens.append(Token(value, line, column))
        if value == '\n':
            line, column = line + 1, 1
        else:
            column += len(value)
        pos = match.end()
    tokens.append(Token('<eof>', line, column))
    return tokens


@dataclass
class Expr:
    token: Token
    kind: str
    args: list


@dataclass
class Statement:
    token: Token
    expr: Expr
    is_return: bool
    annotation: str = ''
    is_var: bool = False


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


@dataclass
class LoopControl:
    token: Token


@dataclass
class Struct:
    name: Token
    fields: list


class Program(list):
    def __init__(self):
        super().__init__()
        self.structs = []
        self.enums = []


@dataclass
class Function:
    name: Token
    params: list
    body: list
    result_type: str
    effect_contract: str = 'pure'


class Parser:
    def __init__(self, source, internal=False):
        self.internal = internal
        self.tokens = lex(source)
        self.index = 0
        self.enum_names = {self.tokens[i+1].text for i,t in enumerate(self.tokens[:-1]) if t.text == "enum"} | {"IoError", "FileError"}

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
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token.text) or token.text in set(SCALAR_TYPES) | {'fn', 'return', 'pure', 'io', 'Text', 'true', 'false', 'if', 'else', 'var', 'while', 'break', 'continue', 'copy', 'move', 'struct', 'view', 'View', 'enum', 'match', 'Option', 'Result', 'Some', 'None', 'Ok', 'Err'}:
            raise CompileError(token, 'expected an identifier')
        return self.take()

    def separators(self):
        while self.current.text in ('\n', ';'):
            self.take()

    def type_name(self):
        if self.current.text == '[':
            self.take('[')
            element = self.type_name()
            self.take(';')
            length = self.take()
            if not re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', length.text):
                raise CompileError(length, 'array length must be a u32 integer literal')
            size = int(length.text, 16 if length.text.startswith('0x') else 10)
            if size > 4294967295:
                raise CompileError(length, 'array length exceeds u32')
            self.take(']')
            return f'[{element};{size}]'
        if self.current.text in ('View', 'Option', 'Result'):
            name = self.take().text
            self.take('<')
            args = [self.type_name()]
            if name == 'Result':
                self.take(',')
                args.append(self.type_name())
            if self.current.text == '>>':
                t = self.current
                self.tokens[self.index:self.index+1] = [Token('>',t.line,t.column), Token('>',t.line,t.column+1)]
            self.take('>')
            return name+'<'+','.join(args)+'>'
        if self.current.text == 'Text':
            return self.take().text
        if self.current.text in SCALAR_TYPES:
            return self.take().text
        return self.identifier().text

    def block(self):
        self.take('{')
        self.separators()
        body = []
        while self.current.text != '}':
            if self.current.text == 'if':
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
                annotation = ''
                if not is_return:
                    if self.current.text == ':':
                        self.take(':')
                        annotation = self.type_name()
                    self.take('=')
                body.append(Statement(token, self.expression(), is_return, annotation, is_var))
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
        name = self.identifier()
        self.take('{')
        fields = []
        self.separators()
        while self.current.text != '}':
            field = self.identifier()
            self.take(':')
            fields.append((field, self.type_name()))
            if self.current.text == ',':
                self.take(',')
            elif self.current.text not in ('\n', ';', '}'):
                raise CompileError(self.current, 'expected field separator or closing brace')
            self.separators()
        self.take('}')
        return Struct(name, fields)

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
            if self.current.text == '.':
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
        functions.uses_console = any(t.text in ('IoError', 'IoFailure') or
                                     (t.text == 'console' and self.tokens[i+1].text == '.')
                                     for i,t in enumerate(self.tokens[:-1]))
        functions.uses_file = any(t.text in ('FileError', 'FileFailure', 'FileBuffer') or
                                  (t.text == 'file' and self.tokens[i+1].text == '.')
                                  for i,t in enumerate(self.tokens[:-1]))
        self.separators()
        while self.current.text != '<eof>':
            if self.current.text == 'enum':
                functions.enums.append(self.enumeration())
                self.separators()
                continue
            if self.current.text == 'struct':
                functions.structs.append(self.structure())
                self.separators()
                continue
            self.take('fn')
            name = self.identifier()
            if self.internal and self.current.text == '.':
                self.take('.')
                name = Token(name.text+'.'+self.identifier().text, name.line, name.column)
            self.take('(')
            params = []
            if self.current.text != ')':
                while True:
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
                if self.current.text not in ('pure', 'io'):
                    raise CompileError(self.current, "expected 'pure' or 'io'")
                effect = self.take().text
            body = self.block()
            functions.append(Function(name, params, body, result_type, effect))
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
            left = Expr(Token(value,token.line,token.column), 'text', [])
        elif token.text == '-' and re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', self.tokens[self.index + 1].text):
            self.take()
            number = self.take()
            left = Expr(Token('-' + number.text, token.line, token.column), 'literal', [])
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
            left = Expr(Token(name,token.line,token.column), 'variant', args)
        elif token.text == '[':
            self.take('[')
            elements = []
            while self.current.text != ']':
                elements.append(self.expression())
                if self.current.text != ',':
                    break
                self.take(',')
            self.take(']')
            left = Expr(token, 'array', elements)
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
            name = self.identifier()
            if self.current.text == '.' and self.index+2 < len(self.tokens) and self.tokens[self.index+2].text == '(':
                self.take('.')
                name = Token(name.text+'.'+self.identifier().text,name.line,name.column)
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
                left = Expr(name, 'call', args)
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
