using System.Collections.ObjectModel;
using System.IO;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;
using DokaponSoFTools.Core.Imaging;
using SkiaSharp;

namespace DokaponSoFTools.App.ViewModels;

public sealed record SpranmFileItem(string Name, string Path);

public sealed partial class AnimationViewerViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private SpranmFileItem? _selectedFile;
    [ObservableProperty] private BitmapImage? _currentFrame;
    [ObservableProperty] private int _currentSequenceIndex;
    [ObservableProperty] private int _sequenceCount;
    [ObservableProperty] private bool _isPlaying;
    [ObservableProperty] private string _animInfo = "";
    [ObservableProperty] private int _fps = 12;

    public ObservableCollection<SpranmFileItem> Files { get; } = [];

    private SpranmDocument? _document;
    private List<SKBitmap>? _renderedFrames;
    private DispatcherTimer? _timer;
    private int _playTick;
    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanFiles();
    }

    [RelayCommand]
    private void ScanFiles()
    {
        if (string.IsNullOrEmpty(GamePath)) return;

        Files.Clear();
        foreach (string file in Directory.EnumerateFiles(GamePath, "*.spranm", SearchOption.AllDirectories))
            Files.Add(new SpranmFileItem(System.IO.Path.GetFileName(file), file));

        Log.Info($"Found {Files.Count} animation files");
    }

    partial void OnSelectedFileChanged(SpranmFileItem? value)
    {
        if (value is not null) LoadAnimation(value.Path);
    }

    partial void OnFpsChanged(int value)
    {
        if (_timer is not null)
            _timer.Interval = TimeSpan.FromMilliseconds(1000.0 / Math.Max(1, value));
    }

    private void LoadAnimation(string path)
    {
        Stop();
        DisposeFrames();

        try
        {
            _document = SpranmDocument.Load(path);
            if (_document is null)
            {
                AnimInfo = "Failed to parse animation";
                CurrentFrame = null;
                return;
            }

            SequenceCount = _document.Sequences.Count;
            CurrentSequenceIndex = 0;

            _renderedFrames = SpranmRenderer.RenderAllFrames(_document);

            bool hasTexture = _document.TexturePng is not null && _document.TextureWidth > 0;
            bool isSelfContained = hasTexture && _document.Sequences.Count > 0 && _document.Parts.Count > 0;
            string fileType = isSelfContained ? "Self-contained" : "Runtime/Player asset";

            AnimInfo = $"[{fileType}] Seq: {_document.Sequences.Count} | Spr: {_document.Sprites.Count} | " +
                       $"Grp: {_document.Groups.Count} | Parts: {_document.Parts.Count}";

            if (hasTexture)
                AnimInfo += $" | Tex: {_document.TextureWidth}x{_document.TextureHeight}";

            if (_renderedFrames.Count > 0)
                ShowFrame(0);
            else
            {
                if (!isSelfContained)
                    AnimInfo += " | Cannot preview (runtime asset with PartsColor, no embedded PNG)";
                else
                    AnimInfo += " | No renderable frames";
                CurrentFrame = null;
            }

            Log.Success($"Loaded: {System.IO.Path.GetFileName(path)} ({_document.Sequences.Count} sequences)");
        }
        catch (Exception ex)
        {
            Log.Error($"Load failed: {ex.Message}");
            AnimInfo = $"Error: {ex.Message}";
            CurrentFrame = null;
        }
    }

    private void ShowFrame(int sequenceIndex)
    {
        if (_renderedFrames is null || sequenceIndex < 0 || sequenceIndex >= _renderedFrames.Count)
            return;

        CurrentSequenceIndex = sequenceIndex;
        CurrentFrame = SkBitmapToWpf(_renderedFrames[sequenceIndex]);
    }

    [RelayCommand]
    private void Play()
    {
        if (_renderedFrames is null || _renderedFrames.Count == 0) return;

        if (_timer is null)
        {
            _timer = new DispatcherTimer();
            _timer.Tick += OnTimerTick;
        }

        _timer.Interval = TimeSpan.FromMilliseconds(1000.0 / Math.Max(1, Fps));
        _playTick = 0;
        IsPlaying = true;
        _timer.Start();
    }

    [RelayCommand]
    private void Stop()
    {
        _timer?.Stop();
        IsPlaying = false;
    }

    [RelayCommand]
    private void PreviousFrame()
    {
        if (_renderedFrames is null || _renderedFrames.Count == 0) return;
        int idx = CurrentSequenceIndex - 1;
        if (idx < 0) idx = _renderedFrames.Count - 1;
        ShowFrame(idx);
    }

    [RelayCommand]
    private void NextFrame()
    {
        if (_renderedFrames is null || _renderedFrames.Count == 0) return;
        int idx = (CurrentSequenceIndex + 1) % _renderedFrames.Count;
        ShowFrame(idx);
    }

    private void OnTimerTick(object? sender, EventArgs e)
    {
        if (_document is null || _renderedFrames is null || _renderedFrames.Count == 0) return;

        int seqIdx = SpranmRenderer.GetSequenceIndexAtTick(_document, _playTick);
        ShowFrame(seqIdx);

        _playTick++;
        if (_playTick >= _document.TotalFrames)
            _playTick = 0; // Loop
    }

    private void DisposeFrames()
    {
        if (_renderedFrames is not null)
        {
            foreach (var bmp in _renderedFrames) bmp.Dispose();
            _renderedFrames = null;
        }
    }

    private static BitmapImage SkBitmapToWpf(SKBitmap bitmap)
    {
        using var image = SKImage.FromBitmap(bitmap);
        using var data = image.Encode(SKEncodedImageFormat.Png, 100);
        using var stream = data.AsStream();
        var bmp = new BitmapImage();
        bmp.BeginInit();
        bmp.CacheOption = BitmapCacheOption.OnLoad;
        bmp.StreamSource = stream;
        bmp.EndInit();
        bmp.Freeze();
        return bmp;
    }
}
