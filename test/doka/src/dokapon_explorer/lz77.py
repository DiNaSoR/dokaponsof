from __future__ import annotations

from dataclasses import dataclass
import struct


@dataclass(slots=True)
class LZ77Info:
    raw_size: int
    token_count: int
    data_offset: int
    flags_end: int
    data_end: int
    out_len: int


def decompress_lz77(buf: bytes) -> tuple[bytes, LZ77Info | None]:
    """Decompress the game's simple LZ77 container if present."""
    if len(buf) < 0x10 or buf[:4] != b"LZ77":
        return buf, None

    raw_size, token_count, data_offset = struct.unpack_from("<III", buf, 0x04)
    flags_ptr = 0x10
    data_ptr = data_offset
    out = bytearray()
    bit_count = 0
    flags = 0

    for _ in range(token_count):
        if bit_count == 0:
            if flags_ptr >= len(buf):
                raise ValueError("LZ77 flags pointer exceeded file size")
            flags = buf[flags_ptr]
            flags_ptr += 1
            bit_count = 8

        if flags & 0x80:
            if data_ptr + 2 > len(buf):
                raise ValueError("LZ77 backref exceeded file size")
            dist = buf[data_ptr]
            length = buf[data_ptr + 1] + 3
            data_ptr += 2
            if dist == 0:
                raise ValueError("LZ77 invalid distance 0")
            start = len(out) - dist
            if start < 0:
                raise ValueError("LZ77 backref before output start")
            for _copy in range(length):
                out.append(out[start])
                start += 1
        else:
            if data_ptr >= len(buf):
                raise ValueError("LZ77 literal exceeded file size")
            out.append(buf[data_ptr])
            data_ptr += 1

        flags = (flags << 1) & 0xFF
        bit_count -= 1

        if len(out) > raw_size + 0x1000:
            raise ValueError("LZ77 output grew beyond guard range")

    if len(out) > raw_size:
        out = out[:raw_size]

    info = LZ77Info(
        raw_size=raw_size,
        token_count=token_count,
        data_offset=data_offset,
        flags_end=flags_ptr,
        data_end=data_ptr,
        out_len=len(out),
    )
    return bytes(out), info
