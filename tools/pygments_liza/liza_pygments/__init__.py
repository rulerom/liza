"""Presentation-only lexer; the compiler remains authoritative for syntax."""
from pygments.lexer import RegexLexer, words
from pygments.token import Comment, Keyword, Name, Number, Operator, Punctuation, String, Whitespace


class LizaLexer(RegexLexer):
    name = 'Liza'
    aliases = ['liza']
    filenames = ['*.liza']
    mimetypes = ['text/x-liza']

    tokens = {
        'root': [
            (r'\s+', Whitespace),
            (r'//[^\n]*', Comment.Single),
            (r'"', String.Double, 'string'),
            (words(('true', 'false'), suffix=r'\b'), Keyword.Constant),
            (words(('fn', 'return', 'var', 'if', 'else', 'while', 'break',
                    'continue', 'match', 'struct', 'enum', 'import', 'pub',
                    'copy', 'move', 'borrow', 'view', 'pure', 'io', 'alloc', 'copyable',
                    'implicit_copy'), suffix=r'\b'), Keyword),
            (words(('bool', 'u8', 'u16', 'u32', 'u64', 'i8', 'i16', 'i32',
                    'i64', 'Text', 'File', 'View', 'Option', 'Result'), suffix=r'\b'), Keyword.Type),
            (words(('Ok', 'Err', 'Some', 'None'), suffix=r'\b'), Name.Class),
            (r'0x[0-9a-fA-F]+\b', Number.Hex),
            (r'[0-9]+\b', Number.Integer),
            (r'[A-Z][A-Za-z_0-9]*', Name.Class),
            (r'[A-Za-z_][A-Za-z_0-9]*(?=\s*(?:<[^\n;{}()]*>)?\s*\()', Name.Function),
            (words(('memory', 'vec', 'console', 'file'), suffix=r'\b'), Name.Namespace),
            (r'[A-Za-z_][A-Za-z_0-9]*', Name),
            (r'->|=>|==|!=|<<|>>|<=|>=|&&|\|\||[+*\-][%|]|[=+*\-!<>~&|^/%]', Operator),
            (r'\.\.|[\[\]{}(),:;.]', Punctuation),
        ],
        'string': [
            (r'\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})', String.Escape),
            (r'[^"\\\n]+', String.Double),
            (r'"', String.Double, '#pop'),
        ],
    }
