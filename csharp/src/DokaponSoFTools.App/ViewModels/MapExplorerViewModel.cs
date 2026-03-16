using System.Collections.ObjectModel;
using System.IO;
using System.Windows.Media.Imaging;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;
using DokaponSoFTools.Core.Imaging;
using SkiaSharp;

namespace DokaponSoFTools.App.ViewModels;

public sealed record MapFileItem(string Name, string Path);

public sealed partial class MapExplorerViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private MapFileItem? _selectedMapFile;
    [ObservableProperty] private BitmapImage? _atlasImage;
    [ObservableProperty] private BitmapImage? _mapImage;
    [ObservableProperty] private int _selectedPalette;
    [ObservableProperty] private int _paletteCount;
    [ObservableProperty] private string _reportText = "";
    [ObservableProperty] private int _selectedTabIndex;

    public ObservableCollection<MapFileItem> MapFiles { get; } = [];
    public ObservableCollection<DecodedCellRecord> Records { get; } = [];
    public ObservableCollection<TexturePart> Parts { get; } = [];

    private LoadedCellDocument? _document;
    private StatusLogService Log => StatusLogService.Instance;

    partial void OnGamePathChanged(string value)
    {
        if (!string.IsNullOrEmpty(value) && Directory.Exists(value))
            ScanMapFiles();
    }

    [RelayCommand]
    private void ScanMapFiles()
    {
        if (string.IsNullOrEmpty(GamePath)) return;

        MapFiles.Clear();
        var files = MapRenderer.ListCellFiles(GamePath);
        foreach (string f in files)
            MapFiles.Add(new MapFileItem(System.IO.Path.GetFileName(f), f));

        Log.Info($"Found {MapFiles.Count} map files");
    }

    partial void OnSelectedMapFileChanged(MapFileItem? value)
    {
        if (value is not null) _ = LoadMapAsync(value.Path);
    }

    partial void OnSelectedPaletteChanged(int value)
    {
        if (_document is not null) RefreshImages();
    }

    [RelayCommand]
    private async Task LoadMapAsync(string path)
    {
        IsBusy = true;
        try
        {
            _document = await Task.Run(() => MapRenderer.LoadCellDocument(path));

            // Update records
            Records.Clear();
            foreach (var r in _document.DecodedRecords) Records.Add(r);

            // Update parts
            Parts.Clear();
            if (_document.Texture is not null)
                foreach (var p in _document.Texture.Parts) Parts.Add(p);

            PaletteCount = _document.Palettes.Count;
            SelectedPalette = 0;

            RefreshImages();
            GenerateReport();

            Log.Success($"Loaded: {System.IO.Path.GetFileName(path)} ({_document.Records.Count} records)");
        }
        catch (Exception ex) { Log.Error($"Failed to load map: {ex.Message}"); }
        finally { IsBusy = false; }
    }

    private void RefreshImages()
    {
        if (_document is null) return;

        try
        {
            // Atlas
            using var atlas = MapRenderer.BuildAtlasForDocument(_document, SelectedPalette);
            AtlasImage = atlas is not null ? SkBitmapToWpf(atlas) : null;

            // Map
            using var map = MapRenderer.RenderMapImage(_document, SelectedPalette, 2048);
            MapImage = map is not null ? SkBitmapToWpf(map) : null;
        }
        catch (Exception ex) { Log.Warning($"Render error: {ex.Message}"); }
    }

    private void GenerateReport()
    {
        if (_document is null) return;

        var sb = new System.Text.StringBuilder();
        sb.AppendLine($"File: {System.IO.Path.GetFileName(_document.SourcePath)}");
        sb.AppendLine($"Raw Size: {_document.RawData.Length:N0} bytes");
        sb.AppendLine($"Decompressed: {_document.DecompressedData.Length:N0} bytes");
        sb.AppendLine($"LZ77: {(_document.Lz77 is not null ? "Yes" : "No")}");
        sb.AppendLine($"Grid: {_document.Header.GridWidth}x{_document.Header.GridHeight}");
        sb.AppendLine($"Records: {_document.Records.Count}");
        sb.AppendLine($"Chunks: {string.Join(", ", _document.Chunks.Select(c => c.Name))}");
        sb.AppendLine($"Palettes: {_document.Palettes.Count}");

        if (_document.Texture is not null)
        {
            sb.AppendLine($"Texture: {_document.Texture.Header.Width}x{_document.Texture.Header.Height} ({_document.Texture.StorageKind})");
            sb.AppendLine($"Parts: {_document.Texture.Parts.Count}");
        }

        if (_document.CellMap is not null)
        {
            sb.AppendLine($"Map: {_document.CellMap.Width}x{_document.CellMap.Height}");
            sb.AppendLine($"Unique values: {_document.CellMap.Values.Distinct().Count()}");
        }

        ReportText = sb.ToString();
    }

    [RelayCommand]
    private void ExportReport()
    {
        if (string.IsNullOrEmpty(ReportText)) return;
        string? path = DialogService.SaveFile("Save Report", "Text files|*.txt;*.md", "map_report.txt");
        if (path is not null) File.WriteAllText(path, ReportText);
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
