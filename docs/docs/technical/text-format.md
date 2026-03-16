---
title: Game Text Format
layout: default
nav_order: 5
parent: Technical Reference
---

# Game Text Format
{: .no_toc }

Documentation of the UTF-8 text format embedded in the DOKAPON! Sword of Fury game executable.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

Game text strings are stored directly inside the game executable (`.exe`) as UTF-8 byte sequences. Each string begins with a `\p` start marker and ends with one of several termination conditions. The engine interprets inline control codes and format specifiers at render time.

The C# implementation is `DokaponSoFTools.Core.Formats.GameText`.

---

## Encoding

All text strings use **UTF-8** encoding. This means:
- ASCII characters are stored as single bytes (`0x20`–`0x7E`)
- Japanese characters (hiragana, katakana, kanji) use 3-byte UTF-8 sequences
- Full-width ASCII characters use 3-byte sequences (e.g., `U+FF03` = `0xEF BC 83`)
- The game natively supports Japanese and English in the same executable

---

## String Boundaries

### Start Marker

Every text string begins with `\p`:

```
0x5C 0x70   →   \p   (backslash + lowercase 'p')
```

The extractor scans the executable byte-by-byte looking for this two-byte sequence.

### End Conditions

A string ends at the **first** of these conditions (checked in order):

| Condition | Bytes | Notes |
|---|---|---|
| `\k` — wait for input | `0x5C 0x6B` | End marker included in extracted text |
| `\z` — string end | `0x5C 0x7A` | End marker included in extracted text |
| Next `\p` — new string | `0x5C 0x70` | End marker NOT included; belongs to next string |
| Null byte | `0x00` | String terminated by null |

The `FindTextEnd` implementation:

```csharp
while (pos < content.Length) {
    byte b = content[pos];
    if (b == 0x5C && pos + 1 < content.Length) {
        byte next = content[pos + 1];
        if (next == 0x6B) return pos + 2; // \k — include
        if (next == 0x7A) return pos + 2; // \z — include
        if (next == 0x70) return pos;      // next \p — exclude
    }
    if (b == 0x00) return pos;             // null — exclude
    pos++;
}
```

---

## Control Codes

All control codes use a backslash prefix (`0x5C`).

| Code | Bytes | Meaning |
|---|---|---|
| `\p` | `5C 70` | Start of text block (also acts as separator between consecutive strings) |
| `\k` | `5C 6B` | Wait for player input (page break); ends the current text buffer |
| `\z` | `5C 7A` | End of string; hides the text box |
| `\n` | `5C 6E` | Newline — advance to next line within the current box |
| `\r` | `5C 72` | Carriage return / line break variant |
| `\h` | `5C 68` | Hard break / forced flush |
| `\m` | `5C 6D` | Message icon or special marker |
| `\,` | `5C 2C` | Pause / brief delay |
| `\C` | `5C 43` | Color reset or color control |

{: .note }
Research is ongoing for `\m`, `\,`, and `\C`. Their exact runtime behaviour has been partially observed but not fully confirmed across all contexts.

---

## Format Specifiers

Format specifiers follow printf-style syntax and are processed by the engine at render time.

### Variable Substitution

| Specifier | Meaning |
|---|---|
| `%s` | Insert string variable (e.g., player name, item name) |
| `%d` | Insert decimal integer variable (e.g., gold amount, stat value) |

### Color Codes

Syntax: `%Nc` where `N` is a decimal color index.

| Specifier | Index | Color |
|---|---|---|
| `%0c` | 0 | Reset to default text color |
| `%1c` | 1 | Gold / yellow |
| `%2c` | 2 | Green |
| `%3c` | 3 | Orange |
| `%4c`–`%14c` | 4–14 | Additional palette colors |
| `%15c` | 15 | HUD / status display color |

### Positioning

| Specifier | Meaning |
|---|---|
| `%Nx` | Set horizontal draw cursor to position `N` (pixels or character units) |
| `%Ny` | Set vertical draw cursor to position `N` |

Positioning specifiers allow text to be placed at arbitrary screen coordinates within the text box, used for aligned columns in status screens and tables.

### Button Icons

| Specifier | Meaning |
|---|---|
| `%NM` | Render button/icon graphic `N` inline with the text |

Used in tutorial and help text to display controller button icons (A, B, X, Y, D-pad, etc.) inline with the surrounding text.

---

## Special Characters

### Full-Width Hash — Heart Symbol

The full-width number sign character `＃` (Unicode `U+FF03`, UTF-8 `0xEF BC 83`) is **rendered as a heart symbol** by the game's custom font. It appears in item names, spell names, and flavor text where a heart glyph is needed.

```
U+FF03  →  ＃  →  rendered as ♥ in-game font
```

This character passes through the UTF-8 extractor unchanged and must be preserved in translations.

---

## Text Categories

Observed categories of text in the executable:

| Category | Examples | Control codes used |
|---|---|---|
| Dialog | NPC speech, story text | `\p`, `\n`, `\k`, `\z`, `%s`, `%d` |
| Item/Spell labels | Item names, descriptions | `\p`, `\z` |
| HUD / Stats | Status screen labels, table headers | `\p`, `%Nx`, `%Ny`, `%Nc`, `%d` |
| System messages | Save/load prompts, error text | `\p`, `\k`, `\z` |
| Tutorial | Button-icon help text | `\p`, `\n`, `%NM`, `\z` |

---

## Extraction

`GameText.ExtractToFiles` scans the executable and writes two parallel files:

- **texts file** — one string per line, UTF-8 encoded
- **offsets file** — one `offset:maxlength` pair per line (matching line numbers)

```csharp
int count = GameText.ExtractToFiles(
    exePath:     "DokaponSoF.exe",
    textsPath:   "output/texts.txt",
    offsetsPath: "output/offsets.txt"
);
```

A string is only included if at least 50% of its decoded characters are printable (filters false-positive matches in binary data regions).

---

## Import / Reimport

`GameText.ImportTexts` writes modified text back into a copy of the executable.

### Safety Rules

1. **MaxLength is a hard cap** — if the UTF-8 byte length of the modified string exceeds `MaxLength`, the string is **truncated** to fit. It is never allowed to grow.
2. **Null padding** — if the new string is shorter than `MaxLength`, the remaining bytes are filled with `0x00`.
3. **No relocation** — strings are written back to their original offsets. The executable binary layout does not change.

```csharp
var (replaced, skipped) = GameText.ImportTexts(
    originalExePath:    "DokaponSoF.exe",
    modifiedTextsPath:  "modified/texts.txt",
    offsetsPath:        "output/offsets.txt",
    outputExePath:      "DokaponSoF_patched.exe"
);
// skipped > 0 means some strings were truncated to fit MaxLength
```

### Offsets File Format

```
<decimal_offset>:<decimal_maxlength>
```

Example:
```
1048576:32
1048610:64
1048676:128
```

Each line corresponds to the same-numbered line in the texts file. `maxlength` is the original byte length of the text region (from `\p` start to end marker, inclusive).

---

## Pattern Analysis

`GameText.AnalyzePatterns` returns statistics about control code usage across all extracted strings:

```csharp
var stats = GameText.AnalyzePatterns("DokaponSoF.exe");
// stats["total_texts"]    — total string count
// stats["with_k"]         — strings using \k
// stats["with_colors"]    — strings using %Nc color codes
// stats["with_positions"] — strings using %Nx / %Ny positioning
// stats["with_variables"] — strings using %s or %d
// stats["avg_length"]     — average string byte length
```

---

## C# Data Model

```csharp
// Represents one extracted text entry
public sealed record TextEntry(
    string Text,      // UTF-8 decoded string including start marker and end marker
    int Offset,       // Byte offset in the executable where the string starts
    int MaxLength     // Original byte length available for this string
);
```

---

## See Also

- [HEX Patch Format](hex-format) — alternative approach to binary patching without text extraction
- Tools: Text Tools feature in DokaponSoFTools uses `GameText` for extraction and import
