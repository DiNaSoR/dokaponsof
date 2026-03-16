using System.IO;
using System.Text.Json;

namespace DokaponSoFTools.App.Services;

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
