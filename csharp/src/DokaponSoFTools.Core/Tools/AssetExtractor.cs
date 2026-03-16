using DokaponSoFTools.Core.Compression;
using SkiaSharp;

namespace DokaponSoFTools.Core.Tools;

public static class AssetExtractor
{
    private static readonly byte[] PngSignature = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
    private static readonly byte[] IendMarker = "IEND"u8.ToArray();

    public static (bool Success, string? OutputPath) ExtractTex(byte[] data, string outputPath, string? originalFile = null)
    {
        // Try LZ77 decompression
        if (data.Length >= 4 && data[0] == 'L' && data[1] == 'Z' && data[2] == '7' && data[3] == '7')
        {
            var decompressed = Lz77FlagByte.Decompress(data);
            if (decompressed is not null) data = decompressed;
        }

        int pngStart = FindSequence(data, PngSignature);
        if (pngStart < 0) return (false, null);

        byte[] pngData = data[pngStart..];
        Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
        File.WriteAllBytes(outputPath, pngData);
        return (true, outputPath);
    }

    public static (bool Success, bool FoundPng, byte[] Data) ExtractSpranm(byte[] data)
    {
        // Try LZ77 decompression
        if (data.Length >= 4 && data.AsSpan(0, 4).SequenceEqual("LZ77"u8))
        {
            var decompressed = Lz77FlagByte.Decompress(data);
            if (decompressed is not null) data = decompressed;
        }

        if (data.Length >= 4 && data.AsSpan(0, 4).SequenceEqual("Sequ"u8))
        {
            int pngStart = FindSequence(data, PngSignature);
            if (pngStart >= 0)
            {
                int iendPos = FindSequence(data.AsSpan(pngStart), IendMarker);
                if (iendPos >= 0)
                {
                    int pngEnd = pngStart + iendPos + 8;
                    return (true, true, data[pngStart..pngEnd]);
                }
            }
            return (true, false, data);
        }

        return (true, false, data);
    }

    public static (bool Success, string? OutputPath) ExtractMpd(byte[] data, string outputPath)
    {
        if (data.Length < 0x20 || !data.AsSpan(0, 4).SequenceEqual("Cell"u8))
            return (false, null);

        int pngStart = FindSequence(data, PngSignature);
        if (pngStart < 0) return (false, null);

        int iendPos = FindSequence(data.AsSpan(pngStart), IendMarker);
        if (iendPos < 0) return (false, null);

        int pngEnd = pngStart + iendPos + 8;
        byte[] pngData = data[pngStart..pngEnd];

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
        File.WriteAllBytes(outputPath, pngData);
        return (true, outputPath);
    }

    public static (int Success, int Failed) ProcessDirectory(string inputDir, string outputDir,
        string fileType = "all", IProgress<string>? progress = null)
    {
        string[] extensions = fileType == "all"
            ? [".mpd", ".tex", ".spranm", ".fnt"]
            : [$".{fileType}"];

        var files = new List<string>();
        foreach (string ext in extensions)
            files.AddRange(Directory.EnumerateFiles(inputDir, $"*{ext}", SearchOption.AllDirectories));

        int success = 0, failed = 0;
        Directory.CreateDirectory(outputDir);

        foreach (string file in files)
        {
            try
            {
                byte[] data = File.ReadAllBytes(file);
                string ext = Path.GetExtension(file).ToLower();
                string baseName = Path.GetFileName(file);

                bool ok = ext switch
                {
                    ".tex" => ExtractTex(data, Path.Combine(outputDir, Path.ChangeExtension(baseName, ".png"))).Success,
                    ".mpd" => ExtractMpd(data, Path.Combine(outputDir, Path.ChangeExtension(baseName, ".png"))).Success,
                    ".spranm" => ExtractSpranmToFile(data, outputDir, baseName),
                    ".fnt" => ExtractFnt(data, Path.Combine(outputDir, baseName + ".bin")),
                    _ => false
                };

                if (ok) success++;
                else failed++;

                progress?.Report($"{(ok ? "OK" : "FAIL")}: {baseName}");
            }
            catch
            {
                failed++;
            }
        }

        return (success, failed);
    }

    private static bool ExtractSpranmToFile(byte[] data, string outputDir, string baseName)
    {
        var (ok, foundPng, finalData) = ExtractSpranm(data);
        if (!ok) return false;

        string outPath = Path.Combine(outputDir, baseName + (foundPng ? ".png" : ".bin"));
        File.WriteAllBytes(outPath, finalData);
        return true;
    }

    private static bool ExtractFnt(byte[] data, string outputPath)
    {
        if (data.AsSpan(0, 4).SequenceEqual("LZ77"u8))
        {
            var decompressed = Lz77FlagByte.Decompress(data);
            if (decompressed is not null) data = decompressed;
        }

        File.WriteAllBytes(outputPath, data);
        return true;
    }

    private static int FindSequence(ReadOnlySpan<byte> data, ReadOnlySpan<byte> seq)
    {
        for (int i = 0; i <= data.Length - seq.Length; i++)
            if (data.Slice(i, seq.Length).SequenceEqual(seq))
                return i;
        return -1;
    }
}
