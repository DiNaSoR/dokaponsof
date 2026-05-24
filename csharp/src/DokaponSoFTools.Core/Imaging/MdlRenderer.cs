using SkiaSharp;

namespace DokaponSoFTools.Core.Imaging;

/// <summary>
/// Lightweight software renderer for <see cref="Formats.MdlGeometry"/>: projects
/// the vertices with a yaw/pitch orbit camera and draws shaded, depth-sorted
/// triangles (painter's algorithm + back-face culling). Falls back to a point
/// cloud when no index buffer was recovered. Pure SkiaSharp so it lives in Core
/// and renders identically on every platform.
/// </summary>
public static class MdlRenderer
{
    public static SKBitmap Render(Formats.MdlGeometry geo, int width, int height,
        float yawDegrees, float pitchDegrees, float zoom)
    {
        var bmp = new SKBitmap(width, height, SKColorType.Bgra8888, SKAlphaType.Premul);
        using var canvas = new SKCanvas(bmp);
        canvas.Clear(new SKColor(0x0B, 0x0B, 0x12));

        var verts = geo.Vertices;
        int n = verts.Length;
        if (n == 0) return bmp;

        var (min, max) = geo.Bounds;
        float[] center = { (min[0] + max[0]) / 2f, (min[1] + max[1]) / 2f, (min[2] + max[2]) / 2f };
        float span = MathF.Max(max[0] - min[0], MathF.Max(max[1] - min[1], max[2] - min[2]));
        if (span < 1e-3f) span = 1f;
        float fit = MathF.Min(width, height) * 0.8f / span * MathF.Max(0.05f, zoom);

        float yaw = yawDegrees * MathF.PI / 180f;
        float pitch = pitchDegrees * MathF.PI / 180f;
        float cy = MathF.Cos(yaw), sy = MathF.Sin(yaw);
        float cp = MathF.Cos(pitch), sp = MathF.Sin(pitch);
        float halfW = width / 2f, halfH = height / 2f;

        // Project to screen + keep view-space coords for normals/depth.
        var px = new float[n];
        var py = new float[n];
        var vx = new float[n];
        var vy = new float[n];
        var vz = new float[n];

        for (int i = 0; i < n; i++)
        {
            float x = verts[i][0] - center[0];
            float y = verts[i][1] - center[1];
            float z = verts[i][2] - center[2];

            float x1 = x * cy + z * sy;       // yaw about Y
            float z1 = -x * sy + z * cy;
            float y2 = y * cp - z1 * sp;       // pitch about X
            float z2 = y * sp + z1 * cp;

            vx[i] = x1; vy[i] = y2; vz[i] = z2;
            px[i] = halfW + x1 * fit;
            py[i] = halfH - y2 * fit;
        }

        var idx = geo.Indices;
        if (idx is { Length: > 0 })
        {
            // Far-to-near draw order.
            var order = new int[idx.Length];
            var faceDepth = new float[idx.Length];
            for (int f = 0; f < idx.Length; f++)
            {
                var t = idx[f];
                faceDepth[f] = (vz[t[0]] + vz[t[1]] + vz[t[2]]) / 3f;
                order[f] = f;
            }
            Array.Sort(order, (a, b) => faceDepth[a].CompareTo(faceDepth[b]));

            // Light from over-the-shoulder of the camera.
            float lx = 0.35f, ly = 0.45f, lz = 0.82f;

            using var fill = new SKPaint { IsAntialias = true, Style = SKPaintStyle.Fill };
            using var path = new SKPath();

            foreach (int f in order)
            {
                var t = idx[f];
                if (t[0] >= n || t[1] >= n || t[2] >= n) continue;

                // View-space face normal.
                float e1x = vx[t[1]] - vx[t[0]], e1y = vy[t[1]] - vy[t[0]], e1z = vz[t[1]] - vz[t[0]];
                float e2x = vx[t[2]] - vx[t[0]], e2y = vy[t[2]] - vy[t[0]], e2z = vz[t[2]] - vz[t[0]];
                float nx = e1y * e2z - e1z * e2y;
                float ny = e1z * e2x - e1x * e2z;
                float nz = e1x * e2y - e1y * e2x;
                float len = MathF.Sqrt(nx * nx + ny * ny + nz * nz);
                if (len < 1e-6f) continue;
                nx /= len; ny /= len; nz /= len;

                if (nz < 0f) continue; // back-face cull (toward viewer = +z)

                float lambert = Math.Clamp(nx * lx + ny * ly + nz * lz, 0f, 1f);
                float shade = 0.30f + 0.70f * lambert;
                byte r = (byte)(120 * shade);
                byte g = (byte)(150 * shade);
                byte b = (byte)(210 * shade);
                fill.Color = new SKColor(r, g, b);

                path.Reset();
                path.MoveTo(px[t[0]], py[t[0]]);
                path.LineTo(px[t[1]], py[t[1]]);
                path.LineTo(px[t[2]], py[t[2]]);
                path.Close();
                canvas.DrawPath(path, fill);
            }
        }
        else
        {
            // No faces — draw a point cloud.
            using var dot = new SKPaint { IsAntialias = true, Color = new SKColor(0x4E, 0xC9, 0xF0) };
            for (int i = 0; i < n; i++)
                canvas.DrawCircle(px[i], py[i], 1.4f, dot);
        }

        return bmp;
    }
}
