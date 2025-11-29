---
title: Technical Reference
layout: default
nav_order: 3
has_children: true
---

# Technical Reference
{: .no_toc }

Detailed documentation of DOKAPON! Sword of Fury's file formats and compression systems.
{: .fs-6 .fw-300 }

## Overview

This section contains reverse-engineered documentation of the game's proprietary file formats. These technical details are essential for creating modding tools and understanding how game assets work.

## File Formats

### [LZ77 Compression](lz77-compression)
The compression system used across multiple file formats in the game.
- Nintendo-style LZ77 variant
- 10-bit sliding window (1-1024 bytes)
- Block-based compression with markers

### [MDL Model Format](mdl-format)
3D model format used for characters, enemies, and objects.
- LZ77 compressed container
- PS2-style VIF commands for geometry
- Vertex, normal, and index data blocks
- Animation and transform sequences

### [SPRANM Sprite Animation Format](spranm-format)
Sprite animation format for 2D graphics and effects.
- Animation control files (compressed)
- Sprite resource files (with embedded PNG)
- Transform matrices and keyframe data
- State-based animation system

### [MPD Map/Cell Format](mpd-format)
Map and cell data format for game environments.
- Cell-based organization
- Index and data sections
- Dimension and alignment data

## Architecture Overview

```
Game Asset Pipeline
├── Raw Assets
│   ├── 3D Models (.mdl)
│   ├── 2D Sprites (.spranm)
│   ├── Map Data (.mpd)
│   └── Textures (.tex)
│
├── Compression Layer
│   └── LZ77 Compression
│       ├── 16-byte header
│       ├── Compressed stream
│       └── Block markers
│
└── Runtime Processing
    ├── Decompression
    ├── Block parsing
    └── GPU upload
```

## Common Patterns

### Block Markers

| Marker | Type | Description |
|--------|------|-------------|
| `0xAAAAAAAA` | Alignment | Block boundary/padding |
| `0x55555555` | Structure | Section structure marker |
| `0x0000C000` | Geometry | Vertex data block |
| `0x000040C1` | Normal | Normal vector data |
| `0x00004000` | Index | Triangle index data |
| `0x000080B9` | Animation | Animation frame data |
| `0xFFFFFFFF` | Data | Raw data block |
| `0x0000803F` | Float | Float value (1.0) |

### Data Alignment

Most data in these formats follows specific alignment rules:

- **4-byte alignment**: Standard for most integer and float data
- **12-byte stride**: Vertex and normal vectors (3× float32)
- **16-byte alignment**: Matrices and quaternions
- **2048-byte boundaries**: Major section divisions

## Tools Reference

The following tools work with these formats:

| Tool | Formats | Purpose |
|------|---------|---------|
| [Dokapon Extract](../tools/dokapon-extract) | .tex, .mpd, .spranm, .fnt | Extract and repack assets |
| [Image Extractor](../tools/image-extractor) | .fnt, .spranm | Extract embedded PNG images |
| [Text Extractor](../tools/text-extractor) | .exe | Extract and modify game text |

## Research Notes

{: .note }
This documentation is based on community reverse-engineering efforts. Some details may be incomplete or subject to revision as research continues.

## Contributing

Help improve this documentation:
- Submit corrections via pull request
- Share additional research findings
- Report inaccuracies in the format documentation
- Join our [Discord](https://discord.gg/HCrYwScDg5) to discuss research

