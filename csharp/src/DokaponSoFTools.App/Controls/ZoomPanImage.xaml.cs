using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media.Imaging;

namespace DokaponSoFTools.App.Controls;

public partial class ZoomPanImage : UserControl
{
    public static readonly DependencyProperty ImageSourceProperty =
        DependencyProperty.Register(nameof(ImageSource), typeof(BitmapImage), typeof(ZoomPanImage),
            new PropertyMetadata(null));

    public BitmapImage? ImageSource
    {
        get => (BitmapImage?)GetValue(ImageSourceProperty);
        set => SetValue(ImageSourceProperty, value);
    }

    private Point _lastMousePos;
    private bool _isPanning;

    public ZoomPanImage()
    {
        InitializeComponent();
    }

    private void OnMouseWheel(object sender, MouseWheelEventArgs e)
    {
        double factor = e.Delta > 0 ? 1.15 : 1 / 1.15;
        double newScale = scaleTransform.ScaleX * factor;

        if (newScale < 0.1 || newScale > 20) return;

        // Mouse position relative to the image content (before zoom)
        var mouseOnContent = e.GetPosition(image);

        // Mouse position relative to the scroll viewer viewport
        var mouseOnViewport = e.GetPosition(scrollViewer);

        // Apply zoom
        scaleTransform.ScaleX = newScale;
        scaleTransform.ScaleY = newScale;

        // Force layout update so ScrollableWidth/Height are current
        scrollViewer.UpdateLayout();

        // Scroll so the point under the mouse stays under the mouse
        double newHOffset = mouseOnContent.X * newScale - mouseOnViewport.X;
        double newVOffset = mouseOnContent.Y * newScale - mouseOnViewport.Y;

        scrollViewer.ScrollToHorizontalOffset(newHOffset);
        scrollViewer.ScrollToVerticalOffset(newVOffset);

        e.Handled = true;
    }

    private void OnMouseDown(object sender, MouseButtonEventArgs e)
    {
        _lastMousePos = e.GetPosition(scrollViewer);
        _isPanning = true;
        scrollViewer.CaptureMouse();
        e.Handled = true;
    }

    private void OnMouseMove(object sender, MouseEventArgs e)
    {
        if (!_isPanning) return;

        var pos = e.GetPosition(scrollViewer);
        double dx = pos.X - _lastMousePos.X;
        double dy = pos.Y - _lastMousePos.Y;

        scrollViewer.ScrollToHorizontalOffset(scrollViewer.HorizontalOffset - dx);
        scrollViewer.ScrollToVerticalOffset(scrollViewer.VerticalOffset - dy);

        _lastMousePos = pos;
    }

    private void OnMouseUp(object sender, MouseButtonEventArgs e)
    {
        _isPanning = false;
        scrollViewer.ReleaseMouseCapture();
    }
}
