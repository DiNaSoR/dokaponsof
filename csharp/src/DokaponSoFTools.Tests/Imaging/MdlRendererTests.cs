using System;
using System.Collections.Generic;
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
    public void RenderSampleModel_ProducesShadedMesh()
    {
        // Diagnostic dump of the first MDLs so the section layout is visible.
        var diag = new List<string>();
        // Scan some MDLs and keep the richest mesh — a representative model.
        string? chosen = null;
        MdlGeometry? geo = null;
        int scanned = 0;
        foreach (string file in FindMdlFiles())
        {
            if (scanned++ > 120) break;
            if (diag.Count < 18)
            {
                try { diag.Add(Path.GetFileName(file) + " :: " + MdlModel.Describe(File.ReadAllBytes(file))); }
                catch { /* ignore */ }
            }
            MdlGeometry? candidate;
            try { candidate = MdlModel.Parse(File.ReadAllBytes(file)); }
            catch { continue; }
            if (candidate is { FaceCount: > 0 } && candidate.FaceCount > (geo?.FaceCount ?? 0))
            {
                chosen = file;
                geo = candidate;
            }
        }

        File.WriteAllLines(Path.Combine(Path.GetTempPath(), "mdl_diag.txt"), diag);

        if (geo is null) return; // no MDL samples on this machine — skip

        using var bmp = MdlRenderer.Render(geo, 512, 512, 30f, 20f, 1f);
        bmp.Width.Should().Be(512);

        using var img = SKImage.FromBitmap(bmp);
        using var png = img.Encode(SKEncodedImageFormat.Png, 100);
        File.WriteAllBytes(Path.Combine(Path.GetTempPath(), "mdl_render_test.png"), png.ToArray());
        File.WriteAllText(
            Path.Combine(Path.GetTempPath(), "mdl_stats.txt"),
            $"file={chosen}{Environment.NewLine}vertices={geo.VertexCount}{Environment.NewLine}faces={geo.FaceCount}");

        // A structured parse produced triangulated faces (not just a point cloud).
        geo.FaceCount.Should().BeGreaterThan(0);
        geo.VertexCount.Should().BeGreaterThan(0);

        // OBJ export emits a valid mesh.
        string objPath = Path.Combine(Path.GetTempPath(), "mdl_export_test.obj");
        MdlObjExporter.Export(geo, objPath);
        string obj = File.ReadAllText(objPath);
        obj.Should().Contain("v ");
        obj.Should().Contain("f ");
    }

    private static IEnumerable<string> FindMdlFiles()
    {
        // 1) Repo research samples (walk up from the test output dir).
        var dir = new DirectoryInfo(AppContext.BaseDirectory);
        while (dir is not null)
        {
            string research = Path.Combine(dir.FullName, "research");
            if (Directory.Exists(research))
            {
                foreach (string f in SafeEnumerate(research))
                    yield return f;
            }
            dir = dir.Parent;
        }

        // 2) Common Steam install locations (prefer Field/Map models).
        string rel = Path.Combine("steamapps", "common", "DOKAPON ~Sword of Fury~");
        foreach (var drive in DriveInfo.GetDrives())
        {
            if (!drive.IsReady) continue;
            string root = drive.RootDirectory.FullName;
            foreach (string steam in new[] { Path.Combine(root, "Program Files (x86)", "Steam"), Path.Combine(root, "Steam"), Path.Combine(root, "SteamLibrary") })
            {
                string game = Path.Combine(steam, rel);
                if (!Directory.Exists(game)) continue;
                foreach (string f in SafeEnumerate(game).OrderByDescending(p => p.Contains("Field", StringComparison.OrdinalIgnoreCase)))
                    yield return f;
            }
        }
    }

    private static IEnumerable<string> SafeEnumerate(string root)
    {
        try { return Directory.EnumerateFiles(root, "*.mdl", SearchOption.AllDirectories); }
        catch { return []; }
    }
}
