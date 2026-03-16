using System.Buffers.Binary;

namespace DokaponSoFTools.Core.Formats;

public sealed class HexPatchEntry
{
    public long Offset { get; }
    public long Size { get; }
    public byte[] Data { get; }
    public string SourceFile { get; }
    public long EndOffset => Offset + Size;

    public HexPatchEntry(long offset, long size, byte[] data, string sourceFile)
    {
        Offset = offset;
        Size = size;
        Data = data;
        SourceFile = sourceFile;
    }

    public string GetHexPreview(int maxBytes = 32)
    {
        int count = Math.Min(maxBytes, Data.Length);
        string preview = BitConverter.ToString(Data, 0, count).Replace('-', ' ');
        if (Data.Length > maxBytes)
            preview += $" ... ({Data.Length - maxBytes} more bytes)";
        return preview;
    }

    public override string ToString()
        => $"{Path.GetFileName(SourceFile)}: 0x{Offset:X8} (0x{Size:X4} bytes)";
}

public sealed record PatchConflict(HexPatchEntry Patch1, HexPatchEntry Patch2, string ConflictType);

public static class HexPatch
{
    public static List<HexPatchEntry> ParseFile(string filePath)
    {
        if (!File.Exists(filePath))
            throw new FileNotFoundException($"Hex file not found: {filePath}");

        byte[] data = File.ReadAllBytes(filePath);
        var patches = new List<HexPatchEntry>();
        int pos = 0;

        while (pos < data.Length)
        {
            if (data.Length - pos < 16)
            {
                if (pos == 0) throw new InvalidDataException($"Invalid hex file format: {filePath} (too small)");
                break;
            }

            // Big-endian int64 for offset and size
            long offset = BinaryPrimitives.ReadInt64BigEndian(data.AsSpan(pos));
            pos += 8;
            long size = BinaryPrimitives.ReadInt64BigEndian(data.AsSpan(pos));
            pos += 8;

            if (size <= 0)
                throw new InvalidDataException($"Invalid patch size at offset {pos - 8} in {filePath}");
            if (pos + size > data.Length)
                throw new InvalidDataException($"Patch data exceeds file size at offset {pos - 16} in {filePath}");

            byte[] patchData = data[pos..(pos + (int)size)];
            pos += (int)size;

            patches.Add(new HexPatchEntry(offset, size, patchData, filePath));
        }

        return patches;
    }

    public static List<HexPatchEntry> ParseFiles(IEnumerable<string> filePaths)
    {
        var allPatches = new List<HexPatchEntry>();
        foreach (string path in filePaths)
        {
            try { allPatches.AddRange(ParseFile(path)); }
            catch { /* skip invalid files */ }
        }
        return allPatches;
    }

    public static List<PatchConflict> DetectConflicts(List<HexPatchEntry> patches)
    {
        var conflicts = new List<PatchConflict>();
        var sorted = patches.OrderBy(p => p.Offset).ToList();

        for (int i = 0; i < sorted.Count; i++)
        {
            for (int j = i + 1; j < sorted.Count; j++)
            {
                if (sorted[i].SourceFile == sorted[j].SourceFile) continue;

                if (sorted[i].Offset == sorted[j].Offset)
                    conflicts.Add(new PatchConflict(sorted[i], sorted[j], "same_offset"));
                else if (sorted[j].Offset < sorted[i].EndOffset)
                    conflicts.Add(new PatchConflict(sorted[i], sorted[j], "overlap"));
                else if (sorted[j].Offset >= sorted[i].EndOffset)
                    break;
            }
        }

        return conflicts;
    }

    public static List<string> ValidatePatches(List<HexPatchEntry> patches, long exeSize)
    {
        var errors = new List<string>();
        foreach (var p in patches)
        {
            if (p.Offset < 0)
                errors.Add($"{p.SourceFile}: Negative offset 0x{p.Offset:X}");
            else if (p.Offset >= exeSize)
                errors.Add($"{p.SourceFile}: Offset 0x{p.Offset:X} exceeds file size");
            else if (p.EndOffset > exeSize)
                errors.Add($"{p.SourceFile}: Patch at 0x{p.Offset:X} extends beyond file end");
        }
        return errors;
    }

    public static (int Applied, List<string> Errors) ApplyPatches(
        string exePath, List<HexPatchEntry> patches,
        string? outputPath = null, bool backup = true)
    {
        if (!File.Exists(exePath))
            return (0, [$"Executable not found: {exePath}"]);
        if (patches.Count == 0)
            return (0, ["No patches to apply"]);

        byte[] exeData = File.ReadAllBytes(exePath);
        var errors = new List<string>();

        var validationErrors = ValidatePatches(patches, exeData.Length);
        if (validationErrors.Count > 0)
            return (0, validationErrors);

        var conflicts = DetectConflicts(patches);
        foreach (var c in conflicts)
            errors.Add($"Warning: Conflict ({c.ConflictType}): {Path.GetFileName(c.Patch1.SourceFile)} vs {Path.GetFileName(c.Patch2.SourceFile)} at 0x{c.Patch1.Offset:X8}");

        var sorted = patches.OrderBy(p => p.Offset).ToList();
        int applied = 0;

        foreach (var patch in sorted)
        {
            try
            {
                Array.Copy(patch.Data, 0, exeData, patch.Offset, patch.Size);
                applied++;
            }
            catch (Exception ex)
            {
                errors.Add($"Failed to apply patch from {patch.SourceFile}: {ex.Message}");
            }
        }

        outputPath ??= backup ? exePath : Path.ChangeExtension(exePath, "_patched" + Path.GetExtension(exePath));

        if (backup && outputPath == exePath)
        {
            string backupPath = exePath + ".backup";
            if (!File.Exists(backupPath))
                File.Copy(exePath, backupPath);
        }

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
        File.WriteAllBytes(outputPath, exeData);

        return (applied, errors);
    }

    public static List<string> FindHexFiles(string directory, bool recursive = true)
    {
        var option = recursive ? SearchOption.AllDirectories : SearchOption.TopDirectoryOnly;
        return Directory.EnumerateFiles(directory, "*.hex", option)
            .OrderBy(f => f)
            .ToList();
    }
}
