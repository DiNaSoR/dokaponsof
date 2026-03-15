from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from .cell import CellMap, CellRecord, decode_record, parse_cell_chunks, parse_cell_header, parse_cell_map, parse_cell_records
from .lz77 import LZ77Info, decompress_lz77
from .scanner import analyze_debug, scan_map_groups
from .texture import (
    TexturePartsContainer,
    build_indexed_atlas_image,
    build_png_image,
    parse_palette_chunk,
    parse_texture_parts_chunk,
)


@dataclass(slots=True)
class LoadedCellDocument:
    source_path: Path
    raw_data: bytes
    decompressed_data: bytes
    lz77: LZ77Info | None
    header: object
    records: list[CellRecord]
    decoded_records: list[object]
    chunks: list[object]
    cell_map: CellMap | None
    texture: TexturePartsContainer | None
    palettes: list[list[tuple[int, int, int, int]]]


def load_cell_document(path: Path) -> LoadedCellDocument:
    raw = path.read_bytes()
    data, lz77 = decompress_lz77(raw)
    header = parse_cell_header(data)
    records = parse_cell_records(data, header)
    chunks = parse_cell_chunks(data, header)
    cell_map = parse_cell_map(data, header, chunks)
    texture_chunk = next((chunk for chunk in chunks if chunk.name == "TextureParts"), None)
    texture = parse_texture_parts_chunk(data, texture_chunk) if texture_chunk is not None else None
    palette_chunk = next((chunk for chunk in chunks if chunk.name == "Palette"), None)
    palettes = parse_palette_chunk(data, palette_chunk) if palette_chunk is not None else []
    return LoadedCellDocument(
        source_path=path,
        raw_data=raw,
        decompressed_data=data,
        lz77=lz77,
        header=header,
        records=records,
        decoded_records=[decode_record(record) for record in records],
        chunks=chunks,
        cell_map=cell_map,
        texture=texture,
        palettes=palettes,
    )


def build_atlas_for_document(document: LoadedCellDocument, palette_index: int = 0) -> Image.Image | None:
    if document.texture is None:
        return None
    if document.texture.storage_kind == "png":
        return build_png_image(document.texture)
    if not document.palettes:
        return None
    palette_index = max(0, min(palette_index, len(document.palettes) - 1))
    return build_indexed_atlas_image(document.texture, document.palettes[palette_index])


def render_map_image(document: LoadedCellDocument, palette_index: int = 0, max_edge: int | None = None) -> Image.Image | None:
    if document.cell_map is None or document.texture is None:
        return None

    atlas = build_atlas_for_document(document, palette_index)
    if atlas is None:
        return None
    if not document.texture.parts:
        return None

    tile_width = max(1, round(document.texture.parts[0].width))
    tile_height = max(1, round(document.texture.parts[0].height))
    image = Image.new("RGBA", (document.cell_map.width * tile_width, document.cell_map.height * tile_height), (0, 0, 0, 0))

    crop_cache: dict[int, Image.Image] = {}
    for index, value in enumerate(document.cell_map.values):
        record_index = value & 0xFFFF
        if record_index >= len(document.decoded_records):
            continue
        record = document.decoded_records[record_index]
        part_index = record.value_a_low16
        if part_index >= len(document.texture.parts):
            continue
        if part_index not in crop_cache:
            part = document.texture.parts[part_index]
            x0, y0, x1, y1 = part.pixel_rect(document.texture.header.width, document.texture.header.height)
            crop_cache[part_index] = atlas.crop((x0, y0, x1, y1))
        x = (index % document.cell_map.width) * tile_width
        y = (index // document.cell_map.width) * tile_height
        image.paste(crop_cache[part_index], (x, y))

    if max_edge is None:
        return image
    if image.width <= max_edge and image.height <= max_edge:
        return image
    scale = min(max_edge / image.width, max_edge / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.NEAREST)
    return resized


def list_cell_files(game_dir: Path) -> list[Path]:
    field_map = game_dir / "GameData" / "app" / "Field" / "Map"
    field_chizu = game_dir / "GameData" / "app" / "Field" / "Chizu"
    results: list[Path] = []
    if field_map.exists():
        results.extend(sorted(path for path in field_map.rglob("*.mpd") if path.is_file()))
    if field_chizu.exists():
        results.extend(sorted(path for path in field_chizu.rglob("*.mpd") if path.is_file()))
    return results


def scan_workspace(game_dir: Path) -> tuple[object, list[object]]:
    return analyze_debug(game_dir), scan_map_groups(game_dir)
