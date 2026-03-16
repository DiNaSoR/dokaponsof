---
title: MPD Format
layout: default
nav_order: 3
parent: Technical Reference
---

# MPD Cell Map Format
{: .no_toc }

Documentation of the Cell container map format used for game environments in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

MPD files store tile-based map data for the game's field environments and chizu (map overview) screens. Each file is a **Cell container** — a structured binary format that may optionally be wrapped in LZ77 Cell-variant compression.

The C# implementation spans three classes:
- `DokaponSoFTools.Core.Formats.CellContainer` — header/record/chunk parsing
- `DokaponSoFTools.Core.Formats.TextureAtlas` — TextureParts and Palette chunk parsing
- `DokaponSoFTools.Core.Imaging.MapRenderer` — full document loading and tile rendering

Map files are located in:
```
GameData/app/Field/Map/      ← field tile maps
GameData/app/Field/Chizu/    ← overview map screens
```

---

## LZ77 Compression Layer

Most MPD files are wrapped in the **Cell** LZ77 variant. The raw file is detected and decompressed before the Cell container is parsed:

```csharp
byte[] raw = File.ReadAllBytes(path);
var (data, lz77Info) = Lz77Cell.Decompress(raw);
// If file is not LZ77, Decompress returns the buffer unchanged
```

See [LZ77 Compression — Cell Variant](lz77-compression#variant-3-cell) for the full decompression algorithm.

---

## Cell Container Header

After decompression, the data begins with a Cell container header. Magic is `Cell` (ASCII, `0x43656C6C`) at offset `0x00`.

```
Offset  Size  Field
------  ----  -----
0x00     4    Magic "Cell" (ASCII)
0x04    16    Name padding (spaces or nulls, to reach 0x14)
0x14     4    TableOffset  — byte offset to the chunk area (LE int32)
0x18     4    EntryCount   — number of records in the record table (LE int32)
0x1C     2    GridWidth    — map width in tiles (LE uint16)
0x1E     2    GridHeight   — map height in tiles (LE uint16)
0x20    var   Record table (EntryCount × 12 bytes each)
```

### C# Record

```csharp
public sealed record CellHeader(
    int TableOffset,
    int EntryCount,
    int GridWidth,
    int GridHeight
);
```

---

## Record Table

Immediately after the header (at `0x20`), the record table contains `EntryCount` entries of 12 bytes each.

**Record entry** (12 bytes = 3 × uint32):

```
Offset  Size  Field
------  ----  -----
+0x00    4    ValueA  (LE uint32)
+0x04    4    ValueB  (LE uint32)
+0x08    4    ValueC  (LE uint32)
```

Records are decoded by splitting each 32-bit value into low and high 16-bit halves:

```csharp
ValueALow16  = (int)(ValueA & 0xFFFF)  // → parts index used by renderer
ValueAHigh16 = (int)(ValueA >> 16)
// ValueB, ValueC decoded similarly
```

During map rendering, `ValueALow16` is used as the **index into the TextureParts `Parts` array** to select the tile crop.

---

## Chunk System

Starting at (approximately) `TableOffset` in the decompressed data, the file contains a sequence of named chunks. The parser searches for the `TextureParts` marker near that offset to find the true chunk start.

### Chunk Header (24 bytes = `0x18`)

```
Offset  Size  Field
------  ----  -----
+0x00   20    Name (ASCII, null-padded to 20 bytes)
+0x14    4    SizeTotal — total chunk size in bytes, including this header (LE int32)
+0x18   var   Chunk payload (SizeTotal - 0x18 bytes)
```

Chunks are 8-byte aligned:
```
nextChunkOffset = AlignUp(currentChunkOffset + sizeTotal, 8)
```

Parsing stops when a chunk name begins with a null byte.

### Known Chunk Types

| Name | Purpose |
|---|---|
| `TextureParts` | Texture atlas and UV part definitions |
| `Map` | Cell grid — width, height, and one uint32 per tile |
| `Palette` | Indexed color palettes (for non-PNG textures) |

---

## Chunk: Map

The Map chunk payload encodes the tile grid.

**Payload layout:**

```
Offset  Size  Field
------  ----  -----
+0x00    2    Width  (LE uint16)  — tiles across
+0x02    2    Height (LE uint16)  — tiles down
+0x04    N    Values: Width × Height × uint32 (LE), row-major order
```

Total payload size = `4 + Width × Height × 4` bytes.

Each 32-bit value encodes tile information:
- Bits 0–15 (low word): **record index** into the record table
- Bits 16–31 (high word): additional flags (flip, variant, etc.)

The renderer looks up `RecordTable[recordIndex].ValueALow16` to get the parts index for the tile.

### C# Record

```csharp
public sealed record CellMap(int Width, int Height, uint[] Values);
```

---

## Chunk: TextureParts

The TextureParts chunk payload is a `Texture` sub-section followed by `Parts` and optionally `Anime` sub-sections — the **same sub-section format used in SPRANM files**.

The chunk payload begins immediately after the 24-byte chunk header. The `TextureAtlas.ParseChunkPayload` method handles the full parse.

### Texture Sub-section Header (at payload start, 40 bytes)

```
Offset  Size  Field
------  ----  -----
+0x00   20    "Texture" (null-padded)
+0x14    4    TotalSize (LE uint32)
+0x18    4    TextureFlags (LE uint32)
               0x4000 = PNG embedded
               0x0080 = LZ77-compressed indexed pixels
+0x1C    4    TextureKind (LE uint32)
+0x20    4    NestedSize (LE uint32) — size of embedded data
+0x24    2    Width  (LE uint16)
+0x26    2    Height (LE uint16)
+0x28   var   Atlas data: PNG bytes OR LZ77 Cell-compressed indexed pixel data
```

Storage kinds (determined by `TextureFlags`):

| Flag | StorageKind | Atlas data |
|---|---|---|
| `0x4000` | `"png"` | Raw PNG starting at `+0x28` |
| `0x0080` | `"indexed_lz77"` | LZ77 Cell-compressed indexed pixels at `+0x28` |

### Parts Sub-section

Immediately after the Texture sub-section (8-byte aligned), the `Parts` sub-section defines UV-mapped crops. Format is identical to [SPRANM Parts entries](spranm-format#sub-section-parts): 28-byte header followed by `EntryCount` × 32-byte float entries.

Each entry (32 bytes = 8 × float32):

```
OffsetX, OffsetY   — placement adjustment
Width, Height      — tile dimensions in pixels
U0, V0             — top-left UV [0.0–1.0]
U1, V1             — bottom-right UV [0.0–1.0]
```

---

## Chunk: Palette

Provides indexed-color palettes for non-PNG textures (`StorageKind = "indexed_lz77"`).

**Payload layout:**

```
Offset  Size  Field
------  ----  -----
+0x00    4    PaletteCount (LE int32)
+0x04    N    PaletteCount × 256 × 4 bytes
               Each color: [R, G, B, A] (1 byte each)
```

Total payload size = `4 + PaletteCount × 1024` bytes.

The renderer selects a palette by index (default `0`) and maps each indexed pixel to an RGBA color.

---

## Rendering Pipeline

```
MPD file
  │
  ▼  Lz77Cell.Decompress
decompressed Cell container bytes
  │
  ▼  CellContainer.ParseHeader
CellHeader { TableOffset, EntryCount, GridWidth, GridHeight }
  │
  ├──▶  CellContainer.ParseRecords       →  RecordTable[]
  ├──▶  CellContainer.ParseChunks        →  Chunk list
  │         ├──▶  "Map" chunk            →  CellMap { Width, Height, Values[] }
  │         ├──▶  "TextureParts" chunk   →  TexturePartsContainer
  │         │         ├── TextureHeader (dimensions, flags)
  │         │         ├── AtlasBytes (PNG or indexed pixels)
  │         │         └── Parts[] (UV crops)
  │         └──▶  "Palette" chunk        →  List<(R,G,B,A)[]>
  │
  ▼  MapRenderer.RenderMapImage
For each tile (index, value) in CellMap.Values:
  recordIndex = value & 0xFFFF
  partIndex   = RecordTable[recordIndex].ValueALow16
  crop        = Parts[partIndex].PixelRect(atlas.Width, atlas.Height)
  destX       = (index % Width)  * tileWidth
  destY       = (index / Width)  * tileHeight
  canvas.DrawBitmap(atlas, crop, destRect)
  │
  ▼
SKBitmap (final rendered map)
```

---

## C# Usage

```csharp
// Load and render a map file
var doc = MapRenderer.LoadCellDocument("field01.mpd");

// Render with default palette
SKBitmap? image = MapRenderer.RenderMapImage(doc, paletteIndex: 0);

// Access individual components
CellHeader     header  = doc.Header;      // GridWidth, GridHeight, EntryCount
List<CellChunk> chunks = doc.Chunks;      // Named chunk list
CellMap?        map    = doc.CellMap;     // Width × Height grid
TexturePartsContainer? tex = doc.Texture; // Atlas + parts
List<(byte,byte,byte,byte)[]> pals = doc.Palettes; // Indexed palettes

// List all map files in the game directory
List<string> files = MapRenderer.ListCellFiles(gamePath);
```

---

## See Also

- [LZ77 Compression](lz77-compression) — Cell variant used for MPD decompression
- [SPRANM Format](spranm-format) — shares the TextureParts / Parts sub-section structure
