"""Source -> AST. No backend semantics live here."""
from dataclasses import dataclass
import re
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
    pattern = re.compile(r"//[^\n]*|[ \t\r]+|\n|0x[0-9a-fA-F]+|[0-9]+|[A-Za-z_][A-Za-z_0-9]*|->|==|!=|<<|>>|<=|>=|&&|\|\||[+*\-][%|]|[{}(),:=;+*\-!<>~&|^/%.]")
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
class LoopControl:
    token: Token


@dataclass
class Function:
    name: Token
    params: list
    body: list
    result_type: str


class Parser:
    def __init__(self, source):
        self.tokens = lex(source)
        self.index = 0

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
        if not re.fullmatch(r'[A-Za-z_][A-Za-z_0-9]*', token.text) or token.text in set(SCALAR_TYPES) | {'fn', 'return', 'pure', 'true', 'false', 'if', 'else', 'var', 'while', 'break', 'continue', 'copy', 'move'}:
            raise CompileError(token, 'expected an identifier')
        return self.take()

    def separators(self):
        while self.current.text in ('\n', ';'):
            self.take()

    def type_name(self):
        if self.current.text not in SCALAR_TYPES:
            raise CompileError(self.current, 'expected a fixed-width integer type or bool')
        return self.take().text

    def block(self):
        self.take('{')
        self.separators()
        body = []
        while self.current.text != '}':
            if self.current.text == 'if':
                body.append(self.conditional())
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

    def parse(self):
        functions = []
        self.separators()
        while self.current.text != '<eof>':
            self.take('fn')
            name = self.identifier()
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
            if self.current.text == ':':
                self.take(':')
                self.take('pure')
            body = self.block()
            functions.append(Function(name, params, body, result_type))
            self.separators()
        return functions

    def expression(self, minimum=0):
        token = self.current
        if token.text == '-' and re.fullmatch(r'0x[0-9a-fA-F]+|[0-9]+', self.tokens[self.index + 1].text):
            self.take()
            number = self.take()
            left = Expr(Token('-' + number.text, token.line, token.column), 'literal', [])
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
        precedence = {'||': 1, '&&': 2, '|': 3, '^': 4, '&': 5,
                      '==': 6, '!=': 6, '<': 7, '<=': 7, '>': 7, '>=': 7,
                      '<<': 8, '>>': 8, '+': 9, '-': 9, '+%': 9, '-%': 9, '+|': 9, '-|': 9,
                      '*': 10, '*%': 10, '*|': 10, '/': 10, '%': 10}
        while self.current.text in precedence and precedence[self.current.text] >= minimum:
            op = self.take()
            right = self.expression(precedence[op.text] + 1)
            left = Expr(op, 'binary', [left, right])
        return left
