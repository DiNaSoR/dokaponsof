---
title: Font Files
layout: default
nav_order: 7
parent: Tools
---

# Font Files
{: .no_toc }

Working with `.fnt` font bitmap files in DOKAPON! Sword of Fury.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

The game stores its font bitmaps in a proprietary `.fnt` format. Each `.fnt` file contains a PNG bitmap sheet of glyphs, optionally preceded by an LZ77-compressed header. The primary tool for working with `.fnt` files is the **Asset Extractor** — its Fonts tab lists every font file in the game and can preview and extract the embedded PNG.

This page documents the `.fnt` format itself and describes how to interpret font files for modding purposes.

---

## Known Font Files

The base game ships one primary font file:

| File | Location | Purpose |
|---|---|---|
| `Quarter.fnt` | `GameData/app/Font/Quarter.fnt` | Main game font (all in-game text rendering) |

Additional `.fnt` files may appear in language-specific subdirectories depending on the game version.

---

## File Format

### Structure

```
[Optional LZ77 header]     -- if the file starts with "LZ77" magic bytes
[PNG data]                 -- standard PNG with signature 89 50 4E 47 0D 0A 1A 0A
[Optional trailing data]   -- game-specific metadata, can be ignored for image extraction
```

The PNG component is a grayscale or RGBA bitmap sheet containing all glyph characters used by the game's text renderer. Each glyph occupies a fixed cell on the sheet, which the renderer references by character code offset.

### LZ77 Compression

Some `.fnt` files are compressed with the game's Nintendo-style LZ77 variant. If the first four bytes of the file are `4C 5A 37 37` (`LZ77` in ASCII), the file must be decompressed before the PNG can be read.

The Asset Extractor handles this transparently — selecting a compressed `.fnt` in the Fonts tab will still show the decompressed PNG in the preview panel.

See [LZ77 Compression](../technical/lz77-compression) for the full format specification.

### PNG Detection

The embedded PNG is located by scanning for the standard 8-byte PNG signature:

```
89 50 4E 47 0D 0A 1A 0A
```

The PNG data runs from this signature to the end of the `IEND` chunk (`49 45 4E 44 AE 42 60 82`).

---

## Extracting Font Bitmaps

### Using the Asset Extractor

1. Open `DokaponSoFTools.App.exe`.
2. Navigate to **Asset Extractor** in the left panel.
3. Switch to the **Fonts** tab.
4. Click any `.fnt` file to see the glyph sheet in the preview panel.
5. Set an output directory and click **Extract All** to save the PNG to disk.

The extracted PNG is the raw glyph sheet, ready to be edited in any image editor that supports PNG (Photoshop, GIMP, Aseprite, etc.).

---

## Modifying Font Bitmaps

{: .warning }
Reimporting a modified font PNG back into a `.fnt` file requires manually replacing the embedded PNG bytes at the correct offset. There is no automated reimport for font files in the current version of the toolkit.

### Manual Reimport Process

1. Note the byte offset of the PNG signature within the original `.fnt` file (available from any hex editor).
2. Prepare your modified PNG — it must be identical in dimensions and colour format to the original. Changing the image dimensions will break the game's glyph indexing.
3. Open the `.fnt` file in a hex editor.
4. Replace the bytes from the PNG signature to the `IEND` chunk with your new PNG data.
5. If the new PNG is smaller than the original, null-pad the remaining bytes to preserve file size.
6. If the new PNG is larger, the file size will grow — this may or may not be compatible depending on whether the game loads the file by absolute size.

{: .note }
Automated font reimport is planned for a future version of the toolkit. Check the [GitHub repository](https://github.com/DiNaSoR/dokaponsof) for updates.

---

## Common Modding Use Cases

### Font Translation

To translate the game into a language with a different character set (e.g. adding Latin Extended glyphs, or replacing CJK glyphs with a custom Latin font):

1. Extract the glyph sheet PNG from `Quarter.fnt`.
2. Identify the glyph layout — which cell corresponds to which character code.
3. Redraw or replace glyphs in the appropriate cells.
4. Reimport the PNG back into the `.fnt` file using the manual process above.

### Visual Font Reskin

To change the visual style of the game's text (e.g. making it bolder, adding an outline, or changing the colour):

1. Extract the glyph sheet.
2. Apply your desired visual treatment in an image editor, keeping glyph positions identical.
3. Reimport using the manual process.

---

## Troubleshooting

**Fonts tab shows no files**
Confirm that your game directory is set and that `GameData/app/Font/` exists within it.

**Preview shows nothing**
The `.fnt` file may be compressed and decompression may have failed, or the file may not contain a standard PNG. Check the status log for error messages.

**Extracted PNG appears all white or all black**
This is normal for some glyph sheets — the visible glyphs are rendered using the alpha channel. Open the extracted PNG in an editor and examine the alpha channel separately.

---

## Technical Reference

For more on the compression format used in font files, see [LZ77 Compression](../technical/lz77-compression).

---

## Contributing

Found a bug or want to suggest an improvement? Open an issue on [GitHub](https://github.com/DiNaSoR/dokaponsof) or join the [Discord](https://discord.gg/HCrYwScDg5).

---

## License

This tool is part of DokaponSoFTools, released under The Unlicense (public domain). See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
