---
title: MDL Model Format
layout: default
nav_order: 2
parent: Technical Reference
---

# MDL Model Format
{: .no_toc }

Documentation of the 3D model format used in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

MDL files contain 3D model data for characters, enemies, and objects. The format features:
- LZ77 compression layer
- PS2-style VIF commands for geometry
- Block-based data organization
- Support for skeletal animation

## File Structure

```
MDL File Layout
├── LZ77 Header (16 bytes)
│   ├── Magic: "LZ77"
│   ├── Decompressed size
│   ├── Flag1
│   └── Flag2
├── Compressed Data Stream
│   └── Block sequence with markers
└── Trailing Data (34-36 KB)
    └── Additional metadata
```

## LZ77 Container

MDL files are wrapped in [LZ77 compression](lz77-compression):

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 4 | Magic `"LZ77"` |
| 0x04 | 4 | Decompressed size (little-endian) |
| 0x08 | 4 | Flag1 - Window configuration |
| 0x0C | 4 | Flag2 - Block type flags |
| 0x10 | var | Compressed data stream |

### Example Header

```
E000.mdl:
  Compressed size: 146,424 bytes
  Decompressed size: 649,400 bytes
  Flags: 0x000182B5, 0x00003067
```

## Decompressed Data Structure

After decompression, the data contains geometry organized by block markers:

### Block Type Markers

| Marker (hex) | Type | Data Format | Alignment |
|-------------|------|-------------|-----------|
| `0x0000C000` | Vertex | 3× float32 (X, Y, Z) | 12 bytes |
| `0x000040C1` | Normal | 3× float32 (nX, nY, nZ) | 12 bytes |
| `0x00004000` | Index | uint16 triangle indices | 2 bytes |
| `0x000080B9` | Frame | Animation frame data | 52 bytes |
| `0x3F800000` | Float | float32 value (1.0) | 4 bytes |
| `0xAAAAAAAA` | Align | Alignment padding | 16 bytes |
| `0x55555555` | Structure | Section marker | variable |
| `0x000080BA` | Transform | 4×4 matrix row | 16 bytes |
| `0x000040C2` | Tangent | 3× float32 | 12 bytes |
| `0x3F000000` | Weight | float32 blend weight | 4 bytes |
| `0x3E800000` | Scale | float32 scale factor | 4 bytes |
| `0x3F400000` | Rotation | Quaternion | 16 bytes |
| `0x3FC00000` | Position | 3× float32 | 12 bytes |

## Geometry Data

### Vertex Format

Vertex data follows the `0x0000C000` marker:

```c
struct Vertex {
    float x;    // X coordinate
    float y;    // Y coordinate
    float z;    // Z coordinate
};
```

### Normal Format

Normal vectors follow the `0x000040C1` marker:

```c
struct Normal {
    float nx;   // Normalized X
    float ny;   // Normalized Y
    float nz;   // Normalized Z
};
```

### Index Format

Triangle indices follow the `0x00004000` marker:

```c
// Triangle strip/list indices
uint16_t indices[];  // Groups of 3 for triangles
```

### Vertex Data Layout

Vertex data appears in clusters:
```
Decompressed MDL Structure (E000.mdl, 649,400 bytes):
0x000000 - 0x00266B: Header/metadata (277 verts block)
0x00266C - 0x07C3EB: Bone/animation data
0x07C3EC - 0x09A007: Vertex data blocks (22 blocks, 4254 vertices total)
  - 0x07E34E: 225 verts
  - 0x08234C: 230 verts
  - 0x08A34C: 269 verts (largest)
0x09A008+: Final vertex block + index data
```

## PS2-Style VIF Commands

The MDL format uses PS2-style VIF (Vector Interface) commands:

| VIF Code | Name | Hits | Purpose |
|----------|------|------|---------|
| 0x6C | UNPACK V3-32 | 2,387 | 3× 32-bit floats (vertex positions) |
| 0x6F | UNPACK V3-16 | 1,001 | 3× 16-bit shorts (compressed pos/normals) |
| 0x6D | UNPACK V4-32 | 555 | 4× 32-bit floats (colors/weights) |
| 0x61 | UNPACK V4-8 | 336 | 4× 8-bit bytes (colors) |
| 0x68 | UNPACK V2-32 | 1,184 | 2× 32-bit floats (UVs) |

## Packed Vertex Formats

### 16-bit Packed Positions

Found throughout vertex data:
- Scale factor: 100 (raw value / 100.0 = coordinate)
- Format: 3× int16 per vertex
- Bounds: typically 0-200 units after scaling

```python
def unpack_int16_vertex(raw):
    x = struct.unpack('<h', raw[0:2])[0] / 100.0
    y = struct.unpack('<h', raw[2:4])[0] / 100.0
    z = struct.unpack('<h', raw[4:6])[0] / 100.0
    return (x, y, z)
```

### 8-bit Packed Normals

Normalized to -1.0 to 1.0 range:
```python
def unpack_int8_normal(raw):
    nx = (raw[0] - 128) / 127.0
    ny = (raw[1] - 128) / 127.0
    nz = (raw[2] - 128) / 127.0
    return (nx, ny, nz)
```

## Animation Data

### Frame Structure

Animation frames (52 bytes each) follow `0x000080B9`:

```c
struct AnimationFrame {
    float time;              // 4 bytes - Frame time
    float transform[12];     // 48 bytes - Transform data
};
```

### Transform Sequences

Common animation patterns:
```
Geometry sequence: vertex → normal → tangent → index
Animation sequence: position → rotation → scale → frame
Transform sequence: transform → position → rotation
```

## Mesh Extraction Results

Analysis of E000.mdl (enemy model):

| Metric | Raw | Filtered |
|--------|-----|----------|
| Vertices | 8,031 | 7,268 |
| Triangles | 4,574 | 1,261 |
| Vertex format | int16 packed | scale=100 |
| Coordinate range | 0-200 units | X, Y, Z |

### Block Distribution

Example file analysis:
```
E000.mdl (Small Monster):
  - 319 float_data blocks
  - 5 geometry blocks
  - High normal data density
  - No animation blocks
  - Block alignment: 2048-byte boundaries

E002.mdl (Large Monster):
  - 178 float_data blocks
  - 4 geometry blocks
  - Sparse normal data
  - 1 animation block sequence
```

## Runtime Loading Pipeline

The game loads MDL files through this pipeline:

```
MDL file (LZ77 compressed)
    ↓ fcn.00522920 (decompress)
Decompressed data with block markers
    ↓ fcn.00178be0 (type dispatcher)
Type-specific processing
    ↓ fcn.00179f00/fcn.001806e0
Buffer setup with vtables
    ↓ fcn.0017a290/fcn.001823a0
5-dword key preparation
    ↓ fcn.001827f0 (loader)
Record matching → payload pointer
    ↓
GPU buffers (vertex/index/normal)
```

### Type Selector Function

The loader dispatches based on block type:
- `esi ≤ 0x0D`: Uses table at `0x6C4348`
- `esi ∈ [0x0E, 0x3E]`: Uses table at `0x6C4368`
- `esi ∈ [0x3F, 0x48]`: Uses table at `0x6C4358`
- `esi ∈ [0x49, 0x4A]`: Uses table at `0x6C4380`

### Record Table Layout

- Record count: 20 (0x14 iterations)
- Record stride: 0x400 bytes apart
- Record layout:
  - `+0x00` to `+0x13`: Five dwords (match key)
  - `+0x14`: Size/length field
  - `+0x18`: Pointer to payload buffer
  - `+0x1C`: Total header size

## Extraction Tools

### Available Scripts

| Tool | Purpose |
|------|---------|
| `lz77_decompressor.py` | Decompress MDL files |
| `mdl_geometry.py` | Extract geometry data |
| `build_mesh.py` | Build complete mesh with vertices + triangles |
| `filter_mesh.py` | Remove zero vertices and degenerate faces |
| `find_vertex_runs.py` | Find float32 vertex sequences |
| `find_short_verts.py` | Find int16 packed vertices |
| `find_indices.py` | Find triangle index sequences |

### Usage Example

```bash
# Decompress MDL file
python lz77_decompressor.py E000.mdl E000_decompressed.bin

# Extract geometry
python mdl_geometry.py E000.mdl

# Build mesh (outputs OBJ)
python build_mesh.py E000_decompressed.bin E000_mesh.obj
```

## Exported File Formats

### OBJ Export

The tools can export to Wavefront OBJ:

```obj
# E000.mdl - Extracted mesh
# Vertices: 7268
# Faces: 1261

v 0.08 0.16 0.24
v 1.20 3.45 6.78
...
f 1 2 3
f 4 5 6
...
```

### Output Files

| File | Description |
|------|-------------|
| `E000_mesh_full.obj` | Complete mesh: 8,031 vertices, 4,574 triangles |
| `E000_filtered.obj` | Filtered: 7,268 vertices, 1,261 triangles |
| `E000_full_points.obj` | Point cloud: 1,580 unique vertices |

## Enemy Model Analysis

### Model Characteristics

| Model | Vertices | Indices | Normals | Animation |
|-------|----------|---------|---------|-----------|
| E000.mdl | 54 | 11,881 | 537 | No |
| E002.mdl | 590 | 985 | Sparse | Yes |

### Geometry Structure

E000.mdl (Small Monster):
- Highly symmetrical
- Efficient topology (4068 faces from 53 vertices)
- Uses long triangle strips (8566 triangles)
- Detailed normals (298)

E002.mdl (Large Monster):
- Less symmetrical
- More complex geometry (590 vertices)
- Uses shorter triangle strips (983 triangles)
- Has animation data

## Known Issues

### Decompression Accuracy

- Current tools achieve ~100% accuracy for declared file sizes
- Some geometry sections may contain padding/garbage data
- Post-decompression processing may be required for full extraction

### Data Quality

The decompressed MDL contains:
- Zero padding (large regions)
- Repeated patterns (`0x47474747`)
- Structure markers (`0x23232323`)

This suggests alignment requirements and possible secondary encoding.

## Research Status

{: .warning }
> Some aspects of the MDL format remain under investigation:
> - Post-decompression transforms
> - Full VIF command parsing
> - Animation interpolation details
> - Bone hierarchy reconstruction

## See Also

- [LZ77 Compression](lz77-compression) - Compression format details
- [SPRANM Format](spranm-format) - 2D animation format
- [Dokapon Extract](../tools/dokapon-extract) - Asset extraction tool

