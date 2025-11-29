---
title: SPRANM Format
layout: default
nav_order: 3
parent: Technical Reference
---

# SPRANM Sprite Animation Format
{: .no_toc }

Documentation of the sprite animation format used in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

SPRANM files contain 2D sprite animations used for characters, effects, UI elements, and title screens. The format supports:
- Animation control sequences
- Embedded PNG textures
- Transform matrices
- Keyframe-based animation
- State machine control

## File Type Variants

SPRANM files come in two distinct formats:

### Type A: Animation Control Files

Compressed files containing animation logic only:
- Uses LZ77 compression
- Small file size (5-13 KB)
- No embedded PNG data
- Contains timing and transform data
- Examples: `CSFIX_00.spranm`, `CSFIX_01.spranm`, `CSFIX_03.spranm`

### Type B: Sprite Resource Files

Uncompressed files with embedded sprites:
- No compression
- Larger file size (43-550 KB)
- Contains embedded PNG image
- Includes sprite sheet definitions
- Examples: `CSFIX_04.spranm`, `TRS001_00.spranm`

## Format Detection

```python
def detect_spranm_type(data: bytes) -> str:
    """Detect SPRANM file type."""
    if data[:4] == b'LZ77':
        return 'animation_control'  # Type A
    elif data[:8] == b'Sequence':
        return 'sprite_resource'    # Type B
    return 'unknown'
```

## Type A: Animation Control Format

### LZ77 Header

```
Offset  Size  Description
------  ----  -----------
0x00    4     Magic: "LZ77"
0x04    4     Flags (e.g., 0xc83a0000)
0x08    4     Compressed size (little-endian)
0x0C    4     Decompressed size (little-endian)
0x10    var   Compressed data
```

### Decompressed Structure

After decompression, the data contains control sections:

#### Control Section Types

| Byte | Type | Description |
|------|------|-------------|
| 0x80 | sprite_flags | Animation behavior control |
| 0x40 | transform_matrix | 2D transformation data |
| 0x20 | sprite_state | Sprite property control |
| 0x04 | sprite_index | References to sprite resources |

### Sprite Flags (0x80)

```c
struct SpriteFlags {
    uint8_t marker;        // 0x80
    uint8_t loop : 1;      // Enable looping animation
    uint8_t reverse : 1;   // Play animation in reverse
    uint8_t pingpong : 1;  // Play animation back and forth
    uint8_t reserved : 5;  // Additional flags
    uint32_t extra_flags;  // Extended flag data
};
```

### Transform Matrix (0x40)

```c
struct TransformMatrix {
    uint8_t marker;     // 0x40
    float scale_x;      // Horizontal scaling factor
    float scale_y;      // Vertical scaling factor
    float translate_x;  // Horizontal translation
    float translate_y;  // Vertical translation
};
```

### Sprite State (0x20)

```c
struct SpriteState {
    uint8_t marker;      // 0x20
    uint8_t visible : 1; // Sprite visibility flag
    uint8_t flip_x : 1;  // Horizontal flip flag
    uint8_t flip_y : 1;  // Vertical flip flag
    uint8_t active : 1;  // Sprite active state
    uint8_t reserved : 4;
    uint32_t state_flags;
};
```

### Example Control File

CSFIX_00.spranm:
```
Compressed size: 11,013 bytes
Decompressed size: 1,406 bytes
Control sections: 40+
Contains: transformations, state changes
```

## Type B: Sprite Resource Format

### Section Layout

```
Offset      Section         Description
------      -------         -----------
0x000       Sequence        Animation properties header
0x030-0xBF  Sprite          Transformation matrices
0x0C0-0x1DF Sprite Data     Sprite properties
0x1E0-0x23F SpriteGp        Sprite grouping
0x240+      TextureParts    Texture region definitions
varies      PNG Data        Embedded PNG image
after PNG   Parts           Part definitions
after Parts Anime           Animation keyframes
end         ConvertInfo     Format conversion data
```

### Sequence Header

```c
struct SequenceHeader {
    char magic[8];      // "Sequence"
    uint32_t version;   // Format version
    uint32_t flags;     // Sequence flags
    float duration;     // Total animation duration
    uint32_t frame_count;
    // ... additional fields
};
```

### TextureParts Section

Defines regions within the sprite sheet:

```c
struct TexturePart {
    uint16_t x;         // X position in texture
    uint16_t y;         // Y position in texture
    uint16_t width;     // Part width
    uint16_t height;    // Part height
    uint16_t pivot_x;   // Pivot point X
    uint16_t pivot_y;   // Pivot point Y
};
```

### PNG Data

The PNG is embedded directly:
```
[PNG header: 89 50 4E 47 0D 0A 1A 0A]
[PNG chunks...]
[IEND chunk]
```

Example sizes:
- CSFIX_04.spranm: PNG at 0x280, 42,750 bytes
- TRS001_00.spranm: PNG at 0xD8, larger image

## Animation System

### Keyframe Structure

```c
struct Keyframe {
    uint8_t index;      // Animation state (0-2)
    uint8_t flags;      // Control flags
    uint16_t reserved;  // Usually 0
    float duration;     // Time in frames/units
};
```

### State System

| Index | State | Description |
|-------|-------|-------------|
| 0 | Base | Default state |
| 1 | Transition | Between states |
| 2 | Special | Effect state |

### Control Flags

| Flag | Value | Description |
|------|-------|-------------|
| Standard | 0x00 | Normal keyframe |
| Wait | 0x01 | Wait for completion |
| Sync | 0x02 | Synchronize with others |
| Ping-pong | 0x20 | Enable ping-pong |
| Reverse | 0x40 | Enable reverse |
| Loop | 0x80 | Enable looping |

## Transform Matrices

### Matrix Types

#### Type A: Basic Transform
```
[0.0-1.0, 0.0, 100-1000, 0.0]
Purpose: Basic element positioning
```

#### Type B: Scale Effect
```
[988416.3, -2.11e+35, -2.00e-12, 2.41e+32]
Purpose: Dramatic scaling effects
```

#### Type C: Rotation Control
```
[-18152450.0, 0.4, 9.00e-24, -9.07]
Purpose: Element rotation with scaling
```

#### Type D: Complex Movement
```
[-7.11e-07, 79210504.0, 7.68e-38, 0.127]
Purpose: Combined transform effects
```

## Animation Sequence Flow

### Title Screen Example

```
Phase 1: Initialization
├── Sequence 0: Initial translation (768.2 units)
├── Setup base state
└── Duration: 2.25 units

Phase 2: Element Introduction (1-33)
├── Control blocks
├── Position elements
├── Set initial states
└── Prepare for main animation

Phase 3: Main Animation (34-54)
├── Multiple transform matrices
├── State transitions
├── Timing control
└── Special effects

Phase 4: Finalization (55)
├── Final positions
├── State stabilization
└── Animation completion
```

## Memory Layout

### Block Alignment

```
16-byte alignment: Matrices
4-byte alignment:  Keyframes
2048-byte boundaries: Major sections
```

### Data Access Pattern

```
Block Header (4 bytes)
    ↓
Transform Data (16-64 bytes)
    ↓
Keyframe Data (variable)
    ↓
Padding (alignment)
```

## Timing System

### Duration Control

| Type | Duration | Description |
|------|----------|-------------|
| Quick | 0.0 | Instant transition |
| Standard | 1.0-2.25 | Normal movement |
| Hold | Large value | Static state |
| Loop | Negative | Infinite loop |

### Synchronization

```python
# Wait flag (0x01)
keyframe.flags & 0x01  # Wait for completion

# Sync flag (0x02)
keyframe.flags & 0x02  # Sync with other animations
```

## Extraction Implementation

### Type A Extraction

```python
def extract_animation_control(data: bytes) -> dict:
    """Extract animation control data."""
    if data[:4] != b'LZ77':
        raise ValueError("Not compressed SPRANM")
    
    # Decompress
    decompressed = decompress_lz77(data)
    
    # Parse control sections
    sections = []
    pos = 0
    while pos < len(decompressed):
        marker = decompressed[pos]
        if marker == 0x80:
            sections.append(parse_sprite_flags(decompressed, pos))
        elif marker == 0x40:
            sections.append(parse_transform_matrix(decompressed, pos))
        elif marker == 0x20:
            sections.append(parse_sprite_state(decompressed, pos))
        elif marker == 0x04:
            sections.append(parse_sprite_index(decompressed, pos))
        pos += 1
    
    return {'sections': sections}
```

### Type B Extraction

```python
def extract_sprite_resource(data: bytes) -> dict:
    """Extract sprite resource file."""
    result = {
        'sequence': None,
        'sprites': [],
        'groups': [],
        'texture_parts': [],
        'png_data': None,
        'animations': []
    }
    
    # Find and extract PNG
    png_start = data.find(b'\x89PNG\r\n\x1a\n')
    if png_start >= 0:
        png_end = find_png_end(data, png_start)
        result['png_data'] = data[png_start:png_end]
    
    # Parse sections
    result['sequence'] = parse_sequence_header(data)
    # ... parse other sections
    
    return result
```

## File Examples

### Animation Control Files

| File | Compressed | Decompressed | Sections |
|------|------------|--------------|----------|
| CSFIX_00 | 11,013 | 1,406 | 40+ |
| CSFIX_01 | 5,789 | 740 | Fewer |
| CSFIX_03 | 7,161 | 912 | Mixed |

### Sprite Resource Files

| File | Size | PNG Size | Sections |
|------|------|----------|----------|
| CSFIX_04 | ~43 KB | 42,750 | Full |
| TRS001_00 | ~550 KB | Large | Compact |

## Relationship Between Files

```
Animation System
├── Control Files (Type A)
│   ├── Define HOW sprites animate
│   ├── Transform sequences
│   ├── Timing data
│   └── State machine
│
└── Resource Files (Type B)
    ├── Define WHAT sprites look like
    ├── PNG sprite sheets
    ├── Texture coordinates
    └── Part definitions
```

Control files reference resource files via `sprite_index` (0x04) sections.

## Usage in Game

### Element Types
- Logo components
- Menu items
- Background elements
- Special effects

### Animation Categories
- Entry animations
- Idle movements
- Interactive responses
- Transition effects

## Implementation Notes

### PNG Extraction

```python
def extract_png(data: bytes, offset: int) -> bytes:
    """Extract embedded PNG from SPRANM."""
    # Find PNG signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    start = data.find(png_sig, offset)
    
    if start < 0:
        return None
    
    # Find IEND chunk
    iend = data.find(b'IEND', start)
    if iend < 0:
        return None
    
    # IEND chunk is 12 bytes (4 length + 4 type + 4 CRC)
    end = iend + 12
    
    return data[start:end]
```

### Metadata Generation

```python
def generate_metadata(spranm_data: bytes, output_path: str):
    """Generate JSON metadata for SPRANM file."""
    metadata = {
        'type': detect_spranm_type(spranm_data),
        'sections': [],
        'transforms': [],
        'keyframes': []
    }
    
    # ... parse and populate
    
    with open(output_path, 'w') as f:
        json.dump(metadata, f, indent=2)
```

## Research Status

{: .note }
> The SPRANM format documentation covers the main structural elements. Some areas need additional research:
> - Complete section enumeration for all file variants
> - Animation interpolation algorithms
> - Full transform matrix interpretation
> - Palette handling for indexed sprites

## See Also

- [LZ77 Compression](lz77-compression) - Compression format for Type A files
- [Image Extractor](../tools/image-extractor) - Tool for PNG extraction
- [Dokapon Extract](../tools/dokapon-extract) - General asset extraction

