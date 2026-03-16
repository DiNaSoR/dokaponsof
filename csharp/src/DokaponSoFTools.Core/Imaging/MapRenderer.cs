using DokaponSoFTools.Core.Compression;
using DokaponSoFTools.Core.Formats;
using SkiaSharp;

namespace DokaponSoFTools.Core.Imaging;

public sealed class LoadedCellDocument
{
    public required string SourcePath { get; init; }
    public required byte[] RawData { get; init; }
    public required byte[] DecompressedData { get; init; }
    public CellLz77Info? Lz77 { get; init; }
    public required CellHeader Header { get; init; }
    public required List<CellRecord> Records { get; init; }
    public required List<DecodedCellRecord> DecodedRecords { get; init; }
    public required List<CellChunk> Chunks { get; init; }
    public CellMap? CellMap { get; init; }
    public TexturePartsContainer? Texture { get; init; }
    public required List<(byte R, byte G, byte B, byte A)[]> Palettes { get; init; }
}

public static class MapRenderer
{
    public static LoadedCellDocument LoadCellDocument(string path)
    {
        byte[] raw = File.ReadAllBytes(path);
        var (data, lz77) = Lz77Cell.Decompress(raw);
        ReadOnlySpan<byte> span = data;

        var header = CellContainer.ParseHeader(span);
        var records = CellContainer.ParseRecords(span, header);
        var chunks = CellContainer.ParseChunks(span, header);
        var cellMap = CellContainer.FindAndParseMap(span, header, chunks);

        TexturePartsContainer? texture = null;
        var textureChunk = chunks.Find(c => c.Name == "TextureParts");
        if (textureChunk is not null)
            texture = TextureAtlas.ParseChunkPayload(span, textureChunk);

        List<(byte, byte, byte, byte)[]> palettes = [];
        var paletteChunk = chunks.Find(c => c.Name == "Palette");
        if (paletteChunk is not null)
            palettes = TextureAtlas.ParsePaletteChunk(span, paletteChunk);

        return new LoadedCellDocument
        {
            SourcePath = path,
            RawData = raw,
            DecompressedData = data,
            Lz77 = lz77,
            Header = header,
            Records = records,
            DecodedRecords = records.Select(CellContainer.DecodeRecord).ToList(),
            Chunks = chunks,
            CellMap = cellMap,
            Texture = texture,
            Palettes = palettes
        };
    }

    public static SKBitmap? BuildAtlasForDocument(LoadedCellDocument doc, int paletteIndex = 0)
    {
        if (doc.Texture is null) return null;

        if (doc.Texture.StorageKind == "png")
            return AtlasRenderer.BuildPngAtlas(doc.Texture);

        if (doc.Palettes.Count == 0) return null;

        paletteIndex = Math.Clamp(paletteIndex, 0, doc.Palettes.Count - 1);
        return AtlasRenderer.BuildIndexedAtlas(doc.Texture, doc.Palettes[paletteIndex]);
    }

    public static SKBitmap? RenderMapImage(LoadedCellDocument doc, int paletteIndex = 0, int? maxEdge = null)
    {
        if (doc.CellMap is null || doc.Texture is null) return null;

        var atlas = BuildAtlasForDocument(doc, paletteIndex);
        if (atlas is null || doc.Texture.Parts.Count == 0) return null;

        int tileWidth = Math.Max(1, (int)MathF.Round(doc.Texture.Parts[0].Width));
        int tileHeight = Math.Max(1, (int)MathF.Round(doc.Texture.Parts[0].Height));
        int imgWidth = doc.CellMap.Width * tileWidth;
        int imgHeight = doc.CellMap.Height * tileHeight;

        var image = new SKBitmap(imgWidth, imgHeight, SKColorType.Rgba8888, SKAlphaType.Premul);
        using var canvas = new SKCanvas(image);
        canvas.Clear(SKColors.Transparent);

        var cropCache = new Dictionary<int, SKBitmap>();

        for (int index = 0; index < doc.CellMap.Values.Length; index++)
        {
            uint value = doc.CellMap.Values[index];
            int recordIndex = (int)(value & 0xFFFF);

            if (recordIndex >= doc.DecodedRecords.Count) continue;

            var record = doc.DecodedRecords[recordIndex];
            int partIndex = record.ValueALow16;

            if (partIndex >= doc.Texture.Parts.Count) continue;

            if (!cropCache.TryGetValue(partIndex, out var crop))
            {
                var part = doc.Texture.Parts[partIndex];
                var (x0, y0, x1, y1) = part.PixelRect(doc.Texture.Header.Width, doc.Texture.Header.Height);
                int cw = Math.Max(1, x1 - x0);
                int ch = Math.Max(1, y1 - y0);

                crop = new SKBitmap(cw, ch);
                using var cropCanvas = new SKCanvas(crop);
                cropCanvas.DrawBitmap(atlas, new SKRect(x0, y0, x1, y1), new SKRect(0, 0, cw, ch));
                cropCache[partIndex] = crop;
            }

            int x = (index % doc.CellMap.Width) * tileWidth;
            int y = (index / doc.CellMap.Width) * tileHeight;
            canvas.DrawBitmap(crop, x, y);
        }

        // Dispose cached crops
        foreach (var c in cropCache.Values) c.Dispose();
        atlas.Dispose();

        if (maxEdge is null) return image;
        if (image.Width <= maxEdge && image.Height <= maxEdge) return image;

        float scale = Math.Min((float)maxEdge / image.Width, (float)maxEdge / image.Height);
        int newW = Math.Max(1, (int)MathF.Round(image.Width * scale));
        int newH = Math.Max(1, (int)MathF.Round(image.Height * scale));

        var resized = image.Resize(new SKImageInfo(newW, newH), SKFilterQuality.None);
        image.Dispose();
        return resized;
    }

    public static List<string> ListCellFiles(string gameDir)
    {
        var results = new List<string>();
        string fieldMap = Path.Combine(gameDir, "GameData", "app", "Field", "Map");
        string fieldChizu = Path.Combine(gameDir, "GameData", "app", "Field", "Chizu");

        if (Directory.Exists(fieldMap))
            results.AddRange(Directory.EnumerateFiles(fieldMap, "*.mpd", SearchOption.AllDirectories).OrderBy(p => p));
        if (Directory.Exists(fieldChizu))
            results.AddRange(Directory.EnumerateFiles(fieldChizu, "*.mpd", SearchOption.AllDirectories).OrderBy(p => p));

        return results;
    }
}
