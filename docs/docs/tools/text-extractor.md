---
title: Smart Text Tools
layout: default
nav_order: 1
parent: Tools
---

# Smart Text Tools
{: .no_toc }

Extract, browse, search, and reimport all localised strings from the game executable.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Smart Text Tools panel reads every text string embedded in `DOKAPON! Sword of Fury.exe` and presents them in a browsable, searchable interface. Strings are automatically sorted into four semantic categories so you can focus on the subset most relevant to your mod. A decoded preview panel strips control codes for readability, while a raw preview panel shows the exact bytes that will be written back to the executable.

The tool is non-destructive by default: extracting and browsing never modifies any file. Only the explicit import step writes data, and even then it operates on a copy of the executable you specify.

---

## Getting Started

1. Open `DokaponSoFTools.App.exe`.
2. Set your game directory in the main toolbar (the field at the top of the window labelled "Game Path"). The application will automatically locate `DOKAPON! Sword of Fury.exe` inside that directory.
3. Navigate to **Text Tools** in the left panel.
4. The exe path field will be pre-filled. Click **Extract Texts** to load all strings.

If you need to target a different executable (e.g. a modded copy), click **Browse...** next to the exe path field and select it manually.

---

## The Interface

### Category Tabs

After extraction the strings are split across five tabs. Each tab header shows the entry count in parentheses:

| Tab | Content |
|---|---|
| All (N) | Every extracted string |
| Dialog (N) | Multi-line dialogue, NPC speech, story text |
| Labels (N) | Short single-line names: items, skills, map locations |
| HUD/Stats (N) | Text with screen-position codes, used in UI overlays |
| System (N) | Short control-only entries, internal markers |

Switching tabs applies the current search filter to that category immediately.

### Search / Filter

The search box at the top of the list filters in real time across two fields simultaneously:

- The **decoded text** — what players see in-game (control codes stripped)
- The **raw text** — the literal string including all escape sequences

This means you can search for `%3c` to find every entry that uses colour code 3, or search for `Darkling` to find all dialogue lines mentioning that word, without switching modes.

### Entry List Columns

| Column | Description |
|---|---|
| Offset | Hex offset of the string in the executable |
| Category | Auto-detected category |
| Decoded Text | Human-readable version with control codes replaced by annotations |
| Byte Used | UTF-8 byte length of the raw string |
| Max Length | Maximum bytes available at this offset in the executable |
| Usage % | Byte Used / Max Length as a percentage |
| Overflow | Highlighted in red if Byte Used exceeds Max Length |

### Preview Panels

Selecting any entry updates two text panels on the right side of the screen:

**Decoded View** — shows the string with control codes translated into readable annotations:

```
--- Decoded View ---

You received [color=3]100[/color] gold. [WAIT]
Press a button to continue. [END]
```

**Raw View** — shows the exact bytes stored in the executable:

```
You received %3c100%0c gold.\kPress a button to continue.\z
```

The raw view is what gets written during import. It is never modified by the tool's display logic.

### Stats Bar

Below the toolbar a stats summary shows:

```
Total: 4821 | Readable: 3102 | With Colors: 287 | With Variables: 194
```

---

## Control Code Reference

The game uses a custom escape system within strings. The tool decodes all of the following for display:

| Raw Sequence | Meaning | Decoded Annotation |
|---|---|---|
| `\p` | Start of text block | (removed) |
| `\k` | Wait for player input | `[WAIT]` |
| `\z` | End of text block | `[END]` |
| `\n` | Line break | newline character |
| `\r` | Frame / scene break | `[FRAME]` |
| `\h` | Header marker | `[HEADER]` |
| `\m` | Modifier flag | `[x]` |
| `\,` | Comma literal | `[,]` |
| `\C` | Clear screen | `[CLR]` |
| `%Nc` | Colour index N (0 = reset) | `[color=N]` / `[/color]` |
| `%Nx` / `%NX` | Horizontal position N | `[pos:Nx]` |
| `%Ny` / `%NY` | Vertical position N | `[pos:Ny]` |
| `%NM` | Button icon N | `[BTN:N]` |
| `%s` / `%S` | String variable (width optional) | `[text]` / `[text:N]` |
| `%d` / `%D` | Integer variable (width optional) | `[num]` / `[num:N]` |

{: .note }
Decoding is applied only to the preview. The raw data stored in memory and used for export/import is never altered.

---

## Categorisation Logic

Entries are assigned to a category by inspecting their raw content and decoded length:

- **System** — decoded text is 2 characters or fewer (pure control sequences)
- **HUD** — contains a position code (`%Nx` or `%Ny`)
- **Labels** — contains `\h` (header marker), or is short (20 chars or fewer) and single-line
- **Dialog** — contains `\k` or `\z` with substantial text, contains `\r`, or is multi-line
- **Dialog** (fallback) — longer entries that do not match any other rule

---

## Exporting Strings

Click **Export Texts** in the toolbar after loading strings. A save dialog lets you choose the format:

### TXT (Binary-Safe Format)

Saves two files side by side:

- `texts.txt` — one raw string per line, UTF-8 encoded, control codes preserved verbatim
- `texts.offsets.txt` — one `offset:maxlength` pair per line, matching the order of `texts.txt`

Example `texts.offsets.txt`:

```
0x1A3F40:48
0x1A3F70:64
0x1A3FAC:32
```

This is the format required for reimport. The `maxlength` value is used to enforce null-padding safety.

### CSV

Columns: `Offset`, `MaxLength`, `Category`, `ByteUsed`, `Text`, `Decoded`

Useful for translation workflows in spreadsheet tools. Not suitable for direct reimport.

### JSON

Array of objects, one per entry:

```json
[
  {
    "offset": 1720128,
    "maxLength": 48,
    "category": "Dialog",
    "text": "You received %3c100%0c gold.\\k",
    "decoded": "You received [color=3]100[/color] gold. [WAIT]"
  }
]
```

Useful for programmatic processing. Not suitable for direct reimport.

---

## Importing Modified Strings

{: .warning }
Import writes directly to an executable file. Always specify a copy (e.g. `modded.exe`), never the original game file.

1. Click **Import Texts** in the toolbar.
2. Select your modified `texts.txt` file.
3. Select the matching `texts.offsets.txt` file.
4. Choose an output path for the patched executable.

The import process:

1. Reads each line from `texts.txt` as a raw UTF-8 string.
2. Reads the corresponding `offset:maxlength` from the offsets file.
3. Writes the string bytes at the specified offset in the executable.
4. If the new string is shorter than `maxlength`, the remaining bytes are null-padded to prevent stale data leaking.
5. If the new string is longer than `maxlength`, it is truncated to `maxlength` bytes at a valid UTF-8 boundary. The entry is counted as "skipped (truncated)" in the result log.

The result log reports: `Imported: N replaced, M truncated (binary-safe)`.

### Safe Modification Rules

- You may freely edit the human-readable portions of a string.
- Do not remove or reorder control codes (`\k`, `\z`, `%Nc`, etc.) unless you understand their effect in-game.
- Do not increase the byte length beyond `maxlength`. If a translation requires more space, the string must be truncated or the game binary must be patched separately to expand the field.
- Do not change the number of lines in `texts.txt` — the line count must match the offsets file exactly.

---

## Practical Example: Translating a Dialog Line

Suppose entry at offset `0x1C4A80` contains:

```
勇者よ、\nこの城を守れ！\k
```

After exporting to TXT, open `texts.txt` and find the corresponding line. Change it to:

```
Hero,\ndefend this castle!\k
```

Ensure the UTF-8 byte length does not exceed the `maxlength` value shown in the offsets file. Run import, point it at your modded exe, and the dialogue line will display the new text in-game.

---

## Troubleshooting

**No entries appear after extraction**
Verify that the exe path points to `DOKAPON! Sword of Fury.exe` and that the file exists and is not locked by another process.

**Many entries show as "Overflow" (red)**
This is expected for some entries where the game uses tightly packed string tables. These entries can still be exported and reimported, but you must not increase their byte length.

**Import reports "0 replaced"**
Check that the offsets file has the same number of lines as the texts file. A line-count mismatch causes all entries to be skipped.

**Modified exe crashes on launch**
A control code was likely removed or corrupted. Compare your modified `texts.txt` against the original export and restore any `\k`, `\z`, or `%` sequences that were accidentally deleted.

---

## Contributing

Found a bug or want to suggest an improvement? Open an issue on [GitHub](https://github.com/DiNaSoR/dokaponsof) or join the [Discord](https://discord.gg/HCrYwScDg5).

---

## License

This tool is part of DokaponSoFTools, released under The Unlicense (public domain). See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
