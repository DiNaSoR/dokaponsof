---
title: Technical Reference
layout: default
nav_order: 3
has_children: true
---

# Technical Reference
{: .no_toc }

Detailed documentation of DOKAPON! Sword of Fury file formats, discovered through reverse engineering.
{: .fs-6 .fw-300 }

## Overview

This section contains reverse-engineered documentation of the game's proprietary file formats. These technical details form the foundation of the C#/.NET 8 modding toolkit (`DokaponSoFTools`) and are essential for building tools, understanding asset pipelines, and creating mods.

All format implementations live in the `DokaponSoFTools.Core` library under the `DokaponSoFTools.Core.Formats` and `DokaponSoFTools.Core.Compression` namespaces.

## File Formats

### [LZ77 Compression](lz77-compression)
The compression layer used across multiple file formats. Three distinct variants exist in the game:
- **FlagByte** — flag-byte-per-8-tokens scheme; used for SPRANM and TEX files
- **TokenStream** — per-token bit-flag scheme; used for MDL model files
- **Cell** — separate flags/data streams with token count; used for MPD map files

All three share the same 16-byte `LZ77` magic header but are distinguished by their header field layout.

### [SPRANM Sprite Animation Format](spranm-format)
The sprite animation format for 2D graphics: character portraits, UI overlays, title screen elements, and effects.
- Two file variants: Self-contained (with embedded PNG) and Runtime/Player (no PNG, uses PartsColor)
- Optional LZ77 FlagByte compression layer
- Section-based structure: Sequence, Sprite, SpriteGp, TextureParts (with Texture/Parts/Anime sub-sections), ConvertInfo
- Rendering pipeline: Sequence → SpriteGroup → Sprite → Part → UV-mapped pixel region
- Bottom-right corner positioning model for sprite pieces

### [MPD Cell Map Format](mpd-format)
Map and environment data stored in a Cell container format.
- Cell container header with grid dimensions and record table
- LZ77 Cell variant compression (optional)
- Named chunk system: Map (cell grid), TextureParts (texture atlas + UV parts), Palette (indexed color tables)
- Cell records encode part index and rendering flags in three 32-bit values
- Map values index into the record table which indexes into the parts atlas

### [PCK Sound Archive](pck-format)
Binary sound archive used for all game audio.
- Two sections: Filename (name lookup) and Pack (data blocks)
- Ogg Opus audio (`OggS` magic = Opus codec)
- 16-byte-aligned sound data with 8-byte section alignment
- Four known archives: `BGM.pck`, `SE.pck`, `Voice.pck`, `Voice-en.pck`

### [Game Text Format](text-format)
UTF-8 text strings embedded in the game executable.
- Start marker `\p` (`0x5C 0x70`); end markers `\k`, `\z`, next `\p`, or null byte
- 15+ control codes for display control, paging, and special characters
- Format specifiers for variables (`%s`, `%d`), colors (`%Nc`), positioning (`%Nx`, `%Ny`), and button icons (`%NM`)
- Import uses `offset:maxlength` pairs; text is null-padded and never grown beyond `MaxLength`

### [TEX Texture Format](spranm-format#texture-sub-section)
Standalone texture container (also embedded inside SPRANM and MPD files as the `TextureParts` chunk).
- 40-byte header with flags and dimensions
- Storage: raw PNG bytes (`0x4000` flag) or LZ77-compressed indexed pixel data (`0x0080` flag)
- Followed by Parts and Anime sub-sections

### [HEX Patch Format](hex-format)
Binary patch files for modifying the game executable.
- Sequence of `[offset: int64 BE][size: int64 BE][data: N bytes]` records
- Tool performs conflict detection (same offset, overlapping ranges) before application
- Automatic backup creation; supports multi-file patch sets

## Asset Pipeline

```
Game Assets
├── Audio
│   └── PCK Archives (BGM.pck, SE.pck, Voice.pck, Voice-en.pck)
│       ├── Filename section  (name lookup)
│       └── Pack section      (Ogg Opus data, 16-byte aligned)
│
├── 2D Graphics
│   ├── SPRANM files          (sprites, UI, title screen)
│   │   ├── [optional] LZ77 FlagByte compression
│   │   ├── Sequence section  (animation frames)
│   │   ├── Sprite section    (piece placement)
│   │   ├── SpriteGp section  (frame → sprite set)
│   │   └── TextureParts      (PNG + UV parts)
│   └── MPD files             (map tiles, environments)
│       ├── [optional] LZ77 Cell compression
│       ├── Cell header       (grid dimensions)
│       ├── Record table      (tile → part mapping)
│       └── Chunks: Map, TextureParts, Palette
│
├── Text
│   └── Embedded in game EXE  (UTF-8, \p-delimited)
│
└── Binary Patches
    └── HEX files             (offset/size/data records)
```

## Common Structures

### LZ77 Header (16 bytes, shared magic)

All compressed files begin with `LZ77` (`0x4C5A3737`). The interpretation of bytes `0x04–0x0F` differs by variant — see [LZ77 Compression](lz77-compression) for details.

### Section Header Pattern

SPRANM sections and PCK sections both use a fixed ASCII name padded to 20 bytes followed by a 32-bit size field. This pattern appears throughout the engine's asset formats.

### 8-byte Alignment

Section boundaries throughout SPRANM and PCK files are aligned to 8-byte boundaries with zero padding.

## Tools Reference

| Tool / Feature | Formats | C# Class |
|---|---|---|
| Asset Extractor | .spranm, .mpd, .tex, .fnt | `AssetExtractor` |
| Map Explorer | .mpd | `MapRenderer`, `CellContainer` |
| Animation Viewer | .spranm | `SpranmDocument`, `SpranmRenderer` |
| Voice Tools | .pck | `PckArchive` |
| Text Tools | game exe | `GameText` |
| Hex Editor | .hex + exe | `HexPatch` |

## Research Notes

{: .note }
This documentation is based on community reverse-engineering efforts combined with implementation experience from the C#/.NET 8 rewrite of the toolkit. Some edge cases and file variants may not be fully documented. Join our [Discord](https://discord.gg/HCrYwScDg5) to discuss ongoing research.
