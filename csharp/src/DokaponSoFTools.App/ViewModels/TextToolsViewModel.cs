using System.Collections.ObjectModel;
using System.IO;
using System.Text.RegularExpressions;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.App.ViewModels;

public sealed record DisplayTextEntry(
    TextEntry Raw,
    string CleanText,
    string Category,
    int ByteLength,
    double UsagePercent,
    bool IsOverflow);

public sealed partial class TextToolsViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _exePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private DisplayTextEntry? _selectedEntry;
    [ObservableProperty] private string _decodedPreview = "";
    [ObservableProperty] private string _rawPreview = "";
    [ObservableProperty] private string _searchFilter = "";
    [ObservableProperty] private int _selectedTabIndex;
    [ObservableProperty] private string _statsText = "";

    // Category tab headers with counts
    [ObservableProperty] private string _allTabHeader = "All";
    [ObservableProperty] private string _dialogTabHeader = "Dialog";
    [ObservableProperty] private string _labelsTabHeader = "Labels";
    [ObservableProperty] private string _hudTabHeader = "HUD/Stats";
    [ObservableProperty] private string _systemTabHeader = "System";

    public ObservableCollection<DisplayTextEntry> AllEntries { get; } = [];
    public ObservableCollection<DisplayTextEntry> DialogEntries { get; } = [];
    public ObservableCollection<DisplayTextEntry> LabelEntries { get; } = [];
    public ObservableCollection<DisplayTextEntry> HudEntries { get; } = [];
    public ObservableCollection<DisplayTextEntry> SystemEntries { get; } = [];

    private const string GameExeName = "DOKAPON! Sword of Fury.exe";
    private StatusLogService Log => StatusLogService.Instance;
    private List<TextEntry> _rawEntries = [];
    private List<DisplayTextEntry> _allDisplayEntries = [];

    // Regex for control codes
    private static readonly Regex ColorCodeRe = new(@"%(\d+)c", RegexOptions.Compiled);
    private static readonly Regex VarRe = new(@"%(\d*)([sSdD])", RegexOptions.Compiled);
    private static readonly Regex PosRe = new(@"%(\d+)([xXyY])", RegexOptions.Compiled);
    private static readonly Regex ButtonRe = new(@"%(\d+)M", RegexOptions.Compiled);

    partial void OnGamePathChanged(string value)
    {
        if (string.IsNullOrEmpty(value)) return;
        string candidate = Path.Combine(value, GameExeName);
        if (File.Exists(candidate)) ExePath = candidate;
    }

    partial void OnSelectedTabIndexChanged(int value) => ApplyFilter();

    [RelayCommand]
    private void BrowseExe()
    {
        string? path = DialogService.OpenFile("Select Game Executable", "Executable|*.exe|All files|*.*");
        if (path is not null) ExePath = path;
    }

    [RelayCommand]
    private async Task ExtractTextsAsync()
    {
        if (string.IsNullOrEmpty(ExePath) || !File.Exists(ExePath))
        {
            Log.Warning("Please select a valid executable file");
            return;
        }

        IsBusy = true;
        Log.Info("Extracting game texts...");

        try
        {
            _rawEntries = await Task.Run(() => GameText.ExtractToMemory(ExePath));

            // Build display entries with categorization
            _allDisplayEntries = _rawEntries.Select(e =>
            {
                string clean = DecodeForDisplay(e.Text);
                string category = CategorizeEntry(e.Text, clean);
                int byteLen = System.Text.Encoding.UTF8.GetByteCount(e.Text);
                double usage = e.MaxLength > 0 ? (double)byteLen / e.MaxLength * 100 : 0;
                return new DisplayTextEntry(e, clean, category, byteLen, usage, byteLen > e.MaxLength);
            }).ToList();

            // Populate category collections
            AllEntries.Clear();
            DialogEntries.Clear();
            LabelEntries.Clear();
            HudEntries.Clear();
            SystemEntries.Clear();

            foreach (var de in _allDisplayEntries)
            {
                AllEntries.Add(de);
                switch (de.Category)
                {
                    case "Dialog": DialogEntries.Add(de); break;
                    case "Labels": LabelEntries.Add(de); break;
                    case "HUD": HudEntries.Add(de); break;
                    case "System": SystemEntries.Add(de); break;
                }
            }

            UpdateTabHeaders();
            UpdateStats();
            Log.Success($"Extracted {_rawEntries.Count} text entries");
        }
        catch (Exception ex) { Log.Error($"Extract failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    private void UpdateTabHeaders()
    {
        AllTabHeader = $"All ({AllEntries.Count})";
        DialogTabHeader = $"Dialog ({DialogEntries.Count})";
        LabelsTabHeader = $"Labels ({LabelEntries.Count})";
        HudTabHeader = $"HUD ({HudEntries.Count})";
        SystemTabHeader = $"System ({SystemEntries.Count})";
    }

    private void UpdateStats()
    {
        int total = _allDisplayEntries.Count;
        int withColors = _allDisplayEntries.Count(e => ColorCodeRe.IsMatch(e.Raw.Text));
        int withVars = _allDisplayEntries.Count(e => VarRe.IsMatch(e.Raw.Text));
        int readable = _allDisplayEntries.Count(e => e.CleanText.Length > 3);
        StatsText = $"Total: {total} | Readable: {readable} | With Colors: {withColors} | With Variables: {withVars}";
    }

    partial void OnSelectedEntryChanged(DisplayTextEntry? value)
    {
        if (value is null)
        {
            DecodedPreview = "";
            RawPreview = "";
            return;
        }

        DecodedPreview = FormatDecodedPreview(value.Raw.Text);
        RawPreview = value.Raw.Text;
    }

    partial void OnSearchFilterChanged(string value) => ApplyFilter();

    private void ApplyFilter()
    {
        var source = SelectedTabIndex switch
        {
            1 => _allDisplayEntries.Where(e => e.Category == "Dialog"),
            2 => _allDisplayEntries.Where(e => e.Category == "Labels"),
            3 => _allDisplayEntries.Where(e => e.Category == "HUD"),
            4 => _allDisplayEntries.Where(e => e.Category == "System"),
            _ => _allDisplayEntries.AsEnumerable()
        };

        if (!string.IsNullOrEmpty(SearchFilter))
            source = source.Where(e =>
                e.CleanText.Contains(SearchFilter, StringComparison.OrdinalIgnoreCase) ||
                e.Raw.Text.Contains(SearchFilter, StringComparison.OrdinalIgnoreCase));

        var target = SelectedTabIndex switch
        {
            1 => DialogEntries,
            2 => LabelEntries,
            3 => HudEntries,
            4 => SystemEntries,
            _ => AllEntries
        };

        target.Clear();
        foreach (var e in source) target.Add(e);
    }

    // --- Export / Import (unchanged binary-safe logic) ---

    [RelayCommand]
    private void ExportTexts()
    {
        if (_rawEntries.Count == 0) { Log.Warning("No texts loaded"); return; }

        string? path = DialogService.SaveFile("Save Texts", "Text files|*.txt|CSV|*.csv|JSON|*.json", "texts.txt");
        if (path is null) return;

        if (path.EndsWith(".json", StringComparison.OrdinalIgnoreCase))
        {
            ExportAsJson(path);
            return;
        }

        if (path.EndsWith(".csv", StringComparison.OrdinalIgnoreCase))
        {
            ExportAsCsv(path);
            return;
        }

        // Standard txt export (binary-safe, used for reimport)
        string offsetsPath = Path.ChangeExtension(path, ".offsets.txt");
        using var tw = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        using var ow = new StreamWriter(offsetsPath, false, System.Text.Encoding.UTF8);

        foreach (var e in _rawEntries)
        {
            tw.WriteLine(e.Text);
            ow.WriteLine($"{e.Offset}:{e.MaxLength}");
        }

        Log.Success($"Exported {_rawEntries.Count} texts + offsets to {Path.GetFileName(path)}");
    }

    private void ExportAsJson(string path)
    {
        using var fs = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        fs.WriteLine("[");
        for (int i = 0; i < _rawEntries.Count; i++)
        {
            var e = _rawEntries[i];
            var de = i < _allDisplayEntries.Count ? _allDisplayEntries[i] : null;
            string escaped = e.Text.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n").Replace("\r", "\\r");
            string clean = (de?.CleanText ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\n", "\\n");
            string comma = i < _rawEntries.Count - 1 ? "," : "";
            fs.WriteLine($"  {{\"offset\": {e.Offset}, \"maxLength\": {e.MaxLength}, \"category\": \"{de?.Category}\", \"text\": \"{escaped}\", \"decoded\": \"{clean}\"}}{comma}");
        }
        fs.WriteLine("]");
        Log.Success($"Exported {_rawEntries.Count} texts as JSON");
    }

    private void ExportAsCsv(string path)
    {
        using var fs = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        fs.WriteLine("Offset,MaxLength,Category,ByteUsed,Text,Decoded");
        for (int i = 0; i < _rawEntries.Count; i++)
        {
            var e = _rawEntries[i];
            var de = i < _allDisplayEntries.Count ? _allDisplayEntries[i] : null;
            string text = e.Text.Replace("\"", "\"\"");
            string clean = (de?.CleanText ?? "").Replace("\"", "\"\"");
            fs.WriteLine($"0x{e.Offset:X},\"{e.MaxLength}\",\"{de?.Category}\",\"{de?.ByteLength}\",\"{text}\",\"{clean}\"");
        }
        Log.Success($"Exported {_rawEntries.Count} texts as CSV");
    }

    [RelayCommand]
    private async Task ImportTextsAsync()
    {
        if (string.IsNullOrEmpty(ExePath))
        {
            Log.Warning("Please select a valid executable");
            return;
        }

        string? textsPath = DialogService.OpenFile("Select Modified Texts", "Text files|*.txt");
        if (textsPath is null) return;
        string? offsetsPath = DialogService.OpenFile("Select Offsets File", "Text files|*.txt");
        if (offsetsPath is null) return;
        string? outputPath = DialogService.SaveFile("Save Modified Executable", "Executable|*.exe", "modded.exe");
        if (outputPath is null) return;

        IsBusy = true;
        try
        {
            var (replaced, skipped) = await Task.Run(() =>
                GameText.ImportTexts(ExePath, textsPath, offsetsPath, outputPath));
            Log.Success($"Imported: {replaced} replaced, {skipped} truncated (binary-safe)");
        }
        catch (Exception ex) { Log.Error($"Import failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    // --- Text Decoding (display only, never touches raw data) ---

    /// <summary>Strip control codes for clean display text.</summary>
    private static string DecodeForDisplay(string raw)
    {
        if (string.IsNullOrEmpty(raw)) return "";

        string s = raw;
        // Remove block markers
        s = s.Replace("\\p", "").Replace("\\k", "").Replace("\\z", "");
        // Convert line breaks
        s = s.Replace("\\n", "\n").Replace("\\r", "");
        // Remove modifiers
        s = s.Replace("\\h", "").Replace("\\m", "").Replace("\\,", "").Replace("\\C", "");
        // Remove color codes %Nc
        s = ColorCodeRe.Replace(s, "");
        // Remove position codes %Nx %Ny %NX
        s = PosRe.Replace(s, "");
        // Replace variables with placeholders
        s = ButtonRe.Replace(s, "[BTN]");
        s = VarRe.Replace(s, m => m.Groups[2].Value.ToUpper() switch
        {
            "S" => "[text]",
            "D" => "[num]",
            _ => "[var]"
        });

        return s.Trim();
    }

    /// <summary>Format text with readable control code annotations.</summary>
    private static string FormatDecodedPreview(string raw)
    {
        if (string.IsNullOrEmpty(raw)) return "";

        var sb = new System.Text.StringBuilder();

        // Add header with offset info
        sb.AppendLine("--- Decoded View ---");
        sb.AppendLine();

        string s = raw;
        // Annotate block markers
        s = s.Replace("\\p", "");
        s = s.Replace("\\k", " [WAIT]");
        s = s.Replace("\\z", " [END]");
        s = s.Replace("\\n", "\n");
        s = s.Replace("\\r", "[FRAME] ");
        s = s.Replace("\\h", "[HEADER] ");
        s = s.Replace("\\m", "[x]");
        s = s.Replace("\\,", "[,]");
        s = s.Replace("\\C", "[CLR]");

        // Annotate colors
        s = ColorCodeRe.Replace(s, m =>
        {
            int idx = int.Parse(m.Groups[1].Value);
            return idx == 0 ? "[/color]" : $"[color={idx}]";
        });

        // Annotate positions
        s = PosRe.Replace(s, m => $"[pos:{m.Groups[1].Value}{m.Groups[2].Value}]");

        // Annotate buttons
        s = ButtonRe.Replace(s, m => $"[BTN:{m.Groups[1].Value}]");

        // Annotate variables
        s = VarRe.Replace(s, m =>
        {
            string width = m.Groups[1].Value;
            string type = m.Groups[2].Value;
            string desc = type switch { "s" or "S" => "text", "d" or "D" => "number", _ => "var" };
            return string.IsNullOrEmpty(width) ? $"[{desc}]" : $"[{desc}:{width}]";
        });

        sb.Append(s.Trim());
        return sb.ToString();
    }

    /// <summary>Categorize a text entry based on its content patterns.</summary>
    private static string CategorizeEntry(string raw, string clean)
    {
        // Short entries with only control codes = system
        if (clean.Length <= 2) return "System";

        // Has positioning codes = HUD/stats display
        if (PosRe.IsMatch(raw)) return "HUD";

        // Has \h header marker = label
        if (raw.Contains("\\h")) return "Labels";

        // Has \k or \z with substantial text = dialog
        if ((raw.Contains("\\k") || raw.Contains("\\z")) && clean.Length > 5) return "Dialog";

        // Has \r = framed dialog
        if (raw.Contains("\\r") && clean.Length > 5) return "Dialog";

        // Short clean text = label
        if (clean.Length <= 20 && !clean.Contains('\n')) return "Labels";

        // Multi-line = dialog
        if (clean.Contains('\n')) return "Dialog";

        // Default
        return clean.Length > 5 ? "Dialog" : "System";
    }
}
