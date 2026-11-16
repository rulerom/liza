"""Download a locked Homebrew bottle; never update the lock from the network."""
import argparse
import json
from pathlib import Path
import subprocess

from verification.v3.toolchain import sha


def fetch(lock_path, package, directory):
    entry = json.loads(Path(lock_path).read_text())['bottles'][package]
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / entry['filename']
    # The local bottle filename lets Homebrew load the archived formula as well
    # as the binaries, instead of installing the current formula's version.
    subprocess.run(['curl', '--fail', '--location', '--retry', '3',
                    '--header', 'Authorization: Bearer QQ==',
                    entry['url'], '--output', str(destination)], check=True)
    if sha(destination) != entry['sha256']:
        raise ValueError('bottle digest mismatch; refusing installation')
    return destination


def restore(lock_path, package, directory):
    """Replace a candidate only after authenticating its locked archive.

    Used on the disposable proof runner, never to modify the lock. Recent
    Homebrew resolves `reinstall <path>` as a formula/tap name; only `install`
    has the explicit local-bottle loader. A relative path also avoids treating
    an absolute runner path as a fully-qualified tap.
    """
    archive = fetch(lock_path, package, directory)
    subprocess.run(['brew', 'uninstall', '--ignore-dependencies', '--force', package], check=True)
    subprocess.run(['brew', 'install', '--ignore-dependencies', './' + archive.name],
                   cwd=archive.parent, check=True)
    return archive


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default=str(Path(__file__).with_name('toolchain-lock.json')))
    parser.add_argument('--package', required=True, choices=('llvm', 'z3', 'zstd'))
    parser.add_argument('--directory', required=True)
    parser.add_argument('--restore', action='store_true', help='Replace the candidate on an isolated proof runner')
    args = parser.parse_args()
    operation = restore if args.restore else fetch
    print(operation(args.lock, args.package, args.directory))
