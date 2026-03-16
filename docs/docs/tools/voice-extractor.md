---
title: Voice Tools
layout: default
nav_order: 2
parent: Tools
---

# Voice Tools
{: .no_toc }

Browse, play, replace, and repack audio from all four PCK sound archives.
{: .fs-6 .fw-300 }

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Voice Tools gives you full read/write access to the game's PCK audio archives. All four archives are loaded automatically when a game path is set:

| Archive | File | Contents |
|---|---|---|
| BGM | `GameData/app/BGM.pck` | Background music tracks |
| Sound Effects | `GameData/app/SE.pck` | In-game sound effects |
| Voice (JP) | `GameData/app/Voice.pck` | Japanese voice acting |
| Voice (EN) | `GameData/app/Voice-en.pck` | English voice acting |

The tool supports both extraction (saving sounds to disk) and replacement (swapping individual entries with new audio), followed by saving the modified archive back as a valid `.pck` file.

---

## Getting Started

1. Open `DokaponSoFTools.App.exe`.
2. Set your game directory in the main toolbar.
3. Navigate to **Voice Tools** in the left panel.
4. All four PCK archives load automatically into their respective tabs.

If the game path has not been set, or if you want to work with a PCK file from a different location, click **Browse PCK...** in the toolbar and select a file manually.

---

## The Interface

### Category Tabs

The main area is a tab control with one tab per PCK archive:

- **BGM** — music tracks, typically larger files
- **Sound Effects** — short sound effects
- **Voice (JP)** — Japanese voice lines (file names like `V_0001.voice`)
- **Voice (EN)** — English voice lines (same naming convention)

Switching tabs switches the active archive. All toolbar actions (Extract All, Replace Selected, Save PCK) operate on whichever tab is currently selected.

### Sound List Columns

Each tab contains a data grid with the following columns:

| Column | Description |
|---|---|
| # | Index of the entry within the archive (zero-based) |
| Name | Internal filename stored in the PCK header |
| Format | `Opus` if the data begins with `OggS`, otherwise `Raw` |
| Size | File size of the individual sound entry |

All entries in the base game archives use Opus audio in an Ogg container.

### Audio Playback Bar

A compact playback bar sits at the bottom of the view:

- **Play** — start playback of the selected entry
- **Stop** — stop playback immediately
- **Now playing** label — shows the name of the currently playing sound

In-app playback uses the [Concentus](https://github.com/lostromb/concentus) pure C# Opus decoder. No system codec or external player is required.

---

## Playing Sounds

### Double-Click to Play

Double-click any row in the sound list to play that entry immediately. This is the fastest way to audition sounds while scrolling through a large archive.

### Single-Click then Play

Select a row by clicking it once to set it as the active selection, then click **Play** in the bottom bar. Use **Stop** to halt playback at any time.

---

## Extracting Sounds

### Extract All

1. Select the tab for the archive you want to extract.
2. Click **Extract All** in the toolbar.
3. Choose an output directory in the folder browser dialog.
4. All sounds in the current archive are saved to that directory using their internal names (e.g. `V_0001.voice`, `BGM_00.voice`).

Extracted files are written with their original names and raw Ogg/Opus data intact — no transcoding occurs. These files can be played directly in VLC, Firefox, or converted with FFmpeg:

```
ffmpeg -i V_0001.voice output.mp3
```

### Extracting Individual Sounds

There is no dedicated single-file extract button. To extract one sound, use Extract All to a temporary directory, then take only the file you need.

---

## Replacing Sounds

1. In the sound list, click the entry you want to replace to select it.
2. Click **Replace Selected** in the toolbar.
3. Choose a replacement audio file. Supported input formats:
   - `.opus` — Ogg Opus (native game format, no conversion needed)
   - `.ogg` — Ogg Vorbis or Ogg Opus container
   - `.wav` — PCM WAV (will be stored as raw bytes; best to use Opus)

{: .note }
For the best result, encode your replacement audio as Ogg Opus before importing. This matches the format already used by the game and keeps file sizes small. The tool accepts other formats as raw bytes, but they may not play correctly in-game if the decoder expects Opus.

The replacement is held in memory. The original `.pck` file on disk is not changed until you click **Save PCK**.

---

## Saving a Modified Archive

After making replacements, click **Save PCK** to write the modified archive to disk:

1. A save dialog appears with the original archive name pre-filled (e.g. `Voice-en.pck`).
2. Choose an output path — save to a new file name during testing, then replace the original once confirmed.
3. The tool writes a fully valid PCK file with the updated sound entries and correct internal offsets.

The saved PCK can be dropped directly into the game's `GameData/app/` directory to replace the original.

---

## PCK File Format Reference

The `.pck` format is a simple archive with three sections:

### Filename Section

Begins with the 20-byte ASCII header `"Filename            "`. Contains:

- A 4-byte total section size
- A table of 4-byte filename offsets (one per entry)
- Null-terminated ASCII filenames

### Pack Section

Begins with the 20-byte ASCII header `"Pack                "`. Contains:

- A 4-byte section length
- A 4-byte entry count
- An info array: one `(offset, size)` pair (8 bytes each) per entry
- The raw sound data, each entry aligned to 16 bytes

### Alignment

The Filename section is padded to 8-byte alignment before the Pack section begins. Sound data entries within the Pack section are padded to 16-byte alignment.

---

## Practical Example: Replacing an English Voice Line

Suppose you want to replace the English voice line `V_0044.voice` with a custom recording:

1. Record or obtain your replacement audio as `my_recording.opus`.
2. In Voice Tools, switch to the **Voice (EN)** tab.
3. Locate `V_0044.voice` in the list (use the scroll bar or sort by name).
4. Click the row to select it.
5. Click **Replace Selected** and choose `my_recording.opus`.
6. Click **Save PCK**, name the output `Voice-en.pck`.
7. Back up the original `Voice-en.pck` in `GameData/app/`.
8. Copy your new `Voice-en.pck` to `GameData/app/`.
9. Launch the game and trigger the relevant dialogue to hear your replacement.

---

## Troubleshooting

**PCK archives do not load automatically**
Confirm that your game directory contains the folder structure `GameData/app/` and that the PCK files are present. Run the Game Scanner tool to check which key files exist.

**Playback produces no sound**
Check your system's default audio output device. The Concentus decoder writes to the Windows audio session. If the sound entry shows format `Raw` instead of `Opus`, the file may not be standard Ogg Opus and in-app playback may not work.

**Save PCK produces a file that crashes the game**
Ensure replacement audio uses the same Ogg Opus format as the original. Replacing an Opus entry with a WAV or MP3 file stored as raw bytes will result in a PCK that fails to parse at runtime.

**"Sound not found" error when replacing**
The replacement lookup matches by filename stem (without extension). Verify that the selected entry in the list matches the name shown in the toolbar status log.

---

## Contributing

Found a bug or want to suggest an improvement? Open an issue on [GitHub](https://github.com/DiNaSoR/dokaponsof) or join the [Discord](https://discord.gg/HCrYwScDg5).

---

## License

This tool is part of DokaponSoFTools, released under The Unlicense (public domain). See the [LICENSE](https://github.com/DiNaSoR/dokaponsof/blob/main/LICENSE) file for full details.
