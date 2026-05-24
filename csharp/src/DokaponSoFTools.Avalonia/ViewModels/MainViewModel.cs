using System.Collections.ObjectModel;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.ViewModels;

public sealed record NavItem(string Name, string Icon, string Key);

public sealed partial class MainViewModel : ObservableObject
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private ObservableObject? _currentView;
    [ObservableProperty] private NavItem? _selectedNavItem;

    public ObservableCollection<NavItem> NavItems { get; } =
    [
        new("Asset Extractor", "\U0001F4E6", "assets"),
        new("Text Tools",      "\U0001F4DD", "text"),
        new("Voice Tools",     "\U0001F399", "voice"),
        new("Hex Editor",      "\U0001F527", "hex"),
        new("Video Tools",     "\U0001F3AC", "video"),
        new("Map Explorer",    "\U0001F5FA", "map"),
        new("3D Models",       "\U0001F5FF", "model"),
        new("Animations",      "\U0001F39E", "anim"),
        new("Game Scanner",    "\U0001F50D", "scanner"),
        new("About",           "\U00002139", "about"),
        new("Settings",        "⚙",     "settings")
    ];

    public StatusLogService StatusLog => StatusLogService.Instance;

    // One lazily-created ViewModel instance per nav key.
    private readonly Dictionary<string, ObservableObject> _viewModels = new();

    public MainViewModel()
    {
        string savedPath = SettingsService.Instance.GamePath;
        if (!string.IsNullOrEmpty(savedPath) && System.IO.Directory.Exists(savedPath))
            GamePath = savedPath;

        StatusLog.Info("Welcome to DOKAPON! Sword of Fury Tools");

        // Always land on the About page first. Setting the selection triggers
        // navigation via OnSelectedNavItemChanged.
        SelectedNavItem = NavItems.First(n => n.Key == "about");
    }

    partial void OnSelectedNavItemChanged(NavItem? value)
    {
        if (value is null) return;
        NavigateTo(value.Key);
        SettingsService.Instance.LastNavKey = value.Key;
    }

    private void NavigateTo(string key)
    {
        if (!_viewModels.TryGetValue(key, out var vm))
        {
            // Only ported tools have real ViewModels yet; the rest show a
            // placeholder until their milestone lands.
            vm = key switch
            {
                "assets" => new AssetExtractorViewModel(),
                "text" => new TextToolsViewModel(),
                "voice" => new VoiceToolsViewModel(),
                "hex" => new HexEditorViewModel(),
                "video" => new VideoToolsViewModel(),
                "map" => new MapExplorerViewModel(),
                "model" => new ModelViewerViewModel(),
                "anim" => new AnimationViewerViewModel(),
                "scanner" => new GameScannerViewModel(),
                "about" => new AboutViewModel(),
                "settings" => new SettingsViewModel(this),
                _ => new PlaceholderViewModel(NavItems.First(n => n.Key == key).Name)
            };
            _viewModels[key] = vm;
        }

        if (vm is IGamePathAware aware)
            aware.GamePath = GamePath;

        CurrentView = vm;
    }

    [RelayCommand]
    private async Task BrowseGamePathAsync()
    {
        string? path = await StorageService.BrowseFolderAsync("Select Game Directory");
        if (path is null) return;
        SetGamePath(path);
    }

    public void SetGamePath(string path)
    {
        GamePath = path;
        SettingsService.Instance.GamePath = path;
        SettingsService.Instance.AddRecentPath(path);
        StatusLog.Success($"Game path set: {path}");

        // Propagate to every already-created tool.
        foreach (var vm in _viewModels.Values)
            if (vm is IGamePathAware aware)
                aware.GamePath = path;
    }

    public List<string> RecentPaths => SettingsService.Instance.RecentPaths;
}

public interface IGamePathAware
{
    string GamePath { get; set; }
}
