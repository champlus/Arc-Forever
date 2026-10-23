"""Bounded Mach-O load-command editing; executable code never moves."""
import struct

GUARD_LOAD_PATH = '@executable_path/../Frameworks/ArcForeverGuard.dylib'


def slices(raw):
    if raw[:4] == b'\xca\xfe\xba\xbe':
        if len(raw) < 8:
            raise ValueError('Truncated universal Mach-O header')
        count = struct.unpack_from('>I', raw, 4)[0]
        if count > 32 or 8 + count * 20 > len(raw):
            raise ValueError('Invalid universal Mach-O architecture table')
        previous = 8 + count * 20
        for i in range(count):
            _, _, offset, size, _ = struct.unpack_from('>IIIII', raw, 8 + i * 20)
            if size < 32 or offset < previous or offset + size > len(raw):
                raise ValueError('Invalid or overlapping Mach-O slice')
            previous = offset + size
            yield offset, size
    elif raw[:4] == b'\xcf\xfa\xed\xfe' and len(raw) >= 32:
        yield 0, len(raw)
    else:
        raise ValueError('Unsupported Mach-O format')


def inject_load_command(raw, load_path=GUARD_LOAD_PATH):
    raw = bytearray(raw)
    name = load_path.encode() + b'\0'
    size = (24 + len(name) + 7) & ~7
    command = struct.pack('<IIIIII', 0xc, size, 24, 0, 0x10000, 0x10000) + name
    command += bytes(size - len(command))
    changes = []
    for base, length in slices(raw):
        if raw[base:base+4] != b'\xcf\xfa\xed\xfe':
            raise ValueError('Expected a little-endian Mach-O 64 slice')
        ncmds, sizeofcmds = struct.unpack_from('<II', raw, base + 16)
        end = 32 + sizeofcmds
        if end > length or ncmds > sizeofcmds // 8:
            raise ValueError('Invalid Mach-O command table')
        first_data, cursor = length, base + 32
        for _ in range(ncmds):
            cmd, cmdsize = struct.unpack_from('<II', raw, cursor)
            if cmdsize < 8 or cursor + cmdsize > base + end:
                raise ValueError('Invalid Mach-O load command bounds')
            if cmd in (0xc, 0x80000018, 0x8000001f):
                if cmdsize < 24:
                    raise ValueError('Invalid dylib command')
                offset = struct.unpack_from('<I', raw, cursor + 8)[0]
                if offset < 24 or offset >= cmdsize:
                    raise ValueError('Invalid dylib name offset')
                existing = bytes(raw[cursor+offset:cursor+cmdsize]).split(b'\0')[0]
                if b'ArcForeverGuard.dylib' in existing:
                    raise ValueError('The binary already contains an Arc Forever guard')
            if cmd == 0x19:
                if cmdsize < 72:
                    raise ValueError('Invalid Mach-O segment')
                count = struct.unpack_from('<I', raw, cursor + 64)[0]
                if 72 + count * 80 > cmdsize:
                    raise ValueError('Invalid Mach-O section table')
                for j in range(count):
                    offset = struct.unpack_from('<I', raw, cursor + 72 + j * 80 + 48)[0]
                    if offset:
                        first_data = min(first_data, offset)
            cursor += cmdsize
        if cursor != base + end:
            raise ValueError('Mach-O command size mismatch')
        if end + size > first_data or end + size > length or any(raw[base+end:base+end+size]):
            raise ValueError('Insufficient unused Mach-O header padding; refusing to shift code')
        raw[base+end:base+end+size] = command
        struct.pack_into('<II', raw, base+16, ncmds+1, sizeofcmds+size)
        changes.append({'slice_offset': base, 'command_offset': end, 'command_size': size})
    return bytes(raw), changes
