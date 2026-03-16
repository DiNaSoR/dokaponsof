using System.Buffers.Binary;

namespace DokaponSoFTools.Core.Compression;

/// <summary>
/// Token-stream LZ77 variant used for MDL model files.
/// Header: [4:"LZ77"][4:decompressed_size LE][4:flag1 LE][4:flag2 LE]
/// Each byte: bit7=0 -> literal, bit7=1 -> backref.
/// </summary>
public static class Lz77TokenStream
{
    private static readonly byte[] Magic = "LZ77"u8.ToArray();

    public static byte[]? Decompress(ReadOnlySpan<byte> data)
    {
        if (data.Length < 16 || !data[..4].SequenceEqual(Magic))
            return null;

        int expectedSize = BinaryPrimitives.ReadInt32LittleEndian(data[4..]);
        // flag1 at offset 8, flag2 at offset 12 — not used for decompression logic

        var output = new byte[expectedSize];
        int outPos = 0;
        int pos = 16;
        int dataLen = data.Length;

        while (pos < dataLen && outPos < expectedSize)
        {
            byte token = data[pos++];

            if ((token & 0x80) != 0)
            {
                // Back-reference
                if (pos >= dataLen) break;

                int length = ((token & 0x7C) >> 2) + 3;
                int offset = ((token & 0x03) << 8) | data[pos++];
                offset += 1;

                for (int i = 0; i < length; i++)
                {
                    if (outPos >= expectedSize) break;
                    if (offset <= outPos)
                        output[outPos] = output[outPos - offset];
                    else
                        output[outPos] = 0; // Window underrun
                    outPos++;
                }
            }
            else
            {
                // Literal byte
                output[outPos++] = token;
            }
        }

        return output;
    }
}
