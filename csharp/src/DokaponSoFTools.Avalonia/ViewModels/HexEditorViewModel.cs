using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.App.ViewModels;

public sealed partial class HexFileItem : ObservableObject
{
    public string Name { get; }
    public string Path { get; }
    [ObservableProperty] private bool _isChecked = true;

    public HexFileItem(string name, string path) { Name = name; Path = path; }
}

public sealed record PatchDisplayItem(string File, string Offset, string Size, string Preview);
public sealed record ConflictDisplayItem(string Type, string File1, string File2, string Offset);

public sealed partial class HexEditorViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _exePath = "";
    [ObservableProperty] private bool _createBackup;
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private int _totalPatches;
    [ObservableProperty] private int _totalBytes;
    [ObservableProperty] private int _sourceFileCount;

    public ObservableCollection<HexFileItem> HexFiles { get; } = [];
    public ObservableCollection<PatchDisplayItem> Patches { get; } = [];
    public ObservableCollection<ConflictDisplayItem> Conflicts { get; } = [];

    private const string GameExeName = "DOKAPON! Sword of Fury.exe";
    private List<HexPatchEntry> _allPatches = [];
    private StatusLogService Log => StatusLogService.Instance;

    public HexEditorViewModel() => _createBackup = SettingsService.Instance.CreateBackup;

    partial void OnCreateBackupChanged(bool value) => SettingsService.Instance.CreateBackup = value;

    partial void OnGamePathChanged(string value)
    {
        if (string.IsNullOrEmpty(value)) return;
        string candidate = System.IO.Path.Combine(value, GameExeName);
        if (System.IO.File.Exists(candidate)) ExePath = candidate;
    }

    [RelayCommand]
    private async Task AddHexFilesAsync()
    {
        var paths = await StorageService.OpenFilesAsync("Select Hex Files", "Hex files|*.hex|All files|*.*");
        if (paths is null) return;

        foreach (string path in paths)
            if (HexFiles.All(f => f.Path != path))
                HexFiles.Add(new HexFileItem(System.IO.Path.GetFileName(path), path));

        RefreshPatches();
    }

    [RelayCommand]
    private async Task AddHexFolderAsync()
    {
        string? dir = await StorageService.BrowseFolderAsync("Select Hex Folder");
        if (dir is null) return;

        foreach (string path in HexPatch.FindHexFiles(dir))
            if (HexFiles.All(f => f.Path != path))
                HexFiles.Add(new HexFileItem(System.IO.Path.GetFileName(path), path));

        RefreshPatches();
    }

    [RelayCommand]
    private void RemoveSelected()
    {
        var toRemove = HexFiles.Where(f => !f.IsChecked).ToList();
        foreach (var item in toRemove) HexFiles.Remove(item);
        RefreshPatches();
    }

    private void RefreshPatches()
    {
        var checkedPaths = HexFiles.Where(f => f.IsChecked).Select(f => f.Path).ToList();
        _allPatches = HexPatch.ParseFiles(checkedPaths);

        Patches.Clear();
        foreach (var p in _allPatches)
        {
            Patches.Add(new PatchDisplayItem(
                System.IO.Path.GetFileName(p.SourceFile),
                $"0x{p.Offset:X8}",
                $"0x{p.Size:X4}",
                p.GetHexPreview(16)
            ));
        }

        var conflicts = HexPatch.DetectConflicts(_allPatches);
        Conflicts.Clear();
        foreach (var c in conflicts)
        {
            Conflicts.Add(new ConflictDisplayItem(
                c.ConflictType,
                System.IO.Path.GetFileName(c.Patch1.SourceFile),
                System.IO.Path.GetFileName(c.Patch2.SourceFile),
                $"0x{c.Patch1.Offset:X8}"
            ));
        }

        TotalPatches = _allPatches.Count;
        TotalBytes = (int)_allPatches.Sum(p => p.Size);
        SourceFileCount = _allPatches.Select(p => p.SourceFile).Distinct().Count();
    }

    [RelayCommand]
    private async Task ApplyPatchesAsync()
    {
        if (string.IsNullOrEmpty(ExePath) || !File.Exists(ExePath))
        {
            Log.Warning("Please select a valid executable");
            return;
        }

        if (_allPatches.Count == 0)
        {
            Log.Warning("No patches loaded");
            return;
        }

        IsBusy = true;
        try
        {
            var (applied, errors) = await Task.Run(() =>
                HexPatch.ApplyPatches(ExePath, _allPatches, backup: CreateBackup));

            foreach (string err in errors) Log.Warning(err);
            Log.Success($"Applied {applied}/{_allPatches.Count} patches to {System.IO.Path.GetFileName(ExePath)}");
        }
        catch (Exception ex) { Log.Error($"Apply failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }
}
