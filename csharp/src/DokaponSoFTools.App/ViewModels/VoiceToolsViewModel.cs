using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.App.ViewModels;

public sealed record SoundItem(string Name, int Size, string SizeStr, string Format, int Index);

public sealed partial class VoiceToolsViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _pckPath = "";
    [ObservableProperty] private bool _isExtractMode = true;
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private SoundItem? _selectedSound;

    public ObservableCollection<SoundItem> Sounds { get; } = [];

    private PckArchive? _archive;
    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (string.IsNullOrEmpty(value) || !Directory.Exists(value)) return;
        // Auto-find first PCK file in game directory tree
        var pck = Directory.EnumerateFiles(value, "*.pck", SearchOption.AllDirectories).FirstOrDefault();
        if (pck is not null)
        {
            PckPath = pck;
            LoadPck();
        }
    }

    [RelayCommand]
    private void BrowsePck()
    {
        string? path = DialogService.OpenFile("Select PCK File", "PCK files|*.pck|All files|*.*");
        if (path is null) return;
        PckPath = path;
        LoadPck();
    }

    private void LoadPck()
    {
        if (string.IsNullOrEmpty(PckPath) || !File.Exists(PckPath)) return;

        try
        {
            _archive = new PckArchive(PckPath);
            Sounds.Clear();

            for (int i = 0; i < _archive.Sounds.Count; i++)
            {
                var s = _archive.Sounds[i];
                string sizeStr = s.Size < 1024 ? $"{s.Size} B" : $"{s.Size / 1024.0:F1} KB";
                Sounds.Add(new SoundItem(s.Name, s.Size, sizeStr, s.IsOpus ? "Opus" : "Raw", i));
            }

            Log.Success($"Loaded PCK: {_archive.Sounds.Count} sounds");
        }
        catch (Exception ex) { Log.Error($"Failed to load PCK: {ex.Message}"); }
    }

    [RelayCommand]
    private async Task ExtractAllAsync()
    {
        if (_archive is null) { Log.Warning("No PCK loaded"); return; }

        string? outputDir = DialogService.BrowseFolder("Select Output Directory");
        if (outputDir is null) return;

        IsBusy = true;
        try
        {
            var paths = await Task.Run(() => _archive.ExtractAll(outputDir));
            Log.Success($"Extracted {paths.Count} sounds to {outputDir}");
        }
        catch (Exception ex) { Log.Error($"Extract failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private async Task ReplaceSelectedAsync()
    {
        if (_archive is null || SelectedSound is null) { Log.Warning("Select a sound first"); return; }

        string? replacementPath = DialogService.OpenFile("Select Replacement Audio",
            "Audio files|*.opus;*.ogg;*.wav|All files|*.*");
        if (replacementPath is null) return;

        IsBusy = true;
        try
        {
            var newSound = await Task.Run(() => Sound.FromFile(replacementPath));
            if (_archive.ReplaceSound(SelectedSound.Name, newSound))
            {
                Log.Success($"Replaced: {SelectedSound.Name}");
                LoadPck(); // Refresh
            }
            else
            {
                Log.Error($"Sound not found: {SelectedSound.Name}");
            }
        }
        catch (Exception ex) { Log.Error($"Replace failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private async Task SavePckAsync()
    {
        if (_archive is null) { Log.Warning("No PCK loaded"); return; }

        string? outputPath = DialogService.SaveFile("Save PCK", "PCK files|*.pck", Path.GetFileName(PckPath));
        if (outputPath is null) return;

        IsBusy = true;
        try
        {
            await Task.Run(() => _archive.Write(outputPath));
            Log.Success($"PCK saved to {outputPath}");
        }
        catch (Exception ex) { Log.Error($"Save failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }
}
