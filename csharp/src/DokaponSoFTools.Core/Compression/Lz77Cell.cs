using System.Buffers.Binary;

namespace DokaponSoFTools.Core.Compression;

/// <summary>
/// Cell-style LZ77 variant used for map data.
/// Header: [4:"LZ77"][4:raw_size LE][4:token_count LE][4:data_offset LE]
/// Flags at 0x10..data_offset, data at data_offset..EOF.
/// </summary>
public static class Lz77Cell
{
    private static readonly byte[] Magic = "LZ77"u8.ToArray();

    public static (byte[] Data, CellLz77Info? Info) Decompress(ReadOnlySpan<byte> buf)
    {
        if (buf.Length < 0x10 || !buf[..4].SequenceEqual(Magic))
            return (buf.ToArray(), null);

        int rawSize = BinaryPrimitives.ReadInt32LittleEndian(buf[0x04..]);
        int tokenCount = BinaryPrimitives.ReadInt32LittleEndian(buf[0x08..]);
        int dataOffset = BinaryPrimitives.ReadInt32LittleEndian(buf[0x0C..]);

        int flagsPtr = 0x10;
        int dataPtr = dataOffset;
        var output = new List<byte>(rawSize);
        int bitCount = 0;
        int flags = 0;

        for (int t = 0; t < tokenCount; t++)
        {
            if (bitCount == 0)
            {
                if (flagsPtr >= buf.Length)
                    throw new InvalidDataException("LZ77 flags pointer exceeded file size");
                flags = buf[flagsPtr++];
                bitCount = 8;
            }

            if ((flags & 0x80) != 0)
            {
                // Back-reference
                if (dataPtr + 2 > buf.Length)
                    throw new InvalidDataException("LZ77 backref exceeded file size");
                int dist = buf[dataPtr];
                int length = buf[dataPtr + 1] + 3;
                dataPtr += 2;

                if (dist == 0)
                    throw new InvalidDataException("LZ77 invalid distance 0");
                int start = output.Count - dist;
                if (start < 0)
                    throw new InvalidDataException("LZ77 backref before output start");

                for (int i = 0; i < length; i++)
                {
                    output.Add(output[start]);
                    start++;
                }
            }
            else
            {
                // Literal byte
                if (dataPtr >= buf.Length)
                    throw new InvalidDataException("LZ77 literal exceeded file size");
                output.Add(buf[dataPtr++]);
            }

            flags = (flags << 1) & 0xFF;
            bitCount--;

            if (output.Count > rawSize + 0x1000)
                throw new InvalidDataException("LZ77 output grew beyond guard range");
        }

        if (output.Count > rawSize)
            output.RemoveRange(rawSize, output.Count - rawSize);

        var info = new CellLz77Info(
            RawSize: rawSize,
            TokenCount: tokenCount,
            DataOffset: dataOffset,
            FlagsEnd: flagsPtr,
            DataEnd: dataPtr,
            OutLen: output.Count
        );

        return (output.ToArray(), info);
    }
}
