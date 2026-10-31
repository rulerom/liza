"""Guard native GitHub path routing and cancellation policy; no custom CI selector.

Uses independent representative change sets, including transitive dependencies.
YAML BaseLoader preserves the GitHub Actions 'on' key (YAML 1.1 treats it as bool).
Only the positive *, **, ? glob subset used by this repository is supported here.
"""
from copy import deepcopy
from pathlib import Path
import re
import json
import yaml

ROOT = Path(__file__).resolve().parents[1]


def matches(path, pattern):
    assert not any(c in pattern for c in '![]+'), ('unsupported pattern', pattern)
    parts = re.split(r'(\*\*|\*|\?)', pattern)
    expression = ''.join({'**': '.*', '*': '[^/]*', '?': '[^/]'}.get(p, re.escape(p)) for p in parts)
    return re.fullmatch(expression, path) is not None


def selected(workflows, paths, event='pull_request', branch='feature/example'):
    result = set()
    for name, workflow in workflows.items():
        trigger = workflow['on'].get(event)
        if event not in workflow['on']:
            continue
        if event == 'workflow_dispatch':
            result.add(name)
            continue
        if event == 'push' and branch not in trigger['branches']:
            continue
        if any(matches(path, pattern) for path in paths for pattern in trigger['paths']):
            result.add(name)
    return result


# These expectations are independent of the actual YAML filter lists.
COMPILER = {'test', 'verified', 'verified-v3', 'verified-v4', 'verified-pipeline',
            'verified-relay-r1', 'verified-relay-r2b', 'verified-relay-r2c',
            'aggregate-lowering', 'mutable-borrow'}
CASES = [
    (['docs/basics.md'], {'docs'}),
    (['experiments/scoped_channel/channel.c'], {'scoped-channel-probe'}),
    (['experiments/reactor_wakeup/probe.c'], {'reactor-wakeup-probe'}),
    (['verification/scoped_channel/model.py'], {'scoped-channel-model', 'verified-pipeline'}),
    (['liza/runtime/scoped_channel_core.c'], COMPILER | {'scoped-channel-model', 'reactor-wakeup-probe'}),
    (['README.md'], set()),
    (['docs/assets/images/liza-logo.png', 'mkdocs.yml'], {'docs'}),
    (['tools/check_docs.py', 'requirements-docs.txt'], {'docs'}),
    (['editors/zed-liza/extension.toml'], {'editor'}),
    (['tests/fixtures/borrow.liza'], {'test', 'editor'}),
    (['tests/test_proxy_lifecycle.py'], {'test'}),
    (['examples/apps/liza_proxy_ops.liza'], {'test', 'editor', 'docs'}),
    (['examples/apps/proxy/config.liza'], {'test', 'editor', 'docs'}),
    (['examples/apps/liza_proxy.liza'], {'test', 'editor', 'docs', 'verified-relay-r2b', 'verified-relay-r2c'}),
    (['examples/apps/relay/direction.liza'], {'test', 'editor', 'docs', 'verified-relay-r1', 'verified-relay-r2b', 'verified-relay-r2c'}),
    (['liza/backend.py'], COMPILER),
    (['liza/runtime/reactor_common.h'], COMPILER),
    (['liza/stdlib/net.liza'], COMPILER),
    (['verification/relay_r2a/model.py'], {'verified-relay-r2a', 'verified-pipeline'}),
    (['verification/relay_model/model.py'], {'relay-model', 'verified-pipeline'}),
    (['verification/relay_r1/semantic.py'], {'verified-relay-r1', 'verified-relay-r2b', 'verified-relay-r2c', 'verified-pipeline'}),
    (['verification/relay_r2b/semantic.py'], {'verified-relay-r2b', 'verified-relay-r2c', 'verified-pipeline'}),
    (['verification/relay_r2c/check.py'], {'verified-relay-r2c', 'verified-pipeline'}),
    (['verification/v1/memory.py'], {'verified', 'verified-v3', 'verified-pipeline'}),
    (['verification/v2/check.py'], {'verified', 'verified-v3', 'verified-pipeline'}),
    (['verification/v3/toolchain-lock.json'], {'verified-v3', 'verified-pipeline'}),
    (['verification/v4/model.py'], {'verified-v4', 'verified-pipeline'}),
    (['verification/pipeline/runner.py'], {'verified-pipeline'}),
    (['benchmarks/json/corpus.py'], {'json-baseline', 'aggregate-lowering', 'mutable-borrow', 'test'}),
    (['benchmarks/aggregate/run.py'], {'aggregate-lowering', 'mutable-borrow'}),
    (['benchmarks/mutable/emit.py'], {'mutable-borrow', 'test'}),
    (['examples/text/json_mut.liza'], {'test', 'docs', 'editor', 'aggregate-lowering', 'mutable-borrow'}),
    (['tools/check_view_cost.py'], {'test'}),
    (['tools/check_ci.py'], {'ci-policy'}),
    (['docs/basics.md', 'liza/borrowing.py'], COMPILER | {'docs'}),
]


def validate(workflows):
    for name, workflow in workflows.items():
        events = workflow['on']
        assert set(events) == {'push', 'pull_request', 'workflow_dispatch'}, name
        assert events['push']['branches'] == ['main'], name
        assert events['push']['paths'] == events['pull_request']['paths'], name
        assert events['pull_request']['paths'], name
        concurrency = workflow['concurrency']
        assert 'github.workflow' in concurrency['group'], name
        assert 'github.event_name' in concurrency['group'], name
        assert 'github.event.pull_request.number || github.ref' in concurrency['group'], name
        assert concurrency['cancel-in-progress'] == "${{ github.event_name == 'pull_request' }}", name
        own_path = f'.github/workflows/{name}.yml'
        assert selected(workflows, [own_path]) == {name, 'ci-policy'}, own_path
    for paths, expected in CASES:
        actual = selected(workflows, paths)
        assert actual == expected, (paths, sorted(actual), sorted(expected))
        assert selected(workflows, paths, 'push', 'main') == expected, paths
        assert not selected(workflows, paths, 'push'), paths
    assert selected(workflows, ['docs/basics.md'], 'workflow_dispatch') == set(workflows)
    # Frozen baselines are dependencies too, even without a Python import.
    for verifier, manifest in [('verified', 'verification/v1/v0-baseline.json'),
                               ('verified', 'verification/v2/baseline.json'),
                               ('verified-v3', 'verification/v3/baseline.json')]:
        for path in json.loads((ROOT / manifest).read_text()):
            assert verifier in selected(workflows, [path]), (verifier, path)
    # This checks union semantics, not GitHub's server-side diff limits.
    # Broad changes cannot accidentally select only the first matching file.
    assert selected(workflows, ['docs/basics.md'] * 350 + ['liza/ir.py']) == COMPILER | {'docs'}


def change_paths(workflows, name, path, remove=False):
    for event in ('push', 'pull_request'):
        patterns = workflows[name]['on'][event]['paths']
        if remove:
            patterns.remove(path)
        else:
            patterns.append(path)


def main():
    workflows = {p.stem: yaml.load(p.read_text(), Loader=yaml.BaseLoader)
                 for p in sorted((ROOT / '.github/workflows').glob('*.yml'))}
    validate(workflows)
    # Broken routing must be caught, including an understated transitive dependency.
    for mutate in (
        lambda w: w['test']['on']['push'].update(branches=['main', 'feature/example']),
        lambda w: change_paths(w, 'verified', 'docs/**'),
        lambda w: change_paths(w, 'verified-relay-r2c', 'verification/relay_r1/**', remove=True),
        lambda w: w['test']['concurrency'].update({'cancel-in-progress': 'false'}),
    ):
        broken = deepcopy(workflows)
        mutate(broken)
        try:
            validate(broken)
        except AssertionError:
            pass
        else:
            raise AssertionError('CI routing mutation escaped detection')
    print(f'{len(workflows)} workflows: {len(CASES)} change sets, manual dispatch, '
          'branch/cancellation policy and 4 negative controls passed')


if __name__ == '__main__':
    main()
