---
title: SPRANM Format
layout: default
nav_order: 2
parent: Technical Reference
---

# SPRANM Sprite Animation Format
{: .no_toc }

Complete documentation of the sprite animation format used in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

SPRANM files define 2D sprite animations used for character portraits, UI overlays, title screen elements, battle effects, and transitions. The format organises animation data as a sequence of named sections that the runtime processes to determine what texture region to display at each frame.

The C# implementation is `DokaponSoFTools.Core.Formats.SpranmDocument` with rendering in `DokaponSoFTools.Core.Imaging.SpranmRenderer`.

---

## File Variants

### Self-Contained (with PNG)

The primary variant includes an embedded PNG texture atlas inside the `TextureParts → Texture` sub-section.

- May or may not be LZ77 compressed (auto-detected from `LZ77` magic)
- Contains the full `Sequence / Sprite / SpriteGp / TextureParts / ConvertInfo` section tree
- The `Texture` sub-section embeds the PNG directly at offset `+0x28` from the sub-section start

### Runtime / Player (no PNG, PartsColor)

A lighter variant used at runtime where the texture is provided externally (e.g., a character-specific palette swap).

- The `Texture` sub-section is absent or the PNG field is empty
- A `PartsColor` section may carry per-part tint/palette data
- Otherwise identical section structure

---

## LZ77 Compression Layer

Some SPRANM files are wrapped in the **FlagByte** LZ77 variant. Detection:

```
if file[0..3] == "LZ77"  →  decompress with Lz77FlagByte first
else                     →  parse sections directly from raw bytes
```

The 16-byte LZ77 header:

```
Offset  Size  Description
------  ----  -----------
0x00    4     Magic "LZ77"
0x04    4     Reserved / unknown
0x08    4     Decompressed size (LE int32)
0x0C    4     Uncompressed tail offset (LE int32, 0 = none)
0x10    var   FlagByte compressed stream
```

See [LZ77 Compression — FlagByte Variant](lz77-compression#variant-1-flagbyte) for full decompression details.

---

## Top-Level Section Structure

After any decompression, the payload is a stream of variable-length sections. Each standard top-level section begins with a **28-byte header**:

```
Offset  Size  Field
------  ----  -----
+0x00   20    Name (ASCII, null-padded to 20 bytes)
+0x14    4    TotalSize — total section length in bytes including this header (LE uint32)
+0x18    4    EntryCount — number of entries that follow (LE uint32)
+0x1C   var   Section payload
```

Sections are laid out sequentially. After each section's `TotalSize` bytes, the parser advances to the next **8-byte-aligned** boundary:

```
nextPosition = AlignUp(sectionStart + totalSize, 8)
```

### Known Top-Level Sections

| Name (20-byte padded) | Header Type | Payload |
|---|---|---|
| `Sequence` | Standard 28-byte | `EntryCount` × 20-byte entries |
| `Sprite` | Standard 28-byte | `EntryCount` × 32-byte entries |
| `SpriteGp` | Standard 28-byte | Count array + index array (variable) |
| `TextureParts` | 24-byte (no `EntryCount`) | Sub-sections (Texture, Parts, Anime) |
| `ConvertInfo` | Standard 28-byte | Metadata; no parsed payload |

---

## Section: Sequence

Each entry describes one **animation frame** — which group of sprites to display and for how long.

**Entry format** (20 bytes = 5 × uint32):

```
Offset  Size  Field
------  ----  -----
+0x00    4    SpriteGroupIndex — index into the SpriteGp table (LE uint32)
+0x04    4    Duration — frame count this sequence entry is held (LE uint32)
+0x08    4    Flags — animation control flags (LE uint32)
+0x0C    4    Unknown1
+0x10    4    Unknown2
```

`TotalFrames = Sum(entry.Duration for all entries)`

---

## Section: Sprite

Each entry describes **one piece** of a composite sprite — which parts entry to sample, which texture to use, where to place it, and how to scale it.

**Entry format** (32 bytes = 8 fields):

```
Offset  Size  Field
------  ----  -----
+0x00    4    PartsIndex  — index into the Parts sub-section (LE uint32)
+0x04    4    Unknown
+0x08    4    TextureIndex — index of texture to use (LE uint32)
+0x0C    4    PositionX — bottom-right X coordinate (LE uint32)
+0x10    4    PositionY — bottom-right Y coordinate (LE uint32)
+0x14    4    ScaleX — horizontal scale factor (float32)
+0x18    4    ScaleY — vertical scale factor (float32)
+0x1C    4    Unknown2 (float32)
```

### Position Interpretation: Bottom-Right Corner

{: .important }
`PositionX` and `PositionY` are the **bottom-right corner** of the rendered piece, **not** the top-left origin. The renderer computes the top-left origin as:

```
destWidth  = part.Width  * sprite.ScaleX
destHeight = part.Height * sprite.ScaleY
topLeftX   = sprite.PositionX - destWidth  + part.OffsetX
topLeftY   = sprite.PositionY - destHeight + part.OffsetY
```

This is confirmed in `SpranmRenderer.RenderSequenceFrame`:

```csharp
float posX = sprite.PositionX - destW + part.OffsetX;
float posY = sprite.PositionY - destH + part.OffsetY;
```

---

## Section: SpriteGp

Groups Sprite entries into named sets. Each group is one animation frame's set of pieces.

**Layout** (variable length):

```
Header (28 bytes):
  name[20]="SpriteGp", totalSize[4], entryCount[4]

Payload:
  Count array:   entryCount × uint32  (number of sprites in each group)
  Index array:   (remaining bytes / 4) × uint32 (flattened sprite indices)
```

The count array and index array are laid out contiguously. For group `g`, its sprite indices are the slice `[sum(counts[0..g-1]) .. sum(counts[0..g])]` of the index array.

---

## Section: TextureParts

A **container** holding sub-sections. Its header is only **24 bytes** (no `EntryCount` field):

```
Offset  Size  Field
------  ----  -----
+0x00   20    Name (ASCII "TextureParts", null-padded)
+0x14    4    TotalSize (LE uint32)
+0x18   var   Sub-sections (parsed until containerStart + totalSize)
```

The parser seeks to `sectionStart + 24` before reading sub-sections.

Sub-sections are also 8-byte aligned within the container.

### Sub-section: Texture

**Header** (40 bytes total):

```
Offset  Size  Field
------  ----  -----
+0x00   20    Name "Texture" (null-padded)
+0x14    4    TotalSize (LE uint32) — includes this header + nested data
+0x18    4    TextureFlags (LE uint32)
               0x4000 = PNG storage
               0x0080 = indexed (palette) storage
+0x1C    4    TextureKind (LE uint32)
+0x20    4    NestedSize — size of embedded data bytes (LE uint32)
+0x24    2    Width  (LE uint16)
+0x26    2    Height (LE uint16)
+0x28   var   Embedded data (PNG or LZ77-compressed indexed pixels)
```

- When `flags & 0x4000`: bytes at `+0x28` are a complete PNG file of length `NestedSize`.
- When `flags & 0x0080`: bytes at `+0x28` are a Cell-variant LZ77-compressed indexed pixel buffer.

### Sub-section: Parts

Defines UV-mapped regions of the texture atlas. Each part is one rectangular crop that can be placed on screen.

**Header** (28 bytes):

```
Offset  Size  Field
------  ----  -----
+0x00   20    Name "Parts" (null-padded)
+0x14    4    TotalSize (LE uint32)
+0x18    4    EntryCount (LE uint32)
```

**Each entry** (32 bytes = 8 × float32):

```
Offset  Size  Field
------  ----  -----
+0x00    4    OffsetX  — X adjustment applied when placing the piece (float32)
+0x04    4    OffsetY  — Y adjustment applied when placing the piece (float32)
+0x08    4    Width    — piece width in pixels (float32)
+0x0C    4    Height   — piece height in pixels (float32)
+0x10    4    U0       — left UV coordinate  [0.0 – 1.0] (float32)
+0x14    4    V0       — top UV coordinate   [0.0 – 1.0] (float32)
+0x18    4    U1       — right UV coordinate [0.0 – 1.0] (float32)
+0x1C    4    V1       — bottom UV coordinate [0.0 – 1.0] (float32)
```

UV coordinates are normalized (0.0–1.0 relative to atlas dimensions). To get pixel coordinates:

```
pixelX0 = round(U0 * atlas.Width)
pixelY0 = round(V0 * atlas.Height)
pixelX1 = round(U1 * atlas.Width)
pixelY1 = round(V1 * atlas.Height)
```

### Sub-section: Anime

Placeholder sub-section read but not parsed. Structure is the standard 28-byte header followed by opaque payload; the parser reads `TotalSize` and skips.

---

## Section: ConvertInfo

A metadata-only section with a standard 28-byte header. No payload is parsed; it records conversion provenance (tool version, source asset path, etc.). The parser advances past it using `TotalSize`.

---

## Rendering Pipeline

The full rendering chain from a tick number to pixels:

```
tick
  │
  ▼  GetSequenceIndexAtTick(doc, tick)
sequenceIndex
  │
  ▼  doc.Sequences[sequenceIndex]
SequenceEntry { SpriteGroupIndex, Duration, Flags }
  │
  ▼  doc.Groups[SpriteGroupIndex]
SpriteGroup { SpriteIndices[] }
  │
  ▼  for each index: doc.Sprites[index]
SpriteEntry { PartsIndex, TextureIndex, PositionX, PositionY, ScaleX, ScaleY }
  │
  ▼  doc.Parts[PartsIndex]
SpranmPart { OffsetX, OffsetY, Width, Height, U0, V0, U1, V1 }
  │
  ▼  Compute src rect from UV × atlas dimensions
  ▼  Compute dest rect using bottom-right positioning formula
  │
  ▼  canvas.DrawBitmap(atlas, srcRect, destRect)
pixel output
```

Bounding box of all destination rectangles determines the output canvas size. Each `SpranmRenderer.RenderSequenceFrame` call produces one `SKBitmap`.

---

## Complete Section Header Table

| Section | Header bytes | EntryCount | Entry size | Notes |
|---|---|---|---|---|
| `Sequence` | 28 | yes | 20 bytes | 5 × uint32 |
| `Sprite` | 28 | yes | 32 bytes | 4 × uint32 + 3 × float32 + 1 × float32 unknown |
| `SpriteGp` | 28 | yes (group count) | variable | counts[] then indices[] |
| `TextureParts` | 24 | no | — | container for sub-sections |
| ↳ `Texture` | 40 | no | — | PNG or LZ77 at +0x28 |
| ↳ `Parts` | 28 | yes | 32 bytes | 8 × float32 |
| ↳ `Anime` | 28 | yes | opaque | skipped |
| `ConvertInfo` | 28 | yes | opaque | skipped |

---

## C# Data Model

```csharp
// Top-level document
public sealed class SpranmDocument {
    public List<SequenceEntry> Sequences { get; }
    public List<SpriteEntry>   Sprites   { get; }
    public List<SpriteGroup>   Groups    { get; }
    public List<SpranmPart>    Parts     { get; }
    public byte[]?             TexturePng     { get; }
    public int                 TextureWidth   { get; }
    public int                 TextureHeight  { get; }
    public int TotalFrames => Sequences.Sum(s => s.Duration);
}

public record SequenceEntry(int SpriteGroupIndex, int Duration, int Flags);
public record SpriteEntry(int PartsIndex, int TextureIndex,
                          int PositionX, int PositionY,
                          float ScaleX, float ScaleY);
public record SpriteGroup(int[] SpriteIndices);
public record SpranmPart(float OffsetX, float OffsetY,
                         float Width, float Height,
                         float U0, float V0, float U1, float V1);
```

---

## See Also

- [LZ77 Compression](lz77-compression) — FlagByte variant used for compressed SPRANM files
- [MPD Format](mpd-format) — uses the same `TextureParts` / `Parts` sub-section structures
