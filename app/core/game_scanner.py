from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any

from .cell_parser import (
    parse_cell_chunks,
    parse_cell_header,
    parse_cell_map,
    parse_cell_records,
    summarize_map,
    summarize_record_decoding,
    summarize_records,
)
from .lz77 import CellLZ77Info as LZ77Info, decompress as _decompress_lz77
from .texture_parser import parse_palette_chunk, parse_texture_parts_chunk, summarize_texture_parts


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PNG_END = b"IEND\xaeB`\x82"
MAP_ID_RE = re.compile(r"^F_(\d{2})_")


@dataclass(slots=True)
class FileInsight:
    path: str
    relative_path: str
    extension: str
    size: int
    signature: str
    png_count: int = 0
    lz77: dict[str, Any] | None = None
    decompressed_signature: str | None = None
    cell_fields: dict[str, Any] | None = None
    cell_chunks: list[str] | None = None
    cell_records: dict[str, Any] | None = None
    cell_map: dict[str, Any] | None = None
    cell_texture: dict[str, Any] | None = None
    parse_error: str | None = None


@dataclass(slots=True)
class MapGroup:
    map_id: str
    files: list[FileInsight] = field(default_factory=list)


@dataclass(slots=True)
class DebugOffsetState:
    offset_hex: str
    current_bytes: str
    backup_bytes: str | None
    matches_backup_expected: bool


@dataclass(slots=True)
class DebugInsight:
    exe_path: str
    backup_path: str | None
    markers_found: dict[str, bool]
    offsets: list[DebugOffsetState]
    has_debug_assets: bool
    debug_assets: list[str]


def detect_signature(buf: bytes) -> str:
    if buf.startswith(b"LZ77"):
        return "LZ77"
    if buf.startswith(b"Sequence"):
        return "Sequence"
    if buf.startswith(b"Texture"):
        return "Texture"
    if buf.startswith(b"Filename"):
        return "Filename"
    if buf.startswith(b"Cell"):
        return "Cell"
    return "Unknown"


def count_pngs(buf: bytes) -> int:
    count = 0
    pos = 0
    while True:
        pos = buf.find(PNG_SIGNATURE, pos)
        if pos < 0:
            return count
        count += 1
        end = buf.find(PNG_END, pos)
        pos = pos + 1 if end < 0 else end + len(PNG_END)


def _decompress_lz77_cell(data: bytes) -> tuple[bytes, LZ77Info | None]:
    """Decompress LZ77 data using the cell variant via the unified lz77 module."""
    return _decompress_lz77(data, variant="cell")


def parse_cell_fields(buf: bytes) -> dict[str, Any]:
    header = parse_cell_header(buf)
    records = parse_cell_records(buf, header)
    return {
        "table_offset": header.table_offset,
        "entry_count": header.entry_count,
        "grid_width": header.grid_width,
        "grid_height": header.grid_height,
        "grid_cells": header.grid_width * header.grid_height,
        **summarize_records(records),
    }


def extract_cell_metadata(
    buf: bytes,
) -> tuple[dict[str, Any], list[str], dict[str, Any], dict[str, Any] | None, dict[str, Any] | None]:
    header = parse_cell_header(buf)
    records = parse_cell_records(buf, header)
    chunks = parse_cell_chunks(buf, header)
    cell_map = parse_cell_map(buf, header, chunks)
    texture_summary: dict[str, Any] | None = None
    texture_chunk = next((chunk for chunk in chunks if chunk.name == "TextureParts"), None)
    if texture_chunk is not None:
        container = parse_texture_parts_chunk(buf, texture_chunk)
        texture_summary = summarize_texture_parts(container)
        palette_chunk = next((chunk for chunk in chunks if chunk.name == "Palette"), None)
        if palette_chunk is not None:
            texture_summary["palette_count"] = len(parse_palette_chunk(buf, palette_chunk))
    return (
        {
            "table_offset": header.table_offset,
            "entry_count": header.entry_count,
            "grid_width": header.grid_width,
            "grid_height": header.grid_height,
            "grid_cells": header.grid_width * header.grid_height,
            **summarize_records(records),
        },
        [chunk.name for chunk in chunks],
        summarize_record_decoding(records),
        summarize_map(cell_map, header.entry_count) if cell_map else None,
        texture_summary,
    )


def analyze_file(path: Path, root: Path) -> FileInsight:
    data = path.read_bytes()
    signature = detect_signature(data[:0x40])
    insight = FileInsight(
        path=str(path),
        relative_path=str(path.relative_to(root)),
        extension=path.suffix.lower(),
        size=path.stat().st_size,
        signature=signature,
        png_count=count_pngs(data),
    )

    try:
        if signature == "LZ77":
            decompressed, info = _decompress_lz77_cell(data)
            assert info is not None
            insight.lz77 = asdict(info)
            insight.decompressed_signature = detect_signature(decompressed[:0x40])
            if insight.decompressed_signature == "Cell":
                (
                    insight.cell_fields,
                    insight.cell_chunks,
                    insight.cell_records,
                    insight.cell_map,
                    insight.cell_texture,
                ) = extract_cell_metadata(decompressed)
        elif signature == "Cell":
            (
                insight.cell_fields,
                insight.cell_chunks,
                insight.cell_records,
                insight.cell_map,
                insight.cell_texture,
            ) = extract_cell_metadata(data)
    except Exception as exc:
        insight.parse_error = str(exc)

    return insight


def scan_map_groups(game_dir: Path) -> list[MapGroup]:
    field_map = game_dir / "GameData" / "app" / "Field" / "Map"
    field_chizu = game_dir / "GameData" / "app" / "Field" / "Chizu"
    groups: dict[str, MapGroup] = {}

    for file_path in sorted(field_map.rglob("*")):
        if not file_path.is_file():
            continue
        match = MAP_ID_RE.match(file_path.name)
        map_id = match.group(1) if match else "misc"
        groups.setdefault(map_id, MapGroup(map_id=map_id))
        groups[map_id].files.append(analyze_file(file_path, game_dir))

    if field_chizu.exists():
        groups.setdefault("chizu", MapGroup(map_id="chizu"))
        for file_path in sorted(field_chizu.rglob("*")):
            if file_path.is_file():
                groups["chizu"].files.append(analyze_file(file_path, game_dir))

    return [groups[key] for key in sorted(groups)]


def read_bytes_at(path: Path, offset: int, length: int = 8) -> str | None:
    if not path.exists():
        return None
    with path.open("rb") as handle:
        handle.seek(offset)
        data = handle.read(length)
    return " ".join(f"{byte:02X}" for byte in data)


def analyze_debug(game_dir: Path) -> DebugInsight:
    exe = game_dir / "DOKAPON! Sword of Fury.exe"
    backup = game_dir / "DOKAPON! Sword of Fury.exe.bak"
    data = exe.read_bytes()
    markers = [
        b"DebugPlayBattle",
        b"DEBUGPLAY",
        b"Load Field Map Thread",
        b"DebugMode",
        b"X%3d Y%3d P%3d",
        b"X%3d Y%3d A%3d",
    ]
    offsets = {
        0x2DAE8: b"\x74\x0B",
        0x968930: b"\x00\x00\x00\x00",
    }
    states = [
        DebugOffsetState(
            offset_hex=f"0x{offset:X}",
            current_bytes=read_bytes_at(exe, offset) or "",
            backup_bytes=read_bytes_at(backup, offset),
            matches_backup_expected=(read_bytes_at(backup, offset, len(expected)) == " ".join(f"{b:02X}" for b in expected))
            if backup.exists()
            else False,
        )
        for offset, expected in offsets.items()
    ]
    debug_dir = game_dir / "GameData" / "app" / "Debug"
    debug_assets = [str(path.relative_to(game_dir)) for path in sorted(debug_dir.rglob("*")) if path.is_file()] if debug_dir.exists() else []
    return DebugInsight(
        exe_path=str(exe),
        backup_path=str(backup) if backup.exists() else None,
        markers_found={marker.decode("ascii", errors="replace"): marker in data for marker in markers},
        offsets=states,
        has_debug_assets=bool(debug_assets),
        debug_assets=debug_assets,
    )


def summarize_map_groups(groups: list[MapGroup]) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "group_count": len(groups),
        "map_ids": [],
        "extensions": {},
    }
    for group in groups:
        summary["map_ids"].append(group.map_id)
        for file in group.files:
            summary["extensions"][file.extension] = summary["extensions"].get(file.extension, 0) + 1
    return summary
