using System.Buffers.Binary;

namespace DokaponSoFTools.Core.Compression;

/// <summary>
/// Flag-byte LZ77 variant used for textures and SPRANM files.
/// Header: [4:"LZ77"][4:?][4:decompressed_size LE][4:uncompressed_offset LE]
/// Flag byte: 8 bits MSB-first, bit=1 -> backref, bit=0 -> literal.
/// </summary>
public static class Lz77FlagByte
{
    private static readonly byte[] Magic = "LZ77"u8.ToArray();

    public static byte[]? Decompress(ReadOnlySpan<byte> data)
    {
        if (data.Length < 16 || !data[..4].SequenceEqual(Magic))
            return null;

        int decompressedSize = BinaryPrimitives.ReadInt32LittleEndian(data[8..]);
        int uncompressedOffset = BinaryPrimitives.ReadInt32LittleEndian(data[12..]);

        int compressedEnd = (uncompressedOffset > 16 && uncompressedOffset <= data.Length)
            ? uncompressedOffset
            : data.Length;

        var result = new List<byte>(decompressedSize);
        int pos = 16;

        while (pos < compressedEnd && result.Count < decompressedSize)
        {
            if (pos >= data.Length) break;
            byte flag = data[pos++];

            for (int bit = 0; bit < 8; bit++)
            {
                if (pos >= compressedEnd || result.Count >= decompressedSize)
                    break;

                if ((flag & (0x80 >> bit)) != 0)
                {
                    // Back-reference
                    if (pos + 1 >= compressedEnd) break;

                    int b1 = data[pos];
                    int b2 = data[pos + 1];
                    pos += 2;

                    int length = ((b1 >> 4) & 0x0F) + 3;
                    int offset = ((b1 & 0x0F) << 8) | b2;
                    offset += 1;

                    for (int i = 0; i < length; i++)
                    {
                        if (result.Count >= decompressedSize) break;
                        if (result.Count >= offset)
                            result.Add(result[result.Count - offset]);
                        else
                            result.Add(0);
                    }
                }
                else
                {
                    // Literal byte
                    if (pos >= compressedEnd) break;
                    result.Add(data[pos++]);
                }
            }
        }

        // Append uncompressed tail data if present
        if (uncompressedOffset > 16 && uncompressedOffset < data.Length)
        {
            for (int i = uncompressedOffset; i < data.Length; i++)
                result.Add(data[i]);
        }

        return result.Count > 0 ? result.ToArray() : null;
    }
}
