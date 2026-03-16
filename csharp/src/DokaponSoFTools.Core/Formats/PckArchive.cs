using System.Buffers.Binary;
using System.Text;

namespace DokaponSoFTools.Core.Formats;

public sealed class Sound
{
    public string Name { get; set; }
    public byte[] Data { get; set; }
    public int LoopStart { get; set; }
    public int LoopEnd { get; set; }
    public int Size => Data.Length;
    public bool IsOpus => Data.Length >= 4 && Data[0] == 'O' && Data[1] == 'g' && Data[2] == 'g' && Data[3] == 'S';

    public Sound(string name, byte[] data, int loopStart = 0, int loopEnd = 0)
    {
        Name = name;
        Data = data;
        LoopStart = loopStart;
        LoopEnd = loopEnd;
    }

    public static Sound FromFile(string filePath, int loopStart = 0, int loopEnd = 0)
    {
        return new Sound(Path.GetFileName(filePath), File.ReadAllBytes(filePath), loopStart, loopEnd);
    }

    public string WriteTo(string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        string path = Path.Combine(outputDir, Name);
        File.WriteAllBytes(path, Data);
        return path;
    }
}

public sealed class PckArchive
{
    private const int HeaderSize = 0x14;
    private static readonly byte[] FilenameHeader = Encoding.ASCII.GetBytes("Filename            ");
    private static readonly byte[] PackHeader = Encoding.ASCII.GetBytes("Pack                ");

    public List<Sound> Sounds { get; } = [];
    public string? SourcePath { get; }

    public PckArchive(string? filePath = null)
    {
        SourcePath = filePath;
        if (filePath is not null)
            Parse(filePath);
    }

    private void Parse(string filePath)
    {
        byte[] data = File.ReadAllBytes(filePath);
        var span = data.AsSpan();

        if (!span[..8].SequenceEqual("Filename"u8))
            throw new InvalidDataException("Invalid PCK file: missing 'Filename' header");

        int filenameSectionSize = BinaryPrimitives.ReadInt32LittleEndian(span[HeaderSize..]);
        int firstOffset = BinaryPrimitives.ReadInt32LittleEndian(span[(HeaderSize + 4)..]);
        int soundCount = firstOffset / 4;

        // Read filename offsets
        int offsetBase = HeaderSize + 4;
        var filenameOffsets = new int[soundCount];
        for (int i = 0; i < soundCount; i++)
            filenameOffsets[i] = BinaryPrimitives.ReadInt32LittleEndian(span[(offsetBase + i * 4)..]);

        // Read filenames
        var soundNames = new string[soundCount];
        for (int i = 0; i < soundCount; i++)
        {
            int nameStart = offsetBase + filenameOffsets[i];
            int nameEnd = Array.IndexOf(data, (byte)0, nameStart);
            if (nameEnd < 0) nameEnd = data.Length;
            soundNames[i] = Encoding.ASCII.GetString(data, nameStart, nameEnd - nameStart);
        }

        // Find Pack section (aligned to 8 bytes)
        int packOffset = filenameSectionSize;
        if (packOffset % 8 != 0)
            packOffset += 8 - (packOffset % 8);

        if (!span.Slice(packOffset, 4).SequenceEqual("Pack"u8))
            throw new InvalidDataException($"Invalid PCK file: missing 'Pack' header at offset {packOffset}");

        int infoBase = packOffset + HeaderSize + 8;

        for (int i = 0; i < soundCount; i++)
        {
            int soundOffset = BinaryPrimitives.ReadInt32LittleEndian(span[(infoBase + i * 8)..]);
            int soundSize = BinaryPrimitives.ReadInt32LittleEndian(span[(infoBase + i * 8 + 4)..]);
            byte[] soundData = data[soundOffset..(soundOffset + soundSize)];
            Sounds.Add(new Sound(soundNames[i], soundData));
        }
    }

    private static int Align(int size, int alignment)
    {
        return size % alignment == 0 ? 0 : alignment - (size % alignment);
    }

    public void Write(string outputPath)
    {
        if (Sounds.Count == 0)
            throw new InvalidOperationException("Cannot write empty PCK file");

        using var ms = new MemoryStream();
        using var bw = new BinaryWriter(ms);

        // --- Filename section ---
        bw.Write(FilenameHeader);
        long sizeOffset = ms.Position;
        bw.Write(0); // placeholder for section size

        // Build name offset array and name data
        var nameBytes = new MemoryStream();
        var nameOffsets = new List<int>();

        foreach (var sound in Sounds)
        {
            nameOffsets.Add((int)nameBytes.Length + Sounds.Count * 4);
            nameBytes.Write(Encoding.ASCII.GetBytes(sound.Name));
            nameBytes.WriteByte(0);
        }

        foreach (var offset in nameOffsets)
            bw.Write(offset);
        bw.Write(nameBytes.ToArray());

        // Update section size (total bytes written so far)
        int sectionSize = (int)ms.Position;
        ms.Position = sizeOffset;
        bw.Write(sectionSize);
        ms.Seek(0, SeekOrigin.End);

        // Alignment padding to 8 bytes
        int padding = Align((int)ms.Position, 8);
        for (int i = 0; i < padding; i++) bw.Write((byte)0);

        // --- Pack section ---
        long packStart = ms.Position;
        bw.Write(PackHeader);

        // Pack section: header(0x14) + size(4) + count(4) + info_array(N*8) = 0x1C + N*8
        int packSectionLength = 0x1C + Sounds.Count * 8;
        bw.Write(packSectionLength);
        bw.Write(Sounds.Count);

        // The info array will be at the current position
        // After info array comes 4 bytes padding, then sound data
        // Sound data absolute offset = packStart + packSectionLength + 4
        int soundDataAbsStart = (int)packStart + packSectionLength + 4;

        // Build sound data with 16-byte alignment between entries
        var soundData = new MemoryStream();
        var soundInfos = new List<(int Offset, int Size)>();

        foreach (var sound in Sounds)
        {
            soundInfos.Add((soundDataAbsStart + (int)soundData.Length, sound.Data.Length));
            soundData.Write(sound.Data);
            int pad = Align(sound.Data.Length, 16);
            for (int i = 0; i < pad; i++) soundData.WriteByte(0);
        }

        // Write info entries (offset, size pairs)
        foreach (var (off, size) in soundInfos)
        {
            bw.Write(off);
            bw.Write(size);
        }

        // 4 bytes padding before sound data
        bw.Write(0);

        // Sound data
        bw.Write(soundData.ToArray());

        // Final padding to 16-byte alignment
        padding = Align((int)ms.Position, 16);
        for (int i = 0; i < padding; i++) bw.Write((byte)0);

        Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
        File.WriteAllBytes(outputPath, ms.ToArray());
    }

    public List<string> ExtractAll(string outputDir)
    {
        Directory.CreateDirectory(outputDir);
        return Sounds.Select(s => s.WriteTo(outputDir)).ToList();
    }

    public Sound? FindSound(string name)
    {
        string nameBase = Path.GetFileNameWithoutExtension(name);
        return Sounds.Find(s =>
            s.Name == name || Path.GetFileNameWithoutExtension(s.Name) == nameBase);
    }

    public bool ReplaceSound(string name, Sound newSound)
    {
        string nameBase = Path.GetFileNameWithoutExtension(name);
        for (int i = 0; i < Sounds.Count; i++)
        {
            if (Sounds[i].Name == name || Path.GetFileNameWithoutExtension(Sounds[i].Name) == nameBase)
            {
                if (Path.GetExtension(newSound.Name) != Path.GetExtension(Sounds[i].Name))
                    newSound.Name = nameBase + Path.GetExtension(Sounds[i].Name);
                Sounds[i] = newSound;
                return true;
            }
        }
        return false;
    }
}
