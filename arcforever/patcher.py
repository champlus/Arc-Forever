"""Reversible edits to an existing Arc installation. Never creates a second app."""
from datetime import datetime, timezone
import base64
import ctypes
import hashlib
import json
import os
from pathlib import Path
import plistlib
import shutil
import stat
import subprocess
import tempfile
import uuid

from . import __version__
from .macho import inject_load_command

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BACKUPS = Path.home() / 'Library/Application Support/Arc Forever/Backups'
SUPPORTED = {
    ('1.169.0', '88758'): '24e2aca39abd6645528b5f5e1241555a1ab5c925bb6e6c1e9ecaabdd2b83ed51',
    ('1.170.0', '89123'): '25af5f4eaaae5aca25021f2737e90cc4d41fdf195c4a5c4012ea31a1bba4b86a',
}
SHIMS = {
    ('1.169.0', '88758'): None,
    ('1.170.0', '89123'): 'cf66b808b27a50fd08bdc46f818cb0dbd65e7a967d35aad9dae16e50b7a80d17',
}
MARKER = 'Contents/Resources/ArcForever.json'
GUARD = 'Contents/Frameworks/ArcForeverGuard.dylib'
MAIN = 'Contents/MacOS/Arc'
SHIM = 'Contents/Frameworks/libswiftCompatibilitySpan.dylib'
SEAL = 'Contents/_CodeSignature/CodeResources'


def run(command, **kwargs):
    return subprocess.run(command, check=True, capture_output=True, **kwargs)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def app_info(app):
    app = Path(app).expanduser().resolve()
    info = plistlib.loads((app / 'Contents/Info.plist').read_bytes())
    if info.get('CFBundleIdentifier') != 'company.thebrowser.Browser' or info.get('CFBundleExecutable') != 'Arc':
        raise ValueError('Expected the original Arc application identity and executable')
    return app, info


def sip_disabled():
    result = run(['/usr/bin/csrutil', 'status']).stdout.decode(errors='replace').lower()
    return 'status: disabled' in result


def ensure_closed(app):
    output = run(['/bin/ps', '-ww', '-axo', 'pid=,comm=']).stdout.decode(errors='replace')
    executable = str(app / MAIN)
    for line in output.splitlines():
        fields = line.strip().split(None, 1)
        if len(fields) == 2 and fields[1] == executable:
            raise ValueError('Quit Arc before applying or restoring the patch; no running browser is force-closed')


def atomic_write(path, contents, mode=0o644):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix='.arc-forever-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(name, mode)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_json(path, value):
    atomic_write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode(), 0o600)


def finder_attributes(app, remove=False):
    """Save only Finder icon attributes that codesign cannot accept; no quarantine changes."""
    libc = ctypes.CDLL(None, use_errno=True)
    result = []
    for root, dirs, files in os.walk(app, followlinks=False):
        paths = [Path(root)] + [Path(root) / name for name in files]
        for path in paths:
            if path.is_symlink():
                continue
            for name in ('com.apple.FinderInfo', 'com.apple.ResourceFork'):
                encoded = os.fsencode(path)
                size = libc.getxattr(encoded, name.encode(), None, 0, 0, 0)
                if size < 0:
                    continue
                buffer = ctypes.create_string_buffer(size)
                got = libc.getxattr(encoded, name.encode(), buffer, size, 0, 0)
                if got < 0:
                    raise OSError(ctypes.get_errno(), 'Cannot read Finder attributes')
                result.append({'path': str(path.relative_to(app)), 'name': name,
                               'data': base64.b64encode(buffer.raw[:got]).decode()})
                if remove and libc.removexattr(encoded, name.encode(), 0) != 0:
                    raise OSError(ctypes.get_errno(), 'Cannot temporarily clear Finder attributes')
    return result


def restore_finder_attributes(app, attributes):
    libc = ctypes.CDLL(None, use_errno=True)
    for entry in attributes:
        relative = Path(entry['path'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Invalid Finder attribute backup path')
        contents = base64.b64decode(entry['data'])
        if libc.setxattr(os.fsencode(app / relative), entry['name'].encode(), contents, len(contents), 0, 0) != 0:
            raise OSError(ctypes.get_errno(), 'Cannot restore Finder icon attributes')


def status(app):
    app, info = app_info(app)
    marker = app / MARKER
    result = {'app': str(app), 'version': info['CFBundleShortVersionString'],
              'build': info['CFBundleVersion'], 'patched': marker.is_file(),
              'supported': (info['CFBundleShortVersionString'], info['CFBundleVersion']) in SUPPORTED}
    if not marker.is_file():
        key = (info['CFBundleShortVersionString'], info['CFBundleVersion'])
        result['supported'] = SUPPORTED.get(key) == digest(app / MAIN)
    if marker.is_file():
        receipt = json.loads(marker.read_text())
        backup = Path(receipt['backup'])
        manifest = json.loads((backup / 'manifest.json').read_text())
        result.update({'strategy': receipt['strategy'], 'backup': str(backup),
                       'state': manifest['state'], 'guard_intact': (app / GUARD).is_file()
                       and digest(app / GUARD) == manifest.get('patched_guard_sha256'),
                       'carrier_intact': digest(app / manifest['carrier']) == manifest.get('patched_carrier_sha256'),
                       'vendor_main_signature_preserved': receipt['strategy'] == 'framework'
                       and digest(app / MAIN) == manifest['original_main_sha256']})
    return result


def compile_guard(destination, preserve_cloudkit):
    run(['xcrun', 'clang', '-dynamiclib', '-fobjc-arc', '-fblocks', '-arch', 'arm64', '-arch', 'x86_64',
         '-mmacosx-version-min=12.0', '-framework', 'Foundation',
         '-DAF_PRESERVE_CLOUDKIT=' + ('1' if preserve_cloudkit else '0'),
         str(ROOT / 'native/ArcForeverGuard.m'), '-install_name', '@rpath/ArcForeverGuard.dylib',
         '-o', str(destination)])
    run(['/usr/bin/codesign', '--force', '--sign', '-', str(destination)])


def apply(app, backup_dir=DEFAULT_BACKUPS, strategy='auto'):
    app, info = app_info(app)
    ensure_closed(app)
    if strategy not in ('auto', 'framework', 'main'):
        raise ValueError('Unknown patch strategy')
    if (app / MARKER).exists() or (app / GUARD).exists():
        raise ValueError('Arc is already patched or contains an unrecognized guard; inspect status or restore first')
    key = (info['CFBundleShortVersionString'], info['CFBundleVersion'])
    if SUPPORTED.get(key) != digest(app / MAIN):
        raise ValueError('Unsupported Arc build or modified executable; refusing to guess patch locations')
    disabled = sip_disabled()
    if strategy == 'auto':
        strategy = 'framework' if disabled and SHIMS.get(key) else 'main'
    if strategy == 'framework' and not disabled:
        raise ValueError('Framework-only injection is not supported with SIP enabled; use --strategy main. Never disable SIP for this tool.')
    carrier = SHIM if strategy == 'framework' else MAIN
    expected_shim = SHIMS.get(key)
    if strategy == 'framework' and (not expected_shim or digest(app / SHIM) != expected_shim):
        raise ValueError('This framework build has not been verified; use --strategy main')
    auth = Path.home() / 'Library/Application Support/Arc/StorableAuthState.json'
    try:
        auth_contents = auth.read_bytes()
        auth_state = json.loads(auth_contents)
        user = auth_state['session']['user']
        if not isinstance(user['id'], str) or not user['id']:
            raise ValueError('Missing local identity')
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('This release requires an existing Arc profile with cached sign-in state. No application files were changed.') from None
    source = (app / carrier).read_bytes()
    load_path = '@loader_path/ArcForeverGuard.dylib' if strategy == 'framework' else '@executable_path/../Frameworks/ArcForeverGuard.dylib'
    patched, changes = inject_load_command(source, load_path)
    backup_dir = Path(backup_dir).expanduser().resolve()
    backup_dir.mkdir(parents=True, mode=0o700, exist_ok=True)
    backup_dir.chmod(0o700)
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + uuid.uuid4().hex[:8]
    backup = backup_dir / stamp
    backup.mkdir(mode=0o700)
    paths = sorted(set((MAIN, carrier, SEAL)))
    manifest = {'format': 1, 'tool_version': __version__, 'app': str(app), 'version': key[0], 'build': key[1],
                'strategy': strategy, 'carrier': carrier, 'original_main_sha256': digest(app / MAIN),
                'created_at': datetime.now(timezone.utc).isoformat(), 'state': 'prepared', 'files': [], 'changes': changes}
    for index, relative in enumerate(paths):
        source_path = app / relative
        name = f'original-{index}'
        shutil.copyfile(source_path, backup / name)
        manifest['files'].append({'path': relative, 'backup_file': name, 'sha256': digest(source_path),
                                  'mode': stat.S_IMODE(source_path.stat().st_mode)})
    (backup / 'auth-state.json').write_bytes(auth_contents)
    (backup / 'auth-state.json').chmod(0o600)
    manifest['finder_attributes'] = finder_attributes(app)
    write_json(backup / 'manifest.json', manifest)
    try:
        with tempfile.TemporaryDirectory(prefix='arc-forever-') as temporary:
            guard = Path(temporary) / 'ArcForeverGuard.dylib'
            compile_guard(guard, strategy == 'framework')
            atomic_write(app / GUARD, guard.read_bytes(), 0o755)
        receipt = {'format': 1, 'tool_version': __version__, 'strategy': strategy, 'backup': str(backup),
                   'auth_backup': str(backup / 'auth-state.json')}
        write_json(app / MARKER, receipt)
        atomic_write(app / carrier, patched, stat.S_IMODE((app / carrier).stat().st_mode))
        if strategy == 'framework':
            run(['/usr/bin/codesign', '--force', '--sign', '-', str(app / carrier)])
            run(['/usr/bin/codesign', '--verify', '--strict', str(app / carrier)])
            if digest(app / MAIN) != manifest['original_main_sha256']:
                raise ValueError('The signed main executable changed unexpectedly')
        else:
            finder_attributes(app, remove=True)
            entitlements = backup / 'local-entitlements.plist'
            entitlements.write_bytes(plistlib.dumps({'com.apple.security.cs.disable-library-validation': True,
                'com.apple.security.device.audio-input': True, 'com.apple.security.device.camera': True,
                'com.apple.security.personal-information.location': True}))
            # Do not deep-sign: original ArcCore and Chromium helper identities stay intact.
            run(['/usr/bin/codesign', '--force', '--sign', '-', '--options', 'runtime',
                 '--entitlements', str(entitlements), str(app)])
            run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(app)])
            restore_finder_attributes(app, manifest['finder_attributes'])
        manifest.update({'state': 'applied', 'patched_carrier_sha256': digest(app / carrier),
                         'patched_guard_sha256': digest(app / GUARD)})
        write_json(backup / 'manifest.json', manifest)
    except BaseException:
        _restore_files(app, backup, manifest)
        manifest['state'] = 'rolled_back'
        write_json(backup / 'manifest.json', manifest)
        raise
    result = status(app)
    result.update({'system_security_changed': False, 'browser_data_modified': False,
                   'original_interface_preserved': True})
    return result


def _restore_files(app, backup, manifest):
    carrier = manifest.get('carrier')
    expected = sorted(set((MAIN, carrier, SEAL))) if carrier in (MAIN, SHIM) else []
    entries = manifest.get('files', [])
    if not expected or sorted(entry.get('path', '') for entry in entries) != expected:
        raise ValueError('Invalid backup file inventory')
    for entry in manifest['files']:
        name = entry['backup_file']
        if not isinstance(name, str) or Path(name).name != name or name in ('.', '..'):
            raise ValueError('Invalid backup file name')
        if not isinstance(entry.get('mode'), int) or entry['mode'] & ~0o777:
            raise ValueError('Invalid backup file permissions')
        source = backup / entry['backup_file']
        if digest(source) != entry['sha256']:
            raise ValueError('Backup checksum mismatch: ' + entry['backup_file'])
    for entry in manifest['files']:
        atomic_write(app / entry['path'], (backup / entry['backup_file']).read_bytes(), entry['mode'])
    for relative in (GUARD, MARKER):
        path = app / relative
        if path.exists():
            path.unlink()
    restore_finder_attributes(app, manifest.get('finder_attributes', []))


def restore(app, backup=None):
    app, info = app_info(app)
    ensure_closed(app)
    marker = app / MARKER
    if backup is None:
        if not marker.is_file():
            raise ValueError('No patch receipt found; provide --backup for an interrupted operation')
        backup = Path(json.loads(marker.read_text())['backup'])
    backup = Path(backup).expanduser().resolve()
    manifest = json.loads((backup / 'manifest.json').read_text())
    if manifest['app'] != str(app):
        raise ValueError('This backup belongs to a different application path')
    key = (manifest['version'], manifest['build'])
    if SUPPORTED.get(key) != manifest['original_main_sha256']:
        raise ValueError('The backup is not a recognized original Arc build')
    if key != (info['CFBundleShortVersionString'], info['CFBundleVersion']):
        raise ValueError('Arc was updated after patching; refusing to overwrite this installation')
    if manifest['carrier'] == SHIM and digest(app / MAIN) != manifest['original_main_sha256']:
        raise ValueError('The main executable changed after patching; refusing to overwrite it')
    if manifest['state'] == 'applied' and digest(app / manifest['carrier']) != manifest['patched_carrier_sha256']:
        raise ValueError('Arc changed after patching; refusing to overwrite a newer or different installation')
    _restore_files(app, backup, manifest)
    manifest['state'] = 'restored'
    write_json(backup / 'manifest.json', manifest)
    return {'app': str(app), 'restored': True, 'original_main_sha256': digest(app / MAIN),
            'backup': str(backup), 'browser_data_modified': False}
