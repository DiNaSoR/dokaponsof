using System.Buffers.Binary;
using System.Text;

namespace DokaponSoFTools.Core.Extensions;

public static class BinaryReaderExtensions
{
    public static string ReadFixedAscii(this BinaryReader reader, int length)
    {
        byte[] bytes = reader.ReadBytes(length);
        int nullIdx = Array.IndexOf(bytes, (byte)0);
        return Encoding.ASCII.GetString(bytes, 0, nullIdx >= 0 ? nullIdx : length).Trim();
    }

    public static int Align8(int value) => (value + 7) & ~7;
    public static int Align16(int value) => (value + 15) & ~15;
}

public static class SpanExtensions
{
    public static int IndexOfSequence(this ReadOnlySpan<byte> span, ReadOnlySpan<byte> sequence)
    {
        for (int i = 0; i <= span.Length - sequence.Length; i++)
            if (span.Slice(i, sequence.Length).SequenceEqual(sequence))
                return i;
        return -1;
    }
}
