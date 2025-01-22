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

The script performs the following operations:
1. Reads the PCK file header (first 16 bytes)
2. Locates voice data starting at offset 0x5B0
3. Extracts each voice file (32KB chunks)
4. Converts raw PCM data to WAV format

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

Author: DiNaSoR [Kunio Discord] 