---
title: HEX Patch Format
layout: default
nav_order: 6
parent: Technical Reference
---

# HEX Patch Format
{: .no_toc }

Documentation of the binary patch file format used to modify the DOKAPON! Sword of Fury executable.
{: .fs-6 .fw-300 }

## Table of contents
{: .no_toc .text-delta }

1. TOC
{:toc}

## Overview

HEX patch files (`.hex`) are binary files that describe one or more targeted overwrites to a specific offset in the game executable. They are the primary mechanism for code and data patches that cannot be handled through the text extraction workflow.

The C# implementation is `DokaponSoFTools.Core.Formats.HexPatch`.

---

## File Format

A `.hex` file is a sequence of **patch records**. There is no file header — the first record begins at byte `0`.

### Patch Record

Each record is `16 + N` bytes:

```
Offset  Size  Field
------  ----  -----
+0x00    8    Target offset — absolute byte offset in the game exe (big-endian int64)
+0x08    8    Patch size    — number of data bytes that follow (big-endian int64)
+0x10    N    Patch data    — N bytes to write at target offset
```

{: .important }
Both `offset` and `size` are stored as **big-endian** (network byte order) 64-bit signed integers, unlike most other formats in this toolkit which use little-endian.

Records are laid out back-to-back with no padding between them. A file with `K` patches is parsed by reading records until fewer than 16 bytes remain.

### Example

A single patch that overwrites 3 bytes at offset `0x00100000`:

```
Hex dump:
00 00 00 00 00 10 00 00   ← offset = 0x100000 (BE int64)
00 00 00 00 00 00 00 03   ← size   = 3       (BE int64)
AA BB CC                  ← data   = [0xAA, 0xBB, 0xCC]
```

A file with two patches:

```
00 00 00 00 00 00 01 00   ← patch 1 offset = 0x100
00 00 00 00 00 00 00 02   ← patch 1 size   = 2
01 02                     ← patch 1 data
00 00 00 00 00 00 02 00   ← patch 2 offset = 0x200
00 00 00 00 00 00 00 03   ← patch 2 size   = 3
03 04 05                  ← patch 2 data
```

---

## Conflict Detection

When multiple `.hex` files are loaded together (a patch set), the `HexPatch.DetectConflicts` method checks every pair of patches from **different files** for conflicts:

### Conflict Types

| Type | Condition | Example |
|---|---|---|
| `same_offset` | `patch1.Offset == patch2.Offset` | Two patches both start at `0x100` |
| `overlap` | `patch2.Offset < patch1.EndOffset` (where `EndOffset = Offset + Size`) | Patch at `0x100` (10 bytes) overlaps patch at `0x105` |

Patches within the **same file** are never flagged as conflicts with each other.

Conflicts are reported as warnings during patch application — they do not prevent the patches from being applied, but the last-applied patch wins in an overlapping region.

```csharp
public sealed record PatchConflict(
    HexPatchEntry Patch1,
    HexPatchEntry Patch2,
    string ConflictType   // "same_offset" or "overlap"
);
```

---

## Validation

Before any patch is applied, `HexPatch.ValidatePatches` checks against the target executable's actual file size:

| Error condition | Message |
|---|---|
| `patch.Offset < 0` | Negative offset |
| `patch.Offset >= exeSize` | Offset beyond end of file |
| `patch.Offset + patch.Size > exeSize` | Patch extends past end of file |

Validation failures abort the entire patch operation — no patches are applied.

---

## Application

`HexPatch.ApplyPatches` applies patches in **ascending offset order** regardless of the order they appear in the source files:

1. Read the full executable into memory.
2. Validate all patches against the exe size.
3. Detect and log conflicts as warnings.
4. Sort patches by offset.
5. For each patch: `Array.Copy(patch.Data, 0, exeData, patch.Offset, patch.Size)`.
6. Optionally create a `.backup` file of the original if no backup exists yet.
7. Write the patched data to the output path.

```csharp
var patches = HexPatch.ParseFiles(new[] { "patch1.hex", "patch2.hex" });

var (applied, errors) = HexPatch.ApplyPatches(
    exePath:    "DokaponSoF.exe",
    patches:    patches,
    outputPath: "DokaponSoF_patched.exe",
    backup:     true   // creates DokaponSoF.exe.backup on first run
);

Console.WriteLine($"Applied: {applied}, Errors: {errors.Count}");
foreach (var e in errors)
    Console.WriteLine(e);
```

---

## C# Data Model

```csharp
public sealed class HexPatchEntry {
    public long   Offset     { get; }  // Target offset in exe
    public long   Size       { get; }  // Byte count
    public byte[] Data       { get; }  // Patch bytes
    public string SourceFile { get; }  // Which .hex file this came from
    public long   EndOffset  => Offset + Size;

    // Human-readable preview of first 32 data bytes
    public string GetHexPreview(int maxBytes = 32);
}
```

---

## Usage with Multiple Patch Files

The toolkit supports applying a directory of `.hex` files as a single patch set:

```csharp
// Find all .hex files recursively under a directory
List<string> files = HexPatch.FindHexFiles("mods/my_mod/", recursive: true);

// Parse them all into a flat list
List<HexPatchEntry> patches = HexPatch.ParseFiles(files);

// Check for conflicts between files
List<PatchConflict> conflicts = HexPatch.DetectConflicts(patches);
if (conflicts.Count > 0)
{
    foreach (var c in conflicts)
        Console.WriteLine($"Conflict ({c.ConflictType}): " +
            $"{Path.GetFileName(c.Patch1.SourceFile)} vs " +
            $"{Path.GetFileName(c.Patch2.SourceFile)} " +
            $"at 0x{c.Patch1.Offset:X8}");
}

// Apply
HexPatch.ApplyPatches("DokaponSoF.exe", patches, "DokaponSoF_patched.exe");
```

---

## Creating Patch Files

To create a `.hex` file manually or programmatically, write records using big-endian 64-bit integers:

```csharp
using var fs = File.Create("my_patch.hex");

// Helper: write one record
void WriteRecord(long offset, byte[] data)
{
    Span<byte> buf = stackalloc byte[8];
    BinaryPrimitives.WriteInt64BigEndian(buf, offset);
    fs.Write(buf);
    BinaryPrimitives.WriteInt64BigEndian(buf, data.Length);
    fs.Write(buf);
    fs.Write(data);
}

WriteRecord(0x0012_3456, new byte[] { 0x90, 0x90, 0x90 });  // NOP sled example
```

---

## Comparison with Text Patching

| Feature | HEX Patch | Text Import |
|---|---|---|
| Target data | Any binary data | UTF-8 text strings |
| Offset discovery | Manual (hex editor) | Automatic scan for `\p` markers |
| Size constraint | Must not exceed exe bounds | Must not exceed original `MaxLength` |
| Conflict detection | Yes (between `.hex` files) | N/A (each string at a fixed offset) |
| Use case | Code patches, value tweaks, binary data edits | Localization, dialog changes |

---

## See Also

- [Game Text Format](text-format) — text-level patching via `GameText.ImportTexts`
- Tools: Hex Editor feature in DokaponSoFTools provides a GUI for loading and applying `.hex` files
