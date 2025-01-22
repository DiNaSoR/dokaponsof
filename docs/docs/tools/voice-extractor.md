---
title: Voice Pack Extractor
layout: default
nav_order: 2
parent: Tools
---

# Voice Pack Extractor
{: .no_toc }

A tool for extracting and converting voice files from DOKAPON! Sword of Fury's `.pck` format to WAV format.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

The Voice Pack Extractor is a Python script that allows you to:
- Extract voice files from the game's proprietary `.pck` format
- Convert the extracted audio data to standard WAV format
- Analyze the voice data structure for modding purposes

## Requirements

- Python 3.6 or higher
- DOKAPON! Sword of Fury (PC Version) installed
- Basic knowledge of using command line tools

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
3. Extract and convert all voice files to WAV format

## Output Format

The extracted files will be saved with the following specifications:
- Format: WAV (uncompressed)
- Sample Rate: 22050 Hz
- Bit Depth: 16-bit
- Channels: Mono (1)

{: .note }
If the extracted audio doesn't sound correct, you can modify the sample rate and bit depth in the script. Common alternatives are listed in the script's output.

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

### Audio Quality Issues

If the extracted audio doesn't sound right, try these settings in `raw_to_wav()`:
- Sample rates: 11025, 22050, or 44100 Hz
- Sample width: 1 (8-bit) or 2 (16-bit)
- Channels: Keep at 1 (mono) as the game uses mono audio

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
- Example:
  ```
  B0 05 00 00 = 0x5B0 (first voice file)
  BD 05 00 00 = 0x5BD (second voice file)
  ...
  ```

#### Filename Table (varies - 0x5AF)
- Null-terminated ASCII strings
- Format: "V_XXXX.voice\0" where XXXX is a zero-padded number
- Special cases include split files like "V_0044_1.voice"
- Example:
  ```
  56 5F 30 30 30 31 2E 76 6F 69 63 65 00 = "V_0001.voice\0"
  ```

#### Pack Marker
- ASCII string "Pack" followed by 4 spaces
- Located just before voice data starts
- Used as a separator between headers and data

#### Voice Data Section (0x5B0 - EOF)
- Raw voice data blocks
- Each block starts at its corresponding offset
- No size headers - size is calculated from offset differences
- Data format: Raw PCM audio (details below)

### Extraction Process

1. **Header Validation**
   ```python
   header = file.read(16)
   if not header.startswith(b'Filename'):
       raise ValueError("Invalid file format")
   ```

2. **Offset Table Reading**
   ```python
   offsets = []
   while current_pos < 0x5B0:
       offset = struct.unpack('<I', file.read(4))[0]
       offsets.append(offset)
   ```

3. **Voice Data Extraction**
   ```python
   for i in range(len(offsets) - 1):
       size = offsets[i + 1] - offsets[i]
       file.seek(offsets[i])
       voice_data = file.read(size)
   ```

### PCM Audio Specifications

The voice data is stored as raw PCM with these characteristics:
- Sample Rate: 22050 Hz (confirmed through analysis)
- Bit Depth: 16-bit signed integer
- Channels: 1 (mono)
- Byte Order: Little-endian
- No headers or metadata

### Repacking Process

When creating a new PCK file:

1. **Calculate File Offsets**
   ```python
   current_offset = 0x5B0
   for voice_file in voice_files:
       offsets.append(current_offset)
       current_offset += os.path.getsize(voice_file)
   ```

2. **Write Header Structure**
   - Write "Filename" + padding + "X"
   - Write offset table
   - Write filenames with null terminators
   - Add padding to reach 0x5B0
   - Write "Pack" marker

3. **Write Voice Data**
   - Seek to 0x5B0
   - Write each voice file sequentially

### Memory Considerations

- Files are processed in chunks to handle large PCK files
- Voice data is read and written directly without loading entire file into memory
- Offset table is kept in memory for random access during extraction

### File Size Verification
The tool verifies file integrity by:
- Checking offset table consistency
- Validating file size matches last offset
- Comparing packed file size with original

### Error Handling

The tool includes comprehensive error checking for:
- Invalid file formats
- Corrupted offset tables
- Missing or inaccessible files
- Incorrect file permissions
- Memory constraints

## Advanced Usage

### Custom Audio Parameters
```python
def raw_to_wav(raw_data, wav_path, 
               sample_rate=22050,
               channels=1,
               sample_width=2):
    # Convert raw PCM to WAV
```

### Batch Processing
The tool can handle multiple PCK files:
```bash
python voice_pck_extractor.py --batch path/to/pck/files
```

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