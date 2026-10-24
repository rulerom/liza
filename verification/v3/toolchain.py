"""Digest guard for the audited macOS ARM64 proof-worker binaries.

This is not a hermetic OS/SDK lock. Homebrew may fetch newer packages; the
proof job must then stop until an explicit toolchain review updates this lock.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def verify(lock_path, prefixes):
    lock = json.loads(Path(lock_path).read_text())
    result = {'status': 'verified', 'lock_sha256': sha(lock_path), 'files': []}
    if platform.system() != lock['system'] or platform.machine() != lock['machine']:
        return {**result, 'status': 'unknown', 'reason': 'unsupported proof-worker platform'}
    if any(Path(prefixes[name]).resolve() != Path(prefix).resolve()
           for name, prefix in lock['prefixes'].items()):
        return {**result, 'status': 'unknown', 'reason': 'unexpected runtime library prefix'}
    for package, files in lock['files'].items():
        for relative, expected in files.items():
            path = Path(prefixes[package])/relative
            try:
                actual = sha(path)
            except OSError:
                actual = None
            result['files'].append({'package': package, 'file': relative,
                                    'expected': expected, 'actual': actual})
            if actual != expected:
                result['status'] = 'unknown'
    if result['status'] != 'verified':
        result['reason'] = 'toolchain digest mismatch; no proof under the pinned environment'
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--lock', default=str(Path(__file__).with_name('toolchain-lock.json')))
    parser.add_argument('--llvm-prefix', required=True)
    parser.add_argument('--z3-prefix', required=True)
    parser.add_argument('--zstd-prefix', required=True)
    args = parser.parse_args()
    result = verify(args.lock, {'llvm': args.llvm_prefix, 'z3': args.z3_prefix, 'zstd': args.zstd_prefix})
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['status'] == 'verified' else 1)
