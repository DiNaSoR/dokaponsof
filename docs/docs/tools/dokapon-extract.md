---
title: Dokapon Extract
layout: default
nav_order: 5
parent: Tools
---

# Dokapon Extract
{: .no_toc }

A versatile tool for extracting and repacking various game assets from DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

Dokapon Extract is a powerful Python tool that handles multiple file formats used in DOKAPON! Sword of Fury:

📦 **Supported Formats**
- `.tex` - Texture files
- `.mpd` - Map/Cell data files
- `.spranm` - Sprite animation files
- `.fnt` - Font files

🔄 **Key Features**
- Extract embedded PNG images
- Handle LZ77 compression
- Preserve file metadata
- Repack modified PNGs
- Maintain directory structure

## Requirements

- Python 3.6 or higher
- PIL (Python Imaging Library)
- Basic command line knowledge

## Installation

1. Download `dokapon_extract.py`
2. Install required Python packages:
   ```bash
   pip install pillow
   ```

## Usage

### Basic Command Structure

```bash
python dokapon_extract.py [-h] [-i INPUT] [-o OUTPUT] [-t {tex,spranm,fnt,all}] [-v] [--repack]
```

### Arguments

| Argument | Description |
|----------|-------------|
| `-i, --input` | Input file/directory (default: current dir) |
| `-o, --output` | Output directory (default: ./output) |
| `-t, --type` | File type to process (default: all) |
| `-v, --verbose` | Show detailed processing information |
| `--repack` | Repack a modified PNG using metadata |

### Quick Usage in Game Directory

If you place `dokapon_extract.py` directly in the game's root folder, you can extract assets without specifying full paths:

1. **Copy the Script**
   ```
   📁 DOKAPON ~Sword of Fury~
   ├── 📄 dokapon_extract.py    # Place script here
   └── 📁 GameData/
   ```

2. **Extract All Assets**
   ```bash
   python dokapon_extract.py -i "GameData/app" -o "extracted"
   ```

3. **Extract Specific Types**
   ```bash
   # Extract all UI textures
   python dokapon_extract.py -i "GameData/app/Field/TXD" -o "extracted/ui" -t tex

   # Extract all battle effects
   python dokapon_extract.py -i "GameData/app/Battle/Effect" -o "extracted/effects" -t spranm

   # Extract all fonts
   python dokapon_extract.py -i "GameData/app/Font" -o "extracted/fonts" -t fnt
   ```

4. **Extract Single Files**
   ```bash
   # Extract a specific UI element
   python dokapon_extract.py -i "GameData/app/Field/TXD/BoxWin.txd" -o "extracted/ui"

   # Extract a specific animation
   python dokapon_extract.py -i "GameData/app/Battle/Effect/EFFECT00_00.spranm" -o "extracted/effects"
   ```

{: .note }
Running the script from the game directory makes it easier to use relative paths and maintain your extracted files organization.

## Real-World Examples

### Game File Structure

```
📁 DOKAPON ~Sword of Fury~
├── 📁 GameData/app/
│   ├── 📁 Battle/          # Battle animations and effects
│   │   ├── 📁 Effect/     # Battle effects
│   │   ├── 📁 Ability/    # Character abilities
│   │   └── 📁 Magic/      # Magic animations
│   ├── 📁 Field/          
│   │   ├── 📁 Face/       # Character face animations
│   │   ├── 📁 Map/        # Map data and textures
│   │   ├── 📁 TXD/        # UI textures
│   │   └── 📁 Guidebook/  # Game guide images
│   ├── 📁 Font/           # Game fonts
│   └── 📁 Title/          # Title screen assets
```

### Common Extraction Tasks

1. **Extract Battle Effects**
   ```bash
   python dokapon_extract.py -i "GameData/app/Battle/Effect" -o "extracted/effects" -t spranm
   ```
   Extracts animation files like:
   - EFFECT00_00.spranm → EFFECT00_00.png
   - EFFECT01_00.spranm → EFFECT01_00.png
   - EFFECT02_00.spranm → EFFECT02_00.png

2. **Extract Character Faces**
   ```bash
   python dokapon_extract.py -i "GameData/app/Field/Face" -o "extracted/faces" -t spranm
   ```
   Extracts character face animations:
   - FACE00A_00.spranm → FACE00A_00.png
   - FACE00B_00.spranm → FACE00B_00.png
   - H_FACE00A_00.spranm → H_FACE00A_00.png

3. **Extract UI Textures**
   ```bash
   python dokapon_extract.py -i "GameData/app/Field/TXD" -o "extracted/ui" -t tex
   ```
   Processes UI elements:
   - BoxWin.txd → BoxWin.png
   - StatusWin.txd → StatusWin.png
   - WeekWin.txd → WeekWin.png

4. **Extract Guidebook Images**
   ```bash
   python dokapon_extract.py -i "GameData/app/Field/Guidebook" -o "extracted/guide"
   ```
   Extracts all guidebook pages:
   ```
   📁 extracted/guide/
   ├── img.png
   ├── img2.png
   ├── img3.png
   ...
   └── img34.png
   ```

### Batch Processing Examples

1. **Extract All Battle Assets**
   ```bash
   #!/bin/bash
   # extract_battle.sh
   BASE_DIR="GameData/app/Battle"
   OUT_DIR="extracted/battle"

   # Extract effects
   python dokapon_extract.py -i "$BASE_DIR/Effect" -o "$OUT_DIR/effects" -t spranm

   # Extract abilities
   python dokapon_extract.py -i "$BASE_DIR/Ability" -o "$OUT_DIR/abilities"

   # Extract magic
   python dokapon_extract.py -i "$BASE_DIR/Magic" -o "$OUT_DIR/magic"
   ```

2. **Extract All Field Assets**
   ```bash
   #!/bin/bash
   # extract_field.sh
   BASE_DIR="GameData/app/Field"
   OUT_DIR="extracted/field"

   # Extract maps
   python dokapon_extract.py -i "$BASE_DIR/Map" -o "$OUT_DIR/maps" -t mpd

   # Extract faces
   python dokapon_extract.py -i "$BASE_DIR/Face" -o "$OUT_DIR/faces" -t spranm

   # Extract UI
   python dokapon_extract.py -i "$BASE_DIR/TXD" -o "$OUT_DIR/ui" -t tex
   ```

### Language-Specific Content

The game includes language-specific variants in "en" subdirectories:

```bash
python dokapon_extract.py -i "GameData/app/Field/TXD/en" -o "extracted/ui/en"
```

This extracts English versions of UI elements:
- F_00_FD_02_txt.txd
- MARK_00.txd
- StatusWin.txd

## File Format Details

### Texture Files (.tex)
{: .d-inline-block }

PNG Container
{: .label .label-green }

Structure:
```
[LZ77 Header (optional)]
[PNG Data]
```

### Map Data Files (.mpd)
{: .d-inline-block }

Cell Data
{: .label .label-blue }

For detailed format documentation, see [MPD Map Format](../technical/mpd-format).

Header Structure:
```c
struct MPDHeader {
    char magic[16];    // "Cell" (padded)
    int data_size;     // Size of data section
    int width;         // Image width
    int height;        // Image height
    int cell_width;    // Width of each cell
    int cell_height;   // Height of each cell
};
```

### Sprite Animation (.spranm)
{: .d-inline-block }

Animation Data
{: .label .label-purple }

For detailed format documentation, see [SPRANM Animation Format](../technical/spranm-format).

Format (two variants):
```
Type A - Animation Control (LZ77 compressed):
[LZ77 Header]
[Compressed control data]

Type B - Sprite Resource (uncompressed):
"Sequence" marker
[Sprite definitions]
[PNG Data]
[Animation Data]
```

### Font Files (.fnt)
{: .d-inline-block }

Font Data
{: .label .label-yellow }

Contains:
- LZ77 compressed data (optional)
- Raw font data

## Technical Details

### LZ77 Decompression

The tool implements Nintendo-style LZ77 decompression. For detailed format documentation, see [LZ77 Compression Format](../technical/lz77-compression).

```python
def decompress_lz77(data: bytes) -> Optional[bytes]:
    """
    Format:
    - 4 byte magic "LZ77"
    - 4 byte decompressed size
    - 4 byte flag1 (compression parameters)
    - 4 byte flag2 (additional parameters)
    - Compressed data stream
    """
```

### Metadata Preservation

Each extracted PNG includes a JSON metadata file:
```json
{
    "original_file": "path/to/source.tex",
    "original_extension": ".tex",
    "offset": 1234,
    "length": 5678,
    "mpd_header": {
        "width": 1024,
        "height": 1024,
        "cell_width": 32,
        "cell_height": 32
    }
}
```

### PNG Processing

The tool handles PNG data carefully:
- Strips unnecessary metadata
- Preserves core image data
- Maintains original dimensions
- Handles size differences during repacking

## Best Practices

### Extracting Files

1. 📁 **Organize Your Files**
   - Keep original files backed up
   - Use meaningful directory names
   - Maintain directory structure

2. 🔍 **Use Verbose Mode**
   ```bash
   python dokapon_extract.py -i "input" -o "output" -v
   ```
   - Helps track processing
   - Shows detailed information
   - Identifies potential issues

3. 📊 **Check Results**
   - Verify extracted files
   - Compare file counts
   - Check metadata files

### Repacking Files

1. 🔒 **Preserve Metadata**
   - Keep .json files with PNGs
   - Don't modify metadata manually
   - Back up original files

2. 📏 **Mind the Size**
   - Keep modifications within original dimensions
   - Check warnings about size differences
   - Test repacked files

3. 🧪 **Test Thoroughly**
   - Verify in-game appearance
   - Check for visual artifacts
   - Test different game scenarios

## Troubleshooting

### Common Issues

1. **LZ77 Decompression Errors**
   ```
   Decompression error: Invalid compressed data
   ```
   - Check file integrity
   - Verify file is actually compressed

2. **PNG Extraction Failed**
   ```
   No PNG signature found
   ```
   - Verify file format
   - Check file corruption

3. **Repacking Size Mismatch**
   ```
   Warning: PNG larger than original
   ```
   - Reduce image size
   - Check image dimensions

## Contributing

We welcome contributions! 
- Report issues on GitHub
- Submit pull requests
- Share improvements
- Join our [Discord](https://discord.gg/HCrYwScDg5)

## License

This tool is licensed under The Unlicense. You can:
- ✅ Use freely for any purpose
- ✅ Modify and distribute without restrictions
- ✅ No attribution required
- ✅ Dedicated to public domain
- ✅ No warranty provided

See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for details. 