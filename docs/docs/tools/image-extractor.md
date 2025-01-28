---
title: Image Extractor
layout: default
nav_order: 5
parent: Tools
---

# Image Extractor
{: .no_toc }

A tool for extracting and repacking PNG files from .fnt and .spranm formats in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

The Image Extractor (all2image.py) is a Python script that allows you to:
- Extract PNG files from the game's .fnt and .spranm formats
- Repack modified PNG files back into their original formats
- Preserve file structure and metadata for accurate repacking

## Requirements

- Python 3.6 or higher
- DOKAPON! Sword of Fury (PC Version) installed
- Basic knowledge of using command line tools

## Installation

1. Download the `all2image.py` script
2. Place it in the directory containing your .fnt or .spranm files

## Usage

The tool provides an interactive menu-driven interface with the following options:

1. Extract PNG from .fnt files only
2. Extract PNG from .spranm files only
3. Extract PNG from both .fnt and .spranm
4. Reinsert (import) PNG using a JSON metadata file
5. Exit the program

### Extracting Images

1. Run the script:
   ```bash
   python all2image.py
   ```
2. Choose the appropriate extraction option (1-3)
3. Either:
   - Press Enter to process all matching files in the current directory
   - Type specific filenames separated by spaces

The script will:
1. Create an output directory (extracted_fnt or extracted_spranm)
2. Extract PNG files
3. Generate JSON metadata files for each extraction

### Reimporting Images

1. Choose option 4 from the main menu
2. Provide:
   - Path to the JSON metadata file
   - Path to your modified PNG file
   - Output filename (or press Enter for default name)

## Output Structure

### Extracted Files
```
extracted_fnt/
  ├── font1.png
  ├── font1.png.json
  ├── font2.png
  └── font2.png.json
```

### JSON Metadata Format
```json
{
    "original_file": "/absolute/path/to/original.fnt",
    "offset": 1234,
    "length": 5678
}
```

## Technical Details

### File Format Analysis

#### FNT/SPRANM Structure
Both file formats embed PNG data with:
- Standard PNG signature (`89 50 4E 47 0D 0A 1A 0A`)
- Complete PNG data including IEND chunk
- Additional game-specific metadata

### Extraction Process

1. **PNG Signature Detection**
   ```python
   PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
   start_index = data.find(PNG_SIGNATURE)
   ```

2. **End Marker Location**
   ```python
   PNG_IEND = b'IEND\xaeB`\x82'
   end_index = data.find(PNG_IEND, start_index) + len(PNG_IEND)
   ```

3. **Data Extraction**
   ```python
   png_data = data[start_index:end_index]
   ```

### Import Process

The tool handles size differences between original and modified PNGs:

1. **Smaller Files**
   - Adds null byte padding to match original size
   - Preserves file structure integrity

2. **Larger Files**
   - Issues warning about size difference
   - Truncates data to fit original space
   - Prevents buffer overflows

### Memory Management

- Streams large files in chunks
- Efficient byte manipulation
- Minimal memory footprint

## Best Practices

1. **Before Extraction**
   - Back up original files
   - Ensure sufficient disk space
   - Verify file permissions

2. **Image Modification**
   - Maintain original PNG dimensions
   - Keep file size similar to original
   - Test modifications thoroughly

3. **Reimporting**
   - Always work with copies
   - Keep original JSON metadata
   - Verify successful imports

## Troubleshooting

### Common Issues

1. **PNG Not Found**
   ```
   [file.fnt] PNG signature not found.
   ```
   - Verify file is correct format
   - Check file isn't corrupted

2. **Import Size Mismatch**
   ```
   Warning: New PNG data is larger than the original space
   ```
   - Reduce modified PNG file size
   - Optimize PNG compression

## Contributing

Found a bug or want to improve the tool?
- Report issues on GitHub
- Submit pull requests with improvements
- Share your findings on our [Discord](https://discord.gg/HCrYwScDg5)

## License

This tool is licensed under The Unlicense. You can:
- ✅ Use freely for any purpose
- ✅ Modify and distribute without restrictions
- ✅ No attribution required
- ✅ Dedicated to public domain
- ✅ No warranty provided

See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details. 