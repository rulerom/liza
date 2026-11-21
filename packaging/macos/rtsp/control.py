#!/usr/bin/env python3
"""Install/manage the macOS RTSP LaunchDaemon. Never reads secrets into argv/logs."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import platform
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import time

try:
    import fcntl
    import pwd
except ImportError:  # Allow cross-platform test discovery; management stays macOS-only.
    fcntl = pwd = None

BASE = Path('/Library/Application Support/Liza/RTSP')
PLISTS = Path('/Library/LaunchDaemons')
NAME = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z')
RELEASE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,95}\Z')


def trusted_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o022:
        raise ValueError('management directory must be owned by the installer and not writable by others')


def private_directory(path, uid, gid):
    if path.is_symlink():
        raise ValueError('refusing a symlink directory')
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != uid or info.st_mode & 0o077:
        # Ownership changes apply only to a newly empty, operator-owned directory.
        if info.st_uid != os.geteuid() or any(path.iterdir()):
            raise ValueError('directory ownership/permissions mismatch')
        os.chown(path, uid, gid)
        path.chmod(0o700)


def atomic(path, data, mode=0o600, owner=None):
    temporary = path.with_name('.' + path.name + '.new')
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, mode)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
            if owner:
                os.fchown(stream.fileno(), *owner)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_config(data):
    try:
        def unique(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError()
                result[key] = value
            return result
        value = json.loads(data, object_pairs_hook=unique)
        assert len(data) <= 4096 and isinstance(value, dict) and type(value.get('run_ms')) is int and value['run_ms'] == 0
        for key, limit in (('camera_url', 1024), ('vg_peer', 64), ('login', 128), ('password', 512), ('conference', 128)):
            item = value[key]
            assert isinstance(item, str) and 0 < len(item.encode('utf8')) <= limit and '\0' not in item
        for key in ('camera_ip', 'vg_ip'):
            ip = ipaddress.IPv4Address(value[key])
            assert not ip.is_unspecified and not ip.is_multicast
        assert type(value['client_version']) is int and 0 < value['client_version'] < 2**32
        for key, default in (('camera_port', 554), ('vg_port', 443)):
            assert type(value.get(key, default)) is int and 0 < value.get(key, default) <= 65535
        assert type(value.get('rtp_pace_ms', 0)) is int and 0 <= value.get('rtp_pace_ms', 0) <= 5
        assert type(value.get('vg_resume_quiet_ms', 0)) is int and 0 <= value.get('vg_resume_quiet_ms', 0) <= 30000
        if 'ca_file' in value:
            assert isinstance(value['ca_file'], str) and Path(value['ca_file']).is_absolute()
    except (ValueError, KeyError, TypeError, AssertionError, UnicodeError):
        raise ValueError('invalid service configuration: require bounded JSON, connection fields and run_ms=0') from None


def manifest(bundle):
    path = bundle / 'manifest.json'
    if path.is_symlink() or path.stat().st_size > 1024 * 1024:
        raise ValueError('invalid manifest')
    data = json.loads(path.read_text())
    if data.get('schema') != 1 or not RELEASE.fullmatch(data.get('release', '')) or data.get('dirty'):
        raise ValueError('require a clean, versioned release')
    if data.get('architecture') != platform.machine():
        raise ValueError('release architecture does not match this Mac')
    files = data.get('files', {})
    required = {'bin/liza-rtsp', 'bin/liza-rtsp-service', 'lib/libssl.3.dylib', 'lib/libcrypto.3.dylib',
                'licenses/Liza.txt', 'licenses/OpenSSL.txt', 'rtspctl.py'}
    if not required <= files.keys():
        raise ValueError('incomplete release')
    actual = set()
    for item in bundle.rglob('*'):
        if item.is_symlink() or not (item.is_dir() or item.is_file()):
            raise ValueError('release contains links or special files')
        if item.is_file() and item != path:
            actual.add(str(item.relative_to(bundle)))
    if actual != set(files):
        raise ValueError('release file set mismatch')
    for name, digest in files.items():
        if Path(name).is_absolute() or '..' in Path(name).parts or not re.fullmatch('[a-f0-9]{64}', digest):
            raise ValueError('invalid manifest file')
        if hashlib.sha256((bundle / name).read_bytes()).hexdigest() != digest:
            raise ValueError('release checksum mismatch')
    return data


class Service:
    def __init__(self, instance, staging=None):
        if not NAME.fullmatch(instance):
            raise ValueError('invalid instance name')
        self.staging = staging
        self.base = (staging / 'LizaRTSP' if staging else BASE)
        self.plists = (staging / 'LaunchDaemons' if staging else PLISTS)
        self.root = self.base / instance
        self.label = 'ru.liza.rtsp.' + instance
        self.plist = self.plists / (self.label + '.plist')

    def command(self, *args, missing_ok=False):
        if self.staging:
            return
        result = subprocess.run(['/bin/launchctl', *args], capture_output=True, text=True)
        if result.returncode:
            if missing_ok:
                probe = subprocess.run(['/bin/launchctl', 'print', 'system/' + self.label],
                                       capture_output=True, text=True, env=dict(os.environ, LC_ALL='C'))
                if probe.returncode and 'Could not find service' in probe.stderr:
                    return
            raise ValueError('launchctl failed; inspect launchctl print system/' + self.label)

    def stop(self):
        # bootout waits for launchd to terminate the job. Independently hold the
        # application's lock before changing releases or clearing attention.
        self.command('bootout', 'system/' + self.label, missing_ok=True)
        lockpath = self.root / 'state/service.lock'
        if lockpath.exists():
            fd = os.open(lockpath, os.O_RDWR | os.O_NOFOLLOW)
            try:
                limit = time.monotonic() + 15
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= limit:
                            raise ValueError('service is still running; release was not changed')
                        time.sleep(.1)
            finally:
                os.close(fd)

    def start(self):
        self.command('bootstrap', 'system', str(self.plist))

    def select(self, release):
        if not RELEASE.fullmatch(release) or not (self.root / 'releases' / release).is_dir():
            raise ValueError('release not installed')
        target = self.root / 'current'
        if target.is_symlink():
            previous = self.root / '.previous.new'
            previous.symlink_to(os.readlink(target))
            os.replace(previous, self.root / 'previous')
        temporary = self.root / '.current.new'
        temporary.symlink_to('releases/' + release)
        os.replace(temporary, target)
        settings = json.loads((self.root / 'installation.json').read_text())
        executable = self.root / 'current/bin'
        plist = {
            'Label': self.label,
            'ProgramArguments': [str(executable / 'liza-rtsp-service'), str(executable / 'liza-rtsp'),
                                 str(self.root / 'config/config.json'), str(self.root / 'state'), release],
            'UserName': settings['user'], 'GroupName': settings['group'],
            'RunAtLoad': True, 'KeepAlive': {'SuccessfulExit': False}, 'ThrottleInterval': 30,
            'ExitTimeOut': 12, 'Umask': 0o077, 'WorkingDirectory': str(self.root / 'state'),
            'AbandonProcessGroup': False,
            'StandardOutPath': '/dev/null', 'StandardErrorPath': '/dev/null',
        }
        atomic(self.plist, plistlib.dumps(plist), 0o644)

    def install(self, bundle, user=None, config=None):
        data = manifest(bundle)
        if not self.staging:
            for path in (bundle / 'bin').iterdir():
                subprocess.run(['/usr/bin/codesign', '--verify', '--strict', str(path)], check=True, capture_output=True)
        if self.base.exists() or self.base.is_symlink():
            trusted_directory(self.base)
        if self.plists.exists() or self.plists.is_symlink():
            trusted_directory(self.plists)
        new = not self.root.exists()
        if self.root.exists() or self.root.is_symlink():
            trusted_directory(self.root)
            if (self.root / 'releases').exists():
                trusted_directory(self.root / 'releases')
        secret = None
        if new:
            if not user or not config:
                raise ValueError('first installation requires --user and --config')
            account = pwd.getpwnam(user)
            if not self.staging and account.pw_uid == 0:
                raise ValueError('service user must be unprivileged')
            import grp
            group = grp.getgrgid(account.pw_gid).gr_name
            fd = os.open(config, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, 'rb') as stream:
                info = os.fstat(stream.fileno())
                if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_nlink != 1:
                    raise ValueError('source configuration must be a private regular file (0600)')
                secret = stream.read(4097)
            validate_config(secret)
            self.base.mkdir(parents=True, exist_ok=True, mode=0o755)
            self.plists.mkdir(parents=True, exist_ok=True, mode=0o755)
            private_directory(self.root, os.geteuid(), os.getegid())
            # Parent is root-owned; service user can traverse but cannot replace releases.
            self.root.chmod(0o755)
            for name in ('config', 'state'):
                private_directory(self.root / name, account.pw_uid, account.pw_gid)
            (self.root / 'releases').mkdir(mode=0o755)
            atomic(self.root / 'installation.json', json.dumps({'user': user, 'group': group}).encode(), 0o644)
            atomic(self.root / 'config/config.json', secret, owner=(account.pw_uid, account.pw_gid))
        elif user or config:
            raise ValueError('updates preserve configuration/user; edit the protected file explicitly')
        if self.root.is_symlink() or self.base.is_symlink():
            raise ValueError('unsafe installation directory')
        release = data['release']
        releases = self.root / 'releases'
        releases.mkdir(mode=0o755, exist_ok=True)
        target = releases / release
        if target.exists():
            if manifest(target) != data:
                raise ValueError('release identity collision')
        else:
            if len(list(releases.iterdir())) >= 2:
                raise ValueError('two releases retained; use prune before installing another')
            temporary = releases / ('.' + release + '.new')
            shutil.copytree(bundle, temporary)
            manifest(temporary)
            for item in temporary.rglob('*'):
                item.chmod(0o755 if item.is_dir() or item.parent.name == 'bin' else 0o644)
            temporary.chmod(0o755)
            os.rename(temporary, target)
        self.stop()
        self.select(release)
        (self.root / 'state/attention').unlink(missing_ok=True)
        self.start()
        return {'release': release, 'instance': self.label}

    def status(self):
        path = self.root / 'state/status.json'
        attention = (self.root / 'state/attention').exists()
        if not path.exists():
            return {'state': 'Attention required' if attention else 'Unknown',
                    'reason': 'operator_restart_required' if attention else 'no_status_file'}
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_size > 4096:
            os.close(fd)
            raise ValueError('invalid status file')
        with os.fdopen(fd) as stream:
            value = json.load(stream)
        if attention:
            value['state'] = 'Attention required'
            if value.get('reason') in ('starting', 'child_crashed'):
                value['reason'] = 'operator_restart_required'
        elif value.get('child_pid') and (time.time() - value['updated_epoch_s'] > 10 or
                                      value['updated_epoch_s'] > time.time() + 1):
            value['state'] = 'Unknown'
            value['reason'] = 'stale_status_check_launchctl'
        return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--instance', default='camera')
    parser.add_argument('--staging', type=Path, help='test install tree; never invokes launchctl')
    commands = parser.add_subparsers(dest='action', required=True)
    install = commands.add_parser('install')
    install.add_argument('bundle', type=Path)
    install.add_argument('--user')
    install.add_argument('--config', type=Path)
    for action in ('status', 'stop', 'start', 'restart', 'rollback', 'prune', 'uninstall'):
        commands.add_parser(action)
    args = parser.parse_args()
    if not args.staging and (sys.platform != 'darwin' or (args.action != 'status' and os.geteuid() != 0)):
        parser.error('management requires sudo on macOS; --staging is only for tests')
    service = Service(args.instance, args.staging.resolve() if args.staging else None)
    try:
        # Serialize administrator operations independently of the child's lock.
        # The daemon never reads or holds this file.
        if args.action != 'status':
            service.base.mkdir(parents=True, exist_ok=True, mode=0o755)
            trusted_directory(service.base)
            management = os.open(service.base / ('.' + args.instance + '.manage.lock'),
                                 os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
            fcntl.flock(management, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if args.action == 'install':
            result = service.install(args.bundle.resolve(), args.user, args.config)
        elif args.action == 'status':
            result = service.status()
        elif args.action == 'stop':
            service.stop(); result = {'state': 'Stopped'}
        elif args.action in ('start', 'restart'):
            service.stop()
            (service.root / 'state/attention').unlink(missing_ok=True)
            service.start(); result = {'state': 'Starting'}
        elif args.action == 'rollback':
            previous = service.root / 'previous'
            if not previous.is_symlink():
                raise ValueError('no previous release')
            release = Path(os.readlink(previous)).name
            manifest(service.root / 'releases' / release)
            service.stop(); service.select(release)
            (service.root / 'state/attention').unlink(missing_ok=True)
            service.start(); result = {'release': release}
        elif args.action == 'prune':
            # Explicitly removes only the inactive rollback artifact to bound disk.
            current = Path(os.readlink(service.root / 'current')).name
            for release in (service.root / 'releases').iterdir():
                if release.name != current:
                    if release.is_symlink() or not RELEASE.fullmatch(release.name):
                        raise ValueError('unsafe release directory')
                    shutil.rmtree(release)
            (service.root / 'previous').unlink(missing_ok=True)
            result = {'retained': current, 'rollback': False}
        else:
            service.stop(); service.plist.unlink(missing_ok=True)
            for name in ('current', 'previous'):
                (service.root / name).unlink(missing_ok=True)
            releases = service.root / 'releases'
            if releases.is_symlink():
                raise ValueError('unsafe releases directory')
            shutil.rmtree(releases)
            result = {'uninstalled': True, 'preserved': ['config', 'state']}
        print(json.dumps(result, indent=2))
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    except (OSError, KeyError, TypeError, subprocess.CalledProcessError):
        parser.exit(1, 'Operation failed. Check instance paths, release integrity, permissions and launchctl. Configuration values were not logged.\n')


if __name__ == '__main__':
    main()
