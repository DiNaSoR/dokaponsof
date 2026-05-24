using System.IO;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Threading;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.Controls;

public partial class StatusLogControl : UserControl
{
    public StatusLogControl()
    {
        InitializeComponent();
        DataContext = StatusLogService.Instance;

        // Newest entries are inserted at the top — keep the top in view.
        StatusLogService.Instance.Messages.CollectionChanged += (_, _) =>
            Dispatcher.UIThread.Post(() => LogScroll?.ScrollToHome());
    }

    private void OnClear(object? sender, RoutedEventArgs e) => StatusLogService.Instance.Clear();

    private async void OnSave(object? sender, RoutedEventArgs e)
    {
        string? path = await StorageService.SaveFileAsync("Save Log", "Text files|*.txt", "dokapon_tools_log.txt");
        if (path is null) return;
        await File.WriteAllTextAsync(path, StatusLogService.Instance.GetLogText());
        StatusLogService.Instance.Info($"Log saved to {path}");
    }
}
