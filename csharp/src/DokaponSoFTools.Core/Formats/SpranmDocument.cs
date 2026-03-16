using System.Text;
using DokaponSoFTools.Core.Compression;

namespace DokaponSoFTools.Core.Formats;

public record SequenceEntry(int SpriteGroupIndex, int Duration, int Flags);
public record SpriteEntry(int PartsIndex, int TextureIndex, int PositionX, int PositionY, float ScaleX, float ScaleY);
public record SpriteGroup(int[] SpriteIndices);
public record SpranmPart(float OffsetX, float OffsetY, float Width, float Height, float U0, float V0, float U1, float V1);

public sealed class SpranmDocument
{
    public List<SequenceEntry> Sequences { get; } = [];
    public List<SpriteEntry> Sprites { get; } = [];
    public List<SpriteGroup> Groups { get; } = [];
    public List<SpranmPart> Parts { get; } = [];
    public byte[]? TexturePng { get; private set; }
    public int TextureWidth { get; private set; }
    public int TextureHeight { get; private set; }
    public string SourcePath { get; }
    public int TotalFrames => Sequences.Sum(s => s.Duration);

    private SpranmDocument(string sourcePath)
    {
        SourcePath = sourcePath;
    }

    public static SpranmDocument? Load(string path)
    {
        try
        {
            byte[] raw = File.ReadAllBytes(path);
            return LoadFromData(raw, path);
        }
        catch
        {
            return null;
        }
    }

    public static SpranmDocument? LoadFromData(byte[] data, string sourcePath = "")
    {
        try
        {
            byte[] payload = data;

            // Decompress if LZ77-compressed
            if (data.Length >= 4 && Encoding.ASCII.GetString(data, 0, 4) == "LZ77")
            {
                byte[]? decompressed = Lz77FlagByte.Decompress(data);
                if (decompressed is null)
                    return null;
                payload = decompressed;
            }

            var doc = new SpranmDocument(sourcePath);
            doc.ParseSections(payload);
            return doc;
        }
        catch
        {
            return null;
        }
    }

    private void ParseSections(byte[] data)
    {
        using var ms = new MemoryStream(data);
        using var br = new BinaryReader(ms, Encoding.ASCII, leaveOpen: false);

        long fileLength = ms.Length;

        while (ms.Position + 28 <= fileLength)
        {
            long sectionStart = ms.Position;

            // Read 28-byte standard header: name[20] + totalSize[4] + entryCount[4]
            string name = ReadFixedAscii(br, 20);
            uint totalSize = br.ReadUInt32();
            uint entryCount = br.ReadUInt32();

            if (totalSize == 0)
                break;

            long sectionEnd = sectionStart + totalSize;

            switch (name)
            {
                case "Sequence":
                    ParseSequenceSection(br, (int)entryCount);
                    break;

                case "Sprite":
                    ParseSpriteSection(br, (int)entryCount);
                    break;

                case "SpriteGp":
                    ParseSpriteGpSection(br, (int)entryCount, sectionStart, totalSize);
                    break;

                case "TextureParts":
                    // TextureParts has a 24-byte header (name[20] + totalSize[4], no entryCount).
                    // We already read 28 bytes (name[20] + totalSize[4] + entryCount[4]),
                    // but entryCount was actually first 4 bytes of the sub-section data.
                    // Seek back to sectionStart + 24 and parse sub-sections.
                    ms.Position = sectionStart + 24;
                    ParseTextureParts(br, sectionStart, totalSize, data);
                    // Force sectionEnd to container end
                    sectionEnd = sectionStart + totalSize;
                    break;

                case "ConvertInfo":
                    // Metadata-only section; no payload to parse.
                    break;
            }

            // Advance to next 8-byte-aligned position after section end
            long nextPos = AlignUp(sectionEnd, 8);
            if (nextPos <= sectionStart || nextPos > fileLength)
                break;

            ms.Position = nextPos;
        }
    }

    // -------------------------------------------------------------------------
    // Section parsers
    // -------------------------------------------------------------------------

    private void ParseSequenceSection(BinaryReader br, int entryCount)
    {
        // Entry: 5 x uint32 = 20 bytes
        for (int i = 0; i < entryCount; i++)
        {
            int spriteGroupIndex = (int)br.ReadUInt32();
            int duration         = (int)br.ReadUInt32();
            int flags            = (int)br.ReadUInt32();
            /* unknown1 */ br.ReadUInt32();
            /* unknown2 */ br.ReadUInt32();

            Sequences.Add(new SequenceEntry(spriteGroupIndex, duration, flags));
        }
    }

    private void ParseSpriteSection(BinaryReader br, int entryCount)
    {
        // Entry: 8 fields = 32 bytes
        for (int i = 0; i < entryCount; i++)
        {
            int   partsIndex    = (int)br.ReadUInt32();
            /* unknown */         br.ReadUInt32();
            int   textureIndex  = (int)br.ReadUInt32();
            int   positionX     = (int)br.ReadUInt32();
            int   positionY     = (int)br.ReadUInt32();
            float scaleX        = br.ReadSingle();
            float scaleY        = br.ReadSingle();
            /* unknown2 */        br.ReadSingle();

            Sprites.Add(new SpriteEntry(partsIndex, textureIndex, positionX, positionY, scaleX, scaleY));
        }
    }

    private void ParseSpriteGpSection(BinaryReader br, int entryCount, long sectionStart, uint totalSize)
    {
        // First entryCount*4 bytes: sprite counts per group
        // Remaining bytes: flattened uint32 sprite indices
        if (entryCount == 0)
            return;

        long dataStart  = sectionStart + 28; // after the standard header
        long dataLength = totalSize - 28;

        int countsBytes   = entryCount * 4;
        long indicesBytes = dataLength - countsBytes;

        if (indicesBytes < 0)
            return;

        int[] counts = new int[entryCount];
        for (int i = 0; i < entryCount; i++)
            counts[i] = (int)br.ReadUInt32();

        int totalIndices = (int)(indicesBytes / 4);
        int[] allIndices = new int[totalIndices];
        for (int i = 0; i < totalIndices; i++)
            allIndices[i] = (int)br.ReadUInt32();

        int idx = 0;
        for (int g = 0; g < entryCount; g++)
        {
            int count = counts[g];
            int[] spriteIndices = new int[count];
            for (int s = 0; s < count && idx < totalIndices; s++, idx++)
                spriteIndices[s] = allIndices[idx];

            Groups.Add(new SpriteGroup(spriteIndices));
        }
    }

    private void ParseTextureParts(BinaryReader br, long containerStart, uint containerSize, byte[] data)
    {
        // The TextureParts container holds sequential sub-sections.
        // Sub-sections end when we reach containerStart + containerSize.
        long containerEnd = containerStart + containerSize;

        var ms = (MemoryStream)br.BaseStream;

        while (ms.Position + 20 <= containerEnd)
        {
            long subStart = ms.Position;
            string subName = ReadFixedAscii(br, 20);

            switch (subName)
            {
                case "Texture":
                {
                    // 40-byte header: name[20], totalSize[4], flags[4], kind[4], nestedSize[4], width[2], height[2]
                    uint   texTotalSize = br.ReadUInt32();
                    /* flags */           br.ReadUInt32();
                    /* kind */            br.ReadUInt32();
                    uint   nestedSize   = br.ReadUInt32();
                    ushort width        = br.ReadUInt16();
                    ushort height       = br.ReadUInt16();

                    // PNG data starts at offset 0x28 from subStart
                    long pngOffset = subStart + 0x28;
                    if (pngOffset + nestedSize <= data.Length && nestedSize > 0)
                    {
                        TexturePng    = new byte[nestedSize];
                        Array.Copy(data, pngOffset, TexturePng, 0, (int)nestedSize);
                        TextureWidth  = width;
                        TextureHeight = height;
                    }

                    // Advance past the full Texture sub-section
                    long subEnd = subStart + texTotalSize;
                    if (subEnd > ms.Position)
                        ms.Position = subEnd;

                    break;
                }

                case "Parts":
                {
                    uint partsTotal = br.ReadUInt32();
                    uint partsCount = br.ReadUInt32();

                    for (int i = 0; i < partsCount; i++)
                    {
                        float offsetX = br.ReadSingle();
                        float offsetY = br.ReadSingle();
                        float width   = br.ReadSingle();
                        float height  = br.ReadSingle();
                        float u0      = br.ReadSingle();
                        float v0      = br.ReadSingle();
                        float u1      = br.ReadSingle();
                        float v1      = br.ReadSingle();

                        Parts.Add(new SpranmPart(offsetX, offsetY, width, height, u0, v0, u1, v1));
                    }

                    long partsEnd = subStart + partsTotal;
                    if (partsEnd > ms.Position)
                        ms.Position = partsEnd;

                    break;
                }

                case "Anime":
                {
                    // Placeholder section – read its size and skip over it
                    uint animeTotal = br.ReadUInt32();
                    /* entryCount */ br.ReadUInt32();

                    long animeEnd = subStart + animeTotal;
                    if (animeEnd > ms.Position)
                        ms.Position = animeEnd;

                    break;
                }

                default:
                {
                    // Unknown sub-section: read totalSize and skip
                    if (ms.Position + 4 > containerEnd)
                        goto done;

                    uint unknownSize = br.ReadUInt32();
                    if (unknownSize < 20)
                        goto done;

                    long skipEnd = subStart + unknownSize;
                    if (skipEnd > ms.Position)
                        ms.Position = Math.Min(skipEnd, containerEnd);

                    break;
                }
            }

            // Sub-sections are also 8-byte aligned
            long aligned = AlignUp(ms.Position, 8);
            if (aligned >= containerEnd)
                break;
            ms.Position = aligned;
        }

        done:;
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private static string ReadFixedAscii(BinaryReader br, int length)
    {
        byte[] bytes = br.ReadBytes(length);
        int nullIdx = Array.IndexOf(bytes, (byte)0);
        return Encoding.ASCII.GetString(bytes, 0, nullIdx >= 0 ? nullIdx : length).Trim();
    }

    private static long AlignUp(long value, int alignment)
        => (value + alignment - 1) & ~(long)(alignment - 1);
}
