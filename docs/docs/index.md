---
title: Home
layout: default
nav_order: 1
description: "Documentation for DOKAPON! Sword of Fury Modding Tools"
permalink: /
---

<div class="banner-container">
  <img src="{{ '/assets/images/dokabannar.png' | relative_url }}" alt="Dokapon Banner" class="banner-image">
</div>

# DOKAPON! Sword of Fury Modding Tools
{: .fs-9 }

A native Windows desktop toolkit for exploring, extracting, and modifying the assets of DOKAPON! Sword of Fury (PC version).
{: .fs-6 .fw-300 }

[Get Started](#quick-start){: .btn .btn-primary .fs-5 .mb-4 .mb-md-0 .mr-2 }
[Browse Tools](tools/){: .btn .fs-5 .mb-4 .mb-md-0 }

---

## About This Project

**DokaponSoFTools** is a C#/.NET 8 WPF application that gives modders direct access to every major file format in DOKAPON! Sword of Fury. It ships as a single self-contained executable (`DokaponSoFTools.App.exe`) — no installation, no Python, no runtime dependencies required.

The application follows a navigator-based layout: set your game directory once in the toolbar, and every tool in the left-hand panel automatically points to the right files.

### Official Links

- [Steam Store Page](https://store.steampowered.com/app/3077020/)
- [Official Dokapon Twitter](https://x.com/dokapon_jp/)
- [Sting Entertainment Twitter](https://x.com/sting_pr/)

---

## Quick Start
{: #quick-start }

1. **Download** `DokaponSoFTools.App.exe` from the [GitHub releases page](https://github.com/DiNaSoR/dokaponsof/releases).
2. **Run** the executable — no installation required.
3. **Set your game path**: click the folder icon in the main toolbar and browse to your DOKAPON! Sword of Fury installation directory (e.g. `C:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~`).
4. Once the path is set, all tools populate automatically. Select any tool from the left navigation panel.

{: .note }
The application saves your game path between sessions. You only need to set it once.

{: .warning }
Always keep backups of original game files before replacing or patching anything. The application offers backup creation where relevant, but it is still good practice to keep copies.

---

## Feature Highlights

The application contains **eight tools** accessible from the left navigation panel:

### Asset Extractor
Browse all game assets organised by file type — textures (`.tex`), sprites (`.spranm`), maps (`.mpd`), and fonts (`.fnt`). Select any file to see a live preview, including full map rendering for `.mpd` files, then batch-extract an entire category with one click.
[Learn more](tools/image-extractor){: .btn .btn-outline .btn-sm }

### Smart Text Tools
Load the game executable and extract every localised string. Entries are automatically sorted into four categories: Dialog, Labels, HUD/Stats, and System. A search bar filters across decoded and raw text simultaneously. Export to TXT (binary-safe reimport format), CSV, or JSON.
[Learn more](tools/text-extractor){: .btn .btn-outline .btn-sm }

### Voice Tools
View all four PCK audio archives (BGM, Sound Effects, Voice JP, Voice EN) in category tabs. Double-click any entry to play it directly in the application using the built-in Concentus Opus decoder. Replace individual sounds with your own audio files, then save a modified PCK back to disk.
[Learn more](tools/voice-extractor){: .btn .btn-outline .btn-sm }

### Hex Editor
Apply community `.hex` patch files to the game executable. Load single files or entire folders of patches, inspect every patch entry before applying, and detect offset conflicts between multiple patch sources automatically.
[Learn more](tools/dokapon-extract#hex-editor){: .btn .btn-outline .btn-sm }

### Video Tools
See all `.ogv` cutscene files in the game with resolution, duration, and size metadata. Queue replacement videos in any common format (MP4, AVI, MKV, MOV, WebM) and convert them to the correct OGV format via FFmpeg in a single pass.
[Learn more](tools/dokapon-extract#video-tools){: .btn .btn-outline .btn-sm }

### Map Explorer
Browse every `.mpd` cell-map file. The explorer renders both the raw texture atlas and the fully assembled map side by side, with a palette-switching slider for files that contain multiple colour palettes. Export the rendered map or atlas as a PNG.
[Learn more](tools/dokapon-extract#map-explorer){: .btn .btn-outline .btn-sm }

### Animation Viewer
Browse and preview all `.spranm` sprite animation files. A search filter narrows the list instantly. Playback controls (Play/Stop/Prev/Next) let you step through frames manually or watch the animation loop at an adjustable FPS. Export the full animation as an animated GIF or as a PNG frame sequence.
[Learn more](tools/dokapon-extract#animation-viewer){: .btn .btn-outline .btn-sm }

### Game Scanner
Point the scanner at your game directory for a complete inventory: file counts and sizes broken down by extension, a directory-by-directory summary, and a key-file checklist that confirms whether the main executable and all four PCK archives are present.
[Learn more](tools/dokapon-extract#game-scanner){: .btn .btn-outline .btn-sm }

---

## Technical Reference

For modders and tool developers who want to understand the underlying file formats:

| Format | Description |
|---|---|
| [LZ77 Compression](technical/lz77-compression) | Nintendo-style compression used across `.tex`, `.mpd`, and `.fnt` files |
| [MPD Map Format](technical/mpd-format) | Cell-based map container with palette, texture atlas, and grid data |
| [SPRANM Animation Format](technical/spranm-format) | Sprite animation format with embedded PNG textures |
| [MDL Model Format](technical/mdl-format) | 3D model format for characters and objects |

---

## System Requirements

| Requirement | Minimum |
|---|---|
| OS | Windows 10 x64 or later |
| Runtime | Self-contained (.NET 8 bundled) |
| Game | DOKAPON! Sword of Fury (Steam) |
| FFmpeg | Required only for Video Tools |

---

## Important Notes

{: .warning }
These tools are for modding purposes only. Please support the developers by purchasing the game on Steam. Do not use these tools for piracy.

---

## Community Links

- Discord: [Dokapon Community](https://discord.gg/HCrYwScDg5)
- Reddit: [r/dokaponofficial](https://reddit.com/r/dokaponofficial/)
- Developer: [Sting Entertainment](https://www.sting.co.jp/)

---

## Contributing

We welcome contributions from the community:

- Report bugs or unexpected behaviour on the GitHub issue tracker
- Submit pull requests with fixes or new features
- Share your mods and discoveries on Discord

---

## License

This project is released under The Unlicense — dedicated to the public domain.

- Use freely for any purpose
- Modify and distribute without restrictions
- No attribution required
- No warranty provided

See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
