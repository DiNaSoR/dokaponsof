using System.IO;
using Avalonia.Media.Imaging;
using SkiaSharp;

namespace DokaponSoFTools.App.Imaging;

/// <summary>
/// Converts Core's <see cref="SKBitmap"/> render results into Avalonia bitmaps
/// for the cases where a live <c>SkiaImage</c> control isn't used — static
/// thumbnails, clipboard, and PNG byte payloads.
/// </summary>
public static class SkiaBitmapConverter
{
    /// <summary>Encode an SKBitmap to PNG and load it as an Avalonia Bitmap.</summary>
    public static Bitmap ToAvaloniaBitmap(SKBitmap src)
    {
        using var image = SKImage.FromBitmap(src);
        using var data = image.Encode(SKEncodedImageFormat.Png, 100);
        using var ms = new MemoryStream();
        data.SaveTo(ms);
        ms.Position = 0;
        return new Bitmap(ms);
    }

    /// <summary>Load already-encoded PNG/JPEG bytes as an Avalonia Bitmap.</summary>
    public static Bitmap FromEncodedBytes(byte[] data)
    {
        using var ms = new MemoryStream(data);
        return new Bitmap(ms);
    }
}
