# PCK Sound Archive Format

> Last updated: 2026-03-16

## Overview

`.pck` files are sound archives containing Ogg Opus audio. Four archives exist:

| File | Contents | Count |
|------|----------|-------|
| BGM.pck | Background music | 47 tracks |
| SE.pck | Sound effects | varies |
| Voice.pck | Japanese voice lines | varies |
| Voice-en.pck | English voice lines | varies |

## Binary Structure

### Filename Section

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 20 | ASCII header: `"Filename"` (padded to 20 bytes) |
| 0x14 | 4 | Section total size (LE uint32) |
| 0x18 | N×4 | Array of LE uint32 offsets to null-terminated filenames |
| varies | varies | Null-terminated ASCII filename strings |

Sound count = `firstOffset / 4` (first offset value divided by 4).

### Pack Section (after Filename, 8-byte aligned)

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 20 | ASCII header: `"Pack"` (padded to 20 bytes) |
| 0x14 | 4 | Pack section length (LE uint32) |
| 0x18 | 4 | Sound count (LE uint32) |
| 0x1C | N×8 | Array of (offset: uint32, size: uint32) pairs |
| +4 | 4 | Padding |
| varies | varies | Raw sound data blobs, 16-byte aligned |

### Sound Data Format

Each sound entry's data is a self-contained Ogg file:
- **Ogg Opus**: Starts with `OggS` magic bytes (`4F 67 67 53`)
- **Raw**: No `OggS` header (treated as raw PCM)

Detection: `IsOpus = Data[0..3] == "OggS"`

## Playback

The sounds use **Ogg Opus** encoding. For playback:
1. Extract raw bytes from the archive
2. Decode Opus using **Concentus** (`OpusDecoder` + `OpusOggReadStream`)
3. Output 48kHz, 16-bit, stereo PCM
4. Play via **NAudio** `WaveOutEvent` with `RawSourceWaveStream`

## Extraction/Replacement

- `ExtractAll(outputDir)`: Dumps each Sound.Data to a file using Sound.Name
- `ReplaceSound(name, newSound)`: Swaps a sound entry by name
- `Write(outputPath)`: Rebuilds the PCK with updated data
- Round-trip safe: write preserves the exact binary format
