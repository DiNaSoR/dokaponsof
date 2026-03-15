"""Unified LZ77 decompression module for Dokapon SoF Tools.

Provides a single dispatch function ``decompress`` that delegates to the
appropriate implementation based on the *variant* parameter:

* ``"flag_byte"``   -- flag-byte style used for textures / SPRANM
                       (delegates to :func:`dokapon_extract.decompress_lz77`)
* ``"token_stream"`` -- MDL-specific token stream
                        (delegates to :class:`mdl_handler.LZ77Decompressor`)
* ``"cell"``         -- cell-based LZ77 used by the explorer tool
* ``"auto"``         -- attempts to detect the correct variant automatically
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Cell-variant data class
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CellLZ77Info:
    """Metadata returned by the cell LZ77 decompressor."""
    raw_size: int
    token_count: int
    data_offset: int
    flags_end: int
    data_end: int
    out_len: int


# ---------------------------------------------------------------------------
# Cell-variant implementation (ported from test/doka/src/dokapon_explorer/lz77.py)
# ---------------------------------------------------------------------------

def _decompress_cell(buf: bytes) -> Tuple[bytes, Optional[CellLZ77Info]]:
    """Decompress the cell-style LZ77 container if present.

    Returns ``(data, info)`` where *info* is ``None`` when the input does not
    start with the ``LZ77`` magic.
    """
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
            # Back-reference
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
            # Literal byte
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

    info = CellLZ77Info(
        raw_size=raw_size,
        token_count=token_count,
        data_offset=data_offset,
        flags_end=flags_ptr,
        data_end=data_ptr,
        out_len=len(out),
    )
    return bytes(out), info


# ---------------------------------------------------------------------------
# Internal helpers for flag_byte and token_stream variants
# ---------------------------------------------------------------------------

def _decompress_flag_byte(data: bytes) -> Optional[bytes]:
    """Delegate to :func:`dokapon_extract.decompress_lz77`."""
    from app.core.dokapon_extract import decompress_lz77 as _flag_byte_impl
    return _flag_byte_impl(data)


def _decompress_token_stream(data: bytes) -> Optional[bytes]:
    """Delegate to :class:`mdl_handler.LZ77Decompressor`."""
    from app.core.mdl_handler import LZ77Decompressor
    decompressor = LZ77Decompressor()
    return decompressor.decompress_data(data)


# ---------------------------------------------------------------------------
# Auto-detection heuristic
# ---------------------------------------------------------------------------

def _detect_variant(data: bytes) -> str:
    """Try to guess the LZ77 variant from the content.

    Heuristic rules:
    1. Must start with ``LZ77`` magic -- otherwise no decompression is needed.
    2. If the word at offset 0x0C (data_offset) points beyond the flags area
       and is consistent with a cell-style layout, use ``"cell"``.
    3. If the declared decompressed size at offset 0x04 looks reasonable and
       the first payload byte has bit 7 patterns typical of the token stream,
       use ``"token_stream"``.
    4. Fall back to ``"flag_byte"``.
    """
    if len(data) < 16 or data[:4] != b"LZ77":
        return "flag_byte"

    # Read header fields
    _raw_size = struct.unpack_from("<I", data, 0x04)[0]
    _token_count = struct.unpack_from("<I", data, 0x08)[0]
    data_offset = struct.unpack_from("<I", data, 0x0C)[0]

    # Cell variant: data_offset typically points past the flags area and is
    # large relative to 0x10, with token_count being a reasonable count.
    if (data_offset > 0x10 and data_offset < len(data)
            and _token_count > 0 and _token_count < 0x100000):
        # Heuristic: in the cell variant the data_offset field separates
        # the flag region from the data region.  In the flag_byte variant
        # the same field is the "uncompressed offset" which can equal the
        # file length or be 0.
        # Additional check: in flag_byte, offset 0x08 is decompressed_size
        # and offset 0x0C is the uncompressed_offset.  In cell, offset 0x08
        # is token_count (usually much smaller than decompressed size).
        if _token_count < _raw_size:
            return "cell"

    # Token-stream (MDL) variant: the header at offset 0x04 is
    # decompressed_size, and offsets 0x08/0x0C are flag1/flag2.
    # A simple check: if the decompressed size at 0x04 is non-zero and
    # the value at 0x08 does not look like a realistic token count
    # (i.e. it is very large or zero) assume token_stream.
    if _raw_size > 0 and (_token_count == 0 or _token_count >= _raw_size):
        return "token_stream"

    return "flag_byte"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def decompress(data: bytes, variant: str = "auto") -> Union[bytes, Tuple[bytes, Optional[CellLZ77Info]]]:
    """Decompress LZ77-compressed data using the specified variant.

    Parameters
    ----------
    data : bytes
        Raw (possibly compressed) data.
    variant : str
        One of ``"flag_byte"``, ``"token_stream"``, ``"cell"``, or ``"auto"``.

    Returns
    -------
    For ``"flag_byte"`` and ``"token_stream"``:
        ``bytes | None`` -- decompressed data, or ``None`` on failure.
    For ``"cell"``:
        ``(bytes, CellLZ77Info | None)`` -- decompressed data and metadata.
    For ``"auto"``:
        Return type matches the detected variant.

    Raises
    ------
    ValueError
        If *variant* is not recognised.
    """
    if variant == "auto":
        variant = _detect_variant(data)

    if variant == "flag_byte":
        return _decompress_flag_byte(data)
    elif variant == "token_stream":
        return _decompress_token_stream(data)
    elif variant == "cell":
        return _decompress_cell(data)
    else:
        raise ValueError(f"Unknown LZ77 variant: {variant!r}")
