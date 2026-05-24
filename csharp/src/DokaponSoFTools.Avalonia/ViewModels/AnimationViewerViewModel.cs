using System.Collections.ObjectModel;
using System.IO;
using Avalonia.Threading;
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
    [ObservableProperty] private SKBitmap? _currentFrame;
    [ObservableProperty][NotifyPropertyChangedFor(nameof(FrameLabel))] private int _currentSequenceIndex;
    [ObservableProperty][NotifyPropertyChangedFor(nameof(MaxFrameIndex))][NotifyPropertyChangedFor(nameof(FrameLabel))] private int _sequenceCount;
    [ObservableProperty] private bool _isPlaying;
    [ObservableProperty] private string _animInfo = "";
    [ObservableProperty] private int _fps = 12;
    [ObservableProperty] private string _searchFilter = "";

    public int MaxFrameIndex => Math.Max(0, SequenceCount - 1);
    public string FrameLabel => SequenceCount > 0 ? $"Frame {CurrentSequenceIndex + 1} / {SequenceCount}" : "—";

    public ObservableCollection<SpranmFileItem> Files { get; } = [];

    private SpranmDocument? _document;
    private List<SKBitmap>? _renderedFrames;
    private List<SpranmFileItem> _allFiles = [];
    private DispatcherTimer? _timer;
    private int _playTick;
    private StatusLogService Log => StatusLogService.Instance;

    partial void OnSearchFilterChanged(string value)
    {
        Files.Clear();
        var filtered = string.IsNullOrEmpty(value)
            ? _allFiles
            : _allFiles.Where(f => f.Name.Contains(value, StringComparison.OrdinalIgnoreCase)).ToList();
        foreach (var f in filtered) Files.Add(f);
    }

    [RelayCommand]
    private void ScanFiles()
    {
        if (string.IsNullOrEmpty(GamePath)) return;

        _allFiles = Directory.EnumerateFiles(GamePath, "*.spranm", SearchOption.AllDirectories)
            .Select(f => new SpranmFileItem(System.IO.Path.GetFileName(f), f))
            .OrderBy(f => f.Name)
            .ToList();

        Files.Clear();
        foreach (var f in _allFiles) Files.Add(f);

        Log.Info($"Found {_allFiles.Count} animation files");
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

    // Rendering the current index (kept separate from ShowFrame to avoid
    // recursion when the timeline slider drives CurrentSequenceIndex).
    partial void OnCurrentSequenceIndexChanged(int value)
    {
        if (_renderedFrames is null || value < 0 || value >= _renderedFrames.Count) return;
        CurrentFrame = _renderedFrames[value];
    }

    private void LoadAnimation(string path)
    {
        Stop();
        // Drop the previous frames; do NOT dispose — the render thread may still
        // reference the bitmap. The GC reclaims native memory safely.
        _renderedFrames = null;
        CurrentFrame = null;

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
            _renderedFrames = SpranmRenderer.RenderAllFrames(_document);

            bool hasTexture = _document.TexturePng is not null && _document.TextureWidth > 0;
            bool isSelfContained = hasTexture && _document.Sequences.Count > 0 && _document.Parts.Count > 0;
            string fileType = isSelfContained ? "Self-contained" : "Runtime/Player asset";

            AnimInfo = $"[{fileType}] Seq: {_document.Sequences.Count} | Spr: {_document.Sprites.Count} | " +
                       $"Grp: {_document.Groups.Count} | Parts: {_document.Parts.Count}";

            if (hasTexture)
                AnimInfo += $" | Tex: {_document.TextureWidth}x{_document.TextureHeight}";

            if (_renderedFrames.Count > 0)
            {
                CurrentSequenceIndex = 0;
                OnCurrentSequenceIndexChanged(0); // ensure first frame renders even if index was already 0
            }
            else
            {
                AnimInfo += isSelfContained ? " | No renderable frames" : " | Cannot preview (runtime asset, no embedded PNG)";
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
        CurrentSequenceIndex = sequenceIndex; // triggers OnCurrentSequenceIndexChanged -> render
    }

    [RelayCommand]
    private void TogglePlayStop()
    {
        if (IsPlaying) Stop(); else Play();
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

    [RelayCommand]
    private async Task ExportGifAsync()
    {
        if (_renderedFrames is null || _renderedFrames.Count == 0)
        {
            Log.Warning("No frames to export");
            return;
        }

        string? path = await StorageService.SaveFileAsync("Export Animation", "GIF|*.gif|PNG Sequence|*.png",
            System.IO.Path.GetFileNameWithoutExtension(_document?.SourcePath ?? "animation") + ".gif");
        if (path is null) return;

        try
        {
            if (path.EndsWith(".gif", StringComparison.OrdinalIgnoreCase))
            {
                ExportAsGif(path);
            }
            else
            {
                string dir = System.IO.Path.GetDirectoryName(path)!;
                string baseName = System.IO.Path.GetFileNameWithoutExtension(path);
                for (int i = 0; i < _renderedFrames.Count; i++)
                {
                    string framePath = System.IO.Path.Combine(dir, $"{baseName}_{i:D4}.png");
                    using var img = SKImage.FromBitmap(_renderedFrames[i]);
                    using var data = img.Encode(SKEncodedImageFormat.Png, 100);
                    using var fs = File.Create(framePath);
                    data.SaveTo(fs);
                }
                Log.Success($"Exported {_renderedFrames.Count} frames to {dir}");
            }
        }
        catch (Exception ex) { Log.Error($"Export failed: {ex.Message}"); }
    }

    [RelayCommand]
    private async Task ExportAtlasAsync()
    {
        if (_document?.TexturePng is null)
        {
            Log.Warning("No texture atlas available");
            return;
        }

        string? path = await StorageService.SaveFileAsync("Export Atlas", "PNG|*.png",
            System.IO.Path.GetFileNameWithoutExtension(_document.SourcePath) + "_atlas.png");
        if (path is null) return;

        await File.WriteAllBytesAsync(path, _document.TexturePng);
        Log.Success($"Atlas exported: {System.IO.Path.GetFileName(path)}");
    }

    [RelayCommand]
    private async Task SaveFrameAsync()
    {
        if (CurrentFrame is null) { Log.Warning("No frame to save"); return; }

        string? path = await StorageService.SaveFileAsync("Save Frame", "PNG|*.png",
            System.IO.Path.GetFileNameWithoutExtension(_document?.SourcePath ?? "frame") + $"_{CurrentSequenceIndex:D3}.png");
        if (path is null) return;

        using var img = SKImage.FromBitmap(CurrentFrame);
        using var data = img.Encode(SKEncodedImageFormat.Png, 100);
        using var fs = File.Create(path);
        data.SaveTo(fs);
        Log.Success($"Frame saved: {System.IO.Path.GetFileName(path)}");
    }

    private void OnTimerTick(object? sender, EventArgs e)
    {
        if (_document is null || _renderedFrames is null || _renderedFrames.Count == 0) return;

        int seqIdx = SpranmRenderer.GetSequenceIndexAtTick(_document, _playTick);
        ShowFrame(seqIdx);

        _playTick++;
        if (_playTick >= _document.TotalFrames)
            _playTick = 0;
    }

    // ===================== GIF encoder (verbatim from the WPF port) =====================

    private void ExportAsGif(string path)
    {
        if (_renderedFrames is null || _document is null) return;

        int maxW = 0, maxH = 0;
        foreach (var bmp in _renderedFrames)
        {
            if (bmp.Width > maxW) maxW = bmp.Width;
            if (bmp.Height > maxH) maxH = bmp.Height;
        }

        int delay = Math.Max(1, 100 / Math.Max(1, Fps));

        using var fs = File.Create(path);
        fs.Write("GIF89a"u8);
        WriteLE16(fs, maxW);
        WriteLE16(fs, maxH);
        fs.WriteByte(0x70);
        fs.WriteByte(0);
        fs.WriteByte(0);

        fs.Write(new byte[] { 0x21, 0xFF, 0x0B });
        fs.Write("NETSCAPE2.0"u8);
        fs.Write(new byte[] { 0x03, 0x01, 0x00, 0x00, 0x00 });

        for (int i = 0; i < _renderedFrames.Count; i++)
        {
            var bmp = _renderedFrames[i];
            int frameDuration = i < _document.Sequences.Count ? Math.Max(1, _document.Sequences[i].Duration * delay) : delay;

            var (palette, indices) = QuantizeFrame(bmp);

            fs.Write(new byte[] { 0x21, 0xF9, 0x04 });
            fs.WriteByte(0x09);
            WriteLE16(fs, frameDuration);
            fs.WriteByte(0);
            fs.WriteByte(0);

            fs.WriteByte(0x2C);
            WriteLE16(fs, 0);
            WriteLE16(fs, 0);
            WriteLE16(fs, bmp.Width);
            WriteLE16(fs, bmp.Height);
            fs.WriteByte(0x87);

            for (int c = 0; c < 256; c++)
            {
                if (c < palette.Length)
                {
                    fs.WriteByte(palette[c].Red);
                    fs.WriteByte(palette[c].Green);
                    fs.WriteByte(palette[c].Blue);
                }
                else
                {
                    fs.Write(new byte[] { 0, 0, 0 });
                }
            }

            WriteLzwData(fs, indices, 8);
        }

        fs.WriteByte(0x3B);
        Log.Success($"Exported GIF: {System.IO.Path.GetFileName(path)} ({_renderedFrames.Count} frames)");
    }

    private static (SKColor[] palette, byte[] indices) QuantizeFrame(SKBitmap bmp)
    {
        var colorMap = new Dictionary<uint, byte>();
        var palette = new List<SKColor> { new(0, 0, 0, 0) };
        var indices = new byte[bmp.Width * bmp.Height];

        for (int y = 0; y < bmp.Height; y++)
        for (int x = 0; x < bmp.Width; x++)
        {
            var c = bmp.GetPixel(x, y);
            int idx = y * bmp.Width + x;

            if (c.Alpha < 128)
            {
                indices[idx] = 0;
                continue;
            }

            uint key = ((uint)(c.Red >> 3) << 10) | ((uint)(c.Green >> 3) << 5) | (uint)(c.Blue >> 3);

            if (!colorMap.TryGetValue(key, out byte ci))
            {
                if (palette.Count < 256)
                {
                    ci = (byte)palette.Count;
                    palette.Add(c);
                    colorMap[key] = ci;
                }
                else
                {
                    ci = FindNearest(palette, c);
                }
            }
            indices[idx] = ci;
        }

        return (palette.ToArray(), indices);
    }

    private static byte FindNearest(List<SKColor> palette, SKColor c)
    {
        int bestDist = int.MaxValue;
        byte best = 1;
        for (int i = 1; i < palette.Count; i++)
        {
            var p = palette[i];
            int dr = c.Red - p.Red, dg = c.Green - p.Green, db = c.Blue - p.Blue;
            int dist = dr * dr + dg * dg + db * db;
            if (dist < bestDist) { bestDist = dist; best = (byte)i; }
        }
        return best;
    }

    private static void WriteLzwData(Stream fs, byte[] indices, int minCodeSize)
    {
        fs.WriteByte((byte)minCodeSize);

        int clearCode = 1 << minCodeSize;
        int eoiCode = clearCode + 1;
        int nextCode = eoiCode + 1;
        int codeSize = minCodeSize + 1;

        var table = new Dictionary<string, int>();
        var output = new List<int> { clearCode };

        for (int i = 0; i < clearCode; i++)
            table[((char)i).ToString()] = i;

        string w = "";
        foreach (byte b in indices)
        {
            string wc = w + (char)b;
            if (table.ContainsKey(wc))
            {
                w = wc;
            }
            else
            {
                output.Add(table[w]);
                if (nextCode < 4096)
                {
                    table[wc] = nextCode++;
                    if (nextCode > (1 << codeSize) && codeSize < 12)
                        codeSize++;
                }
                else
                {
                    output.Add(clearCode);
                    table.Clear();
                    for (int i = 0; i < clearCode; i++)
                        table[((char)i).ToString()] = i;
                    nextCode = eoiCode + 1;
                    codeSize = minCodeSize + 1;
                }
                w = ((char)b).ToString();
            }
        }

        if (w.Length > 0) output.Add(table[w]);
        output.Add(eoiCode);

        var bytes = new List<byte>();
        int bitBuffer = 0, bitsInBuffer = 0;
        int currentCodeSize = minCodeSize + 1;

        nextCode = eoiCode + 1;
        currentCodeSize = minCodeSize + 1;

        foreach (int code in output)
        {
            if (code == clearCode)
            {
                nextCode = eoiCode + 1;
                currentCodeSize = minCodeSize + 1;
            }

            bitBuffer |= code << bitsInBuffer;
            bitsInBuffer += currentCodeSize;

            while (bitsInBuffer >= 8)
            {
                bytes.Add((byte)(bitBuffer & 0xFF));
                bitBuffer >>= 8;
                bitsInBuffer -= 8;
            }

            if (code != clearCode && code != eoiCode)
            {
                nextCode++;
                if (nextCode > (1 << currentCodeSize) && currentCodeSize < 12)
                    currentCodeSize++;
            }
        }

        if (bitsInBuffer > 0)
            bytes.Add((byte)(bitBuffer & 0xFF));

        int pos = 0;
        while (pos < bytes.Count)
        {
            int blockSize = Math.Min(255, bytes.Count - pos);
            fs.WriteByte((byte)blockSize);
            for (int i = 0; i < blockSize; i++)
                fs.WriteByte(bytes[pos + i]);
            pos += blockSize;
        }
        fs.WriteByte(0);
    }

    private static void WriteLE16(Stream s, int value)
    {
        s.WriteByte((byte)(value & 0xFF));
        s.WriteByte((byte)((value >> 8) & 0xFF));
    }
}
