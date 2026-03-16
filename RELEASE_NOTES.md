# ⚔️ DokaponSoFTools v0.4.0 — C# Rewrite Release

## 🔥 Major: Complete C#/.NET 8 Rewrite

The entire toolkit has been rewritten from Python/PyQt6 to **C#/.NET 8 WPF**. Single self-contained executable, no Python or runtime dependencies needed.

**Build Date:** 2026-03-16
**Platform:** Windows 10/11 (64-bit)
**Framework:** .NET 8, WPF, self-contained single-file EXE (~165 MB)
**License:** GNU General Public License v3.0

---

## ✨ New Tools & Features

### 🎭 Animation Viewer (NEW)
- Full **spranm sprite animation** parser and renderer
- Parses all sections: Sequence, Sprite, SpriteGp, TextureParts
- LZ77 decompression for compressed animation files
- **Bottom-right positioning** model (reverse-engineered from EXE)
- Playback with Play/Stop, frame stepping, FPS slider (1-30)
- **GIF export** with LZW encoding
- **PNG sequence export** for individual frames
- **Atlas PNG export** for raw texture atlas
- Keyboard shortcuts: Space (play/stop), arrows (frame step), Ctrl+C (copy)
- Search/filter across 850+ animation files
- Auto-classifies: Self-contained vs Runtime/Player assets

### 📝 Smart Text Tools (REWRITTEN)
- **Control code decoding**: `\p`, `\k`, `\z`, `\n`, `\h`, `\r`, `\m`, `\C`, `%Nc` colors, `%s`/`%d` variables, `%Nx`/`%Ny` positioning, `%NM` button icons
- **Auto-categorization** of 5107 entries: Dialog, Labels, HUD/Stats, System
- Category tabs with counts
- **Decoded preview** (human-readable) + Raw preview (binary-safe)
- Search across decoded AND raw text
- Export as **TXT** (binary-safe reimport), **CSV**, or **JSON**
- Usage % column showing bytes used vs max allocation
- **100% binary-safe import** — Core GameText unchanged

### 🎙️ Voice Tools (ENHANCED)
- **4 PCK category tabs**: BGM (47 tracks), Sound Effects, Voice (JP), Voice (EN)
- Auto-discovers all PCK files from game directory
- **In-app Opus audio playback** via Concentus decoder
- Double-click any sound to play
- Play/Stop controls with "Now Playing" indicator
- Extract all, replace individual sounds, save modified PCK

### 🔍 Game Scanner (NEW)
- Full directory analysis with file type stats
- Directory listing with file counts and sizes
- Key game file validation checklist
- Exportable scan reports

### 📦 Asset Extractor (ENHANCED)
- **Category tabs**: All, Textures (.tex), Sprites (.spranm), Fonts (.fnt), Maps (.mpd)
- **File size totals** in tab headers (e.g. "Textures (185, 42.3 MB)")
- **MapRenderer preview** for .mpd files (assembled tile maps, not raw atlas)
- LZ77 decompression for compressed textures
- Auto-scans when game path is set

### 🗺️ Map Explorer (ENHANCED)
- Atlas and map rendering with palette switching
- **Export map as PNG**
- **Export atlas as PNG**
- Report generation and export

### 🎬 Video Tools
- OGV cutscene listing with metadata (resolution, duration, size)
- Double-click to play in system default player
- FFmpeg integration for video conversion
- Replacement queue with batch processing

### 🔧 Hex Editor
- Binary patch loading with conflict detection
- Add files or folders of .hex patches
- Stats: total patches, bytes, source files
- Backup option before applying

---

## 🎨 UI/UX Improvements

### Dark Theme
- Complete VS Code-inspired dark theme
- Custom styles for all WPF controls: DataGrid, ListView, TabControl, ScrollBar, ComboBox, CheckBox, etc.
- Accent color (#007ACC) with hover/pressed states

### Navigation & Layout
- Sidebar with emoji icons for all 9 tools
- Game path selector in top bar (right-aligned)
- Status log panel with Save/Clear
- GridSplitter between panels

### Quality of Life
- **Window state persistence** — remembers size, position, maximized
- **Last nav tab memory** — restores on reopen
- **Recent game paths** — remembers last 5
- **Auto game path detection** — finds exe, PCK files, maps automatically
- **Single source of truth** — set game path once, all tools use it

### About Page
- Three-column layout: Features, About/Tech, Credits
- Emoji icons for each tool and section
- Hero header with project tagline
- Tech stack and RE knowledge details
- Press F to pay respects counter

---

## 🔬 Reverse Engineering

### Discoveries
- **Spranm position = bottom-right corner** of each sprite piece
- **Texture flags**: 0x4000 = PNG, 0x0080 = indexed/LZ77
- **TextureParts** container uses 24-byte header (not standard 28)
- **Player files** (F_C_*, PL_DMG*) are runtime assets with PartsColor, no PNG
- **Game engine**: dkit / DKFramework (custom native C++)
- **Steam App ID**: 3077020
- **Audio**: WinMM 48kHz 16-bit stereo PCM
- **Text**: UTF-8 with 15+ control codes

### Tools Added
- Capstone disassembly scripts for EXE analysis
- Frida runtime tracer for sprite/file loading hooks
- PE string extraction and xref scanner

---

## 📚 Documentation

- **14 documentation pages** completely rewritten for C#/.NET 8
- 7 technical reference pages (LZ77, SPRANM, MPD, PCK, Text, HEX formats)
- 7 tool documentation pages
- **README.md** fully updated with feature table, build instructions, format knowledge
- **CONTRIBUTING.md** added with project structure and code guidelines
- **LICENSE** updated to GNU GPL v3.0

---

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Framework | C# / .NET 8 / WPF |
| MVVM | CommunityToolkit.Mvvm |
| Rendering | SkiaSharp |
| Audio | NAudio + NAudio.Vorbis + Concentus (Opus) |
| Build | Single-file self-contained (win-x64) |
| Theme | Custom dark theme (VS Code-inspired) |

---

## 📋 Requirements

- ✅ Windows 10/11 (64-bit)
- ✅ No additional software required (self-contained)
- ✅ DOKAPON! Sword of Fury (Steam)
- ✅ ~165 MB disk space

---

## 🙏 Credits

**Created by:** DiNaSoR
**Repository:** https://github.com/DiNaSoR/dokaponsof

**Special Thanks:**
- ⭐ q8fft2 — Original text extraction research
- ⭐ NewDoc — PCK/Hex format documentation
- ⭐ Dokapon Discord — Community support and testing
- ⭐ Sting Entertainment — For creating DOKAPON! Sword of Fury
- 🤖 Claude — AI-assisted development and reverse engineering

---

## 📄 License

GNU General Public License v3.0

---

<p align="center">
  Made with ❤️ by <strong>DiNaSoR</strong>
</p>
