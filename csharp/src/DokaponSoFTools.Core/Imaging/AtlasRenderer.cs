using DokaponSoFTools.Core.Formats;
using SkiaSharp;

namespace DokaponSoFTools.Core.Imaging;

public static class AtlasRenderer
{
    public static SKBitmap BuildIndexedAtlas(TexturePartsContainer container, (byte R, byte G, byte B, byte A)[] palette)
    {
        if (container.StorageKind != "indexed_lz77")
            throw new InvalidOperationException("Indexed atlas rendering requires indexed_lz77 storage");

        int w = container.Header.Width;
        int h = container.Header.Height;

        if (container.AtlasBytes.Length != w * h)
            throw new InvalidDataException("Atlas byte length does not match texture dimensions");

        var bitmap = new SKBitmap(w, h, SKColorType.Rgba8888, SKAlphaType.Premul);
        var pixels = bitmap.GetPixels();

        unsafe
        {
            var ptr = (byte*)pixels.ToPointer();
            for (int i = 0; i < w * h; i++)
            {
                var (r, g, b, a) = palette[container.AtlasBytes[i]];
                ptr[i * 4 + 0] = r;
                ptr[i * 4 + 1] = g;
                ptr[i * 4 + 2] = b;
                ptr[i * 4 + 3] = a;
            }
        }

        return bitmap;
    }

    public static SKBitmap BuildPngAtlas(TexturePartsContainer container)
    {
        if (container.StorageKind != "png")
            throw new InvalidOperationException("PNG atlas rendering requires png storage");

        return SKBitmap.Decode(container.AtlasBytes)
            ?? throw new InvalidDataException("Failed to decode PNG atlas data");
    }

    public static SKBitmap BuildAtlas(TexturePartsContainer container, (byte R, byte G, byte B, byte A)[]? palette = null)
    {
        return container.StorageKind switch
        {
            "png" => BuildPngAtlas(container),
            "indexed_lz77" when palette is not null => BuildIndexedAtlas(container, palette),
            "indexed_lz77" => throw new ArgumentNullException(nameof(palette), "Palette required for indexed atlas"),
            _ => throw new InvalidOperationException($"Unknown storage kind: {container.StorageKind}")
        };
    }

    public static byte[] EncodePng(SKBitmap bitmap)
    {
        using var image = SKImage.FromBitmap(bitmap);
        using var data = image.Encode(SKEncodedImageFormat.Png, 100);
        return data.ToArray();
    }
}
