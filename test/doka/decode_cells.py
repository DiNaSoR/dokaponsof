from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dokapon_explorer.cell import (
    decode_record,
    parse_cell_chunks,
    parse_cell_header,
    parse_cell_map,
    parse_cell_records,
    render_map_text,
    summarize_map,
    summarize_record_decoding,
    summarize_records,
)
from dokapon_explorer.lz77 import decompress_lz77
from dokapon_explorer.texture import (
    build_indexed_atlas_image,
    build_png_image,
    parse_palette_chunk,
    parse_texture_parts_chunk,
    summarize_texture_parts,
)


def decode_one(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    data, lz77 = decompress_lz77(raw)
    header = parse_cell_header(data)
    records = parse_cell_records(data, header)
    chunks = parse_cell_chunks(data, header)
    cell_map = parse_cell_map(data, header, chunks)
    texture_chunk = next((chunk for chunk in chunks if chunk.name == "TextureParts"), None)
    texture = parse_texture_parts_chunk(data, texture_chunk) if texture_chunk else None
    palette_chunk = next((chunk for chunk in chunks if chunk.name == "Palette"), None)
    palettes = parse_palette_chunk(data, palette_chunk) if palette_chunk else []
    return {
        "source_path": str(path),
        "is_lz77": lz77 is not None,
        "lz77": None
        if lz77 is None
        else {
            "raw_size": lz77.raw_size,
            "token_count": lz77.token_count,
            "data_offset": lz77.data_offset,
            "flags_end": lz77.flags_end,
            "data_end": lz77.data_end,
            "out_len": lz77.out_len,
        },
        "header": {
            "table_offset": header.table_offset,
            "entry_count": header.entry_count,
            "grid_width": header.grid_width,
            "grid_height": header.grid_height,
            "grid_cells": header.grid_width * header.grid_height,
        },
        "records": summarize_records(records),
        "record_decoding": summarize_record_decoding(records),
        "map": summarize_map(cell_map, header.entry_count) if cell_map else None,
        "texture": None
        if texture is None
        else {
            **summarize_texture_parts(texture),
            "palette_count": len(palettes),
        },
        "chunks": [
            {
                "name": chunk.name,
                "offset": chunk.offset,
                "size_total": chunk.size_total,
                "payload_offset": chunk.payload_offset,
                "payload_size": chunk.payload_size,
            }
            for chunk in chunks
        ],
    }


def decode_buffer(path: Path) -> tuple[bytes, object | None]:
    raw = path.read_bytes()
    data, lz77 = decompress_lz77(raw)
    return data, lz77


def export_map_csv(out_path: Path, width: int, height: int, values: list[int]) -> None:
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["x", "y", "value_dec", "value_hex", "low16", "high16"])
        for y in range(height):
            for x in range(width):
                value = values[(y * width) + x]
                writer.writerow([x, y, value, f"0x{value:08X}", value & 0xFFFF, value >> 16])


def export_records_csv(out_path: Path, records: list[object], map_values: list[int] | None, texture_container: object | None) -> None:
    ref_counts: dict[int, int] = {}
    if map_values is not None:
        for value in map_values:
            low16 = value & 0xFFFF
            ref_counts[low16] = ref_counts.get(low16, 0) + 1

    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "record_index",
                "value_a_dec",
                "value_a_hex",
                "value_a_low16",
                "value_a_high16",
                "value_b_dec",
                "value_b_hex",
                "value_b_low16",
                "value_b_high16",
                "value_c_dec",
                "value_c_hex",
                "value_c_low16",
                "value_c_high16",
                "map_ref_count",
                "part_index",
                "part_pixel_x0",
                "part_pixel_y0",
                "part_pixel_x1",
                "part_pixel_y1",
            ]
        )
        for record in records:
            decoded = decode_record(record)
            part = None
            part_rect = ("", "", "", "")
            if texture_container is not None and decoded.value_a_low16 < len(texture_container.parts):
                part = texture_container.parts[decoded.value_a_low16]
                part_rect = part.pixel_rect(texture_container.header.width, texture_container.header.height)
            writer.writerow(
                [
                    decoded.index,
                    decoded.value_a,
                    f"0x{decoded.value_a:08X}",
                    decoded.value_a_low16,
                    decoded.value_a_high16,
                    decoded.value_b,
                    f"0x{decoded.value_b:08X}",
                    decoded.value_b_low16,
                    decoded.value_b_high16,
                    decoded.value_c,
                    f"0x{decoded.value_c:08X}",
                    decoded.value_c_low16,
                    decoded.value_c_high16,
                    ref_counts.get(decoded.index, 0),
                    decoded.value_a_low16 if part is not None else "",
                    part_rect[0],
                    part_rect[1],
                    part_rect[2],
                    part_rect[3],
                ]
            )


def export_parts_csv(out_path: Path, container: object) -> None:
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "part_index",
                "offset_x",
                "offset_y",
                "part_width",
                "part_height",
                "u0",
                "v0",
                "u1",
                "v1",
                "pixel_x0",
                "pixel_y0",
                "pixel_x1",
                "pixel_y1",
            ]
        )
        for part in container.parts:
            x0, y0, x1, y1 = part.pixel_rect(container.header.width, container.header.height)
            writer.writerow(
                [
                    part.index,
                    part.offset_x,
                    part.offset_y,
                    part.width,
                    part.height,
                    part.u0,
                    part.v0,
                    part.u1,
                    part.v1,
                    x0,
                    y0,
                    x1,
                    y1,
                ]
            )


def export_texture_assets(base_path: Path, data: bytes, chunks: list[object]) -> list[Path]:
    written: list[Path] = []
    texture_chunk = next((chunk for chunk in chunks if chunk.name == "TextureParts"), None)
    if texture_chunk is None:
        return written

    container = parse_texture_parts_chunk(data, texture_chunk)
    parts_csv_path = base_path.with_suffix(base_path.suffix + ".parts.csv")
    export_parts_csv(parts_csv_path, container)
    written.append(parts_csv_path)

    if container.storage_kind == "png":
        atlas = build_png_image(container)
        atlas_path = base_path.with_suffix(base_path.suffix + ".atlas.png")
        atlas.save(atlas_path)
        written.append(atlas_path)
        return written

    palette_chunk = next((chunk for chunk in chunks if chunk.name == "Palette"), None)
    if palette_chunk is None:
        return written
    palettes = parse_palette_chunk(data, palette_chunk)
    for index, palette in enumerate(palettes):
        atlas = build_indexed_atlas_image(container, palette)
        atlas_path = base_path.with_suffix(base_path.suffix + f".atlas.pal{index}.png")
        atlas.save(atlas_path)
        written.append(atlas_path)
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Decode DOKAPON Cell containers")
    parser.add_argument("inputs", nargs="+", type=Path, help="Cell files to decode")
    parser.add_argument("--out", type=Path, default=Path("out/cells"), help="Output directory")
    parser.add_argument("--export-map", action="store_true", help="Export Map chunk as CSV and TXT preview when present")
    parser.add_argument("--export-texture", action="store_true", help="Export TextureParts atlas PNGs and Parts CSV when present")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    for input_path in args.inputs:
        data, _ = decode_buffer(input_path)
        header = parse_cell_header(data)
        records = parse_cell_records(data, header)
        chunks = parse_cell_chunks(data, header)
        cell_map = parse_cell_map(data, header, chunks)
        texture_chunk = next((chunk for chunk in chunks if chunk.name == "TextureParts"), None)
        texture_container = parse_texture_parts_chunk(data, texture_chunk) if texture_chunk else None
        decoded = decode_one(input_path)
        out_path = args.out / f"{input_path.name}.json"
        out_path.write_text(json.dumps(decoded, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[+] Decoded {input_path} -> {out_path}")
        records_csv_path = args.out / f"{input_path.name}.records.csv"
        export_records_csv(records_csv_path, records, cell_map.values if cell_map else None, texture_container)
        print(f"[+] Records CSV: {records_csv_path}")
        if args.export_texture:
            for written_path in export_texture_assets(args.out / input_path.name, data, chunks):
                print(f"[+] Texture export: {written_path}")
        if args.export_map and cell_map:
            csv_path = args.out / f"{input_path.name}.map.csv"
            txt_path = args.out / f"{input_path.name}.map_low16.txt"
            split_path = args.out / f"{input_path.name}.map_split.txt"
            export_map_csv(csv_path, cell_map.width, cell_map.height, cell_map.values)
            txt_path.write_text(render_map_text(cell_map, mode="low16"), encoding="utf-8")
            split_path.write_text(render_map_text(cell_map, mode="split"), encoding="utf-8")
            print(f"[+] Map CSV: {csv_path}")
            print(f"[+] Map preview: {txt_path}")
            print(f"[+] Map split preview: {split_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
