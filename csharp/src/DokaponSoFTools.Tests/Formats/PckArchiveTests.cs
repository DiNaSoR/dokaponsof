using DokaponSoFTools.Core.Formats;
using FluentAssertions;
using Xunit;

namespace DokaponSoFTools.Tests.Formats;

public class PckArchiveTests
{
    [Fact]
    public void RoundTrip_PreservesData()
    {
        string tempPath = Path.GetTempFileName();
        try
        {
            // Build a PCK with two sounds
            var pck = new PckArchive();
            pck.Sounds.Add(new Sound("test1.opus", [0x4F, 0x67, 0x67, 0x53, 0x01, 0x02, 0x03]));
            pck.Sounds.Add(new Sound("test2.raw", [0xAA, 0xBB, 0xCC, 0xDD]));

            // Write
            pck.Write(tempPath);
            File.Exists(tempPath).Should().BeTrue();

            // Re-read
            var pck2 = new PckArchive(tempPath);
            pck2.Sounds.Should().HaveCount(2);
            pck2.Sounds[0].Name.Should().Be("test1.opus");
            pck2.Sounds[0].Data.Should().BeEquivalentTo(new byte[] { 0x4F, 0x67, 0x67, 0x53, 0x01, 0x02, 0x03 });
            pck2.Sounds[0].IsOpus.Should().BeTrue();

            pck2.Sounds[1].Name.Should().Be("test2.raw");
            pck2.Sounds[1].Data.Should().BeEquivalentTo(new byte[] { 0xAA, 0xBB, 0xCC, 0xDD });
            pck2.Sounds[1].IsOpus.Should().BeFalse();
        }
        finally
        {
            File.Delete(tempPath);
        }
    }

    [Fact]
    public void FindSound_ByNameWithoutExtension()
    {
        var pck = new PckArchive();
        pck.Sounds.Add(new Sound("voice_001.opus", [0x01]));
        pck.Sounds.Add(new Sound("voice_002.opus", [0x02]));

        pck.FindSound("voice_001").Should().NotBeNull();
        pck.FindSound("voice_002.opus").Should().NotBeNull();
        pck.FindSound("voice_003").Should().BeNull();
    }

    [Fact]
    public void ReplaceSound_Works()
    {
        var pck = new PckArchive();
        pck.Sounds.Add(new Sound("test.opus", [0x01, 0x02]));

        var newSound = new Sound("replacement.opus", [0xAA, 0xBB, 0xCC]);
        pck.ReplaceSound("test", newSound).Should().BeTrue();

        pck.Sounds[0].Data.Should().BeEquivalentTo(new byte[] { 0xAA, 0xBB, 0xCC });
    }

    [Fact]
    public void EmptyPck_ThrowsOnWrite()
    {
        var pck = new PckArchive();
        FluentActions.Invoking(() => pck.Write(Path.GetTempFileName()))
            .Should().Throw<InvalidOperationException>();
    }

    [Fact]
    public void ExtractAll_CreatesFiles()
    {
        string tempDir = Path.Combine(Path.GetTempPath(), $"pck_test_{Guid.NewGuid():N}");
        try
        {
            var pck = new PckArchive();
            pck.Sounds.Add(new Sound("s1.raw", [0x01]));
            pck.Sounds.Add(new Sound("s2.raw", [0x02]));

            var paths = pck.ExtractAll(tempDir);
            paths.Should().HaveCount(2);
            File.Exists(paths[0]).Should().BeTrue();
            File.ReadAllBytes(paths[0]).Should().BeEquivalentTo(new byte[] { 0x01 });
        }
        finally
        {
            if (Directory.Exists(tempDir))
                Directory.Delete(tempDir, true);
        }
    }
}
