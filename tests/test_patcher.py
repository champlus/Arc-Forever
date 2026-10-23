import struct
import unittest
from arcforever.macho import inject_load_command, GUARD_LOAD_PATH


def sample():
    raw = bytearray(0x1100)
    struct.pack_into('<IIIIIIII', raw, 0, 0xfeedfacf, 0x100000c, 0, 2, 1, 152, 0, 0)
    struct.pack_into('<II16sQQQQIIII', raw, 32, 0x19, 152, b'__TEXT', 0x100000000,
                     0x2000, 0, len(raw), 5, 5, 1, 0)
    struct.pack_into('<16s16sQQIIIIIIII', raw, 104, b'__text', b'__TEXT', 0x100001000,
                     0x100, 0x1000, 2, 0, 0, 0, 0, 0, 0)
    raw[0x1000:0x1100] = bytes(range(256))
    return bytes(raw)


class PatcherTests(unittest.TestCase):
    def test_preserves_code_offsets_and_bytes(self):
        original = sample()
        result, changes = inject_load_command(original)
        self.assertEqual(len(result), len(original))
        self.assertEqual(result[0x1000:], original[0x1000:])
        self.assertIn(GUARD_LOAD_PATH.encode(), result)
        self.assertEqual(len(changes), 1)

    def test_refuses_already_modified_image(self):
        result, _ = inject_load_command(sample())
        with self.assertRaisesRegex(ValueError, 'already contains'):
            inject_load_command(result)

    def test_refuses_nonzero_padding(self):
        raw = bytearray(sample())
        raw[184] = 1
        with self.assertRaisesRegex(ValueError, 'header padding'):
            inject_load_command(raw)

    def test_refuses_unknown_file(self):
        with self.assertRaisesRegex(ValueError, 'format'):
            inject_load_command(b'not an executable')
