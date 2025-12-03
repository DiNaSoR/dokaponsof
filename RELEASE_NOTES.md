# 🎮 DokaponSoFTools v0.3.0 Release

## 🌟 Overview

DokaponSoFTools is a comprehensive modding toolkit for DOKAPON! Sword of Fury (PC Version), providing an easy-to-use GUI interface for extracting and managing game assets.

This release focuses on documentation improvements, enhanced text extraction capabilities, and UI refinements.

---

## ✨ Key Features

🖼️ **Asset Extractor**: Extract and preview texture files (.tex), sprite animations (.spranm), map data (.mpd), and font files (.fnt)

🎮 **3D Model Viewer**: Interactive 3D preview for MDL model files with mesh visualization

💬 **Text Tool**: Extract and repack game text for translation purposes

🎤 **Voice Extractor**: Extract voice files from .pck format to .opus

🔍 **Preview System**: Built-in preview for textures, sprites, animations, and 3D models

🎨 **User-Friendly GUI**: Modern PyQt6-based interface with dark theme

📁 **Batch Processing**: Support for processing multiple files at once

🗜️ **LZ77 Support**: Decompress and compress LZ77 compressed game files

---

## 🛠️ Technical Details

**Version:** 0.3.0  
**Platform:** Windows  
**Architecture:** 64-bit  
**Framework:** Python 3.12 with PyQt6
**Build Date:** 04-12-2025

### Bundled Dependencies

- PyQt6 6.10.0 - GUI framework
- PyVista 0.46.4 - 3D visualization (includes VTK)
- Pillow 12.0.0 - Image processing
- NumPy 2.3.4 - Numerical computing
- All dependencies included - No Python installation required

---

## 📋 Requirements

- ✅ Windows 10/11 (64-bit)
- ✅ No additional software required (standalone executable)
- ✅ Minimum 4GB RAM recommended
- ✅ ~250MB free disk space
- ✅ DirectX/OpenGL support for 3D viewer

---

## 🔄 Changes from v0.2.0

### ✨ New Features

- 📚 **Comprehensive Documentation Updates**: Major terminology corrections and enhancements across all documentation
- 🔤 **Enhanced Text Extraction**: Improved text extraction and voice tools functionality
- 🎨 **UI Improvements**: Banner centered with max-width for better visual presentation

### 🔧 Improvements

- 📝 **Documentation Accuracy**: Updated all game terminology to match official game text:
  - **Monsters**: Corrected names like "Tamagon" → "Egg'n", "Kinoko Kozo" → "Fungo Kid", "Little Magician" → "Lil' Magician"
  - **Items**: Updated item names like "Recovery" → "Potion", "Full Recovery" → "Elixir", "Bine" → "Spinner"
  - **Equipment**: Renamed weapons and armor for consistency (e.g., "Cheap Sword" → "Shabby Sword", "Ken's Dagger" → "Ken's Knife")
  - **Magic**: Updated spell names (e.g., "Meteor" → "Magma", "Zeni Get" → "Money Get", "Sabir" → "Rust")
  - **Treasures**: Corrected treasure names (e.g., "Heart of Flea" → "Flea's Heart", "Magic Belt" → "Magical Belt")
  - **Special Skills**: Updated skill terminology (e.g., "Scoop" → "Scop", "Head Strike" → "Decapitation")
- 🎯 **Better Consistency**: Ensured consistent formatting and terminology throughout all documentation
- 📖 **Improved Readability**: Enhanced documentation structure for better user understanding

### 📦 Research Tools

- 🧹 **Text Cleaning Tool**: Added `clean_text.py` for processing extracted game text
- 📊 **Name Extraction**: Created comprehensive name extraction from game text files
- 📄 **Translation CSV**: Generated translation-ready CSV files for extracted texts

---

## 🐛 Known Issues

- ⚠️ **File Size**: Executable is larger (~229MB) due to bundled 3D libraries (PyVista/VTK)
- ⚠️ **Large Files**: Very large files may take longer to preview
- ⚠️ **Memory Usage**: 3D model previews may use significant memory
- ⚠️ **Graphics Drivers**: 3D viewer requires up-to-date graphics drivers

---

## 📝 Notes

- 💾 **Backup First**: Please make sure to backup your game files before using the tools
- 🎮 **Modding Only**: For modding purposes only - please support the original game developers
- 💬 **Support**: Join our Discord for support and updates
- 📖 **Documentation**: Check out the comprehensive documentation at [dinasor.github.io/dokaponsof](https://dinasor.github.io/dokaponsof/)

---

## 🚀 Usage

1. Download `DokaponSoFTools.exe` from the build folder
2. Place the executable in your desired location
3. Double-click to launch (no installation needed)
4. Use the file browser to navigate to game files
5. Select the appropriate tab (Asset/Text/Voice)
6. Choose extraction/repacking options and process files

### Supported File Types

- **`.tex`** - Texture files (PNG extraction/repacking)
- **`.mdl`** - 3D model files (mesh extraction, OBJ export)
- **`.spranm`** - Sprite animation files
- **`.mpd`** - Map/cell data files
- **`.fnt`** - Font files
- **`.pck`** - Voice/audio package files

---

## 🙏 Credits

**Tool Development:** DiNaSoR  
**Repository:** https://github.com/DiNaSoR/dokaponsof  
**Special Thanks:** Discord Community and Contributors

### Technologies Used

- PyQt6 - Modern GUI framework
- PyVista - 3D visualization
- Pillow - Image processing
- NumPy - Numerical computing
- PyInstaller - Executable packaging

---

## 📜 License

This project is licensed under the GNU General Public License v3.0 (GPL-3.0)

---

## 💖 If you find this tool helpful, consider supporting the development


**Note:** This is a standalone executable. No Python installation or additional dependencies are required to run the application.
