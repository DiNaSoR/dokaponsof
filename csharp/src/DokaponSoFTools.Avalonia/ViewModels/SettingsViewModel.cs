using System.IO;
using Avalonia;
using Avalonia.Media;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.ViewModels;

public sealed record AccentOption(string Name, string Hex)
{
    public IBrush Swatch => new SolidColorBrush(Color.Parse(Hex));
}

public sealed partial class SettingsViewModel : ObservableObject
{
    /// <summary>The shell — game path stays the single source of truth here.</summary>
    public MainViewModel Main { get; }

    [ObservableProperty] private string _defaultOutputPath;
    [ObservableProperty] private bool _createBackup;
    [ObservableProperty] private string _accentColor;

    public AccentOption[] AccentOptions { get; } =
    [
        new("Blue",   "#FF3B9EFF"),
        new("Teal",   "#FF36C7D0"),
        new("Violet", "#FF9B6BFF"),
        new("Green",  "#FF46C46A"),
        new("Amber",  "#FFE0B341"),
        new("Rose",   "#FFE5557F")
    ];

    public SettingsViewModel(MainViewModel main)
    {
        Main = main;
        _defaultOutputPath = SettingsService.Instance.DefaultOutputPath;
        _createBackup = SettingsService.Instance.CreateBackup;
        _accentColor = SettingsService.Instance.AccentColor;

        // Reflect game-path changes made from the top bar while this page is open.
        Main.PropertyChanged += (_, e) =>
        {
            if (e.PropertyName == nameof(MainViewModel.GamePath))
            {
                OnPropertyChanged(nameof(RecentPaths));
        OnPropertyChanged(nameof(HasRecentPaths));
            }
        };
    }

    public System.Collections.Generic.List<string> RecentPaths => SettingsService.Instance.RecentPaths;
    public bool HasRecentPaths => RecentPaths.Count > 0;

    partial void OnDefaultOutputPathChanged(string value) => SettingsService.Instance.DefaultOutputPath = value;
    partial void OnCreateBackupChanged(bool value) => SettingsService.Instance.CreateBackup = value;
    partial void OnAccentColorChanged(string value) => SettingsService.Instance.AccentColor = value;

    [RelayCommand]
    private async Task BrowseGamePathAsync()
    {
        string? path = await StorageService.BrowseFolderAsync("Select Game Directory");
        if (path is null) return;
        Main.SetGamePath(path);
        OnPropertyChanged(nameof(RecentPaths));
        OnPropertyChanged(nameof(HasRecentPaths));
    }

    [RelayCommand]
    private void AutoDetectGamePath()
    {
        string? found = TryFindGame();
        if (found is not null)
        {
            Main.SetGamePath(found);
            OnPropertyChanged(nameof(RecentPaths));
        OnPropertyChanged(nameof(HasRecentPaths));
        }
        else
        {
            StatusLogService.Instance.Warning("Game folder not found in common Steam locations — use Browse.");
        }
    }

    [RelayCommand]
    private void UseRecentPath(string? path)
    {
        if (string.IsNullOrEmpty(path) || !Directory.Exists(path)) return;
        Main.SetGamePath(path);
        OnPropertyChanged(nameof(RecentPaths));
        OnPropertyChanged(nameof(HasRecentPaths));
    }

    [RelayCommand]
    private async Task BrowseOutputAsync()
    {
        string? path = await StorageService.BrowseFolderAsync("Select Default Output Folder");
        if (path is not null) DefaultOutputPath = path;
    }

    [RelayCommand]
    private void ClearOutput() => DefaultOutputPath = "";

    [RelayCommand]
    private void SetAccent(string? hex)
    {
        if (string.IsNullOrEmpty(hex)) return;
        AccentColor = hex;     // persists via OnAccentColorChanged
        ApplyAccent(hex);      // live update
    }

    /// <summary>Swaps the accent brushes in the app's resources (live + at startup).</summary>
    public static void ApplyAccent(string hex)
    {
        if (Application.Current is not { } app) return;
        if (!Color.TryParse(hex, out var color)) return;

        var brush = new SolidColorBrush(color);
        var dim = new SolidColorBrush(new Color(color.A,
            (byte)(color.R * 0.82), (byte)(color.G * 0.82), (byte)(color.B * 0.82)));

        app.Resources["AccentColor"] = color;
        app.Resources["AccentBrush"] = brush;
        app.Resources["AccentGoldBrush"] = brush;
        app.Resources["AccentGoldDimBrush"] = dim;
    }

    private static string? TryFindGame()
    {
        string rel = Path.Combine("steamapps", "common", "DOKAPON ~Sword of Fury~");
        var bases = new System.Collections.Generic.List<string>();

        foreach (var drive in DriveInfo.GetDrives())
        {
            if (!drive.IsReady) continue;
            string root = drive.RootDirectory.FullName;
            bases.Add(Path.Combine(root, "Program Files (x86)", "Steam"));
            bases.Add(Path.Combine(root, "Steam"));
            bases.Add(Path.Combine(root, "SteamLibrary"));
            bases.Add(Path.Combine(root, "Games", "Steam"));
        }

        foreach (var b in bases)
        {
            string candidate = Path.Combine(b, rel);
            if (Directory.Exists(candidate)) return candidate;
        }
        return null;
    }
}
