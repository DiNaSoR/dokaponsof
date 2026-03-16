using System.Buffers.Binary;
using System.Text;

namespace DokaponSoFTools.Core.Formats;

public sealed record CellHeader(int TableOffset, int EntryCount, int GridWidth, int GridHeight);
public sealed record CellRecord(int Index, uint ValueA, uint ValueB, uint ValueC);
public sealed record CellChunk(string Name, int Offset, int SizeTotal, int PayloadOffset, int PayloadSize);
public sealed record CellMap(int Width, int Height, uint[] Values);

public sealed record DecodedCellRecord(
    int Index,
    uint ValueA, int ValueALow16, int ValueAHigh16,
    uint ValueB, int ValueBLow16, int ValueBHigh16,
    uint ValueC, int ValueCLow16, int ValueCHigh16
);

public static class CellContainer
{
    private static int Align8(int value) => (value + 7) & ~7;

    public static CellHeader ParseHeader(ReadOnlySpan<byte> buf)
    {
        if (buf.Length < 0x20 || !buf[..4].SequenceEqual("Cell"u8))
            throw new InvalidDataException("Buffer is not a Cell container");

        return new CellHeader(
            TableOffset: BinaryPrimitives.ReadInt32LittleEndian(buf[0x14..]),
            EntryCount: BinaryPrimitives.ReadInt32LittleEndian(buf[0x18..]),
            GridWidth: BinaryPrimitives.ReadUInt16LittleEndian(buf[0x1C..]),
            GridHeight: BinaryPrimitives.ReadUInt16LittleEndian(buf[0x1E..])
        );
    }

    public static List<CellRecord> ParseRecords(ReadOnlySpan<byte> buf, CellHeader header)
    {
        var records = new List<CellRecord>(header.EntryCount);
        int off = 0x20;

        for (int i = 0; i < header.EntryCount; i++)
        {
            if (off + 12 > buf.Length)
                throw new InvalidDataException("Cell record table exceeds file size");

            uint a = BinaryPrimitives.ReadUInt32LittleEndian(buf[off..]);
            uint b = BinaryPrimitives.ReadUInt32LittleEndian(buf[(off + 4)..]);
            uint c = BinaryPrimitives.ReadUInt32LittleEndian(buf[(off + 8)..]);
            records.Add(new CellRecord(i, a, b, c));
            off += 12;
        }

        return records;
    }

    public static int FindChunkStart(ReadOnlySpan<byte> buf, CellHeader header)
    {
        ReadOnlySpan<byte> marker = "TextureParts"u8;

        foreach (int candidate in new[] { header.TableOffset, header.TableOffset + 4 })
        {
            if (candidate < buf.Length && candidate + 12 <= buf.Length
                && buf.Slice(candidate, 12).SequenceEqual(marker))
                return candidate;
        }

        int searchStart = Math.Max(0, header.TableOffset - 0x20);
        int searchEnd = Math.Min(buf.Length - 12, header.TableOffset + 0x40);

        for (int pos = searchStart; pos <= searchEnd; pos++)
        {
            if (buf.Slice(pos, 12).SequenceEqual(marker))
                return pos;
        }

        throw new InvalidDataException("TextureParts marker not found near cell table offset");
    }

    public static List<CellChunk> ParseChunks(ReadOnlySpan<byte> buf, CellHeader header)
    {
        var chunks = new List<CellChunk>();
        int off = FindChunkStart(buf, header);

        while (off + 0x18 <= buf.Length)
        {
            var rawName = buf.Slice(off, 0x14);
            if (rawName[0] == 0) break;

            int nullIdx = rawName.IndexOf((byte)0);
            string name = Encoding.ASCII.GetString(
                nullIdx >= 0 ? rawName[..nullIdx] : rawName
            ).Trim();

            int sizeTotal = BinaryPrimitives.ReadInt32LittleEndian(buf[(off + 0x14)..]);
            if (sizeTotal < 0x18 || off + sizeTotal > buf.Length)
                throw new InvalidDataException($"Invalid chunk at 0x{off:X}: {name} size=0x{sizeTotal:X}");

            chunks.Add(new CellChunk(name, off, sizeTotal, off + 0x18, sizeTotal - 0x18));
            off = Align8(off + sizeTotal);
        }

        return chunks;
    }

    public static CellMap? ParseChunkMap(ReadOnlySpan<byte> buf, CellChunk chunk)
    {
        var payload = buf.Slice(chunk.PayloadOffset, chunk.PayloadSize);
        if (payload.Length < 4)
            throw new InvalidDataException("Map chunk payload is too small");

        int width = BinaryPrimitives.ReadUInt16LittleEndian(payload);
        int height = BinaryPrimitives.ReadUInt16LittleEndian(payload[2..]);
        int expectedValues = width * height;
        int expectedSize = 4 + expectedValues * 4;

        if (payload.Length != expectedSize)
            throw new InvalidDataException(
                $"Map chunk size mismatch: width={width} height={height} payload=0x{payload.Length:X} expected=0x{expectedSize:X}");

        var values = new uint[expectedValues];
        for (int i = 0; i < expectedValues; i++)
            values[i] = BinaryPrimitives.ReadUInt32LittleEndian(payload[(4 + i * 4)..]);

        return new CellMap(width, height, values);
    }

    public static CellMap? FindAndParseMap(ReadOnlySpan<byte> buf, CellHeader header, List<CellChunk>? chunks = null)
    {
        chunks ??= ParseChunks(buf, header);
        var mapChunk = chunks.Find(c => c.Name == "Map");
        return mapChunk is not null ? ParseChunkMap(buf, mapChunk) : null;
    }

    public static DecodedCellRecord DecodeRecord(CellRecord r) => new(
        Index: r.Index,
        ValueA: r.ValueA,
        ValueALow16: (int)(r.ValueA & 0xFFFF),
        ValueAHigh16: (int)(r.ValueA >> 16),
        ValueB: r.ValueB,
        ValueBLow16: (int)(r.ValueB & 0xFFFF),
        ValueBHigh16: (int)(r.ValueB >> 16),
        ValueC: r.ValueC,
        ValueCLow16: (int)(r.ValueC & 0xFFFF),
        ValueCHigh16: (int)(r.ValueC >> 16)
    );
}
