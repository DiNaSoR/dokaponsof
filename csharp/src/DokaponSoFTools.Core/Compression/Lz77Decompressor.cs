using System.Buffers.Binary;

namespace DokaponSoFTools.Core.Compression;

/// <summary>
/// Unified LZ77 decompressor with auto-detection for all three game variants.
/// </summary>
public static class Lz77Decompressor
{
    private static readonly byte[] Magic = "LZ77"u8.ToArray();

    public static Lz77Variant DetectVariant(ReadOnlySpan<byte> data)
    {
        if (data.Length < 16 || !data[..4].SequenceEqual(Magic))
            return Lz77Variant.FlagByte;

        int rawSize = BinaryPrimitives.ReadInt32LittleEndian(data[0x04..]);
        int tokenCount = BinaryPrimitives.ReadInt32LittleEndian(data[0x08..]);
        int dataOffset = BinaryPrimitives.ReadInt32LittleEndian(data[0x0C..]);

        // Cell variant: data_offset > 0x10, token_count is reasonable and < raw_size
        if (dataOffset > 0x10 && dataOffset < data.Length
            && tokenCount > 0 && tokenCount < 0x100000
            && tokenCount < rawSize)
        {
            return Lz77Variant.Cell;
        }

        // Token-stream (MDL): decompressed size > 0 and token_count == 0 or >= raw_size
        if (rawSize > 0 && (tokenCount == 0 || tokenCount >= rawSize))
        {
            return Lz77Variant.TokenStream;
        }

        return Lz77Variant.FlagByte;
    }

    /// <summary>
    /// Decompress data using the specified variant (or auto-detect).
    /// For Cell variant, returns (decompressed, info). For others, info is null.
    /// </summary>
    public static (byte[]? Data, CellLz77Info? Info) Decompress(ReadOnlySpan<byte> data, Lz77Variant variant = Lz77Variant.Auto)
    {
        if (variant == Lz77Variant.Auto)
            variant = DetectVariant(data);

        return variant switch
        {
            Lz77Variant.FlagByte => (Lz77FlagByte.Decompress(data), null),
            Lz77Variant.TokenStream => (Lz77TokenStream.Decompress(data), null),
            Lz77Variant.Cell => Lz77Cell.Decompress(data),
            _ => throw new ArgumentException($"Unknown LZ77 variant: {variant}")
        };
    }

    /// <summary>Simple overload that discards the info and just returns bytes.</summary>
    public static byte[]? DecompressBytes(ReadOnlySpan<byte> data, Lz77Variant variant = Lz77Variant.Auto)
    {
        var (result, _) = Decompress(data, variant);
        return result;
    }
}
