import json
from pathlib import Path
import plistlib
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from arcforever import patcher
from test_patcher import sample


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.app = self.root / 'Arc.app'
        (self.app / 'Contents/Resources').mkdir(parents=True)
        self.originals = {patcher.MAIN: sample(), patcher.SHIM: sample(), patcher.SEAL: b'original-resource-seal'}
        for name, data in self.originals.items():
            path = self.app / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(0o755 if name != patcher.SEAL else 0o644)
        self.info = {'CFBundleIdentifier': 'company.thebrowser.Browser', 'CFBundleExecutable': 'Arc',
                     'CFBundleShortVersionString': 'fixture', 'CFBundleVersion': '1'}
        (self.app / 'Contents/Info.plist').write_bytes(plistlib.dumps(self.info))
        self.auth = self.root / 'home/Library/Application Support/Arc/StorableAuthState.json'
        self.auth.parent.mkdir(parents=True)
        self.auth.write_text(json.dumps({'session': {'user': {'id': 'local-fixture'}}}))
        fingerprint = patcher.digest(self.app / patcher.MAIN)
        for name, replacement in (
                ('SUPPORTED', {('fixture', '1'): fingerprint}), ('SHIMS', {('fixture', '1'): fingerprint}),
                ('sip_disabled', lambda: True), ('ensure_closed', lambda app: None),
                ('finder_attributes', lambda *args, **kwargs: []),
                ('compile_guard', lambda destination, preserve: destination.write_bytes(b'fixture-guard')),
                ('run', lambda *args, **kwargs: subprocess.CompletedProcess(args, 0, b'', b''))):
            mock = patch.object(patcher, name, replacement)
            mock.start()
            self.addCleanup(mock.stop)
        home = patch.object(Path, 'home', return_value=self.root / 'home')
        home.start()
        self.addCleanup(home.stop)

    def apply(self):
        return patcher.apply(self.app, self.root / 'backups')

    def assert_original(self):
        for name, data in self.originals.items():
            self.assertEqual((self.app / name).read_bytes(), data)
        self.assertFalse((self.app / patcher.GUARD).exists())
        self.assertFalse((self.app / patcher.MARKER).exists())

    def test_apply_and_restore_exact_original_files(self):
        result = self.apply()
        self.assertTrue(result['vendor_main_signature_preserved'])
        self.assertTrue(result['guard_intact'])
        self.assertTrue(result['carrier_intact'])
        self.assertEqual((self.app / 'Contents/Info.plist').read_bytes(), plistlib.dumps(self.info))
        with self.assertRaisesRegex(ValueError, 'already patched'):
            self.apply()
        patcher.restore(self.app)
        self.assert_original()
        self.assertEqual(json.loads((Path(result['backup']) / 'manifest.json').read_text())['state'], 'restored')

    def test_signing_failure_rolls_back_before_returning(self):
        with patch.object(patcher, 'run', side_effect=subprocess.CalledProcessError(1, ['codesign'])):
            with self.assertRaises(subprocess.CalledProcessError):
                self.apply()
        self.assert_original()
        manifest = next((self.root / 'backups').glob('*/manifest.json'))
        self.assertEqual(json.loads(manifest.read_text())['state'], 'rolled_back')

    def test_corrupt_backup_is_rejected_before_any_restore_write(self):
        result = self.apply()
        backup = Path(result['backup'])
        manifest = json.loads((backup / 'manifest.json').read_text())
        (backup / manifest['files'][-1]['backup_file']).write_bytes(b'corrupt')
        before = (self.app / patcher.SHIM).read_bytes()
        with self.assertRaisesRegex(ValueError, 'checksum mismatch'):
            patcher.restore(self.app)
        self.assertEqual((self.app / patcher.SHIM).read_bytes(), before)
        self.assertTrue((self.app / patcher.MARKER).exists())

    def test_updated_main_is_not_overwritten_by_framework_restore(self):
        self.apply()
        (self.app / patcher.MAIN).write_bytes(b'new-version')
        with self.assertRaisesRegex(ValueError, 'main executable changed'):
            patcher.restore(self.app)
        self.assertEqual((self.app / patcher.MAIN).read_bytes(), b'new-version')

    def test_unsupported_main_is_rejected_before_creating_backup(self):
        (self.app / patcher.MAIN).write_bytes(b'unsupported')
        self.assertFalse(patcher.status(self.app)['supported'])
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            self.apply()
        self.assertFalse((self.root / 'backups').exists())

    def test_missing_local_identity_is_rejected_before_any_mutation(self):
        self.auth.unlink()
        with self.assertRaisesRegex(ValueError, 'cached sign-in state'):
            self.apply()
        self.assert_original()
        self.assertFalse((self.root / 'backups').exists())

    def test_restore_refuses_path_traversal_inventory(self):
        result = self.apply()
        backup = Path(result['backup'])
        path = backup / 'manifest.json'
        manifest = json.loads(path.read_text())
        manifest['files'][0]['path'] = '../outside'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, 'file inventory'):
            patcher.restore(self.app)

    def test_framework_strategy_refuses_sip_enabled(self):
        with patch.object(patcher, 'sip_disabled', return_value=False):
            with self.assertRaisesRegex(ValueError, 'SIP enabled'):
                patcher.apply(self.app, self.root / 'backups', strategy='framework')
        self.assert_original()
