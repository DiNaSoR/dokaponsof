from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Iterable


def align8(value: int) -> int:
    return (value + 7) & ~7


@dataclass(slots=True)
class CellHeader:
    table_offset: int
    entry_count: int
    grid_width: int
    grid_height: int


@dataclass(slots=True)
class CellRecord:
    index: int
    value_a: int
    value_b: int
    value_c: int


@dataclass(slots=True)
class CellChunk:
    name: str
    offset: int
    size_total: int
    payload_offset: int
    payload_size: int


@dataclass(slots=True)
class CellMap:
    width: int
    height: int
    values: list[int]


@dataclass(slots=True)
class DecodedCellRecord:
    index: int
    value_a: int
    value_a_low16: int
    value_a_high16: int
    value_b: int
    value_b_low16: int
    value_b_high16: int
    value_c: int
    value_c_low16: int
    value_c_high16: int


def parse_cell_header(buf: bytes) -> CellHeader:
    if len(buf) < 0x20 or not buf.startswith(b"Cell"):
        raise ValueError("buffer is not a Cell container")
    return CellHeader(
        table_offset=struct.unpack_from("<I", buf, 0x14)[0],
        entry_count=struct.unpack_from("<I", buf, 0x18)[0],
        grid_width=struct.unpack_from("<H", buf, 0x1C)[0],
        grid_height=struct.unpack_from("<H", buf, 0x1E)[0],
    )


def parse_cell_records(buf: bytes, header: CellHeader) -> list[CellRecord]:
    records: list[CellRecord] = []
    off = 0x20
    for index in range(header.entry_count):
        if off + 12 > len(buf):
            raise ValueError("cell record table exceeds file size")
        value_a, value_b, value_c = struct.unpack_from("<III", buf, off)
        records.append(CellRecord(index=index, value_a=value_a, value_b=value_b, value_c=value_c))
        off += 12
    return records


def find_chunk_start(buf: bytes, header: CellHeader) -> int:
    for candidate in (header.table_offset, header.table_offset + 4):
        if candidate < len(buf) and buf[candidate:candidate + 12].startswith(b"TextureParts"):
            return candidate
    marker = b"TextureParts"
    pos = buf.find(marker, max(0, header.table_offset - 0x20), min(len(buf), header.table_offset + 0x40))
    if pos >= 0:
        return pos
    raise ValueError("TextureParts marker not found near cell table offset")


def parse_cell_chunks(buf: bytes, header: CellHeader) -> list[CellChunk]:
    chunks: list[CellChunk] = []
    off = find_chunk_start(buf, header)
    while off + 0x18 <= len(buf):
        raw_name = buf[off:off + 0x14]
        if raw_name[0] == 0:
            break
        name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
        size_total = struct.unpack_from("<I", buf, off + 0x14)[0]
        if size_total < 0x18 or off + size_total > len(buf):
            raise ValueError(f"invalid chunk at 0x{off:X}: {name!r} size=0x{size_total:X}")
        chunks.append(
            CellChunk(
                name=name,
                offset=off,
                size_total=size_total,
                payload_offset=off + 0x18,
                payload_size=size_total - 0x18,
            )
        )
        off = align8(off + size_total)
    return chunks


def parse_chunk_map(buf: bytes, chunk: CellChunk) -> CellMap:
    payload = buf[chunk.payload_offset:chunk.payload_offset + chunk.payload_size]
    if len(payload) < 4:
        raise ValueError("Map chunk payload is too small")
    width, height = struct.unpack_from("<HH", payload, 0)
    expected_values = width * height
    expected_size = 4 + (expected_values * 4)
    if len(payload) != expected_size:
        raise ValueError(
            f"Map chunk size mismatch: width={width} height={height} payload=0x{len(payload):X} expected=0x{expected_size:X}"
        )
    values = list(struct.unpack_from(f"<{expected_values}I", payload, 4))
    return CellMap(width=width, height=height, values=values)


def parse_cell_map(buf: bytes, header: CellHeader, chunks: list[CellChunk] | None = None) -> CellMap | None:
    chunks = chunks or parse_cell_chunks(buf, header)
    for chunk in chunks:
        if chunk.name == "Map":
            return parse_chunk_map(buf, chunk)
    return None


def summarize_records(records: Iterable[CellRecord]) -> dict[str, object]:
    records = list(records)
    unique_a = len({record.value_a for record in records})
    unique_b = len({record.value_b for record in records})
    unique_c = len({record.value_c for record in records})
    return {
        "record_count": len(records),
        "unique_value_a": unique_a,
        "unique_value_b": unique_b,
        "unique_value_c": unique_c,
        "first_records": [
            {
                "index": record.index,
                "value_a": record.value_a,
                "value_b": record.value_b,
                "value_c": record.value_c,
            }
            for record in records[:16]
        ],
    }


def decode_record(record: CellRecord) -> DecodedCellRecord:
    return DecodedCellRecord(
        index=record.index,
        value_a=record.value_a,
        value_a_low16=record.value_a & 0xFFFF,
        value_a_high16=record.value_a >> 16,
        value_b=record.value_b,
        value_b_low16=record.value_b & 0xFFFF,
        value_b_high16=record.value_b >> 16,
        value_c=record.value_c,
        value_c_low16=record.value_c & 0xFFFF,
        value_c_high16=record.value_c >> 16,
    )


def summarize_record_decoding(records: Iterable[CellRecord]) -> dict[str, object]:
    decoded = [decode_record(record) for record in records]
    value_a_high_counts: dict[int, int] = {}
    value_b_counts: dict[int, int] = {}
    value_c_counts: dict[int, int] = {}
    for record in decoded:
        value_a_high_counts[record.value_a_high16] = value_a_high_counts.get(record.value_a_high16, 0) + 1
        value_b_counts[record.value_b] = value_b_counts.get(record.value_b, 0) + 1
        value_c_counts[record.value_c] = value_c_counts.get(record.value_c, 0) + 1

    def top_counts(values: dict[int, int]) -> list[dict[str, int | str]]:
        return [
            {"value": value, "hex": f"0x{value:08X}", "count": count}
            for value, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:16]
        ]

    return {
        "records_with_value_a_high16": sum(1 for record in decoded if record.value_a_high16 != 0),
        "records_with_nonzero_value_b": sum(1 for record in decoded if record.value_b != 0),
        "records_with_nondefault_value_c": sum(1 for record in decoded if record.value_c != 0xFFFF0000),
        "value_a_high16_top": top_counts(value_a_high_counts),
        "value_b_top": top_counts(value_b_counts),
        "value_c_top": top_counts(value_c_counts),
        "first_decoded_records": [
            {
                "index": record.index,
                "value_a_hex": f"0x{record.value_a:08X}",
                "value_a_low16": record.value_a_low16,
                "value_a_high16": record.value_a_high16,
                "value_b_hex": f"0x{record.value_b:08X}",
                "value_b_low16": record.value_b_low16,
                "value_b_high16": record.value_b_high16,
                "value_c_hex": f"0x{record.value_c:08X}",
                "value_c_low16": record.value_c_low16,
                "value_c_high16": record.value_c_high16,
            }
            for record in decoded[:16]
        ],
    }


def summarize_map(cell_map: CellMap, entry_count: int) -> dict[str, object]:
    if not cell_map.values:
        return {
            "width": cell_map.width,
            "height": cell_map.height,
            "cell_count": 0,
            "unique_values": 0,
            "top_values": [],
            "values_with_zero_high16": 0,
            "values_with_nonzero_high16": 0,
            "low16_within_entry_count": 0,
            "low16_outside_entry_count": 0,
        }

    value_counts: dict[int, int] = {}
    zero_high16 = 0
    within_entry_count = 0
    ref_counts: dict[int, int] = {}
    for value in cell_map.values:
        value_counts[value] = value_counts.get(value, 0) + 1
        if (value >> 16) == 0:
            zero_high16 += 1
        low16 = value & 0xFFFF
        if low16 < entry_count:
            within_entry_count += 1
            ref_counts[low16] = ref_counts.get(low16, 0) + 1

    top_values = sorted(value_counts.items(), key=lambda item: (-item[1], item[0]))[:16]
    top_refs = sorted(ref_counts.items(), key=lambda item: (-item[1], item[0]))[:16]
    return {
        "width": cell_map.width,
        "height": cell_map.height,
        "cell_count": len(cell_map.values),
        "unique_values": len(value_counts),
        "top_values": [
            {
                "value": value,
                "hex": f"0x{value:08X}",
                "count": count,
                "low16": value & 0xFFFF,
                "high16": value >> 16,
            }
            for value, count in top_values
        ],
        "values_with_zero_high16": zero_high16,
        "values_with_nonzero_high16": len(cell_map.values) - zero_high16,
        "low16_within_entry_count": within_entry_count,
        "low16_outside_entry_count": len(cell_map.values) - within_entry_count,
        "referenced_record_count": len(ref_counts),
        "top_record_refs": [
            {
                "record_index": record_index,
                "count": count,
            }
            for record_index, count in top_refs
        ],
    }


def render_map_text(cell_map: CellMap, *, mode: str = "full") -> str:
    rows: list[str] = []
    for y in range(cell_map.height):
        row = cell_map.values[y * cell_map.width:(y + 1) * cell_map.width]
        if mode == "low16":
            rows.append(" ".join(f"{value & 0xFFFF:03X}" for value in row))
        elif mode == "split":
            rows.append(" ".join(f"{value & 0xFFFF:03X}:{value >> 16:02X}" for value in row))
        else:
            rows.append(" ".join(f"{value:08X}" for value in row))
    return "\n".join(rows)
