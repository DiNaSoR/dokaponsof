# ⚔️ DOKAPON! Sword of Fury — Modding Tools

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Discord](https://img.shields.io/discord/123456789?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://discord.gg/wXhAEvhTuR)
[![Website](https://img.shields.io/badge/Website-Documentation-green)](https://dinasor.github.io/dokaponsof/)
[![.NET 8](https://img.shields.io/badge/.NET-8.0-512BD4?logo=dotnet)](https://dotnet.microsoft.com/)

<p align="center">
  <img src="docs/assets/images/banner.jpg" alt="Dokapon SoF Banner" width="900">
</p>

A comprehensive modding toolkit for **DOKAPON! Sword of Fury** (Sting Entertainment, 2025 PC remaster). Extract, analyze, edit, and reimport game assets while preserving binary integrity.

## 📚 Table of Contents

- [Features](#-features)
- [Screenshots](#-screenshots)
- [Getting Started](#-getting-started)
- [Tools Overview](#-tools-overview)
- [Supported Formats](#-supported-formats)
- [Building from Source](#-building-from-source)
- [Usage Guidelines](#-usage-guidelines)
- [Community](#-community)
- [Contributing](#-contributing)
- [License](#-license)

## ✨ Features

| Feature | Description |
|---------|-------------|
| 📦 **Asset Extractor** | Extract PNG from .tex, .spranm, .mpd, .fnt with category tabs and preview |
| 📝 **Smart Text Tools** | Extract, decode control codes, categorize, search, and safely reimport game text |
| 🎙️ **Voice Tools** | BGM, SE, Voice (JP/EN) playback with Opus decoding and PCK replacement |
| 🔧 **Hex Editor** | Apply binary patches with conflict detection and backup |
| 🎬 **Video Tools** | OGV cutscene management with FFmpeg integration |
| 🗺️ **Map Explorer** | Render tile maps, atlases, palette switching, cell data analysis |
| 🎭 **Animation Viewer** | Parse and play spranm sprite animations with GIF export |
| 🔍 **Game Scanner** | Full directory analysis with file type stats and key file validation |

## 🚀 Getting Started

### Prerequisites

- ✅ Windows 10/11 (64-bit)
- ✅ DOKAPON! Sword of Fury ([Steam](https://store.steampowered.com/app/3077020/))
- ✅ No additional runtime required (self-contained exe)

### Installation

1. Download the latest release from [Releases](https://github.com/DiNaSoR/dokaponsof/releases)
2. Extract and run `DokaponSoFTools.App.exe`
3. Set your game path (auto-detects Steam install)
4. All tools auto-populate from the game directory

## 🔧 Tools Overview

### 📦 Asset Extractor
Extract embedded PNG images from game asset files with live preview.
- **Category tabs**: All, Textures (.tex), Sprites (.spranm), Fonts (.fnt), Maps (.mpd)
- **File size totals** per category
- **Map rendering**: Assembled tile maps via MapRenderer (not just raw atlas)

### 📝 Smart Text Tools
5107 text entries decoded and categorized automatically.
- **Control code decoding**: `\p`, `\k`, `\z`, `\n`, `\h`, `\r`, `%Nc` colors, `%s`/`%d` variables
- **Auto-categorization**: Dialog, Labels, HUD/Stats, System
- **Export formats**: TXT (binary-safe reimport), CSV, JSON
- **100% binary-safe** import — preserves exact byte layout

### 🎙️ Voice Tools
Four PCK archives with in-app Opus audio playback.
- **BGM** — 47 background music tracks
- **SE** — Sound effects
- **Voice (JP)** — Japanese voice lines
- **Voice (EN)** — English voice lines
- Double-click to play, replace individual sounds, save modified PCK

### 🎭 Animation Viewer
Parse and render the proprietary `.spranm` sprite animation format.
- **Full format parser**: Sequence, Sprite, SpriteGp, TextureParts sections
- **LZ77 decompression** for compressed animation files
- **Playback controls**: Play/Stop, frame stepping, FPS slider
- **Export**: GIF animation, PNG sequence, atlas PNG
- **Keyboard shortcuts**: Space (play/stop), arrows (frame step), Ctrl+C (copy)

### 🗺️ Map Explorer
Analyze and render game map data from .mpd cell files.
- Atlas view with palette switching
- Assembled map rendering
- Record and parts data tables
- Export map/atlas as PNG

## 📋 Supported Formats

| Extension | Type | Description |
|-----------|------|-------------|
| `.tex` | Texture | PNG with optional LZ77 compression |
| `.spranm` | Animation | Sprite animation (Sequence/Sprite/SpriteGp/TextureParts) |
| `.mpd` | Map | Cell-based tile maps with palettes |
| `.fnt` | Font | Binary font data |
| `.pck` | Audio | Sound archive (Ogg Opus) |
| `.ogv` | Video | Ogg Theora cutscenes |
| `.hex` | Patch | Binary hex patches for the executable |

### Format Knowledge

This toolkit includes reverse-engineered format documentation:
- **LZ77 compression**: Nintendo-style LZSS variant (FlagByte, TokenStream, Cell)
- **Spranm structure**: Section-based with 28-byte headers, position = bottom-right corner
- **Text encoding**: UTF-8 with 15+ control codes (`\p` start, `\k` wait, `%Nc` colors)
- **PCK archives**: Filename + Pack sections, 16-byte aligned sound entries
- **Cell/Map format**: Grid-based with TextureParts, palette chunks, and indexed textures

## 🏗️ Building from Source

```bash
# Clone
git clone https://github.com/DiNaSoR/dokaponsof.git
cd dokaponsof/csharp

# Build
dotnet build --configuration Release

# Publish single-file exe
dotnet publish src/DokaponSoFTools.App/DokaponSoFTools.App.csproj \
  --configuration Release --runtime win-x64 --self-contained true \
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true \
  --output publish
```

### Tech Stack

- **C# / .NET 8** — Core framework
- **WPF** — UI with dark theme
- **CommunityToolkit.Mvvm** — MVVM pattern
- **SkiaSharp** — Image rendering (maps, sprites, atlases)
- **NAudio + Concentus** — Ogg Opus audio decoding and playback
- **NAudio.Vorbis** — Ogg Vorbis support

## 📋 Usage Guidelines

### ✅ Do
- Create and share mods with the community
- Report bugs and suggest improvements
- Credit original authors when sharing modifications
- Back up your files before modding

### ❌ Don't
- Use tools for piracy or unauthorized distribution
- Share copyrighted game assets
- Distribute modified executables
- Create harmful or malicious mods

## 🌟 Community

- 💬 [Discord Server](https://discord.gg/wXhAEvhTuR) — Get help and share creations
- 📱 [Reddit](https://reddit.com/r/dokaponofficial/) — Discuss mods and share feedback
- 📖 [Documentation](https://dinasor.github.io/dokaponsof/) — Guides and tutorials

## 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes
4. Push to the branch
5. Open a Pull Request

## 💖 Acknowledgments

- 🎮 **Sting Entertainment** — For creating DOKAPON! Sword of Fury
- ⭐ **q8fft2** — Original text extraction research
- ⭐ **NewDoc** — PCK/Hex format documentation
- ⭐ **Dokapon Discord** — Community support and testing
- 🤖 **Claude** — AI-assisted development

## 📄 License

This project is licensed under the **GNU General Public License v3.0** — see [LICENSE](LICENSE).

- Source code must remain open when distributed
- Modifications must be shared under the same license
- No warranty provided

---

<p align="center">
  Made with ❤️ by <strong>DiNaSoR</strong> and the Dokapon Modding Community
</p>
