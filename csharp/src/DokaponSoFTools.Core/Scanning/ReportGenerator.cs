using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace DokaponSoFTools.Core.Scanning;

public static class ReportGenerator
{
    private static readonly JsonSerializerOptions JsonOptions = new()
    {
        WriteIndented = true,
        DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull
    };

    public static string GenerateJsonReport(DebugInsight debug, List<MapGroup> groups)
    {
        var report = new
        {
            debug = new
            {
                exe_path = debug.ExePath,
                backup_path = debug.BackupPath,
                markers = debug.MarkersFound,
                offsets = debug.Offsets.Select(o => new { o.OffsetHex, o.CurrentBytes, o.BackupBytes, o.MatchesExpected }),
                has_debug_assets = debug.HasDebugAssets,
                debug_assets = debug.DebugAssets
            },
            groups = groups.Select(g => new
            {
                map_id = g.MapId,
                file_count = g.Files.Count,
                files = g.Files.Select(f => new { f.RelativePath, f.Extension, f.Size, f.Signature, f.PngCount })
            })
        };

        return JsonSerializer.Serialize(report, JsonOptions);
    }

    public static string GenerateMarkdownReport(DebugInsight debug, List<MapGroup> groups)
    {
        var sb = new StringBuilder();
        sb.AppendLine("# Dokapon SoF Scan Report");
        sb.AppendLine();

        // Debug section
        sb.AppendLine("## Debug Info");
        sb.AppendLine($"- EXE: `{debug.ExePath}`");
        sb.AppendLine($"- Backup: {(debug.BackupPath is not null ? $"`{debug.BackupPath}`" : "none")}");
        sb.AppendLine();

        sb.AppendLine("### Debug Markers");
        foreach (var (marker, found) in debug.MarkersFound)
            sb.AppendLine($"- {marker}: {(found ? "FOUND" : "not found")}");

        sb.AppendLine();
        sb.AppendLine("### Debug Offsets");
        foreach (var o in debug.Offsets)
            sb.AppendLine($"- {o.OffsetHex}: `{o.CurrentBytes}`");

        sb.AppendLine();
        sb.AppendLine("## Map Groups");
        sb.AppendLine($"Total groups: {groups.Count}");
        sb.AppendLine();

        foreach (var group in groups)
        {
            sb.AppendLine($"### Group {group.MapId} ({group.Files.Count} files)");
            var extCounts = group.Files.GroupBy(f => f.Extension)
                .Select(g => $"{g.Key}: {g.Count()}")
                .ToList();
            sb.AppendLine($"Extensions: {string.Join(", ", extCounts)}");
            sb.AppendLine();
        }

        return sb.ToString();
    }
}
