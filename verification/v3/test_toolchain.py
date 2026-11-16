import json
from pathlib import Path
import platform
import tempfile
import unittest
from unittest.mock import patch
from verification.v3.fetch_bottle import fetch, restore
from verification.v3.toolchain import sha, verify


class ToolchainTests(unittest.TestCase):
    def fixture(self, root):
        package = root/'llvm'
        package.mkdir()
        binary = package/'clang'
        binary.write_bytes(b'fixed toolchain fixture')
        lock = root/'lock.json'
        lock.write_text(json.dumps({'system': platform.system(), 'machine': platform.machine(),
                                   'prefixes': {'llvm': str(package)},
                                   'files': {'llvm': {'clang': sha(binary)}}}))
        return lock, {'llvm': str(package)}, binary

    def test_exact_bytes(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock, prefixes, _ = self.fixture(Path(tmp))
            report = verify(lock, prefixes)
            self.assertEqual(report['status'], 'verified')
            self.assertEqual(report['lock_sha256'], sha(lock))

    def test_modified_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock, prefixes, binary = self.fixture(Path(tmp))
            binary.write_bytes(b'different binary with the same version label')
            self.assertEqual(verify(lock, prefixes)['status'], 'unknown')

    def test_missing_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock, prefixes, binary = self.fixture(Path(tmp))
            binary.unlink()
            self.assertEqual(verify(lock, prefixes)['status'], 'unknown')

    def test_wrong_runtime_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock, _, _ = self.fixture(Path(tmp))
            self.assertEqual(verify(lock, {'llvm': tmp})['status'], 'unknown')

    def test_wrong_platform(self):
        with tempfile.TemporaryDirectory() as tmp:
            lock, prefixes, _ = self.fixture(Path(tmp))
            data = json.loads(lock.read_text()); data['machine'] = 'unsupported'
            lock.write_text(json.dumps(data))
            self.assertEqual(verify(lock, prefixes)['status'], 'unknown')


class BottleTests(unittest.TestCase):
    def test_restore_refuses_changed_bytes_before_touching_installed_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root/'z3--1.arm64_tahoe.bottle.tar.gz'
            archive.write_bytes(b'pinned archive')
            lock = root/'lock.json'
            lock.write_text(json.dumps({'bottles': {'z3': {
                'filename': archive.name, 'url': 'https://example.invalid/pinned',
                'sha256': sha(archive)}}}))
            with patch('verification.v3.fetch_bottle.subprocess.run') as command:
                restore(lock, 'z3', root)
                calls = command.call_args_list
                self.assertEqual(calls[0].args[0][0], 'curl')
                self.assertEqual(calls[1].args[0], ['brew', 'uninstall', '--ignore-dependencies', '--force', 'z3'])
                self.assertEqual(calls[2].args[0], ['brew', 'install', '--ignore-dependencies', './'+archive.name])
                self.assertEqual(calls[2].kwargs['cwd'], root.resolve())
                self.assertTrue(all(call.kwargs['check'] for call in calls))
                command.reset_mock()
                archive.write_bytes(b'changed archive')
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    restore(lock, 'z3', root)
                self.assertEqual([call.args[0][0] for call in command.call_args_list], ['curl'])

    def test_only_matching_archive_is_returned_for_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            archive = root/'z3--1.arm64_tahoe.bottle.tar.gz'
            archive.write_bytes(b'pinned archive')
            lock = root/'lock.json'
            lock.write_text(json.dumps({'bottles': {'z3': {
                'filename': archive.name, 'url': 'https://example.invalid/pinned',
                'sha256': sha(archive)}}}))
            with patch('verification.v3.fetch_bottle.subprocess.run') as download:
                self.assertEqual(fetch(lock, 'z3', root), archive.resolve())
                self.assertTrue(download.call_args.kwargs['check'])
                archive.write_bytes(b'changed archive')
                with self.assertRaisesRegex(ValueError, 'digest mismatch'):
                    fetch(lock, 'z3', root)

    def test_download_failure_is_not_a_cached_success(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lock = root/'lock.json'
            lock.write_text(json.dumps({'bottles': {'z3': {
                'filename': 'z3.bottle.tar.gz', 'url': 'https://example.invalid/pinned',
                'sha256': 'unused'}}}))
            with patch('verification.v3.fetch_bottle.subprocess.run',
                       side_effect=subprocess.CalledProcessError(22, 'curl')):
                with self.assertRaises(subprocess.CalledProcessError):
                    fetch(lock, 'z3', root)
