using SkiaSharp;
using DokaponSoFTools.Core.Formats;

namespace DokaponSoFTools.Core.Imaging;

public static class SpranmRenderer
{
    // Renders a specific sequence index (not frame tick, but sequence entry index)
    public static SKBitmap? RenderSequenceFrame(SpranmDocument doc, int sequenceIndex)
    {
        if (doc.TexturePng is null)
            return null;

        if (sequenceIndex < 0 || sequenceIndex >= doc.Sequences.Count)
            return null;

        using var atlas = SKBitmap.Decode(doc.TexturePng);
        if (atlas is null)
            return null;

        float texW = atlas.Width;
        float texH = atlas.Height;

        var sequence = doc.Sequences[sequenceIndex];

        if (sequence.SpriteGroupIndex < 0 || sequence.SpriteGroupIndex >= doc.Groups.Count)
            return null;

        var group = doc.Groups[sequence.SpriteGroupIndex];

        // Collect valid (sprite, part) pairs for bounding box and rendering
        var renderItems = new List<(SpriteEntry Sprite, SpranmPart Part, SKRect Src, SKRect Dest)>();

        foreach (int spriteIndex in group.SpriteIndices)
        {
            if (spriteIndex < 0 || spriteIndex >= doc.Sprites.Count)
                continue;

            var sprite = doc.Sprites[spriteIndex];

            if (sprite.PartsIndex < 0 || sprite.PartsIndex >= doc.Parts.Count)
                continue;

            var part = doc.Parts[sprite.PartsIndex];

            var src = new SKRect(
                part.U0 * texW,
                part.V0 * texH,
                part.U1 * texW,
                part.V1 * texH);

            // Position is the BOTTOM-RIGHT corner of the piece
            float destW = part.Width * sprite.ScaleX;
            float destH = part.Height * sprite.ScaleY;
            float posX = sprite.PositionX - destW + part.OffsetX;
            float posY = sprite.PositionY - destH + part.OffsetY;

            var dest = new SKRect(posX, posY, posX + destW, posY + destH);

            renderItems.Add((sprite, part, src, dest));
        }

        if (renderItems.Count == 0)
            return null;

        // Calculate canvas size from the bounding box of all destination rects
        float minX = float.MaxValue, minY = float.MaxValue;
        float maxX = float.MinValue, maxY = float.MinValue;

        foreach (var (_, _, _, dest) in renderItems)
        {
            if (dest.Left < minX) minX = dest.Left;
            if (dest.Top < minY) minY = dest.Top;
            if (dest.Right > maxX) maxX = dest.Right;
            if (dest.Bottom > maxY) maxY = dest.Bottom;
        }

        int canvasW = (int)Math.Ceiling(maxX - minX);
        int canvasH = (int)Math.Ceiling(maxY - minY);

        if (canvasW <= 0 || canvasH <= 0)
            return null;

        var bitmap = new SKBitmap(canvasW, canvasH, SKColorType.Rgba8888, SKAlphaType.Premul);
        using var canvas = new SKCanvas(bitmap);
        canvas.Clear(SKColors.Transparent);

        using var paint = new SKPaint { IsAntialias = false, FilterQuality = SKFilterQuality.None };

        foreach (var (_, _, src, dest) in renderItems)
        {
            // Offset dest rect so that minX/minY maps to (0,0)
            var adjustedDest = new SKRect(
                dest.Left - minX,
                dest.Top - minY,
                dest.Right - minX,
                dest.Bottom - minY);

            canvas.DrawBitmap(atlas, src, adjustedDest, paint);
        }

        canvas.Flush();
        return bitmap;
    }

    // Returns which sequence index corresponds to a given tick (frame number counting durations)
    public static int GetSequenceIndexAtTick(SpranmDocument doc, int tick)
    {
        int accumulated = 0;
        for (int i = 0; i < doc.Sequences.Count; i++)
        {
            accumulated += doc.Sequences[i].Duration;
            if (tick < accumulated) return i;
        }
        return doc.Sequences.Count - 1;
    }

    // Renders all unique sequence frames as a list of bitmaps (caller must dispose)
    public static List<SKBitmap> RenderAllFrames(SpranmDocument doc)
    {
        var results = new List<SKBitmap>();

        for (int i = 0; i < doc.Sequences.Count; i++)
        {
            var bitmap = RenderSequenceFrame(doc, i);
            if (bitmap is not null)
                results.Add(bitmap);
        }

        return results;
    }
}
