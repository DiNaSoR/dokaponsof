---
title: Tools
layout: default
nav_order: 2
has_children: true
---

# Modding Tools
{: .no_toc }

Eight integrated tools for exploring, extracting, and modifying DOKAPON! Sword of Fury assets.
{: .fs-6 .fw-300 }

All tools are part of the single `DokaponSoFTools.App.exe` WPF application. Set your game directory once using the toolbar at the top of the main window and every tool will populate automatically.

---

## Available Tools

### [Smart Text Tools](text-extractor)

Extract every localised string from the game executable (`DOKAPON! Sword of Fury.exe`). Entries are automatically categorised as Dialog, Labels, HUD/Stats, or System. A real-time search bar filters across decoded text and raw control-code sequences simultaneously. Export to binary-safe TXT (suitable for reimport), CSV, or JSON. Import a modified TXT file back into the executable with null-padding safety — no buffer overflows possible.

**Key capability:** control-code decoding. The raw format uses sequences such as `%3c` (colour), `%2x` (X position), `\k` (wait), and `\z` (end). The tool decodes all of these for a human-readable preview while keeping the raw data intact for safe reimport.

---

### [Voice Tools](voice-extractor)

Browse all four PCK audio archives in separate category tabs: BGM, Sound Effects, Voice (JP), and Voice (EN). Each tab shows every sound entry with its name, format (Opus / Raw), and file size. Double-click any entry to play it directly in the application — no external player needed. The in-app player uses the Concentus library to decode Opus audio in pure C#.

Supports individual sound replacement: select an entry, click "Replace Selected", and choose a replacement `.opus`, `.ogg`, or `.wav` file. When finished, save the modified archive back to disk with "Save PCK".

---

### [Asset Extractor](image-extractor)

Browse every supported game asset organised into five tabs: All, Textures (`.tex`), Sprites (`.spranm`), Fonts (`.fnt`), and Maps (`.mpd`). Each tab header shows the file count and combined size for that category. Selecting any file triggers a live preview:

- `.tex` — PNG extraction (with LZ77 decompression if needed)
- `.spranm` — PNG extraction or Cell-document rendering
- `.mpd` — full map assembly via MapRenderer (atlas + assembled grid)

Batch-extract the current category or all categories in one operation.

---

### [Font Files](font-extractor)

Supplementary documentation covering the `.fnt` format used in the game's font system and how the Asset Extractor handles font files. The main extraction workflow uses the Asset Extractor's Fonts tab.

---

### [Additional Tools](dokapon-extract)

Documentation for the four remaining tools built into the application:

- **Hex Editor** — Load `.hex` patch files, inspect all patch entries, detect offset conflicts, and apply patches to the game executable with optional automatic backup.
- **Video Tools** — Inventory game `.ogv` cutscenes, queue replacement videos (any common format), and batch-convert to OGV via FFmpeg.
- **Map Explorer** — Deep-dive viewer for `.mpd` cell-map files with atlas and map rendering, multiple palette support, and PNG export.
- **Animation Viewer** — Frame-by-frame `.spranm` playback with search, adjustable FPS, GIF export, PNG sequence export, and clipboard copy.
- **Game Scanner** — Full directory inventory: file counts and sizes by extension, directory breakdown, and key-file presence check.

---

## Technical Documentation

For developers working on modding tools, see the [Technical Reference](../technical/) section:

- [LZ77 Compression](../technical/lz77-compression) — compression algorithm used across multiple formats
- [MDL Model Format](../technical/mdl-format) — 3D model file structure
- [SPRANM Animation Format](../technical/spranm-format) — sprite animation system
- [MPD Map Format](../technical/mpd-format) — map and cell data

Want to contribute a tool or improvement? Open an issue or pull request on [GitHub](https://github.com/DiNaSoR/dokaponsof), or join the community on [Discord](https://discord.gg/HCrYwScDg5).
