---
layout: default
title: Voice Pack Extractor
parent: Tools
nav_order: 1
---

# Voice Pack Extractor
{: .no_toc }

Extract and convert voice files from DOKAPON! Sword of Fury's proprietary `.pck` format to standard `.wav` files.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

The Voice Pack Extractor is a Python-based tool that allows you to extract voice files from the game's `Voice-en.pck` file. This tool is essential for:
- Creating voice mods
- Translating voice lines
- Analyzing voice data

## Requirements

- Python 3.6 or higher
- Original game files (specifically `Voice-en.pck`)
- Basic knowledge of command line operations

## Installation

1. Download `voice_pck_extractor.py` from our repository
2. Place it in the same directory as your `Voice-en.pck` file
3. No additional dependencies required!

## Usage

1. Open a terminal/command prompt in the directory containing both files
2. Run the script:
   ```bash
   python voice_pck_extractor.py
   ```
3. The tool will:
   - Analyze the voice pack format
   - Extract all voice files
   - Convert them to WAV format
   - Save them in an `extracted_voices` folder

## Output Format

Extracted files will be saved with the following specifications:
- Format: WAV (uncompressed)
- Sample Rate: 22050 Hz
- Channels: 1 (mono)
- Bit Depth: 16-bit

## Troubleshooting

If the extracted WAV files don't sound correct, try modifying these settings in the script:
- Sample rate: Try 11025 or 44100 Hz
- Sample width: Try 1 (8-bit) instead of 2 (16-bit)
- Channels: Keep at 1 (mono) for compatibility

## Technical Details

The tool performs the following operations:
1. Verifies the PCK file header
2. Locates voice file entries
3. Extracts raw PCM data
4. Converts to standard WAV format

## Support

If you encounter any issues:
1. Check the console output for error messages
2. Join our [Discord](https://discord.gg/wXhAEvhTuR) for community support
3. Report bugs on our GitHub repository

## Legal Notice

This tool is provided for personal use only. Please support the developers by purchasing DOKAPON! Sword of Fury on Steam. 