using System.Text;
using System.Text.RegularExpressions;
using DokaponSoFTools.Core.Compression;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.Core.Scanning;

public sealed record FileInsight(
    string Path, string RelativePath, string Extension,
    long Size, string Signature,
    int PngCount = 0, CellLz77Info? Lz77 = null,
    string? DecompressedSignature = null,
    string? ParseError = null
);

public sealed record MapGroup(string MapId, List<FileInsight> Files);

public sealed record DebugOffsetState(string OffsetHex, string CurrentBytes, string? BackupBytes, bool MatchesExpected);

public sealed record DebugInsight(
    string ExePath, string? BackupPath,
    Dictionary<string, bool> MarkersFound,
    List<DebugOffsetState> Offsets,
    bool HasDebugAssets, List<string> DebugAssets
);

public static partial class GameScanner
{
    private static readonly byte[] PngSig = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];
    private static readonly byte[] PngEnd = "IEND\xAEB`\x82"u8.ToArray();
    [GeneratedRegex(@"^F_(\d{2})_")]
    private static partial Regex MapIdRegex();

    public static string DetectSignature(ReadOnlySpan<byte> buf)
    {
        if (buf.Length >= 4 && buf[..4].SequenceEqual("LZ77"u8)) return "LZ77";
        if (buf.Length >= 8 && buf[..8].SequenceEqual("Sequence"u8)) return "Sequence";
        if (buf.Length >= 7 && buf[..7].SequenceEqual("Texture"u8)) return "Texture";
        if (buf.Length >= 8 && buf[..8].SequenceEqual("Filename"u8)) return "Filename";
        if (buf.Length >= 4 && buf[..4].SequenceEqual("Cell"u8)) return "Cell";
        return "Unknown";
    }

    public static int CountPngs(ReadOnlySpan<byte> buf)
    {
        int count = 0;
        int pos = 0;
        while (pos <= buf.Length - PngSig.Length)
        {
            int found = -1;
            for (int i = pos; i <= buf.Length - PngSig.Length; i++)
            {
                if (buf.Slice(i, PngSig.Length).SequenceEqual(PngSig)) { found = i; break; }
            }
            if (found < 0) break;
            count++;
            int endPos = -1;
            for (int i = found; i <= buf.Length - PngEnd.Length; i++)
            {
                if (buf.Slice(i, PngEnd.Length).SequenceEqual(PngEnd)) { endPos = i; break; }
            }
            pos = endPos < 0 ? found + 1 : endPos + PngEnd.Length;
        }
        return count;
    }

    public static FileInsight AnalyzeFile(string path, string root)
    {
        byte[] data = File.ReadAllBytes(path);
        string sig = DetectSignature(data.AsSpan(0, Math.Min(0x40, data.Length)));
        string? decompSig = null;
        CellLz77Info? lz77Info = null;
        string? error = null;

        try
        {
            if (sig == "LZ77")
            {
                var (decompressed, info) = Lz77Cell.Decompress(data);
                lz77Info = info;
                decompSig = DetectSignature(decompressed.AsSpan(0, Math.Min(0x40, decompressed.Length)));
            }
        }
        catch (Exception ex) { error = ex.Message; }

        return new FileInsight(
            Path: path,
            RelativePath: System.IO.Path.GetRelativePath(root, path),
            Extension: System.IO.Path.GetExtension(path).ToLower(),
            Size: data.Length,
            Signature: sig,
            PngCount: CountPngs(data),
            Lz77: lz77Info,
            DecompressedSignature: decompSig,
            ParseError: error
        );
    }

    public static List<MapGroup> ScanMapGroups(string gameDir)
    {
        string fieldMap = System.IO.Path.Combine(gameDir, "GameData", "app", "Field", "Map");
        string fieldChizu = System.IO.Path.Combine(gameDir, "GameData", "app", "Field", "Chizu");
        var groups = new Dictionary<string, List<FileInsight>>();

        if (Directory.Exists(fieldMap))
        {
            foreach (string file in Directory.EnumerateFiles(fieldMap, "*", SearchOption.AllDirectories).OrderBy(f => f))
            {
                var match = MapIdRegex().Match(System.IO.Path.GetFileName(file));
                string mapId = match.Success ? match.Groups[1].Value : "misc";
                if (!groups.ContainsKey(mapId)) groups[mapId] = [];
                groups[mapId].Add(AnalyzeFile(file, gameDir));
            }
        }

        if (Directory.Exists(fieldChizu))
        {
            if (!groups.ContainsKey("chizu")) groups["chizu"] = [];
            foreach (string file in Directory.EnumerateFiles(fieldChizu, "*", SearchOption.AllDirectories).OrderBy(f => f))
                groups["chizu"].Add(AnalyzeFile(file, gameDir));
        }

        return groups.OrderBy(kv => kv.Key).Select(kv => new MapGroup(kv.Key, kv.Value)).ToList();
    }

    public static DebugInsight AnalyzeDebug(string gameDir)
    {
        string exePath = System.IO.Path.Combine(gameDir, "DOKAPON! Sword of Fury.exe");
        string backupPath = exePath + ".bak";
        byte[] data = File.ReadAllBytes(exePath);

        string[] markerStrings = [
            "DebugPlayBattle", "DEBUGPLAY", "Load Field Map Thread",
            "DebugMode", "X%3d Y%3d P%3d", "X%3d Y%3d A%3d"
        ];

        var markers = markerStrings.ToDictionary(
            m => m,
            m => FindBytes(data, Encoding.ASCII.GetBytes(m)) >= 0
        );

        var offsets = new (int Offset, byte[] Expected)[] {
            (0x2DAE8, [0x74, 0x0B]),
            (0x968930, [0x00, 0x00, 0x00, 0x00])
        };

        var states = offsets.Select(o => new DebugOffsetState(
            OffsetHex: $"0x{o.Offset:X}",
            CurrentBytes: ReadBytesAt(exePath, o.Offset, 8),
            BackupBytes: File.Exists(backupPath) ? ReadBytesAt(backupPath, o.Offset, 8) : null,
            MatchesExpected: File.Exists(backupPath) && ReadBytesAt(backupPath, o.Offset, o.Expected.Length) ==
                string.Join(" ", o.Expected.Select(b => $"{b:X2}"))
        )).ToList();

        string debugDir = System.IO.Path.Combine(gameDir, "GameData", "app", "Debug");
        var debugAssets = Directory.Exists(debugDir)
            ? Directory.EnumerateFiles(debugDir, "*", SearchOption.AllDirectories)
                .Select(p => System.IO.Path.GetRelativePath(gameDir, p))
                .OrderBy(p => p).ToList()
            : [];

        return new DebugInsight(
            ExePath: exePath,
            BackupPath: File.Exists(backupPath) ? backupPath : null,
            MarkersFound: markers,
            Offsets: states,
            HasDebugAssets: debugAssets.Count > 0,
            DebugAssets: debugAssets
        );
    }

    private static string ReadBytesAt(string path, int offset, int length)
    {
        using var fs = File.OpenRead(path);
        fs.Seek(offset, SeekOrigin.Begin);
        var buf = new byte[length];
        fs.Read(buf);
        return string.Join(" ", buf.Select(b => $"{b:X2}"));
    }

    private static int FindBytes(byte[] haystack, byte[] needle)
    {
        for (int i = 0; i <= haystack.Length - needle.Length; i++)
            if (haystack.AsSpan(i, needle.Length).SequenceEqual(needle))
                return i;
        return -1;
    }
}
