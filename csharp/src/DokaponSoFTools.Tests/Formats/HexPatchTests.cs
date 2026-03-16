using System.Buffers.Binary;
using DokaponSoFTools.Core.Formats;
using FluentAssertions;
using Xunit;

namespace DokaponSoFTools.Tests.Formats;

public class HexPatchTests
{
    private string CreateTempHexFile(params (long Offset, byte[] Data)[] patches)
    {
        string path = Path.GetTempFileName();
        using var fs = File.Create(path);
        foreach (var (offset, data) in patches)
        {
            var offsetBytes = new byte[8];
            BinaryPrimitives.WriteInt64BigEndian(offsetBytes, offset);
            fs.Write(offsetBytes);

            var sizeBytes = new byte[8];
            BinaryPrimitives.WriteInt64BigEndian(sizeBytes, data.Length);
            fs.Write(sizeBytes);

            fs.Write(data);
        }
        return path;
    }

    [Fact]
    public void ParseFile_ReadsSinglePatch()
    {
        string path = CreateTempHexFile((0x100, new byte[] { 0xAA, 0xBB, 0xCC }));
        try
        {
            var patches = HexPatch.ParseFile(path);
            patches.Should().HaveCount(1);
            patches[0].Offset.Should().Be(0x100);
            patches[0].Size.Should().Be(3);
            patches[0].Data.Should().BeEquivalentTo(new byte[] { 0xAA, 0xBB, 0xCC });
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void ParseFile_ReadsMultiplePatches()
    {
        string path = CreateTempHexFile(
            (0x100, [0x01, 0x02]),
            (0x200, [0x03, 0x04, 0x05])
        );
        try
        {
            var patches = HexPatch.ParseFile(path);
            patches.Should().HaveCount(2);
            patches[0].Offset.Should().Be(0x100);
            patches[1].Offset.Should().Be(0x200);
            patches[1].Size.Should().Be(3);
        }
        finally { File.Delete(path); }
    }

    [Fact]
    public void DetectConflicts_FindsOverlap()
    {
        var patches = new List<HexPatchEntry>
        {
            new(0x100, 10, new byte[10], "file1.hex"),
            new(0x105, 10, new byte[10], "file2.hex")
        };

        var conflicts = HexPatch.DetectConflicts(patches);
        conflicts.Should().HaveCount(1);
        conflicts[0].ConflictType.Should().Be("overlap");
    }

    [Fact]
    public void DetectConflicts_FindsSameOffset()
    {
        var patches = new List<HexPatchEntry>
        {
            new(0x100, 5, new byte[5], "file1.hex"),
            new(0x100, 3, new byte[3], "file2.hex")
        };

        var conflicts = HexPatch.DetectConflicts(patches);
        conflicts.Should().HaveCount(1);
        conflicts[0].ConflictType.Should().Be("same_offset");
    }

    [Fact]
    public void DetectConflicts_NoConflictWhenSeparate()
    {
        var patches = new List<HexPatchEntry>
        {
            new(0x100, 5, new byte[5], "file1.hex"),
            new(0x200, 3, new byte[3], "file2.hex")
        };

        HexPatch.DetectConflicts(patches).Should().BeEmpty();
    }

    [Fact]
    public void ValidatePatches_DetectsOutOfBounds()
    {
        var patches = new List<HexPatchEntry>
        {
            new(0x100, 5, new byte[5], "file1.hex")
        };

        var errors = HexPatch.ValidatePatches(patches, 0x50); // exe is too small
        errors.Should().HaveCount(1);
    }

    [Fact]
    public void ApplyPatches_WritesCorrectly()
    {
        string exePath = Path.GetTempFileName();
        string outputPath = Path.GetTempFileName();
        try
        {
            // Create a 256-byte exe full of zeros
            File.WriteAllBytes(exePath, new byte[256]);

            var patches = new List<HexPatchEntry>
            {
                new(0x10, 3, [0xAA, 0xBB, 0xCC], "test.hex")
            };

            var (applied, errors) = HexPatch.ApplyPatches(exePath, patches, outputPath, false);
            applied.Should().Be(1);

            byte[] result = File.ReadAllBytes(outputPath);
            result[0x10].Should().Be(0xAA);
            result[0x11].Should().Be(0xBB);
            result[0x12].Should().Be(0xCC);
            result[0x0F].Should().Be(0x00); // unchanged before
            result[0x13].Should().Be(0x00); // unchanged after
        }
        finally
        {
            File.Delete(exePath);
            File.Delete(outputPath);
        }
    }
}
