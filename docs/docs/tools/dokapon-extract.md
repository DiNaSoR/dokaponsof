---
title: Additional Tools
layout: default
nav_order: 8
parent: Tools
---

# Additional Tools
{: .no_toc }

Hex Editor, Video Tools, Map Explorer, Animation Viewer, and Game Scanner.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Hex Editor
{: #hex-editor }

Apply community-made `.hex` patch files to the game executable.
{: .fs-5 .fw-300 }

### Overview

The Hex Editor is a patch applier, not a full binary editor. It loads one or more `.hex` files containing byte-level patches, displays all patch entries before you commit, detects conflicts between patch sources, and writes the result to the game executable with an optional automatic backup.

### Getting Started

1. Navigate to **Hex Editor** in the left panel.
2. The exe path is pre-filled from the game directory you set in the main toolbar. Click **Browse...** to override it.
3. Add patch files using **Add Hex Files** (select individual `.hex` files) or **Add Hex Folder** (load every `.hex` file from a directory).
4. Review the patch list and conflict list before applying.
5. Click **Apply Patches**.

### The Interface

**Patch List**

Each loaded `.hex` file contributes one or more patch entries. The list shows:

| Column | Description |
|---|---|
| File | Source `.hex` filename |
| Offset | Hex offset in the executable where the patch writes |
| Size | Number of bytes the patch writes |
| Preview | First 16 bytes of the patch data in hex |

**Conflict List**

Conflicts are detected automatically whenever patch files are added or removed. A conflict is any situation where two patch entries write to overlapping byte ranges in the executable. Each conflict shows:

| Column | Description |
|---|---|
| Type | Conflict category (e.g. "Overlap") |
| File 1 | First conflicting source file |
| File 2 | Second conflicting source file |
| Offset | Hex offset where the overlap begins |

{: .warning }
Conflicts do not prevent applying patches, but the result may be unpredictable. Resolve conflicts by disabling one of the conflicting patch files before applying.

**Summary Bar**

Below the toolbar a summary shows: total number of patches loaded, total bytes patched, and number of distinct source files.

### Enabling / Disabling Patch Files

Each entry in the file list has a checkbox. Unchecked files are excluded from patch parsing — their entries disappear from the patch list and conflict detection runs again on the remaining checked files. Click **Remove Unchecked** to remove disabled files from the list entirely.

### Backup Option

The **Create Backup** checkbox (enabled by default) writes a copy of the original executable to `filename.exe.bak` before applying any patches. Disable this only if you have already made a manual backup.

### Applying Patches

Click **Apply Patches**. The tool:

1. Reads the current executable into memory.
2. For each patch entry in offset order, writes the patch bytes at the specified offset.
3. If **Create Backup** is checked, writes the original to `filename.exe.bak` first.
4. Writes the patched result over the original executable.

The status log reports: `Applied N/M patches to filename.exe`.

### HEX File Format

`.hex` patch files use a simple line-based format:

```
# Comment lines begin with #
# Offset (hex) : space-separated hex bytes
0x1A3F40: 90 90 90 EB 05
0x1A3F50: 48 8B 0D 12 34 56 78
```

- Offsets are absolute file offsets in the executable, written in hexadecimal with `0x` prefix.
- Bytes are written as two-digit hex values separated by spaces.
- Lines beginning with `#` are comments and are ignored.
- Blank lines are ignored.

### Practical Example: Applying a Community Patch

Suppose the community has released a `translation_v1.hex` patch:

1. Download `translation_v1.hex`.
2. In Hex Editor, click **Add Hex Files** and select `translation_v1.hex`.
3. Verify the patch list shows the expected entries. Check the conflict list — if it is empty, there are no issues.
4. Ensure **Create Backup** is checked.
5. Click **Apply Patches**.
6. Launch the game. If something goes wrong, restore from the `.bak` file.

---

## Video Tools
{: #video-tools }

Manage and replace cutscene video files in OGV format.
{: .fs-5 .fw-300 }

### Overview

Video Tools scans the game directory for `.ogv` cutscene files, shows metadata for each one, and converts replacement videos from any common format to the OGV format expected by the game. Conversion is delegated to FFmpeg, which must be installed separately.

### FFmpeg Requirement

Video conversion requires FFmpeg to be available on the system PATH. The tool checks on startup and reports its status in the toolbar:

- `FFmpeg: <version string>` — found and ready
- `FFmpeg not found` — install FFmpeg and ensure it is on the PATH

Download FFmpeg from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add the `bin` directory to your Windows PATH environment variable.

### The Interface

**Game Videos List**

After setting the game directory, the tool scans for all `.ogv` files and displays:

| Column | Description |
|---|---|
| Name | Filename of the cutscene |
| Resolution | Width × Height in pixels |
| Duration | Playback duration |
| Size | File size on disk |

**Replacements Queue**

The lower panel shows videos queued for replacement, with their status (`Pending`, `Done`, or `Failed`).

**Conversion Settings**

- **Width / Height** — output resolution (default 1280×720)
- **Video Quality** — OGV Theora quality scale 0–10 (default 8; higher = better quality and larger file)
- **Audio Quality** — Vorbis quality scale 0–10 (default 4)

### Queuing a Replacement

1. Click **Add Replacement**.
2. Select a source video file (MP4, AVI, MKV, MOV, WebM, or any format FFmpeg supports).
3. The tool matches the source filename stem to a game `.ogv` file automatically (e.g. `opening.mp4` → `opening.ogv`). If no match is found, the target name is derived from the source filename.
4. The replacement appears in the queue with status `Pending`.

Repeat for as many videos as needed before processing.

### Processing Replacements

Click **Process Replacements** to convert all queued videos. For each entry:

1. FFmpeg converts the source video to OGV format using the specified quality settings.
2. The output is written directly to `GameData/app/<target_name>.ogv` in the game directory.
3. The status column updates to `Done` or `Failed`.

{: .warning }
Processing overwrites the original OGV files in the game directory. Back up the originals beforehand if you may want to revert.

Progress for each conversion is shown as a progress bar in the main status log area.

### Practical Example: Replacing the Opening Cutscene

1. Prepare your replacement video as `opening.mp4` (any resolution; the tool will rescale).
2. In Video Tools, click **Add Replacement** and select `opening.mp4`.
3. Verify the target name matches `opening.ogv` in the list.
4. Set your desired output resolution and quality.
5. Click **Process Replacements**.
6. Launch the game and watch the opening to confirm the replacement.

---

## Map Explorer
{: #map-explorer }

Deep-dive viewer for `.mpd` cell-map files with palette switching and PNG export.
{: .fs-5 .fw-300 }

### Overview

Map Explorer is a dedicated viewer for the game's map and cell-data files (`.mpd`). It loads a file, decodes its internal chunks, renders the texture atlas and the assembled map image, and presents detailed metadata about the file's structure. Multiple colour palettes can be cycled through in real time. Both the atlas and the assembled map can be exported as high-resolution PNG files.

### Getting Started

1. Navigate to **Map Explorer** in the left panel.
2. Set the game directory (or click **Scan** to refresh the file list).
3. Click any file in the left list to load it. Loading is asynchronous — a busy indicator appears while the file is parsed.

### The Interface

**File List**

The left panel lists every `.mpd` file found recursively in the game directory. Files load on single click.

**Display Area**

The right panel has two tabs:

- **Atlas** — the raw texture atlas for the selected palette: all tiles laid out in a grid
- **Map** — the fully assembled map: tiles placed according to the cell-map grid data

Both images support the ZoomPanImage control (scroll to zoom, drag to pan).

**Palette Slider**

If the map file contains multiple colour palettes, a slider appears beneath the display. Dragging the slider switches the palette in real time — both the atlas and the assembled map update immediately. The label shows the current palette index and total count.

**Records and Parts Lists**

Two data grids on the right side show the decoded cell records and texture parts parsed from the file. These are primarily for technical inspection.

**Report Text**

A text panel shows a structured summary of the loaded file:

```
File: MAP_01.mpd
Raw Size: 245,760 bytes
Decompressed: 512,000 bytes
LZ77: Yes
Grid: 32x24
Records: 768
Chunks: Cell, Palette, Texture, CellMap
Palettes: 4
Texture: 512x512 (Embedded PNG)
Parts: 64
Map: 32x24
Unique values: 128
```

### Exporting

- **Export Map** — saves the assembled map image as PNG at up to 4096×4096 pixels. A save dialog appears with the map filename pre-filled.
- **Export Atlas** — saves the raw texture atlas as PNG.
- **Export Report** — saves the text report as a `.txt` or `.md` file.

### How Rendering Works

The MapRenderer processes the file in three stages:

1. **Load** — reads the raw bytes, detects and performs LZ77 decompression if the `LZ77` magic is present.
2. **Parse** — locates named chunks (`Cell`, `Palette`, `Texture`, `CellMap`) within the decompressed data and decodes each one.
3. **Render** — builds a `SKBitmap` (via SkiaSharp) by blitting each tile from the atlas onto the correct grid position according to the cell-map values.

The atlas is built by applying the selected palette to the indexed-colour tile data.

### Practical Example: Examining a Field Map

1. In Map Explorer, load `GameData/app/Field/Map/MAP_01.mpd`.
2. Switch to the **Map** tab. The assembled field map renders — all tiles placed in their correct positions.
3. Move the palette slider to preview how the map looks under different colour palettes.
4. Click **Export Map** and save as `MAP_01_map.png` for use in mapping tools or documentation.
5. Click **Export Report** to save a text summary for reference.

---

## Animation Viewer
{: #animation-viewer }

Frame-by-frame preview and export for `.spranm` sprite animations.
{: .fs-5 .fw-300 }

### Overview

The Animation Viewer browses all `.spranm` animation files, renders their frames using the SpranmRenderer, and plays them back at an adjustable frame rate. A search box filters the file list in real time. Animations can be exported as animated GIFs or PNG frame sequences. Individual frames can be copied to the clipboard.

### Getting Started

1. Navigate to **Animations** in the left panel.
2. Set the game directory. The viewer scans for all `.spranm` files recursively.
3. Click any file in the left list to load it.

### The Interface

**File List with Search**

The left column shows all `.spranm` files. Type in the search box to filter by filename — the list updates as you type. Click any entry to load that animation.

**Frame Display**

The centre area shows the current frame rendered against a dark background. Rendering uses nearest-neighbour scaling to preserve pixel-art fidelity.

**Playback Controls**

| Control | Action |
|---|---|
| Prev | Step to the previous frame |
| Play / Stop | Toggle animation playback |
| Next | Step to the next frame |
| FPS slider | Adjust playback speed (1–30 FPS) |

The frame counter shows `Frame N / Total` in the centre of the control bar.

**Keyboard Shortcuts**

When the Animation Viewer panel is focused:

| Key | Action |
|---|---|
| Space | Toggle Play / Stop |
| Left arrow | Previous frame |
| Right arrow | Next frame |

**Animation Info Bar**

Below the playback controls, a text bar shows parsed metadata for the loaded file:

```
[Self-contained] Seq: 8 | Spr: 12 | Grp: 3 | Parts: 48 | Tex: 256x256
```

| Field | Meaning |
|---|---|
| Type | `Self-contained` (has embedded texture) or `Runtime/Player asset` (no embedded texture) |
| Seq | Number of sequence (frame group) entries |
| Spr | Number of sprite definitions |
| Grp | Number of animation groups |
| Parts | Number of texture parts |
| Tex | Embedded texture dimensions |

If the file is a runtime-only asset with no embedded PNG, the info bar notes this and no frames are rendered.

**Export Toolbar**

| Button | Action |
|---|---|
| Export GIF | Save all frames as an animated GIF |
| Export Atlas | Save the embedded texture atlas as a PNG |
| Copy Frame | Copy the current frame to the Windows clipboard |

### Exporting as GIF

Click **Export GIF**. A save dialog appears with a default name based on the source file. Selecting a `.gif` extension writes an animated GIF:

- Frame delays are derived from the sequence duration values in the `.spranm` data.
- Each frame is colour-quantised to 256 colours (5-bit per channel) with index 0 reserved for transparency.
- The GIF uses the NETSCAPE 2.0 extension for infinite looping.
- Maximum canvas size is the largest frame size across all sequences.

Selecting a `.png` extension exports a numbered PNG sequence:

```
animation_0000.png
animation_0001.png
animation_0002.png
...
```

Each file in the sequence is a full-colour RGBA PNG, suitable for use in video editors or sprite sheet tools.

### Exporting the Atlas

Click **Export Atlas** to save the raw embedded texture sheet as a PNG. This is the source sprite sheet that the renderer samples to compose each frame. Useful for manual sprite editing.

### Self-Contained vs. Runtime Assets

`.spranm` files come in two varieties:

**Self-contained** — include an embedded PNG texture and all the data needed to render frames independently. These files show a preview in the viewer and can be exported.

**Runtime / Player asset** — contain animation control data (sequences, timing) but reference an external texture that is loaded separately at runtime. These files show metadata in the info bar but no visual preview, and cannot be exported as GIF.

### Practical Example: Exporting a Battle Effect

1. In the Animation Viewer, type `EFFECT` in the search box.
2. Click `EFFECT00_00.spranm` to load it.
3. Press **Play** to watch the animation loop.
4. Adjust the FPS slider to preview at different speeds.
5. Click **Export GIF** and save as `EFFECT00_00.gif`.
6. Open the GIF in a browser or image viewer to confirm it looks correct.

---

## Game Scanner
{: #game-scanner }

Full inventory of the game directory with extension statistics and key-file check.
{: .fs-5 .fw-300 }

### Overview

The Game Scanner performs a complete recursive scan of the game directory and produces a structured report. It breaks down file counts and sizes by extension, lists top-level directories by file count, and checks whether critical game files are present. The report can be saved to disk.

### Getting Started

1. Navigate to **Game Scanner** in the left panel.
2. Set the game directory in the main toolbar. The scan runs automatically.
3. Click **Scan** to re-run after making changes to game files.

### The Interface

**File Stats Grid**

The upper data grid lists every file extension found in the game directory, sorted by total size descending:

| Column | Description |
|---|---|
| Extension | File extension (e.g. `.spranm`, `.pck`) |
| Count | Number of files with this extension |
| Total Size | Combined size of all files with this extension |

This gives a quick overview of where disk space is used and which asset types are most numerous.

**Directories Grid**

The lower data grid lists top-level directories inside the game folder, sorted by file count descending:

| Column | Description |
|---|---|
| Name | Directory name |
| Path | Full path |
| File Count | Total files (recursive) |
| Total Size | Combined size (recursive) |

**Report Text Panel**

A text area on the right shows the full formatted report:

```
Game Directory: C:\...\DOKAPON ~Sword of Fury~
Total Files: 2,847
Total Size: 1.24 GB

By Extension:
  .spranm         843 files      312.4 MB
  .tex            142 files       68.1 MB
  .mpd             78 files       45.2 MB
  .pck              4 files      387.6 MB
  ...

Directories:
  GameData            2,831 files      1.23 GB
  GameData/app        2,821 files      1.22 GB
  ...

Key Files:
  [OK] DOKAPON! Sword of Fury.exe
  [OK] GameData/app/BGM.pck
  [OK] GameData/app/SE.pck
  [OK] GameData/app/Voice.pck
  [OK] GameData/app/Voice-en.pck
  [OK] GameData/app/Font/Quarter.fnt
  [OK] GameData/Windows/Save
  [OK] Setting.ini
```

The `[OK]` / `[--]` prefix in the Key Files section indicates whether each critical file or directory is present. A `[--]` entry means that file is missing — this may indicate an incomplete game installation or that a modded file was accidentally deleted.

### Exporting the Report

Click **Export Report** to save the text report as a `.txt` file. This is useful for sharing your game directory inventory with other modders or for keeping a record of the file state before applying mods.

### Practical Uses

**Verifying a Clean Installation**
After installing the game, run the Game Scanner and confirm all Key Files show `[OK]`. If any are missing, verify the game files through Steam.

**Before Modding**
Run a scan and export the report. After applying mods, run again and compare — any new or changed files will be apparent from size differences.

**Investigating Disk Usage**
The extension breakdown shows which asset types consume the most space. PCK archives (`.pck`) typically dominate due to uncompressed audio. Knowing this helps prioritise which archives are worth working with.

---

## Contributing

Found a bug in any of these tools or want to suggest an improvement? Open an issue on [GitHub](https://github.com/DiNaSoR/dokaponsof) or join the [Discord](https://discord.gg/HCrYwScDg5).

---

## License

These tools are part of DokaponSoFTools, released under The Unlicense (public domain). See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
