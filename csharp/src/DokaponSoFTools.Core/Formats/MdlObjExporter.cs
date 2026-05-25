using System.Globalization;
using System.IO;

namespace DokaponSoFTools.Core.Formats;

/// <summary>
/// Exports parsed <see cref="MdlGeometry"/> as a Wavefront OBJ mesh (positions,
/// normals, triangulated faces) so models can be opened in Blender, etc.
/// </summary>
public static class MdlObjExporter
{
    public static void Export(MdlGeometry geometry, string path)
    {
        using var writer = new StreamWriter(path, append: false);
        Write(geometry, writer);
    }

    public static void Write(MdlGeometry geometry, TextWriter writer)
    {
        var ci = CultureInfo.InvariantCulture;
        writer.WriteLine($"# DOKAPON! Sword of Fury model export");
        writer.WriteLine($"# {geometry.VertexCount} vertices, {geometry.FaceCount} faces");

        foreach (var v in geometry.Vertices)
            writer.WriteLine(string.Create(ci, $"v {v[0]:g9} {v[1]:g9} {v[2]:g9}"));

        if (geometry.Normals is { Length: > 0 })
        {
            foreach (var n in geometry.Normals)
                writer.WriteLine(string.Create(ci, $"vn {n[0]:g9} {n[1]:g9} {n[2]:g9}"));
        }

        bool hasNormals = geometry.Normals is { Length: > 0 };
        if (geometry.Indices is { Length: > 0 })
        {
            foreach (var t in geometry.Indices)
            {
                // OBJ is 1-based; integers are culture-invariant. Emit v//vn when normals exist.
                if (hasNormals)
                    writer.WriteLine($"f {t[0] + 1}//{t[0] + 1} {t[1] + 1}//{t[1] + 1} {t[2] + 1}//{t[2] + 1}");
                else
                    writer.WriteLine($"f {t[0] + 1} {t[1] + 1} {t[2] + 1}");
            }
        }
    }
}
