"""Verify the installed lexer and rendered example after mkdocs build --strict."""
from html.parser import HTMLParser
from pathlib import Path
from pygments.lexers import get_lexer_by_name
from pygments.token import Comment, Error, Keyword, Name, Number, Operator, String

ROOT = Path(__file__).resolve().parents[1]


class CodeBlocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag == 'code':
            self.current = {'text': '', 'classes': set()}
        elif tag == 'span' and self.current is not None:
            self.current['classes'].update(dict(attrs).get('class', '').split())

    def handle_data(self, data):
        if self.current is not None:
            self.current['text'] += data

    def handle_endtag(self, tag):
        if tag == 'code' and self.current is not None:
            self.blocks.append(self.current)
            self.current = None


def check():
    lexer = get_lexer_by_name('liza')
    assert lexer.name == 'Liza', 'Liza Pygments entry point not installed'
    sources = sorted((ROOT/'examples').rglob('*.liza'))
    for source in sources:
        errors = [(t, text) for t, text in lexer.get_tokens(source.read_text(encoding='utf-8')) if t in Error]
        assert not errors, (source, errors)
    sample = 'fn f(x:u32)->u32:alloc { // move 42\n s="fn \\n"\n n=0x80\n return x +% 1 }'
    tokens = list(lexer.get_tokens(sample))
    for expected in [(Keyword, 'fn'), (Name.Function, 'f'), (Keyword.Type, 'u32'),
                     (Keyword, 'alloc'), (Comment.Single, '// move 42'),
                     (String.Double, 'fn '), (String.Escape, '\\n'),
                     (Number.Hex, '0x80'), (Operator, '+%'), (Number.Integer, '1')]:
        assert expected in tokens, expected
    for operator in ('+%', '-%', '*%', '+|', '-|', '*|', '<<', '>>', '=>', '->'):
        assert (Operator, operator) in list(lexer.get_tokens(operator)), operator

    source = (ROOT/'examples/bounded_vec.liza').read_text(encoding='utf-8').strip()
    html = (ROOT/'site/bounded-vec-walkthrough.html').read_text(encoding='utf-8')
    parser = CodeBlocks(); parser.feed(html)
    blocks = [b for b in parser.blocks if b['text'].strip() == source]
    assert len(blocks) == 1, 'Walkthrough must contain the exact executable example once'
    assert {'k', 'kt', 'nf', 'mi', 'c1', 'hll'} <= blocks[0]['classes'], blocks[0]['classes']
    assert 'id="__codelineno-0-28"' in html, 'Expected 28 linked source lines'
    assert '--8&lt;--' not in html, 'Unexpanded source include'
    # Existing pages must gain highlighting too, not only the new walkthrough.
    core = CodeBlocks(); core.feed((ROOT/'site/core.html').read_text(encoding='utf-8'))
    assert any({'k', 'kt', 'mi'} <= b['classes'] for b in core.blocks)
    for page,example in [('utf8','utf8_file'),('utf8-stream','utf8_stream_file')]:
        utf8 = CodeBlocks(); utf8.feed((ROOT/'site'/(page+'.html')).read_text(encoding='utf-8'))
        utf8_source = (ROOT/'examples'/(example+'.liza')).read_text(encoding='utf-8').strip()
        assert sum(b['text'].strip()==utf8_source for b in utf8.blocks)==1, 'UTF-8 example must match its source'
    print(f'{len(sources)} examples lexed; token categories, rendered source, numbered lines and existing pages verified.')


if __name__ == '__main__':
    check()
