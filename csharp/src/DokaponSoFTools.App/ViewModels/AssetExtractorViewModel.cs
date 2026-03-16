using System.Collections.ObjectModel;
using System.IO;
using System.Windows.Media.Imaging;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Tools;

namespace DokaponSoFTools.App.ViewModels;

public sealed record FileItem(string Name, string Path, string Extension, long Size, string SizeStr);

public sealed partial class AssetExtractorViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private string _outputPath = "";
    [ObservableProperty] private string _selectedFileType = "all";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private BitmapImage? _previewImage;
    [ObservableProperty] private string _previewInfo = "";
    [ObservableProperty] private FileItem? _selectedFile;
    [ObservableProperty] private int _selectedTabIndex;

    public ObservableCollection<FileItem> AllFiles { get; } = [];
    public ObservableCollection<FileItem> TexFiles { get; } = [];
    public ObservableCollection<FileItem> SpranmFiles { get; } = [];
    public ObservableCollection<FileItem> FntFiles { get; } = [];
    public ObservableCollection<FileItem> MpdFiles { get; } = [];

    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanFiles();
    }

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
    private void BrowseInput()
    {
        string? path = DialogService.BrowseFolder("Select Input Directory");
        if (path is not null)
        {
            GamePath = path;
            ScanFiles();
        }
    }

    [RelayCommand]
    private void BrowseOutput()
    {
        string? path = DialogService.BrowseFolder("Select Output Directory");
        if (path is not null) OutputPath = path;
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

        Log.Info($"Found {AllFiles.Count} files ({TexFiles.Count} tex, {SpranmFiles.Count} spranm, {FntFiles.Count} fnt, {MpdFiles.Count} mpd)");
    }

    partial void OnSelectedFileChanged(FileItem? value)
    {
        if (value is null) return;
        PreviewInfo = $"Name: {value.Name}\nSize: {value.SizeStr}\nPath: {value.Path}";

        try
        {
            byte[] data = File.ReadAllBytes(value.Path);
            if (value.Extension is ".tex" or ".mpd" or ".spranm")
            {
                var (success, foundPng, finalData) = value.Extension == ".spranm"
                    ? AssetExtractor.ExtractSpranm(data)
                    : (false, false, Array.Empty<byte>());

                if (value.Extension != ".spranm")
                {
                    int pngIdx = FindPng(data);
                    if (pngIdx >= 0)
                    {
                        using var ms = new MemoryStream(data, pngIdx, data.Length - pngIdx);
                        var bmp = new BitmapImage();
                        bmp.BeginInit();
                        bmp.CacheOption = BitmapCacheOption.OnLoad;
                        bmp.StreamSource = ms;
                        bmp.EndInit();
                        bmp.Freeze();
                        PreviewImage = bmp;
                        return;
                    }
                }
                else if (foundPng)
                {
                    using var ms = new MemoryStream(finalData);
                    var bmp = new BitmapImage();
                    bmp.BeginInit();
                    bmp.CacheOption = BitmapCacheOption.OnLoad;
                    bmp.StreamSource = ms;
                    bmp.EndInit();
                    bmp.Freeze();
                    PreviewImage = bmp;
                    return;
                }
            }
            PreviewImage = null;
        }
        catch { PreviewImage = null; }
    }

    [RelayCommand]
    private async Task ExtractAllAsync()
    {
        if (string.IsNullOrEmpty(GamePath) || string.IsNullOrEmpty(OutputPath))
        {
            Log.Warning("Please set both input and output directories");
            return;
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
