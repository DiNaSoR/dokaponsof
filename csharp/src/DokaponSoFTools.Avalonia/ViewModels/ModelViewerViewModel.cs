using System.Collections.ObjectModel;
using System.IO;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.Core.Formats;
using DokaponSoFTools.Core.Imaging;
using SkiaSharp;

namespace DokaponSoFTools.App.ViewModels;

public sealed record ModelFileItem(string Name, string Path);

public sealed partial class ModelViewerViewModel : ObservableObject, IGamePathAware
{
    [ObservableProperty] private string _gamePath = "";
    [ObservableProperty] private bool _isBusy;
    [ObservableProperty] private ModelFileItem? _selectedFile;
    [ObservableProperty] private SKBitmap? _currentImage;
    [ObservableProperty] private string _info = "";
    [ObservableProperty] private string _searchFilter = "";
    [ObservableProperty] private double _yaw = 30;
    [ObservableProperty] private double _pitch = 20;
    [ObservableProperty] private double _zoom = 1.0;

    public ObservableCollection<ModelFileItem> Files { get; } = [];

    private MdlGeometry? _geo;
    private List<ModelFileItem> _allFiles = [];
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

        _allFiles = Directory.EnumerateFiles(GamePath, "*.mdl", SearchOption.AllDirectories)
            .Select(f => new ModelFileItem(System.IO.Path.GetFileName(f), f))
            .OrderBy(f => f.Name)
            .ToList();

        Files.Clear();
        foreach (var f in _allFiles) Files.Add(f);
        Log.Info($"Found {_allFiles.Count} model files");
    }

    partial void OnSelectedFileChanged(ModelFileItem? value)
    {
        if (value is not null) _ = LoadModelAsync(value.Path);
    }

    partial void OnYawChanged(double value) => RenderModel();
    partial void OnPitchChanged(double value) => RenderModel();
    partial void OnZoomChanged(double value) => RenderModel();

    private async Task LoadModelAsync(string path)
    {
        IsBusy = true;
        try
        {
            _geo = await Task.Run(() =>
            {
                byte[] raw = File.ReadAllBytes(path);
                byte[] data = MdlModel.DecompressMdl(raw) ?? raw;
                return MdlModel.Parse(data);
            });

            if (_geo is null)
            {
                Info = "Could not parse model geometry";
                CurrentImage = null;
                return;
            }

            Info = $"Vertices: {_geo.VertexCount}  •  Faces: {_geo.FaceCount}";
            RenderModel();
            Log.Success($"Loaded model: {System.IO.Path.GetFileName(path)}");
        }
        catch (Exception ex)
        {
            Log.Error($"Model load failed: {ex.Message}");
            Info = $"Error: {ex.Message}";
            CurrentImage = null;
        }
        finally { IsBusy = false; }
    }

    private void RenderModel()
    {
        if (_geo is null) return;
        CurrentImage = MdlRenderer.Render(_geo, 640, 640, (float)Yaw, (float)Pitch, (float)Zoom);
    }
}
