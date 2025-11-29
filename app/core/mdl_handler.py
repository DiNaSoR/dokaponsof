"""MDL LZ77 variant decompressor used for enemy model files.

The format is a simple token stream that differs from the flag-byte style
used for textures/SPRANM. Each byte is either:
- literal byte if bit 7 is 0
- back-reference if bit 7 is 1
    length  = ((token & 0x7C) >> 2) + 3   # 5 bits, range 3-34
    offset  = ((token & 0x03) << 8) | next_byte
    offset += 1                           # 10-bit window, range 1-1024
Decompression stops once the declared output size is reached; any remaining
input bytes are preserved as `trailing_data`.
"""

import logging
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Optional, Tuple, Union


@dataclass
class LZ77Header:
    """Header for MDL LZ77 files."""

    magic: bytes
    decompressed_size: int
    flag1: int
    flag2: int


class LZ77Decompressor:
    """Decompresses the MDL-specific LZ77 token stream."""

    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("LZ77Decompressor")
        if debug and not logging.getLogger().handlers:
            logging.basicConfig(level=logging.DEBUG)

        self.trailing_data: bytes = b""
        self.bytes_consumed: int = 0

    def read_header(self, source: Union[BinaryIO, bytes]) -> Optional[LZ77Header]:
        """Read the 16-byte MDL header from a file handle or raw bytes."""
        try:
            if isinstance(source, (bytes, bytearray, memoryview)):
                header_bytes = bytes(source[:16])
            else:
                header_bytes = source.read(16)

            if len(header_bytes) < 16:
                self.logger.error("File too small for LZ77 header")
                return None

            magic, size, flag1, flag2 = struct.unpack("<4sIII", header_bytes)
            return LZ77Header(magic=magic, decompressed_size=size, flag1=flag1, flag2=flag2)
        except Exception as exc:  # pragma: no cover - defensive
            self.logger.error("Failed to read LZ77 header: %s", exc)
            return None

    def _decompress_stream(self, data: bytes, expected_size: int) -> Tuple[bytes, int]:
        """Core token-based decompression. Returns (output, bytes_consumed)."""
        output = bytearray()
        pos = 0
        data_len = len(data)

        while pos < data_len and len(output) < expected_size:
            token = data[pos]
            pos += 1

            if token & 0x80:
                if pos >= data_len:
                    self.logger.warning("Unexpected end of stream while reading offset")
                    break

                length = ((token & 0x7C) >> 2) + 3
                offset = ((token & 0x03) << 8) | data[pos]
                pos += 1
                offset += 1

                for _ in range(length):
                    if len(output) >= expected_size:
                        break
                    if offset <= len(output):
                        output.append(output[-offset])
                    else:
                        # Window underrun: mirror observed decompressor behaviour with zero fill
                        output.append(0)
            else:
                output.append(token)

        return bytes(output), pos

    def decompress_data(self, data: bytes) -> Optional[bytes]:
        """Decompress MDL data provided as raw bytes."""
        if len(data) < 16:
            self.logger.error("Data too small to contain LZ77 header")
            return None

        header = self.read_header(data)
        if not header or header.magic != b"LZ77":
            self.logger.error("Invalid LZ77 header")
            return None

        compressed = data[16:]
        output, consumed = self._decompress_stream(compressed, header.decompressed_size)
        self.bytes_consumed = consumed
        self.trailing_data = compressed[consumed:]

        if len(output) != header.decompressed_size:
            self.logger.warning(
                "Decompressed size mismatch: got %d, expected %d",
                len(output),
                header.decompressed_size,
            )

        return output

    def decompress_file(self, filename: str) -> bytes:
        """Decompress an MDL file from disk."""
        path = Path(filename)
        raw = path.read_bytes()

        result = self.decompress_data(raw)
        if result is None:
            raise ValueError(f"Failed to decompress MDL file: {filename}")

        return result


def show_file_info(filename: str) -> None:
    """Quick header dump for debugging from the CLI."""
    raw = Path(filename).read_bytes()
    header = LZ77Decompressor().read_header(raw)
    if not header:
        print(f"{filename}: invalid LZ77 header")
        return

    print(f"{filename}")
    print(f"  Magic: {header.magic}")
    print(f"  Declared decompressed size: {header.decompressed_size:,} bytes")
    print(f"  Flag1: 0x{header.flag1:08x}")
    print(f"  Flag2: 0x{header.flag2:08x}")
