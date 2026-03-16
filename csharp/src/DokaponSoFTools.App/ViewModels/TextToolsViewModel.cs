using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.App.ViewModels;

public sealed partial class TextToolsViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _exePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private bool _isExtractMode = true;
    [ObservableProperty] private TextEntry? _selectedEntry;
    [ObservableProperty] private string _selectedText = "";
    [ObservableProperty] private string _searchFilter = "";
    [ObservableProperty] private int _totalEntries;
    [ObservableProperty] private int _withColors;
    [ObservableProperty] private int _withVariables;

    public ObservableCollection<TextEntry> TextEntries { get; } = [];

    private const string GameExeName = "DOKAPON! Sword of Fury.exe";
    private StatusLogService Log => StatusLogService.Instance;
    private List<TextEntry> _allEntries = [];

    partial void OnGamePathChanged(string value)
    {
        if (string.IsNullOrEmpty(value)) return;
        string candidate = Path.Combine(value, GameExeName);
        if (File.Exists(candidate)) ExePath = candidate;
    }

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
            _allEntries = await Task.Run(() => GameText.ExtractToMemory(ExePath));
            TextEntries.Clear();
            foreach (var e in _allEntries) TextEntries.Add(e);

            TotalEntries = _allEntries.Count;
            WithColors = _allEntries.Count(e => e.Text.Contains("%") && e.Text.Contains("c"));
            WithVariables = _allEntries.Count(e => e.Text.Contains("%s") || e.Text.Contains("%d"));

            Log.Success($"Extracted {_allEntries.Count} text entries");
        }
        catch (Exception ex) { Log.Error($"Extract failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private void ExportTexts()
    {
        if (_allEntries.Count == 0) { Log.Warning("No texts loaded"); return; }

        string? path = DialogService.SaveFile("Save Texts", "Text files|*.txt", "texts.txt");
        if (path is null) return;

        string offsetsPath = Path.ChangeExtension(path, ".offsets.txt");
        using var tw = new StreamWriter(path, false, System.Text.Encoding.UTF8);
        using var ow = new StreamWriter(offsetsPath, false, System.Text.Encoding.UTF8);

        foreach (var e in _allEntries)
        {
            tw.WriteLine(e.Text);
            ow.WriteLine($"{e.Offset}:{e.MaxLength}");
        }

        Log.Success($"Exported {_allEntries.Count} texts to {Path.GetFileName(path)}");
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
            Log.Success($"Imported: {replaced} replaced, {skipped} truncated");
        }
        catch (Exception ex) { Log.Error($"Import failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    partial void OnSelectedEntryChanged(TextEntry? value)
    {
        SelectedText = value?.Text ?? "";
    }

    partial void OnSearchFilterChanged(string value)
    {
        TextEntries.Clear();
        var filtered = string.IsNullOrEmpty(value)
            ? _allEntries
            : _allEntries.Where(e => e.Text.Contains(value, StringComparison.OrdinalIgnoreCase)).ToList();
        foreach (var e in filtered) TextEntries.Add(e);
    }
}
