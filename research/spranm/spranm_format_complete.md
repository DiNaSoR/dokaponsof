# SPRANM Sprite Animation Format — Complete Reference

> Last updated: 2026-03-16
> Based on static analysis, runtime Frida tracing, and empirical testing

## Overview

`.spranm` files are the game's sprite animation format. They exist in two variants:

- **Self-contained** (resource files): Start with `Sequence`, contain embedded PNG atlas
- **Runtime/Player** (control files): LZ77-compressed, no embedded PNG, use `PartsColor`

## File Structure

### LZ77 Compression Layer

Files starting with `LZ77` are compressed. 16-byte header:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Magic: `"LZ77"` |
| 0x04 | 4 | Flags/checksum |
| 0x08 | 4 | Decompressed size |
| 0x0C | 4 | Uncompressed offset (tail data position) |

Compressed data: `[0x10, uncompressed_offset)` — FlagByte LZ77
Tail data: `[uncompressed_offset, EOF)` — appended raw to output

### Section Header Format (Standard: 28 bytes)

All sections use this header:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 20 | Section name (ASCII, space-padded) |
| 0x14 | 4 | Total section size (includes header) |
| 0x18 | 4 | Entry count |

**Exception:** `TextureParts` uses a 24-byte header (no entry count field).

Sections are 8-byte aligned with zero padding between them.

## Sections (in order)

### 1. Sequence

Animation keyframe timeline. Entry size: **20 bytes** (5 × uint32 LE)

| Field | Type | Description |
|-------|------|-------------|
| SpriteGroupIndex | uint32 | Index into SpriteGp section |
| Duration | uint32 | Ticks to display this keyframe |
| Flags | uint32 | 0x1=loop marker, 0x2=transition |
| Unknown1 | uint32 | Always 0 |
| Unknown2 | uint32 | Always 0 |

### 2. Sprite

Individual sprite piece definitions. Entry size: **32 bytes**

| Offset | Size | Type | Description |
|--------|------|------|-------------|
| 0 | 4 | uint32 | PartsIndex — references Parts entry |
| 4 | 4 | uint32 | Unknown (always 0) |
| 8 | 4 | uint32 | TextureIndex (0xFFFFFFFF = use PartsIndex lookup) |
| 12 | 4 | int32 | **PositionX** — BOTTOM-RIGHT corner X |
| 16 | 4 | int32 | **PositionY** — BOTTOM-RIGHT corner Y |
| 20 | 4 | float32 | ScaleX |
| 24 | 4 | float32 | ScaleY |
| 28 | 4 | float32 | Unknown (always 0.0) |

### CRITICAL: Position Interpretation

**Position values are the BOTTOM-RIGHT corner of each sprite piece.**

To get the top-left corner for rendering:
```
topLeftX = PositionX - (Part.Width * ScaleX)
topLeftY = PositionY - (Part.Height * ScaleY)
```

This was verified empirically:
```
H_FACE02A_00.spranm, Group 0:
  Sprite[0] (body 288x288): pos=(144,282)  → X range [-144, 144], center=0
  Sprite[4] (face 96x72):   pos=(48,210)   → X range [-48, 48],   center=0
  → Face perfectly centered in body ✓
```

### 3. SpriteGp (Sprite Groups)

Variable-length section defining which sprites compose each animation frame.

**Layout:**
1. First `entryCount × 4` bytes: Array of uint32 sprite counts per group
2. Remaining bytes: Flattened array of uint32 sprite indices

Example (B_MG.spranm, 7 groups):
- Group 0: 2 sprites [0, 1]
- Group 1: 2 sprites [2, 3]
- Group 2: 5 sprites [4, 5, 6, 7, 8]

### 4. TextureParts (Container)

**24-byte header** (NOT the standard 28-byte header):

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 20 | Name: `"TextureParts"` |
| 0x14 | 4 | Total container size |

Contains sub-sections:

#### 4a. Texture Sub-Section

40-byte header:

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 20 | Name: `"Texture"` |
| 0x14 | 4 | Total Texture size |
| 0x18 | 4 | Flags: **0x4000 = PNG**, **0x0080 = indexed/LZ77** |
| 0x1C | 4 | Kind (e.g., 0x08100001 for PNG, 0x02100000 for indexed) |
| 0x20 | 4 | Nested data size (PNG/pixel data length) |
| 0x24 | 2 | Width (LE uint16) |
| 0x26 | 2 | Height (LE uint16) |

Image data at offset 0x28:
- If flags contain 0x4000: raw PNG data (starts with `89 50 4E 47`)
- If flags contain 0x0080: LZ77-compressed indexed pixel data

**Confirmed via Frida runtime tracing** against the running game EXE.

#### 4b. Parts Sub-Section

Standard 28-byte header. Entry size: **32 bytes** (8 × float32)

| Field | Type | Description |
|-------|------|-------------|
| OffsetX | float32 | X offset for placement (usually 0.0) |
| OffsetY | float32 | Y offset for placement (usually 0.0) |
| Width | float32 | Display width in pixels |
| Height | float32 | Display height in pixels |
| U0 | float32 | Texture UV left (0.0-1.0) |
| V0 | float32 | Texture UV top (0.0-1.0) |
| U1 | float32 | Texture UV right (0.0-1.0) |
| V1 | float32 | Texture UV bottom (0.0-1.0) |

Pixel coordinates: `srcX = U0 × textureWidth`, `srcY = V0 × textureHeight`

#### 4c. Anime Sub-Section

Standard 28-byte header. Usually empty/placeholder (totalSize = 0x1C).

### 5. ConvertInfo

Standard 28-byte header. Metadata section (header-only, minimal body).

## File Variants

### Self-Contained (H_FACE*, CSFIX*, INTROPI*, NEW_TITLE*)

- Start with `Sequence` (uncompressed)
- Contain: Sequence + Sprite + SpriteGp + TextureParts(Texture+Parts+Anime) + ConvertInfo
- Texture has embedded PNG (flags 0x4000)
- Can be rendered standalone

### Runtime/Player (F_C_*, PL_DMG*)

- Start with `LZ77` (compressed)
- After decompression: binary pre-header before named sections
- Have `PartsColor` section (not plain `Parts`)
- NO embedded PNG, NO Anime, NO ConvertInfo
- A/B file pairs: A = timeline carrier, B = supplemental layout
- Player texture resolved at runtime by the game engine
- Cannot be rendered standalone without external texture binding

## EXE Integration

From reverse engineering the game executable:

- Internal framework: **dkit / DKFramework**
- Loader: "Load Anime Model Thread" (background loading)
- Renderer: Direct3D 11 with textured quads
- PDB path: `C:\usr\project\dkit\git\Program\Project\Windows\WindowsMain\x64\Final\WindowsMain.pdb`
- Section name copy function at EXE+0x43720
- Parts parser xrefs at EXE+0x167C4A and EXE+0x17502A
- Steam App ID: 3077020

## Rendering Pipeline

```
1. Load file → decompress LZ77 if needed
2. Parse sections sequentially (28-byte headers, 8-byte aligned)
3. Handle TextureParts container (24-byte header exception)
4. Decode embedded PNG atlas from Texture sub-section
5. For each Sequence entry:
   a. Get SpriteGroup → list of sprite indices
   b. For each Sprite:
      - Get Parts entry (UV coords → source rect from atlas)
      - Calculate dest rect: topLeft = (posX - width, posY - height)
      - Draw atlas region at dest position with scale
6. Composite all sprites in group order (back to front)
7. Advance tick counter, loop at TotalFrames
```
