# Game Text Format — Complete Reference

> Last updated: 2026-03-16
> Based on EXE string analysis, Python research code, and C# implementation

## Encoding

**UTF-8** — confirmed via both C# `Encoding.UTF8.GetString` and Python `.decode('utf-8')`.
No Shift-JIS, CP932, or custom encoding.

## Text Entry Structure

```csharp
public sealed record TextEntry(string Text, int Offset, int MaxLength);
```

- `Text` — decoded UTF-8 string including all control codes
- `Offset` — byte offset from start of the EXE where `\p` appears
- `MaxLength` — original byte count of the text block

## Delimiters

### Start Marker

`\p` — two bytes `0x5C 0x70` (backslash + lowercase p)

Every text entry begins with `\p`. The extractor scans the entire EXE for all occurrences.

### End Detection (FindTextEnd logic)

| Condition | Bytes | Result |
|-----------|-------|--------|
| `\k` found | `0x5C 0x6B` | End at pos+2 (included in text) |
| `\z` found | `0x5C 0x7A` | End at pos+2 (included in text) |
| Next `\p` found | `0x5C 0x70` | End at pos (NOT included) |
| Null byte | `0x00` | End at pos (NOT included) |
| End of file | — | Entry extends to EOF |

### Filtering

Entries are discarded if:
- Decoded text < 3 characters
- < 50% of characters are printable/whitespace

## Control Codes

All codes are literal ASCII sequences in the UTF-8 stream.

### Block Markers

| Code | Bytes | Description |
|------|-------|-------------|
| `\p` | `5C 70` | **Start of text block** — required prefix |
| `\k` | `5C 6B` | **Wait for keypress** — page pause, terminates block |
| `\z` | `5C 7A` | **Block end** — terminates block |

### Inline Modifiers

| Code | Bytes | Description |
|------|-------|-------------|
| `\n` | `5C 6E` | Newline / line break |
| `\r` | `5C 72` | Framed dialog mode (centered/bordered presentation) |
| `\h` | `5C 68` | Header / label marker (distinct font/alignment) |
| `\m` | `5C 6D` | Multiplier / stat-bar separator |
| `\,` | `5C 2C` | Thousands-comma formatter for following number |
| `\C` | `5C 43` | Color/style reference (used with `%S`) |

## Format Specifiers

Printf-style runtime substitutions filled by the game engine.

### Variables

| Pattern | Examples | Description |
|---------|----------|-------------|
| `%s` | `%s`, `%8s` | String variable (player name, item name) |
| `%d` | `%d`, `%2d` | Decimal integer |
| `%S` | `%S`, `%8S` | Styled/colored string |
| `%D` | `%D`, `%5D` | Formatted large number (gold, stats) |

### Color Codes

Pattern: `%Nc` where N is an integer index.

| Code | Color/Usage |
|------|-------------|
| `%0c` | Reset to default (white/normal) |
| `%1c` | Gold/yellow (NPC names, ＃ heart symbol) |
| `%2c` | Green/positive (received items, character names) |
| `%3c` | Orange (player name highlights) |
| `%15c` | HUD rank display headers |

Colors bracket text: `%3c%s%0c` = show `%s` in orange, then reset.

### Positioning

| Pattern | Description |
|---------|-------------|
| `%Nx` | Set horizontal cursor to column N |
| `%Ny` | Set vertical cursor to row N |
| `%NX` | Horizontal position (uppercase, multi-column layouts) |

Used in HUD/stat screens: `\p%12x%0y\hAttacks Conducted%35x\,%5D`

### Button Icons

| Pattern | Description |
|---------|-------------|
| `%NM` | Controller button graphic (e.g., `%527M`, `%528M`) |

## Special Characters

### ＃ (U+FF03, Full-Width Number Sign)

UTF-8 bytes: `EF BC 83`

Appears in dialog wrapped in color codes:
```
\pOh, I'm so glad! %1c＃%0c\nPlease, call me %2cBilda%0c...
```

Rendered as a decorative heart/musical note in the game font (common Japanese game font remapping).

## Categories (Auto-Detection)

| Category | Detection Rule |
|----------|---------------|
| **Dialog** | Has `\k` or `\z` with >5 char clean text, multi-line, or `\r` |
| **Labels** | Has `\h` header marker, or short single-line (<20 chars) |
| **HUD/Stats** | Has position codes `%Nx`, `%Ny`, `%NX` |
| **System** | Clean text ≤2 characters (control-only entries) |

Total extracted: **5107 entries** from DOKAPON! Sword of Fury.exe
- With colors: ~1255
- With variables: ~738

## Import/Export Safety

### Export Format

Two files:
1. `texts.txt` — one text entry per line (raw, with all control codes)
2. `texts.offsets.txt` — one `offset:maxlength` pair per line

### Import Rules (Binary-Safe)

1. Original EXE loaded into memory
2. Modified text re-encoded as UTF-8
3. If new byte count > `MaxLength`: **truncated** (counted as "skipped")
4. If new byte count < `MaxLength`: **null-padded** (`0x00`)
5. Bytes written back in-place at `Offset`
6. Modified buffer saved as new EXE

**Text can only shrink or stay same size — it CANNOT grow beyond MaxLength.**

### Additional Export Formats

- **CSV**: Offset, MaxLength, Category, ByteUsed, Text, Decoded
- **JSON**: Array of objects with offset, maxLength, category, text, decoded
