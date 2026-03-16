using DokaponSoFTools.Core.Compression;
using FluentAssertions;
using Xunit;

namespace DokaponSoFTools.Tests.Compression;

public class Lz77Tests
{
    [Fact]
    public void FlagByte_ReturnsNull_WhenNoMagic()
    {
        byte[] data = [0x00, 0x00, 0x00, 0x00];
        Lz77FlagByte.Decompress(data).Should().BeNull();
    }

    [Fact]
    public void FlagByte_ReturnsNull_WhenTooSmall()
    {
        byte[] data = "LZ77"u8.ToArray();
        Lz77FlagByte.Decompress(data).Should().BeNull();
    }

    [Fact]
    public void FlagByte_DecompressesLiterals()
    {
        // Header: LZ77 + unknown(4) + decompressed_size(4)=3 + uncompressed_offset(4)=0
        // Flag byte: 0x00 (all literals), then 3 literal bytes
        byte[] data = [
            (byte)'L', (byte)'Z', (byte)'7', (byte)'7',
            0x00, 0x00, 0x00, 0x00,  // unknown
            0x03, 0x00, 0x00, 0x00,  // decompressed size = 3
            0x00, 0x00, 0x00, 0x00,  // uncompressed offset = 0 (no tail)
            0x00,                     // flag byte: all 8 are literals
            0x41, 0x42, 0x43         // literals: ABC
        ];
        var result = Lz77FlagByte.Decompress(data);
        result.Should().NotBeNull();
        result![..3].Should().BeEquivalentTo(new byte[] { 0x41, 0x42, 0x43 });
    }

    [Fact]
    public void FlagByte_DecompressesBackref()
    {
        // 4 bytes: literal "ABAB" via backref
        // Flag: bit7=0(lit A), bit6=0(lit B), bit5=1(backref), rest unused
        // Backref: len=((0x00>>4)&0xF)+3=3, offset=((0x00&0xF)<<8)|0x01+1=2
        // So copy 3 bytes from -2: AB -> ABA -> ABAB -> ABABA (but size is 5)
        byte[] data = [
            (byte)'L', (byte)'Z', (byte)'7', (byte)'7',
            0x00, 0x00, 0x00, 0x00,
            0x05, 0x00, 0x00, 0x00,  // decompressed size = 5
            0x00, 0x00, 0x00, 0x00,  // no tail
            0x20,                     // flag: 00100000 -> lit, lit, backref, ...
            0x41, 0x42,              // literals: A, B
            0x00, 0x01               // backref: len=3, offset=2
        ];
        var result = Lz77FlagByte.Decompress(data);
        result.Should().NotBeNull();
        result!.Length.Should().BeGreaterOrEqualTo(5);
        // First 5 bytes should be ABABA
        result[0].Should().Be(0x41); // A
        result[1].Should().Be(0x42); // B
        result[2].Should().Be(0x41); // A (from -2)
        result[3].Should().Be(0x42); // B (from -2)
        result[4].Should().Be(0x41); // A (from -2)
    }

    [Fact]
    public void TokenStream_ReturnsNull_WhenNoMagic()
    {
        byte[] data = [0x00, 0x00, 0x00, 0x00];
        Lz77TokenStream.Decompress(data).Should().BeNull();
    }

    [Fact]
    public void TokenStream_DecompressesLiterals()
    {
        // Header: LZ77 + decompressed_size=3 + flag1=0 + flag2=0
        // Tokens: 3 literal bytes (bit7=0)
        byte[] data = [
            (byte)'L', (byte)'Z', (byte)'7', (byte)'7',
            0x03, 0x00, 0x00, 0x00,  // decompressed size = 3
            0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0x41, 0x42, 0x43         // literal tokens: ABC
        ];
        var result = Lz77TokenStream.Decompress(data);
        result.Should().NotBeNull();
        result.Should().HaveCount(3);
        result.Should().BeEquivalentTo(new byte[] { 0x41, 0x42, 0x43 });
    }

    [Fact]
    public void Cell_ReturnsUnmodified_WhenNoMagic()
    {
        byte[] data = [0x01, 0x02, 0x03];
        var (result, info) = Lz77Cell.Decompress(data);
        result.Should().BeEquivalentTo(data);
        info.Should().BeNull();
    }

    [Fact]
    public void Cell_DecompressesLiterals()
    {
        // Header: LZ77 + raw_size=3 + token_count=3 + data_offset=0x11
        // Flags at 0x10: 1 byte = 0x00 (all literals)
        // Data at 0x11: 3 literal bytes
        byte[] data = [
            (byte)'L', (byte)'Z', (byte)'7', (byte)'7',
            0x03, 0x00, 0x00, 0x00,  // raw_size = 3
            0x03, 0x00, 0x00, 0x00,  // token_count = 3
            0x11, 0x00, 0x00, 0x00,  // data_offset = 0x11
            0x00,                     // flags: 0b00000000 (all literals)
            0x41, 0x42, 0x43         // data: A, B, C
        ];
        var (result, info) = Lz77Cell.Decompress(data);
        result.Should().BeEquivalentTo(new byte[] { 0x41, 0x42, 0x43 });
        info.Should().NotBeNull();
        info!.RawSize.Should().Be(3);
        info.TokenCount.Should().Be(3);
        info.OutLen.Should().Be(3);
    }

    [Fact]
    public void AutoDetect_DetectsCell()
    {
        // data_offset must be < data.Length, so we need enough bytes
        byte[] data = new byte[0x30];
        "LZ77"u8.CopyTo(data);
        // raw_size = 4096
        data[4] = 0x00; data[5] = 0x10; data[6] = 0x00; data[7] = 0x00;
        // token_count = 5 (< raw_size)
        data[8] = 0x05; data[9] = 0x00; data[10] = 0x00; data[11] = 0x00;
        // data_offset = 0x20 (> 0x10 and < data.Length=0x30)
        data[12] = 0x20; data[13] = 0x00; data[14] = 0x00; data[15] = 0x00;

        Lz77Decompressor.DetectVariant(data).Should().Be(Lz77Variant.Cell);
    }

    [Fact]
    public void AutoDetect_DetectsTokenStream()
    {
        byte[] data = [
            (byte)'L', (byte)'Z', (byte)'7', (byte)'7',
            0x00, 0x10, 0x00, 0x00,  // decompressed_size = 4096
            0x00, 0x00, 0x00, 0x00,  // flag1 = 0 (token_count==0)
            0x00, 0x00, 0x00, 0x00   // flag2 = 0
        ];
        Lz77Decompressor.DetectVariant(data).Should().Be(Lz77Variant.TokenStream);
    }

    [Fact]
    public void AutoDetect_FallsBackToFlagByte()
    {
        byte[] data = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
                        0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00];
        Lz77Decompressor.DetectVariant(data).Should().Be(Lz77Variant.FlagByte);
    }
}
