using System.Buffers.Binary;
using System.Runtime.InteropServices;
using DokaponSoFTools.Core.Compression;

namespace DokaponSoFTools.Core.Formats;

public sealed class MdlGeometry
{
    public required float[][] Vertices { get; init; }
    public float[][]? Normals { get; init; }
    public int[][]? Indices { get; init; }
    public required (float[] Min, float[] Max) Bounds { get; init; }
    public int VertexCount => Vertices.Length;
    public int FaceCount => Indices?.Length ?? 0;
}

public static class MdlModel
{
    public static MdlGeometry? Parse(byte[] data)
    {
        try
        {
            // Strategy 1: structured vertex table
            var (vertices, indices, normals) = ExtractStructuredGeometry(data);

            // Strategy 2: heuristic float32
            vertices ??= ExtractVerticesHeuristic(data);

            // Strategy 3: uint16 fixed-point
            vertices ??= ExtractVerticesUint16(data);

            if (vertices is null || vertices.Length < 3) return null;

            normals ??= ExtractNormalsHeuristic(data, vertices.Length);
            indices ??= ExtractIndicesHeuristic(data, vertices.Length);

            var bounds = ComputeBounds(vertices);

            return new MdlGeometry
            {
                Vertices = vertices,
                Normals = normals,
                Indices = indices,
                Bounds = bounds
            };
        }
        catch
        {
            return null;
        }
    }

    public static byte[]? DecompressMdl(byte[] data)
    {
        return Lz77TokenStream.Decompress(data);
    }

    private static (float[][]? Verts, int[][]? Idx, float[][]? Norms) ExtractStructuredGeometry(byte[] data)
    {
        int labelPos = FindSequence(data, "Vertex"u8);
        if (labelPos < 0) return (null, null, null);

        int pos = labelPos + 6;
        while (pos < data.Length && data[pos] == 0x20) pos++;
        int baseOffset = pos;

        var table = new List<uint>();
        for (int i = 0; i < 32 && pos + 4 <= data.Length; i++)
        {
            table.Add(BinaryPrimitives.ReadUInt32LittleEndian(data.AsSpan(pos)));
            pos += 4;
        }

        if (table.Count < 2) return (null, null, null);

        var pairs = table.Skip(1).Where(v => v != 0)
            .Select(v => (Offset: (int)(v >> 16), Size: (int)(v & 0xFFFF)))
            .ToList();

        if (pairs.Count == 0) return (null, null, null);

        // Find vertex candidates
        float[][]? bestVertices = null;
        foreach (var (offRaw, size) in pairs)
        {
            foreach (int off in new[] { offRaw, baseOffset + offRaw })
            {
                if (size == 0 || size % 6 != 0 || off + size > data.Length) continue;
                int count = size / 6;
                if (count < 10 || count > 20000) continue;

                var verts = new float[count][];
                for (int i = 0; i < count; i++)
                {
                    short x = BinaryPrimitives.ReadInt16LittleEndian(data.AsSpan(off + i * 6));
                    short y = BinaryPrimitives.ReadInt16LittleEndian(data.AsSpan(off + i * 6 + 2));
                    short z = BinaryPrimitives.ReadInt16LittleEndian(data.AsSpan(off + i * 6 + 4));
                    verts[i] = [(x - 0x4000) / 128f, (y - 0x4000) / 128f, (z - 0x4000) / 128f];
                }

                var bounds = ComputeBounds(verts);
                float span = Enumerable.Range(0, 3).Sum(i => MathF.Abs(bounds.Max[i] - bounds.Min[i]));
                if (span > 1f && span < 2000f)
                {
                    bestVertices = verts;
                    break;
                }
            }
            if (bestVertices is not null) break;
        }

        if (bestVertices is null) return (null, null, null);

        // Try to find index buffer
        int vcount = bestVertices.Length;
        int[][]? bestIndices = null;
        float bestQuality = 0f;

        foreach (var (offRaw, size) in pairs)
        {
            if (size == 0 || size % 2 != 0) continue;
            foreach (int off in new[] { offRaw, baseOffset + offRaw })
            {
                if (off + size > data.Length) continue;
                int rawCount = size / 2;
                var raw = new ushort[rawCount];
                for (int i = 0; i < rawCount; i++)
                    raw[i] = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(off + i * 2));

                foreach (int mask in new[] { 0x1FF, 0x3FF, 0x7FF, 0xFFF })
                {
                    foreach (int shift in new[] { 0, 4, 8, 12 })
                    {
                        var decoded = raw.Select(r => ((r >> shift) & mask)).ToArray();
                        var triList = new List<int[]>();
                        int good = 0, total = 0;

                        for (int i = 0; i + 2 < decoded.Length; i += 3)
                        {
                            int a = decoded[i], b = decoded[i + 1], c = decoded[i + 2];
                            total++;
                            if (a == b || b == c || a == c) continue;
                            if (a >= vcount || b >= vcount || c >= vcount) continue;
                            good++;
                            triList.Add([a, b, c]);
                        }

                        if (total == 0) continue;
                        float quality = (float)good / total;
                        if (triList.Count > 0 && quality > bestQuality)
                        {
                            bestQuality = quality;
                            bestIndices = triList.ToArray();
                        }
                    }
                    if (bestQuality >= 0.6f) break;
                }
                if (bestQuality >= 0.6f) break;
            }
            if (bestQuality >= 0.6f) break;
        }

        return (bestVertices, bestIndices, null);
    }

    private static float[][]? ExtractVerticesHeuristic(byte[] data)
    {
        var allVertices = new List<float[]>();
        byte[] marker = [0x00, 0xC0, 0x00, 0x00];
        int pos = 0;

        while (true)
        {
            int markerPos = FindSequence(data.AsSpan(pos), marker);
            if (markerPos < 0) break;
            markerPos += pos;

            var blockVerts = ExtractBlockVertices(data, markerPos + 4);
            if (blockVerts is not null) allVertices.AddRange(blockVerts);
            pos = markerPos + 4;
            if (allVertices.Count > 10000) break;
        }

        if (allVertices.Count == 0)
        {
            byte[] floatMarker = [0x00, 0x00, 0x80, 0x3F];
            pos = FindSequence(data, floatMarker);
            if (pos >= 0)
            {
                var blockVerts = ExtractBlockVertices(data, pos + 4);
                if (blockVerts is not null) allVertices.AddRange(blockVerts);
            }
        }

        return allVertices.Count >= 3 ? allVertices.ToArray() : null;
    }

    private static float[][]? ExtractVerticesUint16(byte[] data, float scale = 1024f)
    {
        float[][]? bestRun = null;
        int pos = 0;

        while (pos + 6 <= data.Length)
        {
            ushort x = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos));
            ushort y = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 2));
            ushort z = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 4));

            if (x < 40000 && y < 40000 && z < 40000)
            {
                int runStart = pos;
                var run = new List<float[]>();
                int bad = 0;

                while (pos + 6 <= data.Length)
                {
                    x = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos));
                    y = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 2));
                    z = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 4));

                    if (x < 40000 && y < 40000 && z < 40000)
                    {
                        run.Add([x / scale, y / scale, z / scale]);
                        pos += 6;
                        if (run.Count >= 5000) break;
                    }
                    else
                    {
                        bad++;
                        pos += 2;
                        if (bad > 5) break;
                    }
                }

                if (runStart >= 0x1000 && run.Count >= 20 && run.Count <= 5000
                    && (bestRun is null || run.Count > bestRun.Length))
                {
                    bestRun = run.ToArray();
                }
            }
            else
            {
                pos += 2;
            }
        }

        if (bestRun is null || bestRun.Length < 20) return null;

        var bounds = ComputeBounds(bestRun);
        if (Enumerable.Range(0, 3).All(i => MathF.Abs(bounds.Max[i] - bounds.Min[i]) < 0.001f))
            return null;

        return bestRun;
    }

    private static List<float[]>? ExtractBlockVertices(byte[] data, int startPos, int maxVertices = 2000)
    {
        var vertices = new List<float[]>();
        int pos = startPos;
        int consecutive = 0;

        while (pos + 12 <= data.Length && vertices.Count < maxVertices)
        {
            float x = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos));
            float y = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos + 4));
            float z = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos + 8));

            if (IsValidVertex(x, y, z))
            {
                vertices.Add([x, y, z]);
                pos += 12;
                consecutive = 0;
            }
            else
            {
                consecutive++;
                pos += 4;
                if (consecutive > 10) break;
            }
        }

        return vertices.Count >= 3 ? vertices : null;
    }

    private static float[][]? ExtractNormalsHeuristic(byte[] data, int vertexCount)
    {
        byte[] marker = [0x00, 0x00, 0x40, 0xC1];
        int markerPos = FindSequence(data, marker);
        if (markerPos < 0) return null;

        var normals = new List<float[]>();
        int pos = markerPos + 4;

        while (pos + 12 <= data.Length && normals.Count < vertexCount)
        {
            float nx = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos));
            float ny = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos + 4));
            float nz = BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(pos + 8));

            float length = MathF.Sqrt(nx * nx + ny * ny + nz * nz);
            if (length is > 0.9f and < 1.1f)
            {
                normals.Add([nx, ny, nz]);
                pos += 12;
            }
            else
            {
                pos += 4;
            }
        }

        return normals.Count >= 3 ? normals.ToArray() : null;
    }

    private static int[][]? ExtractIndicesHeuristic(byte[] data, int vertexCount)
    {
        byte[] marker = [0x00, 0x00, 0x40, 0x00];
        int pos = FindSequence(data, marker);
        if (pos >= 0) pos += 4;
        else pos = 0;

        var indices = new List<int[]>();

        while (pos + 6 <= data.Length)
        {
            ushort i0 = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos));
            ushort i1 = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 2));
            ushort i2 = BinaryPrimitives.ReadUInt16LittleEndian(data.AsSpan(pos + 4));

            if (i0 < vertexCount && i1 < vertexCount && i2 < vertexCount
                && i0 != i1 && i1 != i2 && i0 != i2)
            {
                indices.Add([i0, i1, i2]);
                pos += 6;
                if (indices.Count > 100000) break;
            }
            else
            {
                pos += 2;
            }
        }

        return indices.Count >= 1 ? indices.ToArray() : null;
    }

    private static bool IsValidVertex(float x, float y, float z)
    {
        if (float.IsNaN(x) || float.IsNaN(y) || float.IsNaN(z)) return false;
        if (float.IsInfinity(x) || float.IsInfinity(y) || float.IsInfinity(z)) return false;
        if (MathF.Abs(x) > 10000 || MathF.Abs(y) > 10000 || MathF.Abs(z) > 10000) return false;

        foreach (float v in new[] { x, y, z })
            if (v != 0 && MathF.Abs(v) < 0.0001f) return false;

        return true;
    }

    private static (float[] Min, float[] Max) ComputeBounds(float[][] vertices)
    {
        if (vertices.Length == 0) return ([], []);

        float[] min = [(float)vertices.Min(v => v[0]), (float)vertices.Min(v => v[1]), (float)vertices.Min(v => v[2])];
        float[] max = [(float)vertices.Max(v => v[0]), (float)vertices.Max(v => v[1]), (float)vertices.Max(v => v[2])];
        return (min, max);
    }

    private static int FindSequence(ReadOnlySpan<byte> data, ReadOnlySpan<byte> sequence)
    {
        for (int i = 0; i <= data.Length - sequence.Length; i++)
            if (data.Slice(i, sequence.Length).SequenceEqual(sequence))
                return i;
        return -1;
    }
}
