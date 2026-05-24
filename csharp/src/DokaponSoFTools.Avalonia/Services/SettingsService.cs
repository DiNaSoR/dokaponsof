using System.IO;
using System.Text.Json;

namespace DokaponSoFTools.App.Services;

/// <summary>
/// Cross-platform settings store (JSON under the user's ApplicationData).
/// Ported verbatim from the WPF app — it had no platform dependencies.
/// </summary>
public sealed class SettingsService
{
    private static readonly string SettingsDir = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
        "DokaponSoFTools");

    private static readonly string SettingsPath = Path.Combine(SettingsDir, "settings.json");

    private Dictionary<string, string> _settings = new();

    public static SettingsService Instance { get; } = new();

    private SettingsService()
    {
        Load();
    }

    public string? Get(string key) => _settings.GetValueOrDefault(key);

    public void Set(string key, string value)
    {
        _settings[key] = value;
        Save();
    }

    public string GamePath
    {
        get => Get("game_path") ?? "";
        set => Set("game_path", value);
    }

    // Recent game paths (max 5)
    public List<string> RecentPaths
    {
        get
        {
            var json = Get("recent_paths");
            if (string.IsNullOrEmpty(json)) return [];
            try { return JsonSerializer.Deserialize<List<string>>(json) ?? []; }
            catch { return []; }
        }
    }

    public void AddRecentPath(string path)
    {
        var recent = RecentPaths;
        recent.Remove(path);
        recent.Insert(0, path);
        if (recent.Count > 5) recent.RemoveRange(5, recent.Count - 5);
        Set("recent_paths", JsonSerializer.Serialize(recent));
    }

    // Window state
    public double WindowLeft { get => double.TryParse(Get("win_left"), out var v) ? v : double.NaN; set => Set("win_left", value.ToString()); }
    public double WindowTop { get => double.TryParse(Get("win_top"), out var v) ? v : double.NaN; set => Set("win_top", value.ToString()); }
    public double WindowWidth { get => double.TryParse(Get("win_width"), out var v) ? v : 1200; set => Set("win_width", value.ToString()); }
    public double WindowHeight { get => double.TryParse(Get("win_height"), out var v) ? v : 800; set => Set("win_height", value.ToString()); }
    public bool WindowMaximized { get => Get("win_max") == "1"; set => Set("win_max", value ? "1" : "0"); }

    // Last selected nav item
    public string LastNavKey { get => Get("last_nav") ?? ""; set => Set("last_nav", value); }

    // Default extraction output folder (used by Asset Extractor when set)
    public string DefaultOutputPath { get => Get("default_output") ?? ""; set => Set("default_output", value); }

    // Create a backup before applying hex patches (default true)
    public bool CreateBackup { get => Get("create_backup") != "0"; set => Set("create_backup", value ? "1" : "0"); }

    // UI accent colour (hex ARGB)
    public string AccentColor { get => Get("accent_color") ?? "#FF3B9EFF"; set => Set("accent_color", value); }

    private void Load()
    {
        try
        {
            if (File.Exists(SettingsPath))
            {
                string json = File.ReadAllText(SettingsPath);
                _settings = JsonSerializer.Deserialize<Dictionary<string, string>>(json) ?? new();
            }
        }
        catch { _settings = new(); }
    }

    private void Save()
    {
        try
        {
            Directory.CreateDirectory(SettingsDir);
            string json = JsonSerializer.Serialize(_settings, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(SettingsPath, json);
        }
        catch { /* best effort */ }
    }
}
