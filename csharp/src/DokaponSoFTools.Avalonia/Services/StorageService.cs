using System.Threading.Tasks;
using Avalonia.Controls;
using Avalonia.Platform.Storage;

namespace DokaponSoFTools.App.Services;

/// <summary>
/// Cross-platform file/folder dialogs via Avalonia's <see cref="IStorageProvider"/>.
/// Replaces the WPF Microsoft.Win32 DialogService. The owning TopLevel (main
/// window) is registered once at startup. Filter strings use the familiar
/// "Name|*.ext;*.ext2|Name2|*.foo" format for easy porting of call sites.
/// </summary>
public static class StorageService
{
    public static TopLevel? TopLevel { get; set; }

    public static async Task<string?> BrowseFolderAsync(string title = "Select Folder")
    {
        if (TopLevel is null) return null;
        var folders = await TopLevel.StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions
        {
            Title = title,
            AllowMultiple = false
        });
        return folders.Count > 0 ? folders[0].TryGetLocalPath() : null;
    }

    public static async Task<string?> OpenFileAsync(string title = "Open File", string filter = "All files|*.*")
    {
        if (TopLevel is null) return null;
        var files = await TopLevel.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = false,
            FileTypeFilter = ParseFilter(filter)
        });
        return files.Count > 0 ? files[0].TryGetLocalPath() : null;
    }

    public static async Task<IReadOnlyList<string>?> OpenFilesAsync(string title = "Open Files", string filter = "All files|*.*")
    {
        if (TopLevel is null) return null;
        var files = await TopLevel.StorageProvider.OpenFilePickerAsync(new FilePickerOpenOptions
        {
            Title = title,
            AllowMultiple = true,
            FileTypeFilter = ParseFilter(filter)
        });
        if (files.Count == 0) return null;
        return files.Select(f => f.TryGetLocalPath())
                    .Where(p => !string.IsNullOrEmpty(p))
                    .Cast<string>()
                    .ToList();
    }

    public static async Task<string?> SaveFileAsync(string title = "Save File", string filter = "All files|*.*", string? defaultName = null)
    {
        if (TopLevel is null) return null;
        var file = await TopLevel.StorageProvider.SaveFilePickerAsync(new FilePickerSaveOptions
        {
            Title = title,
            SuggestedFileName = defaultName,
            FileTypeChoices = ParseFilter(filter)
        });
        return file?.TryGetLocalPath();
    }

    private static List<FilePickerFileType> ParseFilter(string filter)
    {
        var parts = filter.Split('|');
        var result = new List<FilePickerFileType>();
        for (int i = 0; i + 1 < parts.Length; i += 2)
        {
            var patterns = parts[i + 1].Split(';', StringSplitOptions.RemoveEmptyEntries);
            result.Add(new FilePickerFileType(parts[i]) { Patterns = patterns });
        }
        return result;
    }
}
