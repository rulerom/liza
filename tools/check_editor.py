"""Validate the editor parser and every Zed query against real Liza sources."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / 'editors/tree-sitter-liza'
CLI = GRAMMAR / 'node_modules/tree-sitter-cli/cli.js'


def check_grammar_pin():
    # Zed builds this revision, not the parser in the current worktree.
    manifest = (ROOT/'editors/zed/extension.toml').read_text()
    section = manifest.split('[grammars.liza]', 1)[1]
    revision = re.search(r'^rev = "([0-9a-f]{40})"$', section, re.M).group(1)
    for relative in ('grammar.js', 'src/parser.c', 'src/grammar.json', 'src/node-types.json'):
        path = 'editors/tree-sitter-liza/' + relative
        pinned = subprocess.run(['git', 'show', revision+':'+path], cwd=ROOT,
                                capture_output=True, check=True).stdout
        if pinned != (GRAMMAR/relative).read_bytes():
            raise AssertionError('Zed grammar pin is stale for '+path+
                                 '; commit the grammar and update extension.toml rev')
    print('Zed pinned grammar matches the tested parser:', revision)


def check():
    check_grammar_pin()
    with tempfile.TemporaryDirectory(prefix='liza-editor-') as temp:
        env = dict(os.environ, XDG_CACHE_HOME=temp)
        def run(*args):
            result = subprocess.run(['node', str(CLI), *map(str,args)], cwd=GRAMMAR,
                                    env=env, capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout
        print(run('test'))
        sources = sorted((ROOT/'examples').rglob('*.liza'))
        sources += sorted((ROOT/'tests/fixtures').glob('*.liza'))
        run('parse', '--quiet', *sources)
        queries = ROOT/'editors/zed/languages/liza'
        for query in sorted(queries.glob('*.scm')):
            run('query', '--quiet', query, *sources)
        # Assert actual semantic categories, not merely query compilation.
        highlighted = run('query', queries/'highlights.scm', ROOT/'examples/hello.liza')
        for category,text in [('keyword','fn'), ('function','main'), ('function','println'),
                              ('type.builtin','u32'), ('constructor','Ok'),
                              ('string','"Hello, Liza!"')]:
            assert re.search(r' - '+re.escape(category)+r',.*text: `'+re.escape(text)+r'`',highlighted), (category,text)
        borrowed = run('query', queries/'highlights.scm', ROOT/'examples/text/string.liza')
        assert re.search(r' - keyword,.*text: `borrow`',borrowed)
        outline = run('query', queries/'outline.scm', ROOT/'examples/tables/connections.liza')
        for name in ['ConnectionId','TableError','edit']:
            assert re.search(r' - name,.*text: `'+name+r'`',outline),name
        # Recovery while editing: one unfinished expression must not hide the
        # next top-level declaration from the outline.
        incomplete=Path(temp)/'incomplete.liza'
        incomplete.write_text('fn unfinished()->u32 { x = }\nfn next()->u32 {return 0}\n')
        recovered=run('query', queries/'outline.scm', incomplete)
        assert 'text: `next`' in recovered
        print(f'{len(sources)} Liza sources parsed; 4 Zed queries, highlights and recovery checked.')


if __name__ == '__main__':
    check()
