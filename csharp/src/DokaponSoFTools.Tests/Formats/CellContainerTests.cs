using System.Buffers.Binary;
using DokaponSoFTools.Core.Formats;
using FluentAssertions;
using Xunit;

namespace DokaponSoFTools.Tests.Formats;

public class CellContainerTests
{
    private static byte[] BuildCellBuffer(int entryCount = 2, int gridWidth = 4, int gridHeight = 4)
    {
        // Minimum Cell buffer: magic "Cell" padded to 0x14, then header fields, then records,
        // then a TextureParts chunk marker
        var buf = new byte[0x20 + entryCount * 12 + 0x20]; // header + records + space for chunk marker
        "Cell"u8.CopyTo(buf.AsSpan(0));
        // Pad with spaces
        for (int i = 4; i < 0x14; i++) buf[i] = (byte)' ';

        // Header at 0x14
        BinaryPrimitives.WriteInt32LittleEndian(buf.AsSpan(0x14), 0x20 + entryCount * 12); // table_offset
        BinaryPrimitives.WriteInt32LittleEndian(buf.AsSpan(0x18), entryCount);
        BinaryPrimitives.WriteUInt16LittleEndian(buf.AsSpan(0x1C), (ushort)gridWidth);
        BinaryPrimitives.WriteUInt16LittleEndian(buf.AsSpan(0x1E), (ushort)gridHeight);

        // Records at 0x20
        for (int i = 0; i < entryCount; i++)
        {
            int off = 0x20 + i * 12;
            BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(off), (uint)(i * 100));     // value_a
            BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(off + 4), (uint)(i * 200)); // value_b
            BinaryPrimitives.WriteUInt32LittleEndian(buf.AsSpan(off + 8), (uint)(i * 300)); // value_c
        }

        return buf;
    }

    [Fact]
    public void ParseHeader_ReadsFields()
    {
        var buf = BuildCellBuffer(3, 8, 6);
        var header = CellContainer.ParseHeader(buf);

        header.EntryCount.Should().Be(3);
        header.GridWidth.Should().Be(8);
        header.GridHeight.Should().Be(6);
    }

    [Fact]
    public void ParseHeader_ThrowsOnInvalidMagic()
    {
        var buf = new byte[0x20];
        FluentActions.Invoking(() => CellContainer.ParseHeader(buf))
            .Should().Throw<InvalidDataException>();
    }

    [Fact]
    public void ParseRecords_ReadsCorrectly()
    {
        var buf = BuildCellBuffer(2);
        var header = CellContainer.ParseHeader(buf);
        var records = CellContainer.ParseRecords(buf, header);

        records.Should().HaveCount(2);
        records[0].ValueA.Should().Be(0);
        records[1].ValueA.Should().Be(100);
        records[1].ValueB.Should().Be(200);
        records[1].ValueC.Should().Be(300);
    }

    [Fact]
    public void DecodeRecord_SplitsHighLow()
    {
        var record = new CellRecord(0, 0x0001_0002, 0, 0xFFFF_0000);
        var decoded = CellContainer.DecodeRecord(record);

        decoded.ValueALow16.Should().Be(2);
        decoded.ValueAHigh16.Should().Be(1);
        decoded.ValueCLow16.Should().Be(0);
        decoded.ValueCHigh16.Should().Be(0xFFFF);
    }

    [Fact]
    public void ParseHeader_ThrowsOnTooSmall()
    {
        var buf = new byte[0x10];
        FluentActions.Invoking(() => CellContainer.ParseHeader(buf))
            .Should().Throw<InvalidDataException>();
    }
}
