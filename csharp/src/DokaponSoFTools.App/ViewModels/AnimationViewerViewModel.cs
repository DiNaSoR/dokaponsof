using System.Collections.ObjectModel;
using System.IO;
using System.Windows;
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
    [ObservableProperty] private string _searchFilter = "";

    public ObservableCollection<SpranmFileItem> Files { get; } = [];

    private SpranmDocument? _document;
    private List<SKBitmap>? _renderedFrames;
    private List<SpranmFileItem> _allFiles = [];
    private DispatcherTimer? _timer;
    private int _playTick;
    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanFiles();
    }

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
                    AnimInfo += " | Cannot preview (runtime asset, no embedded PNG)";
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
    private void ExportGif()
    {
        if (_renderedFrames is null || _renderedFrames.Count == 0)
        {
            Log.Warning("No frames to export");
            return;
        }

        string? path = DialogService.SaveFile("Export Animation", "GIF|*.gif|PNG Sequence|*.png",
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
                // Export as PNG sequence
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

    private void ExportAsGif(string path)
    {
        if (_renderedFrames is null || _document is null) return;

        // Find max canvas size
        int maxW = 0, maxH = 0;
        foreach (var bmp in _renderedFrames)
        {
            if (bmp.Width > maxW) maxW = bmp.Width;
            if (bmp.Height > maxH) maxH = bmp.Height;
        }

        int delay = Math.Max(1, 100 / Math.Max(1, Fps)); // GIF delay in centiseconds

        using var fs = File.Create(path);
        // GIF89a header
        fs.Write("GIF89a"u8);
        WriteLE16(fs, maxW);
        WriteLE16(fs, maxH);
        fs.WriteByte(0x70); // GCT flag=0, color res=7, no sort, no GCT
        fs.WriteByte(0);    // bg color
        fs.WriteByte(0);    // pixel aspect

        // Netscape loop extension
        fs.Write(new byte[] { 0x21, 0xFF, 0x0B });
        fs.Write("NETSCAPE2.0"u8);
        fs.Write(new byte[] { 0x03, 0x01, 0x00, 0x00, 0x00 }); // loop forever

        for (int i = 0; i < _renderedFrames.Count; i++)
        {
            var bmp = _renderedFrames[i];
            int frameDuration = i < _document.Sequences.Count ? Math.Max(1, _document.Sequences[i].Duration * delay) : delay;

            // Encode frame as PNG, then convert to indexed color for GIF
            using var img = SKImage.FromBitmap(bmp);
            using var pngData = img.Encode(SKEncodedImageFormat.Png, 100);
            byte[] pngBytes = pngData.ToArray();

            // Use a simpler approach: write each frame as a full-image GIF frame
            // Convert RGBA to indexed 256-color palette using median cut
            var (palette, indices) = QuantizeFrame(bmp);

            // Graphic Control Extension
            fs.Write(new byte[] { 0x21, 0xF9, 0x04 });
            fs.WriteByte(0x09); // dispose=restore to bg, transparent=1
            WriteLE16(fs, frameDuration);
            fs.WriteByte(0); // transparent color index (0)
            fs.WriteByte(0);

            // Image descriptor
            fs.WriteByte(0x2C);
            WriteLE16(fs, 0); // left
            WriteLE16(fs, 0); // top
            WriteLE16(fs, bmp.Width);
            WriteLE16(fs, bmp.Height);
            fs.WriteByte(0x87); // local color table, 256 entries

            // Local color table (256 * 3 = 768 bytes)
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

            // LZW compressed image data
            WriteLzwData(fs, indices, 8);
        }

        fs.WriteByte(0x3B); // GIF trailer
        Log.Success($"Exported GIF: {System.IO.Path.GetFileName(path)} ({_renderedFrames.Count} frames)");
    }

    private static (SKColor[] palette, byte[] indices) QuantizeFrame(SKBitmap bmp)
    {
        // Simple quantization: collect unique colors, use first 255 + transparent
        var colorMap = new Dictionary<uint, byte>();
        var palette = new List<SKColor> { new(0, 0, 0, 0) }; // index 0 = transparent
        var indices = new byte[bmp.Width * bmp.Height];

        for (int y = 0; y < bmp.Height; y++)
        for (int x = 0; x < bmp.Width; x++)
        {
            var c = bmp.GetPixel(x, y);
            int idx = y * bmp.Width + x;

            if (c.Alpha < 128)
            {
                indices[idx] = 0; // transparent
                continue;
            }

            // Reduce to 5-bit per channel for better palette fit
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
                    // Find nearest existing color
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

        // Simple LZW encoder
        int clearCode = 1 << minCodeSize;
        int eoiCode = clearCode + 1;
        int nextCode = eoiCode + 1;
        int codeSize = minCodeSize + 1;

        var table = new Dictionary<string, int>();
        var output = new List<int>();

        output.Add(clearCode);

        // Init table
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

        // Pack codes into bytes
        var bytes = new List<byte>();
        int bitBuffer = 0, bitsInBuffer = 0;
        int currentCodeSize = minCodeSize + 1;
        int resetNextCode = eoiCode + 1;

        // Re-init for packing
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
                if (nextCode >= 4096)
                {
                    // Will be followed by clear code
                }
            }
        }

        if (bitsInBuffer > 0)
            bytes.Add((byte)(bitBuffer & 0xFF));

        // Write sub-blocks (max 255 bytes each)
        int pos = 0;
        while (pos < bytes.Count)
        {
            int blockSize = Math.Min(255, bytes.Count - pos);
            fs.WriteByte((byte)blockSize);
            for (int i = 0; i < blockSize; i++)
                fs.WriteByte(bytes[pos + i]);
            pos += blockSize;
        }
        fs.WriteByte(0); // block terminator
    }

    private static void WriteLE16(Stream s, int value)
    {
        s.WriteByte((byte)(value & 0xFF));
        s.WriteByte((byte)((value >> 8) & 0xFF));
    }

    [RelayCommand]
    private void ExportAtlas()
    {
        if (_document?.TexturePng is null)
        {
            Log.Warning("No texture atlas available");
            return;
        }

        string? path = DialogService.SaveFile("Export Atlas", "PNG|*.png",
            System.IO.Path.GetFileNameWithoutExtension(_document.SourcePath) + "_atlas.png");
        if (path is null) return;

        File.WriteAllBytes(path, _document.TexturePng);
        Log.Success($"Atlas exported: {System.IO.Path.GetFileName(path)}");
    }

    [RelayCommand]
    private void CopyFrameToClipboard()
    {
        if (CurrentFrame is null) return;
        Clipboard.SetImage(CurrentFrame);
        Log.Info("Frame copied to clipboard");
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
