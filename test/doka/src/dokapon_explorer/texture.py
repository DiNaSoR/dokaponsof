from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import struct
from typing import Iterable

from PIL import Image

from .cell import CellChunk
from .lz77 import LZ77Info, decompress_lz77


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(slots=True)
class TextureHeader:
    total_size: int
    texture_flags: int
    texture_kind: int
    nested_size: int
    width: int
    height: int


@dataclass(slots=True)
class TexturePart:
    index: int
    offset_x: float
    offset_y: float
    width: float
    height: float
    u0: float
    v0: float
    u1: float
    v1: float

    def pixel_rect(self, atlas_width: int, atlas_height: int) -> tuple[int, int, int, int]:
        return (
            round(self.u0 * atlas_width),
            round(self.v0 * atlas_height),
            round(self.u1 * atlas_width),
            round(self.v1 * atlas_height),
        )


@dataclass(slots=True)
class TexturePartsContainer:
    header: TextureHeader
    storage_kind: str
    lz77: LZ77Info | None
    atlas_bytes: bytes
    parts: list[TexturePart]
    anime_size: int | None


def parse_texture_header(payload: bytes) -> TextureHeader:
    if len(payload) < 0x28 or not payload.startswith(b"Texture"):
        raise ValueError("payload is not a Texture container")
    return TextureHeader(
        total_size=struct.unpack_from("<I", payload, 0x14)[0],
        texture_flags=struct.unpack_from("<I", payload, 0x18)[0],
        texture_kind=struct.unpack_from("<I", payload, 0x1C)[0],
        nested_size=struct.unpack_from("<I", payload, 0x20)[0],
        width=struct.unpack_from("<H", payload, 0x24)[0],
        height=struct.unpack_from("<H", payload, 0x26)[0],
    )


def _parse_parts_from_trailing(trailing: bytes) -> tuple[list[TexturePart], int | None]:
    parts: list[TexturePart] = []
    anime_size: int | None = None

    parts_pos = trailing.find(b"Parts")
    if parts_pos >= 0:
        parts_size = struct.unpack_from("<I", trailing, parts_pos + 20)[0]
        parts_count = struct.unpack_from("<I", trailing, parts_pos + 24)[0]
        parts_base = parts_pos + 28
        if parts_base + (parts_count * 32) > len(trailing):
            raise ValueError("Parts table exceeds Texture trailing data")
        for index in range(parts_count):
            values = struct.unpack_from("<8f", trailing, parts_base + (index * 32))
            parts.append(
                TexturePart(
                    index=index,
                    offset_x=values[0],
                    offset_y=values[1],
                    width=values[2],
                    height=values[3],
                    u0=values[4],
                    v0=values[5],
                    u1=values[6],
                    v1=values[7],
                )
            )
        # parts_size is currently not used, but validating here helps catch bad assumptions.
        expected_min = 28 + (parts_count * 32)
        if parts_size < expected_min:
            raise ValueError(f"invalid Parts size: 0x{parts_size:X} < 0x{expected_min:X}")

    anime_pos = trailing.find(b"Anime")
    if anime_pos >= 0:
        anime_size = struct.unpack_from("<I", trailing, anime_pos + 20)[0]

    return parts, anime_size


def parse_texture_parts_payload(payload: bytes) -> TexturePartsContainer:
    header = parse_texture_header(payload)
    storage = payload[0x28:]

    if storage.startswith(PNG_SIGNATURE):
        storage_kind = "png"
        atlas_bytes = storage[: header.nested_size]
        lz77 = None
    elif storage.startswith(b"LZ77"):
        storage_kind = "indexed_lz77"
        atlas_bytes, lz77 = decompress_lz77(storage)
    else:
        raise ValueError("unsupported Texture storage")

    trailing = payload[header.total_size:]
    parts, anime_size = _parse_parts_from_trailing(trailing)
    return TexturePartsContainer(
        header=header,
        storage_kind=storage_kind,
        lz77=lz77,
        atlas_bytes=atlas_bytes,
        parts=parts,
        anime_size=anime_size,
    )


def parse_texture_parts_chunk(buf: bytes, chunk: CellChunk) -> TexturePartsContainer:
    payload = buf[chunk.payload_offset:chunk.payload_offset + chunk.payload_size]
    return parse_texture_parts_payload(payload)


def parse_palette_chunk(buf: bytes, chunk: CellChunk) -> list[list[tuple[int, int, int, int]]]:
    payload = buf[chunk.payload_offset:chunk.payload_offset + chunk.payload_size]
    if len(payload) < 4:
        raise ValueError("Palette chunk payload is too small")
    palette_count = struct.unpack_from("<I", payload, 0)[0]
    expected_size = 4 + (palette_count * 256 * 4)
    if len(payload) != expected_size:
        raise ValueError(
            f"Palette chunk size mismatch: payload=0x{len(payload):X} expected=0x{expected_size:X}"
        )
    palettes: list[list[tuple[int, int, int, int]]] = []
    off = 4
    for _ in range(palette_count):
        colors: list[tuple[int, int, int, int]] = []
        for _ in range(256):
            r, g, b, a = struct.unpack_from("<BBBB", payload, off)
            colors.append((r, g, b, a))
            off += 4
        palettes.append(colors)
    return palettes


def build_indexed_atlas_image(container: TexturePartsContainer, palette: list[tuple[int, int, int, int]]) -> Image.Image:
    if container.storage_kind != "indexed_lz77":
        raise ValueError("indexed atlas rendering requires indexed_lz77 storage")
    if len(container.atlas_bytes) != container.header.width * container.header.height:
        raise ValueError("atlas byte length does not match texture dimensions")

    rgba = bytearray()
    for index in container.atlas_bytes:
        r, g, b, a = palette[index]
        rgba.extend((r, g, b, a))
    return Image.frombytes("RGBA", (container.header.width, container.header.height), bytes(rgba))


def build_png_image(container: TexturePartsContainer) -> Image.Image:
    if container.storage_kind != "png":
        raise ValueError("png atlas rendering requires png storage")
    return Image.open(BytesIO(container.atlas_bytes)).copy()


def summarize_texture_parts(container: TexturePartsContainer) -> dict[str, object]:
    return {
        "storage_kind": container.storage_kind,
        "width": container.header.width,
        "height": container.header.height,
        "atlas_byte_len": len(container.atlas_bytes),
        "parts_count": len(container.parts),
        "anime_size": container.anime_size,
        "texture_flags": container.header.texture_flags,
        "texture_kind": container.header.texture_kind,
        "first_parts": [
            {
                "index": part.index,
                "offset_x": part.offset_x,
                "offset_y": part.offset_y,
                "width": part.width,
                "height": part.height,
                "u0": part.u0,
                "v0": part.v0,
                "u1": part.u1,
                "v1": part.v1,
            }
            for part in container.parts[:16]
        ],
    }
