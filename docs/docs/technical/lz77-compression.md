---
title: LZ77 Compression
layout: default
nav_order: 1
parent: Technical Reference
---

# LZ77 Compression
{: .no_toc }

Three distinct LZ77 variants used across DOKAPON! Sword of Fury file formats.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

DOKAPON! Sword of Fury uses three distinct variants of LZ77-style compression. All three share the same 4-byte magic `LZ77` (`0x4C5A3737`) and a 16-byte header, but differ in how the remaining header fields are interpreted and how the compressed bitstream is structured.

The C# implementation lives in `DokaponSoFTools.Core.Compression`:

| Class | Variant | Used By |
|---|---|---|
| `Lz77FlagByte` | FlagByte | SPRANM, TEX files |
| `Lz77TokenStream` | TokenStream | MDL model files |
| `Lz77Cell` | Cell | MPD map files |
| `Lz77Decompressor` | Auto-detect + dispatch | All callers |

---

## Shared: 16-byte Header

All variants begin with the same magic and a 16-byte header block starting at offset `0x00`:

```
Offset  Size  Description
------  ----  -----------
0x00    4     Magic: "LZ77"  (ASCII, 0x4C5A3737)
0x04    4     Field A        (interpretation varies by variant)
0x08    4     Field B        (interpretation varies by variant)
0x0C    4     Field C        (interpretation varies by variant)
0x10    var   Compressed stream / flags / data
```

Compressed data begins at offset `0x10` in all variants.

---

## Variant Auto-Detection

`Lz77Decompressor.DetectVariant` reads the 16-byte header and applies these rules in order:

1. **Cell** — `field_C` (`data_offset`) is `> 0x10` and `< file_length`, AND `field_B` (`token_count`) is `> 0` and `< field_A` (`raw_size`).
2. **TokenStream** — `field_A` (`decompressed_size`) is `> 0` and `field_B` is `0` or `>= field_A`.
3. **FlagByte** — default fallback.

```csharp
// Detection pseudocode
if (dataOffset > 0x10 && tokenCount > 0 && tokenCount < rawSize)
    return Lz77Variant.Cell;
if (rawSize > 0 && (tokenCount == 0 || tokenCount >= rawSize))
    return Lz77Variant.TokenStream;
return Lz77Variant.FlagByte;
```

---

## Variant 1: FlagByte

Used by **SPRANM** (sprite animation) and **TEX** (texture) files.

### Header Layout

```
0x00  [4]  "LZ77"
0x04  [4]  Unknown / reserved
0x08  [4]  Decompressed size (little-endian int32)
0x0C  [4]  Uncompressed tail offset (little-endian int32)
             0 or equal to file length = no uncompressed tail
```

### Bitstream Structure

Starting at `0x10`, the stream is organized in **9-byte groups**: one flag byte followed by up to 8 tokens.

- The flag byte encodes 8 bits, read **MSB first** (bit 7 down to bit 0).
- Each bit controls whether the corresponding token is a **literal** (`0`) or a **back-reference** (`1`).

**Literal token** (1 byte):
```
[byte]  →  output byte as-is
```

**Back-reference token** (2 bytes):
```
Byte 1:  [LLLL][OOOO high]
Byte 2:  [OOOO low 8 bits]

length = ((byte1 >> 4) & 0x0F) + 3     →  range 3–18
offset = ((byte1 & 0x0F) << 8) | byte2 + 1  →  range 1–4096
```

Copy `length` bytes from `output[current - offset]` (overlapping copies allowed for RLE patterns).

### Uncompressed Tail

If `uncompressed_offset > 0x10` and is less than the file length, bytes from `uncompressed_offset` to EOF are **appended verbatim** to the decompressed output. This tail is used in some TEX files to carry data that compresses poorly.

### Example Header

```
4C 5A 37 37   "LZ77"
00 00 00 00   (reserved)
A0 2F 00 00   decompressed size = 0x2FA0 = 12192 bytes
00 00 00 00   no uncompressed tail
```

---

## Variant 2: TokenStream

Used by **MDL** (3D model) files.

### Header Layout

```
0x00  [4]  "LZ77"
0x04  [4]  Decompressed size (little-endian int32)
0x08  [4]  Flag1  (not used during decompression)
0x0C  [4]  Flag2  (not used during decompression)
```

### Bitstream Structure

Starting at `0x10`, **each byte is its own token** — there are no separate flag bytes.

- Bit 7 = `0` → **literal** byte (the 7 remaining bits are the output byte value)
- Bit 7 = `1` → **back-reference** (2 bytes total including this token byte)

**Literal token** (1 byte):
```
token & 0x7F  →  output byte
```

**Back-reference token** (2 bytes):
```
Token byte:   [1][LLLLL][OO high]
Next byte:    [OO low 8 bits]

length = ((token & 0x7C) >> 2) + 3   →  5 bits, range 3–34
offset = ((token & 0x03) << 8) | next_byte + 1  →  10 bits, range 1–1024
```

### Example

```
Token 0x88 = 1000 1000
             ^    ^^^^ ^^
             |      |   |
             |      |   +-- offset high: 0b00 = 0
             |      +------ length bits: 0b00010 = 2 → length = 5
             +------------- bit 7 set → back-reference

Next byte 0x40 = 64
offset = (0 << 8 | 64) + 1 = 65
Action: copy 5 bytes from output[-65]
```

### Example Header

```
4C 5A 37 37   "LZ77"
A8 E9 09 00   decompressed size = 649,400 bytes
B5 82 01 00   flag1 = 0x000182B5
67 30 00 00   flag2 = 0x00003067
```

MDL files may be large; example sizes:

| File | Compressed | Decompressed |
|---|---|---|
| `E000.mdl` | ~146 KB | ~649 KB |
| `E001.mdl` | ~varies | ~716 KB |
| `E002.mdl` | ~85 KB | ~287 KB |

---

## Variant 3: Cell

Used by **MPD** map files.

### Header Layout

```
0x00  [4]  "LZ77"
0x04  [4]  Raw (decompressed) size  (little-endian int32)
0x08  [4]  Token count              (little-endian int32)
0x0C  [4]  Data offset              (little-endian int32)
             Points to the literal/backref data bytes.
             Flag bytes occupy 0x10 .. data_offset - 1.
```

### Bitstream Structure

The Cell variant uses **two separate streams** within the file:

- **Flags stream**: bytes at `0x10 .. data_offset - 1` — one bit per token, MSB first per byte
- **Data stream**: bytes at `data_offset .. EOF` — literal bytes or back-reference pairs

The decompressor processes exactly `token_count` tokens:

1. Read next bit from flags stream (consume a new flags byte every 8 bits, MSB first).
2. If bit = `0` → **literal**: read 1 byte from data stream, emit it.
3. If bit = `1` → **back-reference**: read 2 bytes from data stream.

**Back-reference encoding** (2 bytes from data stream):
```
Byte 1:  distance   (how far back in output, 1-based)
Byte 2:  length - 3  (add 3 to get actual copy length, range 3–258)

Action: copy length bytes from output[current - distance]
```

{: .note }
The Cell back-reference format differs from the other two variants — distance is a direct byte value rather than a bit-packed field, and distance `0` is invalid.

### Example Header

```
4C 5A 37 37   "LZ77"
80 12 03 00   raw_size    = 0x31280 = 201,344 bytes
A0 08 00 00   token_count = 0x8A0  = 2,208 tokens
40 00 00 00   data_offset = 0x40   (flags at 0x10..0x3F, data at 0x40..)
```

---

## Decompressor Usage (C#)

```csharp
// Auto-detect and decompress
byte[] raw = File.ReadAllBytes("field01.mpd");
byte[]? decompressed = Lz77Decompressor.DecompressBytes(raw);

// Force a specific variant
byte[]? result = Lz77Decompressor.DecompressBytes(raw, Lz77Variant.Cell);

// Get Cell metadata (token counts, stream positions)
var (data, info) = Lz77Decompressor.Decompress(raw, Lz77Variant.Cell);
// info.TokenCount, info.DataOffset, info.FlagsEnd, info.DataEnd, info.OutLen
```

---

## Variant Comparison

| Property | FlagByte | TokenStream | Cell |
|---|---|---|---|
| Header `0x04` | (reserved) | decompressed size | raw size |
| Header `0x08` | decompressed size | flag1 (unused) | token count |
| Header `0x0C` | uncompressed tail offset | flag2 (unused) | data stream offset |
| Flag encoding | 1 flag byte per 8 tokens | per-token bit 7 | separate flags stream |
| Backref encoding | 4-bit length + 12-bit offset | 5-bit length + 10-bit offset | 1-byte distance + 1-byte length |
| Length range | 3–18 | 3–34 | 3–258 |
| Offset range | 1–4096 | 1–1024 | 1–255 |
| Uncompressed tail | yes (optional) | no | no |
| Used by | SPRANM, TEX | MDL | MPD |

---

## See Also

- [SPRANM Format](spranm-format) — uses FlagByte variant
- [MPD Format](mpd-format) — uses Cell variant
