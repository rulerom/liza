#!/usr/bin/env python3
"""Build a native macOS release; Python is a build/install tool, never a daemon dependency."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def output(*args):
    return subprocess.check_output(args, text=True, cwd=ROOT).strip()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dependencies(path):
    return [line.strip().split(' (')[0] for line in output('otool', '-L', str(path)).splitlines()[1:]]


def build(destination, allow_dirty=False):
    if sys.platform != 'darwin':
        raise ValueError('release builds require macOS')
    dirty = bool(output('git', 'status', '--porcelain'))
    if dirty and not allow_dirty:
        raise ValueError('commit source changes before a release build (--allow-dirty is for local tests)')
    destination.mkdir(parents=True, exist_ok=False)
    binary = destination / 'bin'
    binary.mkdir()
    (destination / 'lib').mkdir()
    licenses = destination / 'licenses'
    licenses.mkdir()
    shutil.copyfile(ROOT / 'LICENSE', licenses / 'Liza.txt')
    shutil.copyfile(Path(__file__).with_name('control.py'), destination / 'rtspctl.py')
    prefix = Path(os.environ.get('LIZA_OPENSSL_PREFIX') or output('brew', '--prefix', 'openssl@3')).resolve()
    # Private copies keep an existing release usable across Homebrew updates.
    # Certificate validation still uses the existing system-trust implementation.
    env = dict(os.environ, LIZA_OPENSSL_PREFIX=str(prefix))
    run(sys.executable, '-m', 'liza', 'build', '--project-root', 'examples',
        'examples/apps/liza_rtsp.liza', '-O', '2', '-o', str(binary / 'liza-rtsp'), cwd=ROOT, env=env)
    run('clang', '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
        str(Path(__file__).with_name('service.c')), '-o', str(binary / 'liza-rtsp-service'))
    library_names = ('libssl.3.dylib', 'libcrypto.3.dylib')
    for name in library_names:
        shutil.copyfile(prefix / 'lib' / name, destination / 'lib' / name)
    license_file = prefix / 'share/doc/openssl/LICENSE.txt'
    if not license_file.is_file():
        candidates = list(prefix.glob('LICENSE*'))
        if not candidates:
            raise ValueError('OpenSSL license file missing')
        license_file = candidates[0]
    shutil.copyfile(license_file, licenses / 'OpenSSL.txt')
    machos = list(binary.iterdir()) + list((destination / 'lib').iterdir())
    for path in machos:
        for dependency in dependencies(path):
            name = Path(dependency).name
            if name in library_names and dependency != str(path):
                replacement = ('@executable_path/../lib/' if path.parent == binary else '@loader_path/') + name
                run('install_name_tool', '-change', dependency, replacement, str(path))
        if path.parent.name == 'lib':
            run('install_name_tool', '-id', '@loader_path/' + path.name, str(path))
        for dependency in dependencies(path):
            if not dependency.startswith(('/usr/lib/', '/System/Library/', '@loader_path/', '@executable_path/')):
                raise ValueError('unbundled dependency: ' + dependency)
        path.chmod(0o755)
        run('codesign', '--force', '--sign', '-', str(path))
        run('codesign', '--verify', '--strict', str(path))
    commit = output('git', 'rev-parse', 'HEAD')
    manifest = {
        'schema': 1, 'source_commit': commit, 'dirty': dirty, 'optimization': 'O2',
        'architecture': platform.machine(), 'macos': platform.mac_ver()[0],
        'python': sys.version, 'clang': output('clang', '--version'),
        'sdk': output('xcrun', '--show-sdk-version'),
        'openssl': output(str(prefix / 'bin/openssl'), 'version'),
        'signing': 'ad-hoc; no Developer ID or notarization',
        'files': {str(p.relative_to(destination)): sha(p) for p in sorted(destination.rglob('*')) if p.is_file()},
    }
    identity = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()[:16]
    manifest['release'] = commit[:12] + '-' + identity
    (destination / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'release': manifest['release'], 'bundle': str(destination)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    parser.add_argument('--allow-dirty', action='store_true')
    args = parser.parse_args()
    try:
        build(args.destination.resolve(), args.allow_dirty)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')
