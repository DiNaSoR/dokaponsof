using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.App.ViewModels;

public sealed record SoundItem(string Name, int Size, string SizeStr, string Format, int Index);
public sealed record PckFileItem(string Name, string Path, string Category);

public sealed partial class VoiceToolsViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _pckPath = "";
    [ObservableProperty] private bool _isExtractMode = true;
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private SoundItem? _selectedSound;
    [ObservableProperty] private int _selectedTabIndex;

    public ObservableCollection<SoundItem> BgmSounds { get; } = [];
    public ObservableCollection<SoundItem> SeSounds { get; } = [];
    public ObservableCollection<SoundItem> VoiceSounds { get; } = [];
    public ObservableCollection<SoundItem> VoiceEnSounds { get; } = [];
    public ObservableCollection<PckFileItem> PckFiles { get; } = [];

    // Keep archives keyed by category
    private readonly Dictionary<string, PckArchive> _archives = new();
    private StatusLogService Log => StatusLogService.Instance;

    public PckArchive? CurrentArchive => SelectedTabIndex >= 0 && SelectedTabIndex < PckFiles.Count
        ? _archives.GetValueOrDefault(PckFiles[SelectedTabIndex].Category)
        : null;

    partial void OnGamePathChanged(string value)
    {
        if (string.IsNullOrEmpty(value) || !Directory.Exists(value)) return;
        ScanPckFiles();
    }

    partial void OnSelectedTabIndexChanged(int value)
    {
        if (value >= 0 && value < PckFiles.Count)
            PckPath = PckFiles[value].Path;
    }

    [RelayCommand]
    private void ScanPckFiles()
    {
        if (string.IsNullOrEmpty(GamePath)) return;

        PckFiles.Clear();
        _archives.Clear();
        BgmSounds.Clear();
        SeSounds.Clear();
        VoiceSounds.Clear();
        VoiceEnSounds.Clear();

        var pckFiles = Directory.EnumerateFiles(GamePath, "*.pck", SearchOption.AllDirectories)
            .OrderBy(f => f)
            .ToList();

        foreach (string path in pckFiles)
        {
            string name = System.IO.Path.GetFileNameWithoutExtension(path);
            string category = name.ToLowerInvariant() switch
            {
                "bgm" => "bgm",
                "se" => "se",
                "voice-en" => "voice-en",
                "voice" => "voice",
                _ => name.ToLowerInvariant()
            };

            PckFiles.Add(new PckFileItem(name, path, category));
            LoadPckIntoCategory(path, category);
        }

        if (PckFiles.Count > 0)
        {
            SelectedTabIndex = 0;
            PckPath = PckFiles[0].Path;
        }

        Log.Info($"Found {PckFiles.Count} PCK files ({string.Join(", ", PckFiles.Select(p => p.Name))})");
    }

    private void LoadPckIntoCategory(string path, string category)
    {
        try
        {
            var archive = new PckArchive(path);
            _archives[category] = archive;

            var target = GetCollectionForCategory(category);
            target.Clear();

            for (int i = 0; i < archive.Sounds.Count; i++)
            {
                var s = archive.Sounds[i];
                string sizeStr = s.Size < 1024 ? $"{s.Size} B" : $"{s.Size / 1024.0:F1} KB";
                target.Add(new SoundItem(s.Name, s.Size, sizeStr, s.IsOpus ? "Opus" : "Raw", i));
            }

            Log.Success($"Loaded {archive.Sounds.Count} sounds from {System.IO.Path.GetFileName(path)}");
        }
        catch (Exception ex) { Log.Error($"Failed to load {System.IO.Path.GetFileName(path)}: {ex.Message}"); }
    }

    private ObservableCollection<SoundItem> GetCollectionForCategory(string category) => category switch
    {
        "bgm" => BgmSounds,
        "se" => SeSounds,
        "voice" => VoiceSounds,
        "voice-en" => VoiceEnSounds,
        _ => BgmSounds
    };

    [RelayCommand]
    private void BrowsePck()
    {
        string? path = DialogService.OpenFile("Select PCK File", "PCK files|*.pck|All files|*.*");
        if (path is null) return;
        PckPath = path;
        string name = System.IO.Path.GetFileNameWithoutExtension(path);
        LoadPckIntoCategory(path, name.ToLowerInvariant());
    }

    [RelayCommand]
    private async Task ExtractAllAsync()
    {
        var archive = CurrentArchive;
        if (archive is null) { Log.Warning("No PCK loaded"); return; }

        string? outputDir = DialogService.BrowseFolder("Select Output Directory");
        if (outputDir is null) return;

        IsBusy = true;
        try
        {
            var paths = await Task.Run(() => archive.ExtractAll(outputDir));
            Log.Success($"Extracted {paths.Count} sounds to {outputDir}");
        }
        catch (Exception ex) { Log.Error($"Extract failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private async Task ReplaceSelectedAsync()
    {
        var archive = CurrentArchive;
        if (archive is null || SelectedSound is null) { Log.Warning("Select a sound first"); return; }

        string? replacementPath = DialogService.OpenFile("Select Replacement Audio",
            "Audio files|*.opus;*.ogg;*.wav|All files|*.*");
        if (replacementPath is null) return;

        IsBusy = true;
        try
        {
            var newSound = await Task.Run(() => Sound.FromFile(replacementPath));
            if (archive.ReplaceSound(SelectedSound.Name, newSound))
                Log.Success($"Replaced: {SelectedSound.Name}");
            else
                Log.Error($"Sound not found: {SelectedSound.Name}");
        }
        catch (Exception ex) { Log.Error($"Replace failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private async Task SavePckAsync()
    {
        var archive = CurrentArchive;
        if (archive is null) { Log.Warning("No PCK loaded"); return; }

        string? outputPath = DialogService.SaveFile("Save PCK", "PCK files|*.pck",
            PckFiles.Count > SelectedTabIndex ? PckFiles[SelectedTabIndex].Name + ".pck" : "output.pck");
        if (outputPath is null) return;

        IsBusy = true;
        try
        {
            await Task.Run(() => archive.Write(outputPath));
            Log.Success($"PCK saved to {outputPath}");
        }
        catch (Exception ex) { Log.Error($"Save failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }
}
