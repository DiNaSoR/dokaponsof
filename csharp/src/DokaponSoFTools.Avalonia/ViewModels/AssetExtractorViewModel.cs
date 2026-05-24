using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Compression;
using DokaponSoFTools.Core.Imaging;
using DokaponSoFTools.Core.Tools;
using SkiaSharp;

namespace DokaponSoFTools.App.ViewModels;

public sealed record FileItem(string Name, string Path, string Extension, long Size, string SizeStr);

public sealed partial class AssetExtractorViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _outputPath = "";
    [ObservableProperty] private string _selectedFileType = "all";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private SKBitmap? _previewImage;
    [ObservableProperty] private string _previewInfo = "";
    [ObservableProperty] private FileItem? _selectedFile;
    [ObservableProperty] private int _selectedTabIndex;

    [ObservableProperty] private string _allTabHeader = "All";
    [ObservableProperty] private string _texTabHeader = "Textures (.tex)";
    [ObservableProperty] private string _spranmTabHeader = "Sprites (.spranm)";
    [ObservableProperty] private string _fntTabHeader = "Fonts (.fnt)";
    [ObservableProperty] private string _mpdTabHeader = "Maps (.mpd)";

    public ObservableCollection<FileItem> AllFiles { get; } = [];
    public ObservableCollection<FileItem> TexFiles { get; } = [];
    public ObservableCollection<FileItem> SpranmFiles { get; } = [];
    public ObservableCollection<FileItem> FntFiles { get; } = [];
    public ObservableCollection<FileItem> MpdFiles { get; } = [];

    private StatusLogService Log => StatusLogService.Instance;

    partial void OnSelectedTabIndexChanged(int value)
    {
        SelectedFileType = value switch
        {
            1 => "tex",
            2 => "spranm",
            3 => "fnt",
            4 => "mpd",
            _ => "all"
        };
    }

    [RelayCommand]
    private void ScanFiles()
    {
        if (string.IsNullOrEmpty(GamePath) || !Directory.Exists(GamePath)) return;

        AllFiles.Clear();
        TexFiles.Clear();
        SpranmFiles.Clear();
        FntFiles.Clear();
        MpdFiles.Clear();

        string[] exts = [".tex", ".spranm", ".fnt", ".mpd"];

        foreach (string ext in exts)
        {
            foreach (string file in Directory.EnumerateFiles(GamePath, $"*{ext}", SearchOption.AllDirectories))
            {
                var info = new FileInfo(file);
                string sizeStr = info.Length switch
                {
                    < 1024 => $"{info.Length} B",
                    < 1024 * 1024 => $"{info.Length / 1024.0:F1} KB",
                    _ => $"{info.Length / (1024.0 * 1024):F1} MB"
                };
                var item = new FileItem(info.Name, file, ext, info.Length, sizeStr);
                AllFiles.Add(item);

                switch (ext)
                {
                    case ".tex": TexFiles.Add(item); break;
                    case ".spranm": SpranmFiles.Add(item); break;
                    case ".fnt": FntFiles.Add(item); break;
                    case ".mpd": MpdFiles.Add(item); break;
                }
            }
        }

        AllTabHeader = $"All ({AllFiles.Count}, {FormatSize(AllFiles.Sum(f => f.Size))})";
        TexTabHeader = $"Textures ({TexFiles.Count}, {FormatSize(TexFiles.Sum(f => f.Size))})";
        SpranmTabHeader = $"Sprites ({SpranmFiles.Count}, {FormatSize(SpranmFiles.Sum(f => f.Size))})";
        FntTabHeader = $"Fonts ({FntFiles.Count}, {FormatSize(FntFiles.Sum(f => f.Size))})";
        MpdTabHeader = $"Maps ({MpdFiles.Count}, {FormatSize(MpdFiles.Sum(f => f.Size))})";

        Log.Info($"Found {AllFiles.Count} files ({TexFiles.Count} tex, {SpranmFiles.Count} spranm, {FntFiles.Count} fnt, {MpdFiles.Count} mpd)");
    }

    private static string FormatSize(long bytes) => bytes switch
    {
        < 1024 => $"{bytes} B",
        < 1024 * 1024 => $"{bytes / 1024.0:F1} KB",
        _ => $"{bytes / (1024.0 * 1024):F1} MB"
    };

    partial void OnSelectedFileChanged(FileItem? value)
    {
        if (value is null) return;
        PreviewInfo = $"Name: {value.Name}\nSize: {value.SizeStr}\nPath: {value.Path}";

        try
        {
            // .mpd: assemble the real tile map (not the raw atlas)
            if (value.Extension == ".mpd")
            {
                var doc = MapRenderer.LoadCellDocument(value.Path);
                var rendered = MapRenderer.RenderMapImage(doc, 0, 2048);
                if (rendered is not null) { PreviewImage = rendered; return; }

                var atlas = MapRenderer.BuildAtlasForDocument(doc, 0);
                if (atlas is not null) { PreviewImage = atlas; return; }
            }

            byte[] data = File.ReadAllBytes(value.Path);

            if (value.Extension == ".spranm")
            {
                var (_, foundPng, finalData) = AssetExtractor.ExtractSpranm(data);
                if (foundPng) { PreviewImage = DecodePng(finalData); return; }

                // Some .spranm are Cell-based — try rendering as a Cell document.
                try
                {
                    var doc = MapRenderer.LoadCellDocument(value.Path);
                    var rendered = MapRenderer.RenderMapImage(doc, 0, 2048)
                                   ?? MapRenderer.BuildAtlasForDocument(doc, 0);
                    if (rendered is not null)
                    {
                        PreviewImage = rendered;
                        PreviewInfo += $"\nRecords: {doc.Records.Count}";
                        return;
                    }
                }
                catch { /* not a Cell document */ }

                PreviewInfo += "\nNo embedded image (raw sprite data)";
                PreviewImage = null;
                return;
            }

            if (value.Extension == ".tex")
            {
                int pngIdx = FindPng(data);
                if (pngIdx >= 0) { PreviewImage = DecodePng(data, pngIdx); return; }

                // Try LZ77 decompression, then look for an embedded PNG.
                if (data.Length >= 4 && data[0] == 'L' && data[1] == 'Z' && data[2] == '7' && data[3] == '7')
                {
                    var dec = Lz77FlagByte.Decompress(data);
                    if (dec is not null)
                    {
                        int idx = FindPng(dec);
                        if (idx >= 0) { PreviewImage = DecodePng(dec, idx); return; }
                    }
                }
            }

            PreviewImage = null;
        }
        catch { PreviewImage = null; }
    }

    private static SKBitmap? DecodePng(byte[] data, int offset = 0, int count = -1)
    {
        if (count < 0) count = data.Length - offset;
        using var ms = new MemoryStream(data, offset, count);
        return SKBitmap.Decode(ms);
    }

    [RelayCommand]
    private async Task ExtractAllAsync()
    {
        if (string.IsNullOrEmpty(GamePath))
        {
            Log.Warning("Set the game path first (top bar)");
            return;
        }

        // Use the default output from Settings; otherwise prompt for a destination.
        if (string.IsNullOrEmpty(OutputPath))
        {
            OutputPath = SettingsService.Instance.DefaultOutputPath;
            if (string.IsNullOrEmpty(OutputPath))
            {
                string? dir = await StorageService.BrowseFolderAsync("Select Output Folder");
                if (string.IsNullOrEmpty(dir)) return;
                OutputPath = dir;
            }
        }

        IsBusy = true;
        Log.Info($"Extracting {SelectedFileType} files...");

        try
        {
            var progress = new Progress<string>(msg => Log.Info(msg));
            var (success, failed) = await Task.Run(() =>
                AssetExtractor.ProcessDirectory(GamePath, OutputPath, SelectedFileType, progress));
            Log.Success($"Extraction complete: {success} succeeded, {failed} failed");
        }
        catch (Exception ex)
        {
            Log.Error($"Extraction failed: {ex.Message}");
        }
        finally
        {
            IsBusy = false;
        }
    }

    private static int FindPng(byte[] data)
    {
        byte[] sig = [0x89, 0x50, 0x4E, 0x47];
        for (int i = 0; i <= data.Length - sig.Length; i++)
            if (data[i] == sig[0] && data[i + 1] == sig[1] && data[i + 2] == sig[2] && data[i + 3] == sig[3])
                return i;
        return -1;
    }
}
