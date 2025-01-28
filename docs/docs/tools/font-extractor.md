---
title: Font Pack Extractor
layout: default
nav_order: 3
parent: Tools
---

# Font Pack Extractor
{: .no_toc }

A tool for extracting and repacking PNG font files from .fnt format in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

Font Pack Extractor is a Python script that allows you to:
- Extract PNG files from the game's proprietary .fnt format
- Repack modified PNG files back into .fnt format
- Analyze font file structure for modding purposes

## Requirements

- Python 3.6 or higher
- DOKAPON! Sword of Fury (PC Version) installed
- Basic knowledge of using command line tools

## Installation

1. Download the `font_extract_repack.py` script
2. Place it in the same directory as your .fnt files (usually in the game's installation directory)

## Usage

### Extracting PNG from FNT

```bash
python font_extract_repack.py extract input.fnt output.png
```

### Importing PNG to FNT

```bash
python font_extract_repack.py import original.fnt modified.png output.fnt
```

The script will:
1. Validate the input FNT file
2. Extract/Import PNG data
3. Maintain original file format integrity

## Output Format

The extracted files will be:
- Format: PNG
- Original quality preserved
- Original image parameters maintained

{: .note }
You can edit the extracted PNG files using any image editing software.

## Troubleshooting

### Common Issues

1. **File Not Found Error**
   ```
   Error: Could not find file at [path]/file.fnt
   ```
   - Make sure the script is in the same directory as your .fnt files
   - Verify the file name is exact

2. **Invalid Format Error**
   ```
   No embedded PNG data found in the .fnt file
   ```
   - Ensure you're using a valid .fnt file from the game
   - Check if the file isn't corrupted

### Size Warnings

When importing a modified PNG:
- If the new file is smaller, padding will be added
- If larger, it will be truncated to match the original size

## Technical Details

### FNT File Structure
The .fnt file format is a proprietary format used in DOKAPON! Sword of Fury to store font data:

#### Data Section (0x000 - EOF)
- Embedded PNG data
- Standard PNG signature
- Standard PNG ending

### Extraction Process

1. **File Validation**
   ```python
   if start_index != -1 and end_index != -1:
       png_data = fnt_data[start_index:end_index]
   ```

2. **PNG Processing**
   ```python
   # Extract PNG data
   with open(output_png_path, 'wb') as png_file:
       png_file.write(png_data)
   ```

### Memory Considerations

- Files are processed in streams
- Direct PNG extraction without conversion
- Efficient handling of large files

## Contributing

Found a bug or want to improve the tool?
- Report issues on GitHub
- Submit pull requests with improvements
- Share your findings on our [Discord](https://discord.gg/HCrYwScDg5)

## License

This tool is licensed under The Unlicense. This means:
- ✅ Use freely for any purpose
- ✅ Modify and distribute without restrictions
- ✅ No attribution required
- ✅ Dedicated to public domain
- ✅ No warranty provided

See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details. 