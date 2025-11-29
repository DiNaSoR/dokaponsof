---
title: MPD Format
layout: default
nav_order: 4
parent: Technical Reference
---

# MPD Map/Cell Format
{: .no_toc }

Documentation of the map and cell data format used in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

MPD files contain map data and cell-based graphics used for game environments, UI elements, and other grid-based content. The format features:
- Cell-based organization
- Index and data sections
- Support for both compressed and uncompressed data
- Dimension and alignment metadata

## File Types

MPD files serve different purposes:

| Type | Description | Example |
|------|-------------|---------|
| Resource Index | Table of resource references | CREDIT.mpd |
| Sprite Container | Cell-based sprite data | S_TIT00_00.mpd |
| Map Data | Game map information | Various map files |

## Header Structure

### Cell Header Format

```c
struct MPDHeader {
    char magic[16];      // "Cell" + padding
    uint32_t data_size;  // Size of data section
    uint32_t width;      // Image/grid width
    uint32_t height;     // Image/grid height
    uint32_t cell_width; // Width of each cell
    uint32_t cell_height;// Height of each cell
};
```

### Example Header (CREDIT.mpd)

```hex
00000000  43 65 6C 6C 20 20 20 20 20 20 20 20 20 20 20 20  Cell            
00000010  20 20 20 20 A0 04 00 00 60 00 00 00 60 00 60 00      ...`...`.`.
```

Interpretation:
- Magic: `"Cell"` (padded to 16 bytes)
- Data size: `0x04A0` (1184 bytes)
- Width: `0x60` (96 pixels)
- Height: `0x60` (96 pixels)

## Index Section

Following the header, an index table defines entries:

### Index Record Format

```c
struct IndexRecord {
    uint16_t marker;     // 0xFFFF separator
    uint16_t id;         // Entry ID
    uint8_t type;        // Record type (usually 0x01)
    uint8_t reserved[7]; // Padding
};
```

### Example Index Data

```hex
00 00 FF FF 01 00 00 00 00 00 00 00
00 00 FF FF 02 00 00 00 00 00 00 00
00 00 FF FF 03 00 00 00 00 00 00 00
```

Pattern:
- `FF FF` markers between entries
- Sequential IDs
- Fixed 12-byte record stride

## Data Section

### Cell Data Organization

Cell data follows the index section:

```
[Index Section End]
    ↓
[Cell Data Block 0]
[Cell Data Block 1]
[Cell Data Block 2]
    ...
[Cell Data Block N]
```

### Data Characteristics

- High entropy (compressed/encoded content)
- No `FF FF` markers in data section
- Binary data (possibly texture or tilemap)

## S_TIT Format Variant

Sprite title files (S_TIT*) use a different structure:

### S_TIT Header

```hex
00000000  00 00 00 00 00 00 00 00 00 00 35 55 55 55 55 55  ..........5UUUUU
00000010  55 00 00 00 00 03 00 00 00 00 00 00 00 44 00 00  U............D..
```

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 10 | Zero padding |
| 0x0A | 7 | Magic: `35 55 55 55 55 55 55` |
| 0x12 | 4 | Version/type (e.g., `03 00 00 00`) |
| 0x1D | 4 | Data offset (e.g., `44 00 00`) |

### S_TIT Field Layout

```c
struct STITHeader {
    uint8_t padding[10];      // Zero padding
    uint8_t magic[7];         // 35 55 55... magic
    uint32_t version;         // Format version
    uint32_t data_offset;     // Offset to data section
    uint32_t width;           // Width or block size
    uint16_t height;          // Height or count
    uint16_t stride;          // Stride or alignment
    uint32_t palette_offset;  // Palette data offset
};
```

### Palette Information

16-color palette example:
```
Color 0:  Black (0,0,0) - Background
Color 2:  Dark Blue (0,0,136)
Color 5:  Red (128,0,0)
Color 8:  Very Dark Blue (0,0,16)
Color 9:  Blue (0,0,56)
Color 12: Bright Red (192,0,0)
Color 13: Brown (32,8,0)
```

## Data Alignment

MPD files use specific alignment patterns:

| Alignment | Purpose |
|-----------|---------|
| 4 bytes | Standard integer data |
| 16 bytes | Block boundaries |
| Power of 2 | Memory/cache optimization |

## Extraction Strategy

### Header Parsing

```python
class MPDHeader:
    def __init__(self, data: bytes):
        self.magic = data[0:16].rstrip(b' \x00')
        self.data_size = struct.unpack('<I', data[16:20])[0]
        self.width = struct.unpack('<I', data[20:24])[0]
        self.height = struct.unpack('<I', data[24:28])[0]
        
        if len(data) >= 32:
            self.cell_width = struct.unpack('<I', data[28:32])[0]
            self.cell_height = struct.unpack('<I', data[32:36])[0]
```

### Index Parsing

```python
def parse_index_records(data: bytes, start: int) -> list:
    """Parse index records from MPD file."""
    records = []
    pos = start
    
    while pos + 12 <= len(data):
        marker = struct.unpack('<H', data[pos:pos+2])[0]
        if marker == 0:
            # Check for FF FF marker
            if data[pos+2:pos+4] == b'\xFF\xFF':
                record_id = struct.unpack('<H', data[pos+4:pos+6])[0]
                record_type = data[pos+6]
                records.append({
                    'id': record_id,
                    'type': record_type,
                    'offset': pos
                })
        pos += 12
    
    return records
```

### Data Extraction

```python
def extract_cell_data(data: bytes, header: MPDHeader, index: list) -> list:
    """Extract individual cell data blocks."""
    cells = []
    data_start = header_size + (len(index) * 12)
    
    for i, record in enumerate(index):
        # Calculate cell boundaries
        cell_size = header.cell_width * header.cell_height
        cell_start = data_start + (i * cell_size)
        cell_end = cell_start + cell_size
        
        cells.append(data[cell_start:cell_end])
    
    return cells
```

## Image Processing

### Planar vs Linear Format

Some MPD files use different pixel organizations:

#### Planar Format
```python
def decode_planar(data: bytes, width: int, height: int) -> bytes:
    """Decode planar pixel data."""
    output = bytearray(width * height)
    plane_size = (width * height) // 8
    
    for plane in range(8):
        for i in range(plane_size):
            byte = data[plane * plane_size + i]
            for bit in range(8):
                if byte & (1 << (7 - bit)):
                    pixel_idx = i * 8 + bit
                    output[pixel_idx] |= (1 << plane)
    
    return bytes(output)
```

#### Linear Format
```python
def decode_linear(data: bytes, width: int, height: int) -> bytes:
    """Decode linear pixel data."""
    return data[:width * height]
```

### Color Conversion

```python
def apply_palette(pixel_data: bytes, palette: list) -> bytes:
    """Convert indexed pixels to RGB."""
    rgb_data = bytearray()
    
    for pixel in pixel_data:
        if pixel < len(palette):
            r, g, b = palette[pixel]
        else:
            r, g, b = 0, 0, 0
        rgb_data.extend([r, g, b])
    
    return bytes(rgb_data)
```

## File Format Comparison

### CREDIT.mpd vs S_TIT Files

| Feature | CREDIT.mpd | S_TIT Files |
|---------|------------|-------------|
| Magic | "Cell" | "5UUUUU" |
| Purpose | Resource index | Sprite data |
| Structure | Records + markers | Header + data |
| Data | References | Actual pixels |
| Organization | Table format | Container format |

## Practical Examples

### Extracting CREDIT.mpd

```python
def extract_credit_mpd(filepath: str) -> dict:
    """Extract CREDIT.mpd resource index."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    header = MPDHeader(data)
    records = parse_index_records(data, 32)
    
    return {
        'header': {
            'magic': header.magic.decode('ascii'),
            'dimensions': f'{header.width}x{header.height}',
            'data_size': header.data_size
        },
        'records': records
    }
```

### Extracting S_TIT Sprite

```python
def extract_stit_sprite(filepath: str, output_dir: str):
    """Extract sprite from S_TIT file."""
    with open(filepath, 'rb') as f:
        data = f.read()
    
    header = parse_stit_header(data)
    
    # Extract palette
    palette = extract_palette(data, header.palette_offset)
    
    # Extract pixel data
    pixels = decode_planar(
        data[header.data_offset:],
        header.width,
        header.height
    )
    
    # Apply palette and save
    rgb_data = apply_palette(pixels, palette)
    save_as_png(rgb_data, header.width, header.height, output_dir)
```

## Known Issues

### Sparse Data

S_TIT files contain significant sparse data:
- ~88% of pixels may be value 0 (background)
- Remaining pixels distributed across few values
- Suggests indexed color with transparency

### Format Variations

Different MPD files may have:
- Different header sizes
- Varying alignment requirements
- Optional sections

## Tool Support

The following tools work with MPD files:

| Tool | Purpose |
|------|---------|
| [Dokapon Extract](../tools/dokapon-extract) | Extract MPD cell data |
| sprite_extractor.py | Extract sprites from MPD |
| stit_extract.py | Extract S_TIT format files |

## Research Status

{: .note }
> MPD format documentation is based on analysis of limited sample files. Additional research needed:
> - Complete format specification for all variants
> - Compression detection for newer files
> - Animation/sequence data if present
> - Relationship with other asset formats

## See Also

- [SPRANM Format](spranm-format) - Related sprite animation format
- [Dokapon Extract](../tools/dokapon-extract) - Asset extraction tool
- [Image Extractor](../tools/image-extractor) - Image extraction utilities

