from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import json

from .scanner import DebugInsight, MapGroup, summarize_map_groups


def _fmt_chunks(chunks: list[str] | None) -> str:
    if not chunks:
        return "-"
    return ", ".join(chunks)


def _fmt_cell_summary(file: object) -> list[str]:
    file_dict = asdict(file) if hasattr(file, "__dataclass_fields__") else file
    cell_fields = file_dict.get("cell_fields")
    cell_records = file_dict.get("cell_records")
    cell_map = file_dict.get("cell_map")
    cell_texture = file_dict.get("cell_texture")
    chunks = file_dict.get("cell_chunks")
    if not cell_fields:
        return []

    lines = [
        f"  - cell grid=`{cell_fields['grid_width']}x{cell_fields['grid_height']}` "
        f"entries=`{cell_fields['entry_count']}` "
        f"unique_record_a=`{cell_fields['unique_value_a']}` "
        f"chunks=`{_fmt_chunks(chunks)}`"
    ]
    if cell_map:
        top_values = ", ".join(
            f"{item['hex']}->{item['count']}"
            for item in cell_map["top_values"][:6]
        )
        lines.append(
            f"  - map grid=`{cell_map['width']}x{cell_map['height']}` "
            f"unique_values=`{cell_map['unique_values']}` "
            f"low16_in_range=`{cell_map['low16_within_entry_count']}/{cell_map['cell_count']}` "
            f"high16_nonzero=`{cell_map['values_with_nonzero_high16']}`"
        )
        if top_values:
            lines.append(f"  - map top values: `{top_values}`")
        top_refs = ", ".join(
            f"{item['record_index']}->{item['count']}"
            for item in cell_map["top_record_refs"][:6]
        )
        if top_refs:
            lines.append(f"  - map top record refs: `{top_refs}`")
    if cell_records:
        top_a = ", ".join(
            f"{item['value']}->{item['count']}"
            for item in cell_records["value_a_high16_top"][:4]
        )
        top_b = ", ".join(
            f"{item['hex']}->{item['count']}"
            for item in cell_records["value_b_top"][:4]
        )
        top_c = ", ".join(
            f"{item['hex']}->{item['count']}"
            for item in cell_records["value_c_top"][:4]
        )
        lines.append(
            f"  - record flags: a_high16=`{cell_records['records_with_value_a_high16']}` "
            f"nonzero_b=`{cell_records['records_with_nonzero_value_b']}` "
            f"nondefault_c=`{cell_records['records_with_nondefault_value_c']}`"
        )
        if top_a:
            lines.append(f"  - record a_high16 top: `{top_a}`")
        if top_b:
            lines.append(f"  - record value_b top: `{top_b}`")
        if top_c:
            lines.append(f"  - record value_c top: `{top_c}`")
    if cell_texture:
        lines.append(
            f"  - texture atlas=`{cell_texture['width']}x{cell_texture['height']}` "
            f"storage=`{cell_texture['storage_kind']}` "
            f"parts=`{cell_texture['parts_count']}` "
            f"palettes=`{cell_texture.get('palette_count', 0)}`"
        )
    return lines


def write_json_report(out_dir: Path, debug: DebugInsight, map_groups: list[MapGroup]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "debug": asdict(debug),
        "maps": [asdict(group) for group in map_groups],
        "summary": summarize_map_groups(map_groups),
    }
    path = out_dir / "scan_report.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def write_markdown_report(out_dir: Path, debug: DebugInsight, map_groups: list[MapGroup]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = summarize_map_groups(map_groups)
    lines: list[str] = []
    lines.append("# Dokapon Reverse-Engineering Report")
    lines.append("")
    lines.append("## Debug")
    lines.append(f"- Executable: `{debug.exe_path}`")
    lines.append(f"- Backup: `{debug.backup_path or 'missing'}`")
    lines.append(f"- Debug assets present: `{debug.has_debug_assets}`")
    if debug.debug_assets:
        lines.append(f"- Debug assets: {', '.join(f'`{item}`' for item in debug.debug_assets)}")
    lines.append("- Internal markers:")
    for marker, found in debug.markers_found.items():
        lines.append(f"  - `{marker}`: `{found}`")
    lines.append("- Offset snapshots:")
    for state in debug.offsets:
        lines.append(
            f"  - `{state.offset_hex}` current=`{state.current_bytes}` backup=`{state.backup_bytes or 'missing'}` "
            f"backup_matches_expected=`{state.matches_backup_expected}`"
        )
    lines.append("")
    lines.append("## Maps")
    lines.append(f"- Groups found: `{summary['group_count']}`")
    lines.append(f"- Map IDs: `{', '.join(summary['map_ids'])}`")
    lines.append("- Extensions:")
    for ext, count in sorted(summary["extensions"].items()):
        lines.append(f"  - `{ext}`: `{count}`")
    lines.append("")
    lines.append("## Group Details")
    for group in map_groups:
        lines.append(f"### Group `{group.map_id}`")
        for file in group.files:
            line = (
                f"- `{file.relative_path}` sig=`{file.signature}` size=`{file.size}` pngs=`{file.png_count}`"
            )
            if file.lz77:
                line += (
                    f" raw=`{file.lz77['raw_size']}` tokens=`{file.lz77['token_count']}` "
                    f"decomp_sig=`{file.decompressed_signature}`"
                )
            if file.parse_error:
                line += f" error=`{file.parse_error}`"
            lines.append(line)
            lines.extend(_fmt_cell_summary(file))
        lines.append("")
    lines.append("## Next Targets")
    lines.append("- Decode decompressed `F_xx_MD_00.mpd` structures after LZ77.")
    lines.append("- Compare `Field/Map` vs `Field/Chizu` to separate visual and logical map layers.")
    lines.append("- Fingerprint executable builds before any future debug patching.")
    lines.append("- Locate gameplay parameter tables after text tables are mapped.")
    path = out_dir / "scan_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_logic_report(out_dir: Path, map_groups: list[MapGroup]) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    md00_dims: dict[tuple[int, int], int] = {}
    md01_dims: dict[tuple[int, int], int] = {}
    chizu_dims: dict[tuple[int, int], int] = {}
    md00_high_map: list[str] = []
    md01_flagged: list[str] = []
    placeholder_md01: list[str] = []

    for group in map_groups:
        for file in group.files:
            if not file.cell_map or not file.cell_fields:
                continue
            dims = (file.cell_map["width"], file.cell_map["height"])
            rel = file.relative_path
            if rel.endswith("_MD_00.mpd"):
                md00_dims[dims] = md00_dims.get(dims, 0) + 1
                if file.cell_map["values_with_nonzero_high16"] > 0:
                    md00_high_map.append(
                        f"{rel} high16_nonzero={file.cell_map['values_with_nonzero_high16']} "
                        f"a_high16={file.cell_records['records_with_value_a_high16'] if file.cell_records else 0}"
                    )
            elif rel.endswith("_MD_01.mpd"):
                md01_dims[dims] = md01_dims.get(dims, 0) + 1
                if file.cell_records and (
                    file.cell_records["records_with_nonzero_value_b"] > 0
                    or file.cell_records["records_with_nondefault_value_c"] > 0
                ):
                    md01_flagged.append(
                        f"{rel} value_b_nonzero={file.cell_records['records_with_nonzero_value_b']} "
                        f"value_c_nondefault={file.cell_records['records_with_nondefault_value_c']}"
                    )
                if file.cell_map["referenced_record_count"] == 1:
                    placeholder_md01.append(rel)
            elif "\\Field\\Chizu\\" in rel:
                chizu_dims[dims] = chizu_dims.get(dims, 0) + 1

    def fmt_dims(items: dict[tuple[int, int], int]) -> list[str]:
        return [f"- `{width}x{height}`: `{count}`" for (width, height), count in sorted(items.items(), key=lambda item: (-item[1], item[0]))]

    lines: list[str] = []
    lines.append("# Dokapon Map Logic Findings")
    lines.append("")
    lines.append("## Confirmed Structures")
    lines.append("- `Cell` contains a 12-byte record table followed by named chunks such as `TextureParts`, `Palette`, `Map`, and `ConvertInfo`.")
    lines.append("- `Map` chunk payload starts with `width` and `height` as `u16`, followed by `width * height` values of `u32`.")
    lines.append("- `Map` values usually reference record indices through `low16`; `high16` behaves like an extra flag/variant field in some files.")
    lines.append("- `TextureParts` contains a nested texture atlas plus a `Parts` table of 32-byte entries with UV rectangles.")
    lines.append("")
    lines.append("## Dimensions")
    lines.append("### MD_00")
    lines.extend(fmt_dims(md00_dims))
    lines.append("### MD_01")
    lines.extend(fmt_dims(md01_dims))
    lines.append("### CHIZU")
    lines.extend(fmt_dims(chizu_dims))
    lines.append("")
    lines.append("## Inference")
    lines.append("- `record.value_a_low16` is very likely a direct `Part` index into `TextureParts`. Evidence: `Parts.count` matches the valid low16 range used by records in tested files, and the first records map cleanly to the first atlas tiles.")
    lines.append("- `MD_01` is likely a compact logic/template layer. Evidence: its map grids are small, direct record references are common, and many files have uniform record flags such as `value_b=0x10`, `value_b=0x30`, or `value_c=0x00010000/0x00020000/0x00030000`.")
    lines.append("- `MD_00` is likely the larger terrain/placement layer. Evidence: grids are much larger, every tested file keeps record refs in `low16`, and many cells carry non-zero `high16` flags.")
    lines.append("- `CHIZU` is likely a world-map index layer. Evidence: it uses a small `20x20` or `10x8` grid and record IDs form structured blocks with repeated border sentinels.")
    lines.append("- Placeholder or degenerate `MD_01` files exist. Evidence: some maps reference only a single record even when the file defines more records.")
    lines.append("")
    lines.append("## Flagged MD_00")
    for item in md00_high_map[:20]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Flagged MD_01")
    for item in md01_flagged[:20]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Placeholder MD_01")
    for item in placeholder_md01[:20]:
        lines.append(f"- `{item}`")
    lines.append("")
    lines.append("## Next Reverse-Engineering Targets")
    lines.append("- Name the semantics of record `value_b` and `value_c` by comparing flagged files in-game.")
    lines.append("- Decode `TextureParts` entries to map record indices to actual tiles or atlas pages.")
    lines.append("- Correlate `MD_01` record refs with `RD_*.mdl` and `RD_*.spranm` to identify map objects and events.")
    lines.append("- Compare localized `CHIZU` and `Map` variants to separate logic from presentation.")
    path = out_dir / "map_logic_report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path
