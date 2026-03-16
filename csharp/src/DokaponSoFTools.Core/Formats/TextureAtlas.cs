using System.Buffers.Binary;
using System.Text;
using DokaponSoFTools.Core.Compression;

namespace DokaponSoFTools.Core.Formats;

public sealed record TextureHeader(
    int TotalSize, uint TextureFlags, uint TextureKind,
    int NestedSize, int Width, int Height
);

public sealed record TexturePart(
    int Index,
    float OffsetX, float OffsetY,
    float Width, float Height,
    float U0, float V0, float U1, float V1
)
{
    public (int X0, int Y0, int X1, int Y1) PixelRect(int atlasWidth, int atlasHeight) => (
        (int)MathF.Round(U0 * atlasWidth),
        (int)MathF.Round(V0 * atlasHeight),
        (int)MathF.Round(U1 * atlasWidth),
        (int)MathF.Round(V1 * atlasHeight)
    );
}

public sealed class TexturePartsContainer
{
    public required TextureHeader Header { get; init; }
    public required string StorageKind { get; init; }
    public CellLz77Info? Lz77Info { get; init; }
    public required byte[] AtlasBytes { get; init; }
    public required List<TexturePart> Parts { get; init; }
    public int? AnimeSize { get; init; }
}

public static class TextureAtlas
{
    private static readonly byte[] PngSignature = [0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A];

    public static TextureHeader ParseHeader(ReadOnlySpan<byte> payload)
    {
        if (payload.Length < 0x28 || !payload[..7].SequenceEqual("Texture"u8))
            throw new InvalidDataException("Payload is not a Texture container");

        return new TextureHeader(
            TotalSize: BinaryPrimitives.ReadInt32LittleEndian(payload[0x14..]),
            TextureFlags: BinaryPrimitives.ReadUInt32LittleEndian(payload[0x18..]),
            TextureKind: BinaryPrimitives.ReadUInt32LittleEndian(payload[0x1C..]),
            NestedSize: BinaryPrimitives.ReadInt32LittleEndian(payload[0x20..]),
            Width: BinaryPrimitives.ReadUInt16LittleEndian(payload[0x24..]),
            Height: BinaryPrimitives.ReadUInt16LittleEndian(payload[0x26..])
        );
    }

    private static (List<TexturePart> Parts, int? AnimeSize) ParseTrailingParts(ReadOnlySpan<byte> trailing)
    {
        var parts = new List<TexturePart>();
        int? animeSize = null;

        int partsPos = FindMarker(trailing, "Parts"u8);
        if (partsPos >= 0)
        {
            int partsSize = BinaryPrimitives.ReadInt32LittleEndian(trailing[(partsPos + 20)..]);
            int partsCount = BinaryPrimitives.ReadInt32LittleEndian(trailing[(partsPos + 24)..]);
            int partsBase = partsPos + 28;

            if (partsBase + partsCount * 32 > trailing.Length)
                throw new InvalidDataException("Parts table exceeds Texture trailing data");

            for (int i = 0; i < partsCount; i++)
            {
                int off = partsBase + i * 32;
                parts.Add(new TexturePart(
                    Index: i,
                    OffsetX: BinaryPrimitives.ReadSingleLittleEndian(trailing[off..]),
                    OffsetY: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 4)..]),
                    Width: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 8)..]),
                    Height: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 12)..]),
                    U0: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 16)..]),
                    V0: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 20)..]),
                    U1: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 24)..]),
                    V1: BinaryPrimitives.ReadSingleLittleEndian(trailing[(off + 28)..])
                ));
            }

            int expectedMin = 28 + partsCount * 32;
            if (partsSize < expectedMin)
                throw new InvalidDataException($"Invalid Parts size: 0x{partsSize:X} < 0x{expectedMin:X}");
        }

        int animePos = FindMarker(trailing, "Anime"u8);
        if (animePos >= 0)
            animeSize = BinaryPrimitives.ReadInt32LittleEndian(trailing[(animePos + 20)..]);

        return (parts, animeSize);
    }

    private static int FindMarker(ReadOnlySpan<byte> data, ReadOnlySpan<byte> marker)
    {
        for (int i = 0; i <= data.Length - marker.Length; i++)
        {
            if (data.Slice(i, marker.Length).SequenceEqual(marker))
                return i;
        }
        return -1;
    }

    public static TexturePartsContainer ParsePayload(ReadOnlySpan<byte> payload)
    {
        var header = ParseHeader(payload);
        var storage = payload[0x28..];
        string storageKind;
        byte[] atlasBytes;
        CellLz77Info? lz77Info = null;

        if (storage.Length >= 8 && storage[..8].SequenceEqual(PngSignature))
        {
            storageKind = "png";
            atlasBytes = storage[..header.NestedSize].ToArray();
        }
        else if (storage.Length >= 4 && storage[..4].SequenceEqual("LZ77"u8))
        {
            storageKind = "indexed_lz77";
            var (decompressed, info) = Lz77Cell.Decompress(storage);
            atlasBytes = decompressed;
            lz77Info = info;
        }
        else
        {
            throw new InvalidDataException("Unsupported Texture storage");
        }

        var trailing = payload[header.TotalSize..];
        var (parts, animeSize) = ParseTrailingParts(trailing);

        return new TexturePartsContainer
        {
            Header = header,
            StorageKind = storageKind,
            Lz77Info = lz77Info,
            AtlasBytes = atlasBytes,
            Parts = parts,
            AnimeSize = animeSize
        };
    }

    public static TexturePartsContainer ParseChunkPayload(ReadOnlySpan<byte> buf, CellChunk chunk)
    {
        var payload = buf.Slice(chunk.PayloadOffset, chunk.PayloadSize);
        return ParsePayload(payload);
    }

    public static List<(byte R, byte G, byte B, byte A)[]> ParsePaletteChunk(ReadOnlySpan<byte> buf, CellChunk chunk)
    {
        var payload = buf.Slice(chunk.PayloadOffset, chunk.PayloadSize);
        if (payload.Length < 4)
            throw new InvalidDataException("Palette chunk payload is too small");

        int paletteCount = BinaryPrimitives.ReadInt32LittleEndian(payload);
        int expectedSize = 4 + paletteCount * 256 * 4;
        if (payload.Length != expectedSize)
            throw new InvalidDataException(
                $"Palette chunk size mismatch: payload=0x{payload.Length:X} expected=0x{expectedSize:X}");

        var palettes = new List<(byte, byte, byte, byte)[]>(paletteCount);
        int off = 4;

        for (int p = 0; p < paletteCount; p++)
        {
            var colors = new (byte R, byte G, byte B, byte A)[256];
            for (int c = 0; c < 256; c++)
            {
                colors[c] = (payload[off], payload[off + 1], payload[off + 2], payload[off + 3]);
                off += 4;
            }
            palettes.Add(colors);
        }

        return palettes;
    }
}
