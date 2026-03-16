namespace DokaponSoFTools.Core.Compression;

public sealed record CellLz77Info(
    int RawSize,
    int TokenCount,
    int DataOffset,
    int FlagsEnd,
    int DataEnd,
    int OutLen
);
