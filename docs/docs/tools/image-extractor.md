---
title: Asset Extractor
layout: default
nav_order: 3
parent: Tools
---

# Asset Extractor
{: .no_toc }

Browse, preview, and batch-extract all game assets by file type.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The Asset Extractor scans a game directory (or any directory you choose) for all supported asset file types and presents them in a tabbed browser. Selecting any file immediately renders a live preview in the right panel — including full map assembly for `.mpd` files and PNG extraction from compressed textures. When you are ready to export, a single click batch-extracts an entire category.

---

## Supported File Types

| Extension | Type | Preview Method |
|---|---|---|
| `.tex` | Texture | PNG extraction; LZ77 decompression if required |
| `.spranm` | Sprite animation | PNG extraction from embedded texture, or Cell-document rendering |
| `.fnt` | Font bitmap | PNG extraction |
| `.mpd` | Map / cell data | MapRenderer: full map assembly + atlas |

---

## Getting Started

1. Open `DokaponSoFTools.App.exe`.
2. Set your game directory in the main toolbar. The Asset Extractor automatically scans the entire game directory tree.
3. Navigate to **Asset Extractor** in the left panel.
4. The tab headers update to show file counts and combined sizes (e.g. `Textures (142, 8.3 MB)`).

To scan a different directory — for example, a folder containing only the files you are working on — click **Browse Input** in the toolbar and select that folder.

---

## The Interface

### Category Tabs

| Tab | Contents |
|---|---|
| All (N, size) | Every supported file across all types |
| Textures (N, size) | `.tex` files |
| Sprites (N, size) | `.spranm` files |
| Fonts (N, size) | `.fnt` files |
| Maps (N, size) | `.mpd` files |

The tab header format is `Category (count, total size)`. Switching tabs narrows the file list to that category and updates the active selection for batch extraction.

### File List

The left side of the view shows a scrollable list of files in the current tab. Each entry shows the filename. The list is populated recursively, so files from all subdirectories appear together.

### Preview Panel

Selecting any file in the list triggers an automatic preview on the right side:

**For `.mpd` files:**
The MapRenderer loads the cell document, decompresses it if LZ77-compressed, assembles the texture atlas from all palette entries, and renders the assembled map grid into a single image. If map rendering fails (e.g. the file is a cell-only document with no grid data), the raw atlas is shown instead.

**For `.spranm` files:**
The extractor looks for an embedded PNG texture. If found, the PNG is displayed directly. If not found, it attempts to load the file as a Cell document and renders it the same way as an `.mpd`. Some `.spranm` files are runtime-only (no embedded texture) and show "No embedded image" in the info panel.

**For `.tex` files:**
The extractor scans for a PNG signature (`89 50 4E 47`). If found, the PNG is decoded and displayed. If the file begins with `LZ77`, it is decompressed first and then searched for a PNG.

**For `.fnt` files:**
Same PNG-signature search as `.tex`.

The preview info panel below the image shows:

```
Name: BoxWin.tex
Size: 14.2 KB
Path: C:\...\GameData\app\Field\TXD\BoxWin.tex
```

For cell documents it also shows the record count.

### Output Directory

Before extracting, set the output directory using the **Browse Output** button in the toolbar. Extracted files are written there, mirroring the subdirectory structure of the source.

---

## Extracting Assets

### Batch Extract Current Tab

1. Make sure an output directory is set.
2. Switch to the tab you want to extract (Textures, Sprites, Fonts, Maps, or All).
3. Click **Extract All** in the toolbar.
4. A progress log updates in the main status log panel at the bottom of the application window.

The extraction result reports: `Extraction complete: N succeeded, M failed`.

### What Gets Written

Each supported file is processed as follows:

- **`.tex`** — the embedded PNG is extracted and saved as `filename.png`. LZ77-compressed files are decompressed transparently.
- **`.spranm`** — the embedded PNG texture is extracted and saved as `filename.png`.
- **`.mpd`** — the assembled map image is rendered and saved as `filename.png`.
- **`.fnt`** — the embedded PNG is extracted and saved as `filename.png`.

Files that contain no extractable image (e.g. runtime-only `.spranm` without an embedded texture) are counted in the failed total and skipped.

---

## Game Directory Structure

Understanding where assets live helps when targeting specific categories:

```
GameData/app/
  Battle/
    Effect/        # Battle spell and effect animations (.spranm)
    Ability/       # Character ability assets
    Magic/         # Magic animations (.spranm)
  Field/
    Face/          # Character face animations (.spranm)
    Map/           # Map cell data (.mpd)
    TXD/           # UI textures (.tex)
    TXD/en/        # English UI texture variants
    Guidebook/     # In-game guide page images (.tex)
  Font/            # Game fonts (.fnt)
  Title/           # Title screen assets (.tex, .spranm)
BGM.pck            # Background music
SE.pck             # Sound effects
Voice.pck          # Japanese voice
Voice-en.pck       # English voice
```

---

## Preview Limitations

Not all files produce a visible preview:

| Situation | Displayed |
|---|---|
| `.spranm` with embedded PNG | PNG texture shown |
| `.spranm` as Cell document | Assembled atlas shown |
| `.spranm` runtime-only | "No embedded image (raw sprite data)" |
| `.mpd` with full map data | Assembled map shown |
| `.mpd` atlas-only | Raw texture atlas shown |
| `.mpd` with no texture | No preview |
| `.tex` with PNG | PNG shown |
| `.tex` compressed only | PNG after decompression |
| `.fnt` with PNG | PNG shown |

A missing preview does not mean the file is corrupt — it may simply be a data container without an embedded image (e.g. a `.spranm` that references an external atlas at runtime).

---

## Practical Example: Extracting All UI Textures

1. In the main toolbar, set your game directory.
2. Navigate to Asset Extractor and click **Textures** tab.
3. Confirm the tab header shows a reasonable count (the base game has over 100 `.tex` files).
4. Click **Browse Output** and choose a destination folder such as `C:\DokaponMods\textures`.
5. Click **Extract All**.
6. Open your destination folder. You will find PNG files corresponding to every texture, ready for editing in any image editor.

To reimport a modified texture, you must patch the `.tex` file directly (replacing the embedded PNG bytes), which is a manual operation described in the [technical documentation](../technical/).

---

## Practical Example: Previewing a Map

1. Switch to the **Maps** tab.
2. Scroll to a file such as `MAP_01.mpd` and click it.
3. The preview panel renders the assembled map — all tiles laid out on the grid using the first available palette.
4. The info panel shows grid dimensions, record count, palette count, and texture size.

To export the rendered map as a high-resolution PNG, use the **Map Explorer** tool (see [Additional Tools](dokapon-extract#map-explorer)), which supports up to 4096-pixel export resolution and palette switching.

---

## Troubleshooting

**Tab headers show 0 files**
Confirm the game path or input directory is set correctly and that `DOKAPON! Sword of Fury` files are present. The Asset Extractor only counts `.tex`, `.spranm`, `.fnt`, and `.mpd` files. Other extensions are ignored.

**Preview shows nothing for a .tex file**
The texture may be a raw data block without an embedded PNG, or the LZ77 decompression may have failed due to file corruption. Check the status log for error messages.

**Extraction reports many failures**
Runtime-only `.spranm` files (those without embedded PNG textures) always fail extraction since there is no image to write. This is expected — the failure count includes these files.

**Output files are missing subdirectory structure**
All extracted files are written flat into the output directory. Subdirectory mirroring is not currently implemented.

---

## Contributing

Found a bug or want to suggest an improvement? Open an issue on [GitHub](https://github.com/DiNaSoR/dokaponsof) or join the [Discord](https://discord.gg/HCrYwScDg5).

---

## License

This tool is part of DokaponSoFTools, released under The Unlicense (public domain). See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
