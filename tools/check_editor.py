"""Validate the editor parser and every Zed query against real Liza sources."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / 'editors/tree-sitter-liza'
CLI = GRAMMAR / 'node_modules/tree-sitter-cli/cli.js'


def check():
    with tempfile.TemporaryDirectory(prefix='liza-editor-') as temp:
        env = dict(os.environ, XDG_CACHE_HOME=temp)
        def run(*args):
            result = subprocess.run(['node', str(CLI), *map(str,args)], cwd=GRAMMAR,
                                    env=env, capture_output=True, text=True, timeout=120)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout
        print(run('test'))
        sources = sorted((ROOT/'examples').glob('*.liza'))
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
        outline = run('query', queries/'outline.scm', ROOT/'examples/connection_table.liza')
        for name in ['ConnectionId','TableError','table_edit']:
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
