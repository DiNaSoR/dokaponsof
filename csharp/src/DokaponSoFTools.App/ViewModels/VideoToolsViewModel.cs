using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Tools;

namespace DokaponSoFTools.App.ViewModels;

public sealed record GameVideoItem(string Name, string Path, string Resolution, string Duration, string Size);
public sealed record ReplacementItem(string TargetName, string SourcePath, string Status);

public sealed partial class VideoToolsViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private bool _ffmpegAvailable;
    [ObservableProperty] private string _ffmpegStatus = "Checking...";
    [ObservableProperty] private int _videoQuality = 8;
    [ObservableProperty] private int _audioQuality = 4;
    [ObservableProperty] private int _width = 1280;
    [ObservableProperty] private int _height = 720;
    [ObservableProperty] private string _previewVideoPath = "";

    public ObservableCollection<GameVideoItem> GameVideos { get; } = [];
    public ObservableCollection<ReplacementItem> Replacements { get; } = [];

    private readonly VideoConverter _converter = new();
    private StatusLogService Log => StatusLogService.Instance;

    public VideoToolsViewModel()
    {
        CheckFfmpeg();
    }

    private void CheckFfmpeg()
    {
        var (available, message) = ToolManager.Instance.VerifyTool("ffmpeg");
        FfmpegAvailable = available;
        FfmpegStatus = available ? $"FFmpeg: {message}" : "FFmpeg not found";
    }

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanGameVideos();
    }

    [RelayCommand]
    private async Task ScanGameVideosAsync()
    {
        ScanGameVideos();
        await Task.CompletedTask;
    }

    private async void ScanGameVideos()
    {
        if (string.IsNullOrEmpty(GamePath)) return;

        GameVideos.Clear();
        var videos = VideoConverter.FindGameVideos(GamePath);

        foreach (string path in videos)
        {
            var info = await _converter.GetVideoInfoAsync(path);
            GameVideos.Add(new GameVideoItem(
                System.IO.Path.GetFileName(path), path,
                info.Resolution, info.DurationStr, info.FileSizeStr
            ));
        }

        Log.Info($"Found {GameVideos.Count} game videos");
    }

    [RelayCommand]
    private void AddReplacement()
    {
        string? sourcePath = DialogService.OpenFile("Select Replacement Video",
            "Video files|*.mp4;*.avi;*.mkv;*.mov;*.webm|All files|*.*");
        if (sourcePath is null) return;

        // Find matching game video
        string fileName = System.IO.Path.GetFileNameWithoutExtension(sourcePath) + ".ogv";
        var target = GameVideos.FirstOrDefault(v => v.Name.Equals(fileName, StringComparison.OrdinalIgnoreCase));
        string targetName = target?.Name ?? fileName;

        Replacements.Add(new ReplacementItem(targetName, sourcePath, "Pending"));
        Log.Info($"Queued replacement: {System.IO.Path.GetFileName(sourcePath)} -> {targetName}");
    }

    [RelayCommand]
    private async Task ProcessReplacementsAsync()
    {
        if (Replacements.Count == 0) { Log.Warning("No replacements queued"); return; }
        if (!FfmpegAvailable) { Log.Error("FFmpeg not available"); return; }

        IsBusy = true;
        var settings = new ConversionSettings
        {
            Width = Width,
            Height = Height,
            VideoQuality = VideoQuality,
            AudioQuality = AudioQuality
        };

        int success = 0;
        for (int i = 0; i < Replacements.Count; i++)
        {
            var r = Replacements[i];
            Log.Info($"Converting: {System.IO.Path.GetFileName(r.SourcePath)}...");

            string outputPath = System.IO.Path.Combine(GamePath, "GameData", "app", r.TargetName);
            var progress = new Progress<double>(p =>
                StatusLogService.Instance.SetProgress(p * 100));

            bool ok = await _converter.ConvertToGameFormatAsync(r.SourcePath, outputPath, settings, progress);

            Replacements[i] = r with { Status = ok ? "Done" : "Failed" };
            if (ok) success++;

            StatusLogService.Instance.SetProgress(0);
        }

        IsBusy = false;
        Log.Success($"Processed {success}/{Replacements.Count} conversions");
    }
}
