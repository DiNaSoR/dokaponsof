using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.ViewModels;

public sealed record FileStat(string Extension, int Count, long TotalSize, string SizeStr);
public sealed record DirEntry(string Name, string Path, int FileCount, string TotalSize);

public sealed partial class GameScannerViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private string _scanReport = "";

    public ObservableCollection<FileStat> FileStats { get; } = [];
    public ObservableCollection<DirEntry> Directories { get; } = [];

    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanGame();
    }

    [RelayCommand]
    private async Task ScanGameAsync()
    {
        ScanGame();
        await Task.CompletedTask;
    }

    private void ScanGame()
    {
        if (string.IsNullOrEmpty(GamePath) || !Directory.Exists(GamePath)) return;

        IsBusy = true;
        FileStats.Clear();
        Directories.Clear();

        try
        {
            var allFiles = Directory.EnumerateFiles(GamePath, "*.*", SearchOption.AllDirectories).ToList();

            // Stats by extension
            var byExt = allFiles
                .GroupBy(f => Path.GetExtension(f).ToLowerInvariant())
                .Select(g =>
                {
                    long total = g.Sum(f => new FileInfo(f).Length);
                    return new FileStat(
                        string.IsNullOrEmpty(g.Key) ? "(none)" : g.Key,
                        g.Count(),
                        total,
                        FormatSize(total));
                })
                .OrderByDescending(s => s.TotalSize)
                .ToList();

            foreach (var s in byExt) FileStats.Add(s);

            // Top-level directories
            var topDirs = Directory.EnumerateDirectories(GamePath)
                .Select(d =>
                {
                    var files = Directory.EnumerateFiles(d, "*.*", SearchOption.AllDirectories).ToList();
                    long total = files.Sum(f => new FileInfo(f).Length);
                    return new DirEntry(Path.GetFileName(d), d, files.Count, FormatSize(total));
                })
                .OrderByDescending(d => d.FileCount)
                .ToList();

            foreach (var d in topDirs) Directories.Add(d);

            // Build report
            long totalSize = allFiles.Sum(f => new FileInfo(f).Length);
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"Game Directory: {GamePath}");
            sb.AppendLine($"Total Files: {allFiles.Count}");
            sb.AppendLine($"Total Size: {FormatSize(totalSize)}");
            sb.AppendLine();
            sb.AppendLine("By Extension:");
            foreach (var s in byExt)
                sb.AppendLine($"  {s.Extension,-12} {s.Count,6} files  {s.SizeStr,10}");
            sb.AppendLine();
            sb.AppendLine("Directories:");
            foreach (var d in topDirs)
                sb.AppendLine($"  {d.Name,-20} {d.FileCount,6} files  {d.TotalSize,10}");

            // Check key game files
            sb.AppendLine();
            sb.AppendLine("Key Files:");
            string[] keyFiles = [
                "DOKAPON! Sword of Fury.exe",
                "GameData/app/BGM.pck", "GameData/app/SE.pck",
                "GameData/app/Voice.pck", "GameData/app/Voice-en.pck",
                "GameData/app/Font/Quarter.fnt",
                "GameData/Windows/Save",
                "Setting.ini"
            ];
            foreach (string kf in keyFiles)
            {
                string full = Path.Combine(GamePath, kf.Replace('/', Path.DirectorySeparatorChar));
                bool exists = File.Exists(full) || Directory.Exists(full);
                sb.AppendLine($"  {(exists ? "[OK]" : "[--]")} {kf}");
            }

            ScanReport = sb.ToString();
            Log.Success($"Scan complete: {allFiles.Count} files, {FormatSize(totalSize)}");
        }
        catch (Exception ex) { Log.Error($"Scan failed: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    [RelayCommand]
    private void ExportReport()
    {
        if (string.IsNullOrEmpty(ScanReport)) return;
        string? path = DialogService.SaveFile("Save Scan Report", "Text files|*.txt", "game_scan.txt");
        if (path is not null)
        {
            File.WriteAllText(path, ScanReport);
            Log.Success($"Report saved: {path}");
        }
    }

    private static string FormatSize(long bytes) => bytes switch
    {
        < 1024 => $"{bytes} B",
        < 1024 * 1024 => $"{bytes / 1024.0:F1} KB",
        < 1024L * 1024 * 1024 => $"{bytes / (1024.0 * 1024):F1} MB",
        _ => $"{bytes / (1024.0 * 1024 * 1024):F2} GB"
    };
}
