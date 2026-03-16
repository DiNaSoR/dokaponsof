using Microsoft.Win32;

namespace DokaponSoFTools.App.Services;

public static class DialogService
{
    public static string? BrowseFolder(string title = "Select Folder")
    {
        var dialog = new OpenFolderDialog { Title = title };
        return dialog.ShowDialog() == true ? dialog.FolderName : null;
    }

    public static string? OpenFile(string title = "Open File", string filter = "All files|*.*")
    {
        var dialog = new OpenFileDialog { Title = title, Filter = filter };
        return dialog.ShowDialog() == true ? dialog.FileName : null;
    }

    public static string? SaveFile(string title = "Save File", string filter = "All files|*.*", string? defaultName = null)
    {
        var dialog = new SaveFileDialog { Title = title, Filter = filter, FileName = defaultName ?? "" };
        return dialog.ShowDialog() == true ? dialog.FileName : null;
    }

    public static string[]? OpenFiles(string title = "Open Files", string filter = "All files|*.*")
    {
        var dialog = new OpenFileDialog { Title = title, Filter = filter, Multiselect = true };
        return dialog.ShowDialog() == true ? dialog.FileNames : null;
    }
}
