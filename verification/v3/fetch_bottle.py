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


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default=str(Path(__file__).with_name('toolchain-lock.json')))
    parser.add_argument('--package', required=True, choices=('llvm', 'z3', 'zstd'))
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    print(fetch(args.lock, args.package, args.directory))
