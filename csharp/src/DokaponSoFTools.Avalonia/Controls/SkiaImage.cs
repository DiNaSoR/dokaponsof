using System;
using Avalonia;
using Avalonia.Controls;
using Avalonia.Input;
using Avalonia.Media;
using Avalonia.Rendering.SceneGraph;
using Avalonia.Skia;
using SkiaSharp;

namespace DokaponSoFTools.App.Controls;

/// <summary>
/// Renders an <see cref="SKBitmap"/> directly through Skia (no PNG round-trip),
/// with a transparency checkerboard, pixel-perfect (NearestNeighbor) scaling,
/// and interactive zoom (wheel) + pan (drag). Used for every asset preview.
///
/// Displayed bitmaps are intentionally NOT disposed here: the draw operation
/// runs on the render thread, so the owning ViewModel must let the GC reclaim
/// the bitmap (which keeps it alive while an op references it) rather than
/// disposing it from the UI thread.
/// </summary>
public class SkiaImage : Control
{
    public static readonly StyledProperty<SKBitmap?> SourceProperty =
        AvaloniaProperty.Register<SkiaImage, SKBitmap?>(nameof(Source));

    public static readonly StyledProperty<bool> ShowCheckerboardProperty =
        AvaloniaProperty.Register<SkiaImage, bool>(nameof(ShowCheckerboard), true);

    public static readonly StyledProperty<bool> AllowZoomProperty =
        AvaloniaProperty.Register<SkiaImage, bool>(nameof(AllowZoom), true);

    public static readonly StyledProperty<bool> ResetViewOnSourceChangeProperty =
        AvaloniaProperty.Register<SkiaImage, bool>(nameof(ResetViewOnSourceChange), true);

    public SKBitmap? Source
    {
        get => GetValue(SourceProperty);
        set => SetValue(SourceProperty, value);
    }

    public bool ShowCheckerboard
    {
        get => GetValue(ShowCheckerboardProperty);
        set => SetValue(ShowCheckerboardProperty, value);
    }

    public bool AllowZoom
    {
        get => GetValue(AllowZoomProperty);
        set => SetValue(AllowZoomProperty, value);
    }

    /// <summary>When false, changing <see cref="Source"/> keeps the current
    /// zoom/pan (used for animation playback so frames don't reset the view).</summary>
    public bool ResetViewOnSourceChange
    {
        get => GetValue(ResetViewOnSourceChangeProperty);
        set => SetValue(ResetViewOnSourceChangeProperty, value);
    }

    private double _zoom = 1.0;       // user zoom on top of the fit-to-bounds scale
    private Point _pan;               // user pan offset, in control pixels
    private Point? _lastDrag;

    static SkiaImage()
    {
        AffectsRender<SkiaImage>(SourceProperty, ShowCheckerboardProperty);
    }

    protected override void OnPropertyChanged(AvaloniaPropertyChangedEventArgs change)
    {
        base.OnPropertyChanged(change);
        if (change.Property == SourceProperty)
        {
            if (ResetViewOnSourceChange) ResetView();
            else InvalidateVisual();
        }
    }

    public void ResetView()
    {
        _zoom = 1.0;
        _pan = default;
        InvalidateVisual();
    }

    protected override void OnPointerWheelChanged(PointerWheelEventArgs e)
    {
        base.OnPointerWheelChanged(e);
        if (!AllowZoom || Source is null) return;

        double factor = e.Delta.Y > 0 ? 1.1 : 1.0 / 1.1;
        _zoom = Math.Clamp(_zoom * factor, 0.05, 64.0);
        InvalidateVisual();
        e.Handled = true;
    }

    protected override void OnPointerPressed(PointerPressedEventArgs e)
    {
        base.OnPointerPressed(e);
        if (Source is null) return;
        _lastDrag = e.GetPosition(this);
        e.Pointer.Capture(this);
    }

    protected override void OnPointerMoved(PointerEventArgs e)
    {
        base.OnPointerMoved(e);
        if (_lastDrag is { } last && Equals(e.Pointer.Captured, this))
        {
            var pos = e.GetPosition(this);
            _pan += pos - last;
            _lastDrag = pos;
            InvalidateVisual();
        }
    }

    protected override void OnPointerReleased(PointerReleasedEventArgs e)
    {
        base.OnPointerReleased(e);
        _lastDrag = null;
        e.Pointer.Capture(null);
    }

    public override void Render(DrawingContext context)
    {
        base.Render(context);
        context.Custom(new DrawOp(new Rect(Bounds.Size), Source, ShowCheckerboard, _zoom, _pan));
    }

    private sealed class DrawOp(Rect bounds, SKBitmap? bmp, bool checker, double zoom, Point pan)
        : ICustomDrawOperation
    {
        public Rect Bounds => bounds;
        public bool HitTest(Point p) => bounds.Contains(p);
        public bool Equals(ICustomDrawOperation? other) => false;
        public void Dispose() { }

        public void Render(ImmediateDrawingContext context)
        {
            if (context.TryGetFeature(typeof(ISkiaSharpApiLeaseFeature)) is not ISkiaSharpApiLeaseFeature feature)
                return;

            using var lease = feature.Lease();
            var canvas = lease.SkCanvas;

            var area = SKRect.Create((float)bounds.X, (float)bounds.Y, (float)bounds.Width, (float)bounds.Height);
            canvas.Save();
            canvas.ClipRect(area);

            if (checker) DrawCheckerboard(canvas, area);

            if (bmp is not null && bmp.Width > 0 && bmp.Height > 0)
            {
                double fit = Math.Min(bounds.Width / bmp.Width, bounds.Height / bmp.Height);
                if (fit <= 0 || double.IsInfinity(fit) || double.IsNaN(fit)) fit = 1;
                double scale = fit * zoom;
                double w = bmp.Width * scale;
                double h = bmp.Height * scale;
                double x = (bounds.Width - w) / 2 + pan.X;
                double y = (bounds.Height - h) / 2 + pan.Y;

                using var paint = new SKPaint { FilterQuality = SKFilterQuality.None, IsAntialias = false };
                canvas.DrawBitmap(bmp, SKRect.Create((float)x, (float)y, (float)w, (float)h), paint);
            }

            canvas.Restore();
        }

        private static void DrawCheckerboard(SKCanvas canvas, SKRect area)
        {
            const int cell = 12;
            using var dark = new SKPaint { Color = new SKColor(0x14, 0x14, 0x1C) };
            using var light = new SKPaint { Color = new SKColor(0x22, 0x22, 0x2E) };
            canvas.DrawRect(area, dark);
            for (int y = (int)area.Top; y < area.Bottom; y += cell)
            {
                for (int x = (int)area.Left; x < area.Right; x += cell)
                {
                    int cx = (x - (int)area.Left) / cell;
                    int cy = (y - (int)area.Top) / cell;
                    if (((cx + cy) & 1) == 0)
                        canvas.DrawRect(SKRect.Create(x, y, cell, cell), light);
                }
            }
        }
    }
}
