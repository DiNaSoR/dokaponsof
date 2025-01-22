---
title: Voice Pack Extractor
layout: default
nav_order: 2
parent: Tools
---

# Voice Pack Extractor
{: .no_toc }

A tool for extracting voice files from DOKAPON! Sword of Fury's `.pck` format to Opus audio format.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

The Voice Pack Extractor is a Python script that allows you to:
- Extract voice files from the game's proprietary `.pck` format
- Extract the original Opus audio streams
- Analyze the voice data structure for modding purposes

## Requirements

- Python 3.6 or higher
- DOKAPON! Sword of Fury (PC Version) installed
- Basic knowledge of using command line tools
- VLC, Firefox, or FFmpeg for playing/converting Opus files

## Installation

1. Download the `voice_pck_extractor.py` script
2. Place it in the same directory as your `Voice-en.pck` file (usually in the game's installation directory)

## Usage

1. Open a terminal/command prompt
2. Navigate to the directory containing both files
3. Run the script:
   ```bash
   python voice_pck_extractor.py
   ```

The script will:
1. Analyze the PCK file structure
2. Create an `extracted_voices` directory
3. Extract all voice files in their original Opus format

## Output Format

The extracted files will be saved with the following specifications:
- Format: Opus audio (.opus)
- Container: Ogg
- Original quality preserved
- Original audio parameters maintained

{: .note }
The extracted .opus files can be played with VLC media player, Firefox browser, or converted to other formats using FFmpeg.

## Troubleshooting

### Common Issues

1. **File Not Found Error**
   ```
   Error: Could not find file at [path]/Voice-en.pck
   ```
   - Make sure the script is in the same directory as `Voice-en.pck`
   - Verify the PCK file name matches exactly

2. **Invalid Format Error**
   ```
   Invalid file format - missing 'Filename' header
   ```
   - Ensure you're using the correct PCK file from the game
   - Verify the file isn't corrupted

### Playing Opus Files

If you need to convert the Opus files to another format:
1. Using FFmpeg:
   ```bash
   ffmpeg -i input.opus output.mp3
   ```
2. Using VLC:
   - Open VLC
   - Media -> Convert/Save
   - Select Opus file and desired output format

## Technical Details

### PCK File Structure
The `.pck` file format is a proprietary container format used by DOKAPON! Sword of Fury to store voice audio data. Here's the detailed breakdown:

#### Header Section (0x000 - 0x013)
```
Filename            X
```
- First 8 bytes: ASCII string "Filename"
- Next 12 bytes: Padding (spaces)
- Byte 20: ASCII character 'X' (marker)

#### Offset Table (0x014 - varies)
- Series of 4-byte little-endian integers
- Each integer represents the absolute offset to a voice file
- First offset typically starts at 0x5B0

#### Filename Table (varies - 0x5AF)
- Null-terminated ASCII strings
- Format: "V_XXXX.voice\0" where XXXX is a zero-padded number
- Special cases include split files like "V_0044_1.voice"

#### Pack Marker
- ASCII string "Pack"
- Located just before voice data starts
- Used as a separator between headers and data

#### Voice Data Section (0x5B0 - EOF)
- Opus audio streams in Ogg containers
- Each stream starts with "OggS" marker
- Each block starts at its corresponding offset
- Size determined by next file's offset or EOF

### Extraction Process

1. **Header Validation**
   ```python
   header = file.read(16)
   if not header.startswith(b'Filename'):
       raise ValueError("Invalid file format")
   ```

2. **Filename Reading**
   ```python
   filenames = []
   while True:
       char = file.read(1).decode('ascii', errors='ignore')
       # Process filename characters
   ```

3. **Opus Stream Extraction**
   ```python
   opus_start = find_opus_header(voice_data)
   if opus_start >= 0:
       # Extract Opus stream until next "OggS" marker
   ```

### Opus Audio Format

The voice data is stored as Opus audio with these characteristics:
- Container: Ogg
- Codec: Opus
- Headers: Standard Opus headers present
- Quality: Original game quality preserved

### Memory Considerations

- Files are processed in chunks (32KB for initial read, 4KB for streaming)
- Opus streams are extracted directly without transcoding
- Efficient handling of large files through streaming

### Error Handling

The tool includes comprehensive error checking for:
- Invalid file formats
- Missing Opus streams
- File access issues
- Memory constraints

## Contributing

Found a bug or want to improve the tool? 
- Report issues on our GitHub repository
- Submit pull requests with improvements
- Share your findings on our [Discord](https://discord.gg/HCrYwScDg5)

## License

This tool is licensed under the GNU General Public License v3.0 (GPL-3.0). You can:
- Use the tool for any purpose
- Modify and distribute the code
- Must keep the source code open source
- Must license modifications under GPL-3.0

See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.