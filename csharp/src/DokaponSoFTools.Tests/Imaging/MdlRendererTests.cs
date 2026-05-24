using System;
using System.IO;
using System.Linq;
using DokaponSoFTools.Core.Formats;
using DokaponSoFTools.Core.Imaging;
using FluentAssertions;
using SkiaSharp;
using Xunit;

namespace DokaponSoFTools.Tests.Imaging;

public class MdlRendererTests
{
    [Fact]
    public void RenderSampleModel_ProducesNonEmptyBitmap()
    {
        string? mdl = FindSampleMdl();
        if (mdl is null) return; // research samples not present — skip gracefully

        byte[] raw = File.ReadAllBytes(mdl);
        byte[] data = MdlModel.DecompressMdl(raw) ?? raw;
        var geo = MdlModel.Parse(data);
        geo.Should().NotBeNull("a sample enemy model should parse into geometry");

        using var bmp = MdlRenderer.Render(geo!, 512, 512, 30f, 20f, 1f);
        bmp.Width.Should().Be(512);
        bmp.Height.Should().Be(512);

        // Save a copy for manual inspection of the 3D pipeline.
        using var img = SKImage.FromBitmap(bmp);
        using var png = img.Encode(SKEncodedImageFormat.Png, 100);
        File.WriteAllBytes(Path.Combine(Path.GetTempPath(), "mdl_render_test.png"), png.ToArray());
    }

    private static string? FindSampleMdl()
    {
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            string candidate = Path.Combine(dir.FullName, "research", "Enemy");
            if (Directory.Exists(candidate))
            {
                string? f = Directory.EnumerateFiles(candidate, "*.mdl").OrderBy(p => p).FirstOrDefault();
                if (f is not null) return f;
            }
            dir = dir.Parent;
        }
        return null;
    }
}
