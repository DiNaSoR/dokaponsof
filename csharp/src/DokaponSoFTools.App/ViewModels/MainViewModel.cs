using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.ViewModels;

public sealed record NavItem(string Name, string Icon, string Key);

public sealed partial class MainViewModel : ObservableObject
{
    [ObservableProperty]
    private string _gamePath = "";

    [ObservableProperty]
    private ObservableObject? _currentView;

    [ObservableProperty]
    private NavItem? _selectedNavItem;

    public ObservableCollection<NavItem> NavItems { get; } =
    [
        new("Asset Extractor", "\U0001F4E6", "assets"),
        new("Text Tools", "\U0001F4DD", "text"),
        new("Voice Tools", "\U0001F399", "voice"),
        new("Hex Editor", "\U0001F527", "hex"),
        new("Video Tools", "\U0001F3AC", "video"),
        new("Map Explorer", "\U0001F5FA", "map"),
        new("About", "\U00002139", "about")
    ];

    public StatusLogService StatusLog => StatusLogService.Instance;

    // Lazily created ViewModels (one instance each)
    private readonly Dictionary<string, ObservableObject> _viewModels = new();

    public MainViewModel()
    {
        // Restore game path
        string savedPath = SettingsService.Instance.GamePath;
        if (!string.IsNullOrEmpty(savedPath) && System.IO.Directory.Exists(savedPath))
            GamePath = savedPath;

        StatusLog.Info("Welcome to DOKAPON! Sword of Fury Tools v0.4.0");
    }

    [RelayCommand]
    private void Navigate(NavItem? item)
    {
        if (item is null) return;
        SelectedNavItem = item;
        NavigateTo(item.Key);
    }

    private void NavigateTo(string key)
    {
        if (!_viewModels.TryGetValue(key, out var vm))
        {
            vm = key switch
            {
                "assets" => new AssetExtractorViewModel(),
                "text" => new TextToolsViewModel(),
                "voice" => new VoiceToolsViewModel(),
                "hex" => new HexEditorViewModel(),
                "video" => new VideoToolsViewModel(),
                "map" => new MapExplorerViewModel(),
                "about" => new AboutViewModel(),
                _ => throw new ArgumentException($"Unknown nav key: {key}")
            };
            _viewModels[key] = vm;
        }

        // Propagate game path
        if (vm is IGamePathAware aware)
            aware.GamePath = GamePath;

        CurrentView = vm;
    }

    [RelayCommand]
    private void BrowseGamePath()
    {
        string? path = DialogService.BrowseFolder("Select Game Directory");
        if (path is null) return;

        GamePath = path;
        SettingsService.Instance.GamePath = path;
        StatusLog.Success($"Game path set: {path}");

        // Propagate to current view
        if (CurrentView is IGamePathAware aware)
            aware.GamePath = path;
    }

    [RelayCommand]
    private void ClearLog() => StatusLog.Clear();

    [RelayCommand]
    private void SaveLog()
    {
        string? path = DialogService.SaveFile("Save Log", "Text files|*.txt", "dokapon_tools_log.txt");
        if (path is null) return;

        System.IO.File.WriteAllText(path, StatusLog.GetLogText());
        StatusLog.Info($"Log saved to {path}");
    }
}

public interface IGamePathAware
{
    string GamePath { get; set; }
}
