using System.Buffers.Binary;
using System.Text;

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

/// <summary>
/// Structured MDL parser. Reverse-engineered layout learned from the DokaEngine
/// clean-room project: flag-byte LZ77 wrapper, then labelled sections
/// (20-byte ASCII label + length@0x14 + count@0x18 + data@0x1C). A "Vertex"
/// section (stride 36: position, normal, materialId, uv) plus a "Primitive"
/// section (stride 20: kind, …, vertexCount@0x0C, vertexStart@0x10) define the
/// mesh. Faces are implicit and sequential — indices are [start..start+count]
/// (count is 3 or 4), with quads triangulated as a fan. Falls back to a
/// float3 point cloud when the structured sections are absent.
/// </summary>
public static class MdlModel
{
    private static readonly HashSet<string> KnownLabels = new(StringComparer.Ordinal)
    {
        "Object", "Primitive", "Vertex", "Anime", "AnimeFrame", "AnimePacket", "AnimeAttr", "AnimeCoord",
    };

    public static MdlGeometry? Parse(byte[] data)
    {
        try
        {
            byte[] payload = MaybeDecompress(data);

            var sections = FindSections(payload, 0);
            if (sections.Count == 0)
                sections = FindRecoveredMeshSections(payload);

            return ReadStructuredGeometry(payload, sections) ?? ScanFloat3PointCloud(payload);
        }
        catch
        {
            return null;
        }
    }

    /// <summary>Diagnostic dump of the decompressed payload's section layout and parse result.</summary>
    public static string Describe(byte[] fileBytes)
    {
        var sb = new StringBuilder();
        try
        {
            byte[] payload = MaybeDecompress(fileBytes);
            sb.Append($"raw={fileBytes.Length} payload={payload.Length} lz77={HasLz77Magic(fileBytes)} ");
            var sections = FindSections(payload, 0);
            bool recovered = false;
            if (sections.Count == 0) { sections = FindRecoveredMeshSections(payload); recovered = true; }
            sb.Append(recovered ? "(recovered) " : "");
            sb.Append("sections=[" + string.Join(", ", sections.Select(s => $"{s.Label} c={s.Count} st={s.Stride}")) + "] ");
            var geo = ReadStructuredGeometry(payload, sections);
            sb.Append(geo is null ? "structured=NULL" : $"verts={geo.VertexCount} faces={geo.FaceCount}");
        }
        catch (Exception ex) { sb.Append("ERR: " + ex.Message); }
        return sb.ToString();
    }

    /// <summary>Returns the LZ77-decompressed payload, or null if not compressed.</summary>
    public static byte[]? DecompressMdl(byte[] data) =>
        HasLz77Magic(data) ? DecompressLz77(data) : null;

    private static byte[] MaybeDecompress(byte[] data) =>
        HasLz77Magic(data) ? DecompressLz77(data) ?? data : data;

    private static bool HasLz77Magic(byte[] data) =>
        data.Length >= 4 && data[0] == 'L' && data[1] == 'Z' && data[2] == '7' && data[3] == '7';

    /// <summary>
    /// LZ77 decompressor ported byte-for-byte from DokaEngine's Lz77Codec
    /// (validated across the game's assets). The flag stream (8 MSB-first bits
    /// per byte, from 0x10) and the token stream (from the header's data-offset)
    /// are SEPARATE: a set bit = a 2-byte back-reference (distance, length-3),
    /// a clear bit = a literal byte.
    /// </summary>
    private static byte[]? DecompressLz77(byte[] buffer)
    {
        if (buffer.Length < 0x10) return null;
        int rawSize = ReadI(buffer, 0x04);
        int tokenCount = ReadI(buffer, 0x08);
        int dataOffset = ReadI(buffer, 0x0C);
        if (rawSize < 0 || tokenCount < 0 || dataOffset < 0x10 || dataOffset > buffer.Length) return null;

        int flagsPointer = 0x10;
        int dataPointer = dataOffset;
        var output = new List<byte>(Math.Max(rawSize, 16));
        int bitCount = 0;
        byte flags = 0;

        for (int token = 0; token < tokenCount; token++)
        {
            if (bitCount == 0)
            {
                if (flagsPointer >= buffer.Length) break;
                flags = buffer[flagsPointer++];
                bitCount = 8;
            }

            if ((flags & 0x80) != 0)
            {
                if (dataPointer + 2 > buffer.Length) break;
                int distance = buffer[dataPointer];
                int length = buffer[dataPointer + 1] + 3;
                dataPointer += 2;
                if (distance == 0) break;
                int start = output.Count - distance;
                if (start < 0) break;
                for (int c = 0; c < length; c++) { output.Add(output[start]); start++; }
            }
            else
            {
                if (dataPointer >= buffer.Length) break;
                output.Add(buffer[dataPointer++]);
            }

            flags = (byte)((flags << 1) & 0xFF);
            bitCount--;
            if (output.Count > rawSize + 0x1000) break;
        }

        if (output.Count > rawSize) output.RemoveRange(rawSize, output.Count - rawSize);
        return output.ToArray();
    }

    // ===================== Structured geometry =====================

    private static MdlGeometry? ReadStructuredGeometry(byte[] payload, List<Section> sections)
    {
        var vertex = sections.FirstOrDefault(s => s.Label == "Vertex" && s.Count >= 3 && s.Stride >= 36);
        var primitive = sections.FirstOrDefault(s => s.Label == "Primitive" && s.Stride == 20 && s.Count > 0);
        if (vertex is null || primitive is null) return null;

        int vertexCount = vertex.Count;
        var vertices = new float[vertexCount][];
        var normals = new float[vertexCount][];
        for (int i = 0; i < vertexCount; i++)
        {
            int o = vertex.DataOffset + i * vertex.Stride;
            if (o + 36 > payload.Length) return null;
            vertices[i] = [ReadF(payload, o), ReadF(payload, o + 4), ReadF(payload, o + 8)];
            normals[i] = [ReadF(payload, o + 12), ReadF(payload, o + 16), ReadF(payload, o + 20)];
        }

        // Faces are implicit: each primitive references a sequential run of
        // 3 (triangle) or 4 (quad → fan) vertices.
        var triangles = new List<int[]>(primitive.Count * 2);
        int previousEnd = 0;
        for (int i = 0; i < primitive.Count; i++)
        {
            int o = primitive.DataOffset + i * primitive.Stride;
            if (o + 20 > payload.Length) return null;

            int count = ReadI(payload, o + 12);
            int start = ReadI(payload, o + 16);
            if (count is < 3 or > 4) return null;
            if (start < 0 || start + count > vertexCount) return null;
            if (i > 0 && start != previousEnd) return null; // must be a clean sequential run
            previousEnd = start + count;

            triangles.Add([start, start + 1, start + 2]);
            if (count == 4)
                triangles.Add([start, start + 2, start + 3]);
        }

        if (triangles.Count == 0) return null;

        return new MdlGeometry
        {
            Vertices = vertices,
            Normals = normals,
            Indices = triangles.ToArray(),
            Bounds = ComputeBounds(vertices),
        };
    }

    // ===================== Section scanning (ported from DokaEngine MdlScanner) =====================

    private sealed record Section(string Label, int Offset, int Length, int Count, int DataOffset, int DataLength, int Stride);

    private static List<Section> FindSections(byte[] payload, int startOffset)
    {
        var sections = new List<Section>();
        int offset = startOffset;
        while (offset + 28 <= payload.Length)
        {
            if (!TryReadSection(payload, offset, out var section)) break;
            sections.Add(section);

            int next = Align4(offset + section.Length);
            int recovered = FindNextSectionOffset(payload, next, maxLookaheadBytes: 16);
            if (recovered < 0 || recovered <= offset) break;
            offset = recovered;
        }
        return sections;
    }

    private static List<Section> FindRecoveredMeshSections(byte[] payload)
    {
        for (int offset = 0; offset + 28 <= payload.Length; offset += 4)
        {
            if (!TryReadSection(payload, offset, out var section) || section.Label != "Object")
                continue;

            var sections = FindSections(payload, offset);
            if (sections.Any(s => s.Label == "Primitive") && sections.Any(s => s.Label == "Vertex"))
                return sections;
        }
        return [];
    }

    private static int FindNextSectionOffset(byte[] payload, int offset, int maxLookaheadBytes)
    {
        int limit = Math.Min(payload.Length - 28, offset + maxLookaheadBytes);
        for (int candidate = offset; candidate <= limit; candidate += 4)
            if (TryReadSection(payload, candidate, out _))
                return candidate;
        return -1;
    }

    private static bool TryReadSection(byte[] payload, int offset, out Section section)
    {
        section = default!;
        if (offset < 0 || offset + 28 > payload.Length) return false;

        string label = ReadPaddedAsciiLabel(payload.AsSpan(offset, 20));
        if (!KnownLabels.Contains(label)) return false;

        int length = ReadI(payload, offset + 20);
        int count = ReadI(payload, offset + 24);
        if (length < 28 || count < 0 || offset + length > payload.Length) return false;

        int dataOffset = offset + 28;
        int dataLength = length - 28;
        int stride = count > 0 && dataLength % count == 0 ? dataLength / count : 0;
        section = new Section(label, offset, length, count, dataOffset, dataLength, stride);
        return true;
    }

    private static string ReadPaddedAsciiLabel(ReadOnlySpan<byte> bytes)
    {
        int length = 0;
        while (length < bytes.Length)
        {
            byte value = bytes[length];
            if (value == 0 || value == 0x20) break;
            if (value < 0x20 || value > 0x7E) return string.Empty;
            length++;
        }
        return Encoding.ASCII.GetString(bytes[..length]);
    }

    private static int Align4(int value) => (value + 3) & ~3;

    // ===================== Float3 point-cloud fallback =====================

    private static MdlGeometry? ScanFloat3PointCloud(byte[] payload)
    {
        int[] strides = [12, 16, 20, 24, 28, 32, 36];
        float[][]? best = null;

        foreach (int stride in strides)
        {
            int offset = 0;
            while (offset + 12 <= payload.Length)
            {
                int run = CountFloat3Run(payload, offset, stride);
                if (run >= 16)
                {
                    if (best is null || run > best.Length)
                    {
                        var arr = new float[run][];
                        for (int i = 0; i < run; i++)
                        {
                            int p = offset + i * stride;
                            arr[i] = [ReadF(payload, p), ReadF(payload, p + 4), ReadF(payload, p + 8)];
                        }
                        best = arr;
                    }
                    offset += run * stride;
                }
                else
                {
                    offset += 4;
                }
            }
        }

        if (best is null || best.Length < 3) return null;
        return new MdlGeometry { Vertices = best, Normals = null, Indices = null, Bounds = ComputeBounds(best) };
    }

    private static int CountFloat3Run(byte[] payload, int offset, int stride)
    {
        int count = 0;
        for (int p = offset; p + 12 <= payload.Length; p += stride)
        {
            float x = ReadF(payload, p), y = ReadF(payload, p + 4), z = ReadF(payload, p + 8);
            if (!IsPlausible(x) || !IsPlausible(y) || !IsPlausible(z)) break;
            if (MathF.Abs(x) < 1e-6f && MathF.Abs(y) < 1e-6f && MathF.Abs(z) < 1e-6f) break;
            count++;
        }
        return count;
    }

    private static bool IsPlausible(float v) => float.IsFinite(v) && MathF.Abs(v) <= 100000f;

    private static (float[] Min, float[] Max) ComputeBounds(float[][] vertices)
    {
        float[] min = [vertices[0][0], vertices[0][1], vertices[0][2]];
        float[] max = [vertices[0][0], vertices[0][1], vertices[0][2]];
        foreach (var v in vertices)
            for (int i = 0; i < 3; i++)
            {
                if (v[i] < min[i]) min[i] = v[i];
                if (v[i] > max[i]) max[i] = v[i];
            }
        return (min, max);
    }

    private static float ReadF(byte[] data, int offset) => BinaryPrimitives.ReadSingleLittleEndian(data.AsSpan(offset, 4));
    private static int ReadI(byte[] data, int offset) => BinaryPrimitives.ReadInt32LittleEndian(data.AsSpan(offset, 4));
}
