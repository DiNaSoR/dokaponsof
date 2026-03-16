using System.Text;
using System.Text.RegularExpressions;

namespace DokaponSoFTools.Core.Formats;

public sealed record TextEntry(string Text, int Offset, int MaxLength);

public static class GameText
{
    private static readonly byte[] TextStartMarker = [(byte)'\\', (byte)'p']; // \p

    public static List<TextEntry> ExtractToMemory(string exePath)
    {
        byte[] content = File.ReadAllBytes(exePath);
        var results = new List<TextEntry>();

        for (int i = 0; i <= content.Length - 2; i++)
        {
            if (content[i] != 0x5C || content[i + 1] != 0x70) continue; // \p

            int start = i;
            int end = FindTextEnd(content, start);
            int length = end - start;

            try
            {
                string text = Encoding.UTF8.GetString(content, start, length);
                if (text.Length < 3) continue;

                int printable = text.Count(c => !char.IsControl(c) || c is '\n' or '\r' or '\t');
                if ((double)printable / text.Length < 0.5) continue;

                results.Add(new TextEntry(text, start, length));
            }
            catch (DecoderFallbackException) { /* skip non-UTF8 */ }
        }

        return results;
    }

    public static int ExtractToFiles(string exePath, string textsPath, string offsetsPath)
    {
        var entries = ExtractToMemory(exePath);
        Directory.CreateDirectory(Path.GetDirectoryName(textsPath) ?? ".");

        using var textWriter = new StreamWriter(textsPath, false, Encoding.UTF8);
        using var offsetWriter = new StreamWriter(offsetsPath, false, Encoding.UTF8);

        foreach (var entry in entries)
        {
            textWriter.WriteLine(entry.Text);
            offsetWriter.WriteLine($"{entry.Offset}:{entry.MaxLength}");
        }

        return entries.Count;
    }

    public static (int Replaced, int Skipped) ImportTexts(
        string originalExePath, string modifiedTextsPath,
        string offsetsPath, string outputExePath)
    {
        byte[] content = File.ReadAllBytes(originalExePath);
        string[] modifiedTexts = File.ReadAllLines(modifiedTextsPath, Encoding.UTF8);
        string[] offsetLines = File.ReadAllLines(offsetsPath, Encoding.UTF8);

        int replaced = 0, skipped = 0;

        for (int i = 0; i < Math.Min(offsetLines.Length, modifiedTexts.Length); i++)
        {
            string line = offsetLines[i].Trim();
            if (!line.Contains(':')) continue;

            var parts = line.Split(':', 2);
            int offset = int.Parse(parts[0]);
            int originalLength = int.Parse(parts[1]);

            byte[] newBytes = Encoding.UTF8.GetBytes(modifiedTexts[i].TrimEnd('\r', '\n'));

            if (newBytes.Length > originalLength)
            {
                newBytes = newBytes[..originalLength];
                skipped++;
            }

            // Pad with nulls if shorter
            Array.Copy(newBytes, 0, content, offset, newBytes.Length);
            for (int j = newBytes.Length; j < originalLength; j++)
                content[offset + j] = 0;

            replaced++;
        }

        Directory.CreateDirectory(Path.GetDirectoryName(outputExePath) ?? ".");
        File.WriteAllBytes(outputExePath, content);

        return (replaced, skipped);
    }

    public static Dictionary<string, int> AnalyzePatterns(string exePath)
    {
        var entries = ExtractToMemory(exePath);
        var stats = new Dictionary<string, int>
        {
            ["total_texts"] = entries.Count,
            ["with_k"] = entries.Count(e => e.Text.Contains("\\k")),
            ["with_r"] = entries.Count(e => e.Text.Contains("\\r")),
            ["with_h"] = entries.Count(e => e.Text.Contains("\\h")),
            ["with_colors"] = entries.Count(e => Regex.IsMatch(e.Text, @"%\d+c")),
            ["with_positions"] = entries.Count(e => Regex.IsMatch(e.Text, @"%\d+[xy]")),
            ["with_variables"] = entries.Count(e => e.Text.Contains("%s") || e.Text.Contains("%d"))
        };

        if (entries.Count > 0)
        {
            stats["avg_length"] = entries.Sum(e => e.Text.Length) / entries.Count;
            stats["min_length"] = entries.Min(e => e.Text.Length);
            stats["max_length"] = entries.Max(e => e.Text.Length);
        }

        return stats;
    }

    private static int FindTextEnd(byte[] content, int start)
    {
        int pos = start + 2; // Skip initial \p

        while (pos < content.Length)
        {
            byte b = content[pos];

            if (b == 0x5C && pos + 1 < content.Length)
            {
                byte next = content[pos + 1];
                if (next == 0x6B) return pos + 2; // \k - include it
                if (next == 0x7A) return pos + 2; // \z - include it
                if (next == 0x70) return pos;      // next \p - don't include
            }

            if (b == 0x00) return pos; // Null byte = end

            pos++;
        }

        return content.Length;
    }
}
