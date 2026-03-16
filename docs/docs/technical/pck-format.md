---
title: PCK Sound Archive
layout: default
nav_order: 4
parent: Technical Reference
---

# PCK Sound Archive Format
{: .no_toc }

Documentation of the binary sound archive format used for all game audio in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

PCK files are binary archives that bundle multiple audio files together with a filename index. The format consists of exactly two sections: a **Filename** section for name lookup and a **Pack** section containing the actual audio data.

The C# implementation is `DokaponSoFTools.Core.Formats.PckArchive`.

### Known Archives

| File | Contents |
|---|---|
| `BGM.pck` | Background music tracks |
| `SE.pck` | Sound effects |
| `Voice.pck` | Japanese voice acting |
| `Voice-en.pck` | English voice acting |

All audio data uses **Ogg Opus** encoding, detected by the `OggS` magic bytes (`0x4F 0x67 0x67 0x53`) at the start of each sound entry.

---

## File Layout

```
[Filename section]
[alignment padding to 8-byte boundary]
[Pack section]
[alignment padding to 16-byte boundary]
```

---

## Section: Filename

The Filename section provides the name for each archived sound.

### Section Header (20 bytes)

```
Offset  Size  Field
------  ----  -----
0x00    20    Name "Filename" (ASCII, space-padded to 20 bytes)
```

Immediately after the 20-byte name:

```
Offset  Size  Field
------  ----  -----
+0x00    4    SectionSize — total byte length of this entire section (LE int32)
               (includes the 20-byte name + this size field + all data that follows)
+0x04   N×4   Offset array: N × int32 (LE), one entry per sound
               offset[i] is the byte offset of sound i's name string,
               measured from the start of the offset array itself
+var    var   Null-terminated ASCII filename strings, packed sequentially
```

### Filename Count Derivation

The archive does not store the sound count explicitly. Instead, it is computed from the **first offset value**:

```
soundCount = firstOffset / 4
```

Because `firstOffset` is the byte offset to the first filename string, and the offset array occupies `soundCount × 4` bytes before the strings, the first offset equals `soundCount × 4`.

### Example

For an archive with 3 sounds named `"bgm_01.opus"`, `"bgm_02.opus"`, `"bgm_03.opus"`:

```
Offset array (12 bytes):   0x0C, 0x18, 0x24    (each relative to offset array start)
Name data:                 "bgm_01.opus\0bgm_02.opus\0bgm_03.opus\0"
soundCount = 0x0C / 4 = 3
```

### 8-byte Alignment Gap

After the Filename section ends, zero-padding is inserted to reach the next 8-byte boundary before the Pack section begins:

```csharp
if (filenameSectionSize % 8 != 0)
    packOffset = filenameSectionSize + (8 - filenameSectionSize % 8);
else
    packOffset = filenameSectionSize;
```

---

## Section: Pack

The Pack section stores the raw audio data with an index table for offset/size lookup.

### Section Header (20 bytes)

```
Offset  Size  Field
------  ----  -----
0x00    20    Name "Pack" (ASCII, space-padded to 20 bytes)
```

After the 20-byte name:

```
Offset  Size  Field
------  ----  -----
+0x00    4    PackSectionLength — total byte length of header + info array (LE int32)
               PackSectionLength = 0x1C + soundCount × 8
+0x04    4    SoundCount (LE int32)
+0x08   N×8   Info array: N × (offset[4] + size[4]), all LE int32
               offset = absolute byte offset of sound data in the file
               size   = byte length of sound data
+0x08+(N×8)
       4    Zero padding (4 bytes)
+0x0C+(N×8)
      var   Sound data blocks, 16-byte aligned between entries
```

The first sound data block starts at absolute offset:
```
packSectionStart + PackSectionLength + 4
```

### Sound Data Alignment

Each sound's data block is padded to a **16-byte boundary** after its last byte before the next sound begins:

```csharp
int pad = soundData.Length % 16 == 0 ? 0 : 16 - (soundData.Length % 16);
// write pad zero bytes after sound data
```

The entire PCK file ends with padding to 16-byte alignment.

---

## Sound Data Format

Each sound entry is an **Ogg Opus** file stored verbatim:

| Field | Value |
|---|---|
| Magic bytes | `OggS` (`0x4F 0x67 0x67 0x53`) |
| Codec | Opus |
| Container | Ogg |
| Detection | `Sound.IsOpus` property checks for `OggS` magic |

Sound files within `.pck` archives use the `.opus` extension. Files without `OggS` magic are stored as raw bytes and can be extracted as-is.

---

## Full File Structure Diagram

```
+0x00   [20]   "Filename           " (space-padded)
+0x14   [ 4]   section_size (total Filename section bytes)
+0x18   [N×4]  filename offset array
+0x18+(N×4)    null-terminated filename strings
...
[padding to 8-byte boundary]
+P+0x00 [20]   "Pack                " (space-padded)
+P+0x14 [ 4]   pack_section_length = 0x1C + N×8
+P+0x18 [ 4]   sound_count = N
+P+0x1C [N×8]  info array: (absolute_offset, size) pairs
+P+0x1C+(N×8)
        [ 4]   zero padding
+P+0x20+(N×8)  sound data blocks (16-byte aligned between entries)
...
[padding to 16-byte boundary]
```

---

## C# Usage

```csharp
// Load a PCK archive
var pck = new PckArchive("BGM.pck");
Console.WriteLine($"{pck.Sounds.Count} sounds loaded");

// Access individual sounds
foreach (var sound in pck.Sounds)
{
    Console.WriteLine($"{sound.Name}  {sound.Size} bytes  opus={sound.IsOpus}");
}

// Extract all sounds to a directory
pck.ExtractAll("output/BGM/");

// Find a specific sound (by name with or without extension)
Sound? track = pck.FindSound("bgm_title");

// Replace a sound
var replacement = Sound.FromFile("my_bgm_title.opus");
pck.ReplaceSound("bgm_title", replacement);

// Save modified archive
pck.Write("BGM_modified.pck");
```

---

## Round-trip Guarantee

The `PckArchive` class supports a full read-modify-write cycle. The `Write` method rebuilds both sections from scratch using the current `Sounds` list:

1. Filename section: recomputes offset array and packs name strings.
2. Pack section: rewrites info table with correct absolute offsets; pads each sound to 16 bytes.
3. Final file is padded to a 16-byte boundary.

---

## See Also

- [LZ77 Compression](lz77-compression) — used by other format types but **not** PCK files
- Tools: Voice Tools feature in DokaponSoFTools uses `PckArchive` for extraction and replacement
