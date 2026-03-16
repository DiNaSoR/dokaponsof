using System.Collections.ObjectModel;
using System.Windows.Media;
using CommunityToolkit.Mvvm.ComponentModel;

namespace DokaponSoFTools.App.Services;

public sealed record StatusMessage(string Timestamp, string Text, string Level, Brush Color);

public sealed partial class StatusLogService : ObservableObject
{
    public static StatusLogService Instance { get; } = new();

    public ObservableCollection<StatusMessage> Messages { get; } = [];

    [ObservableProperty]
    private double _progress;

    [ObservableProperty]
    private bool _isProgressVisible;

    private static readonly Brush InfoBrush = new SolidColorBrush(Color.FromRgb(0xCC, 0xCC, 0xCC));
    private static readonly Brush SuccessBrush = new SolidColorBrush(Color.FromRgb(0x4E, 0xC9, 0xB0));
    private static readonly Brush WarningBrush = new SolidColorBrush(Color.FromRgb(0xDC, 0xDC, 0xAA));
    private static readonly Brush ErrorBrush = new SolidColorBrush(Color.FromRgb(0xF1, 0x4C, 0x4C));

    static StatusLogService()
    {
        InfoBrush.Freeze();
        SuccessBrush.Freeze();
        WarningBrush.Freeze();
        ErrorBrush.Freeze();
    }

    public void Log(string message, string level = "info")
    {
        var brush = level switch
        {
            "success" => SuccessBrush,
            "warning" => WarningBrush,
            "error" => ErrorBrush,
            _ => InfoBrush
        };

        var msg = new StatusMessage(DateTime.Now.ToString("HH:mm:ss"), message, level, brush);

        if (System.Windows.Application.Current?.Dispatcher.CheckAccess() == true)
            Messages.Add(msg);
        else
            System.Windows.Application.Current?.Dispatcher.Invoke(() => Messages.Add(msg));
    }

    public void Info(string message) => Log(message, "info");
    public void Success(string message) => Log(message, "success");
    public void Warning(string message) => Log(message, "warning");
    public void Error(string message) => Log(message, "error");

    public void Clear() => Messages.Clear();

    public void SetProgress(double value)
    {
        Progress = Math.Clamp(value, 0, 100);
        IsProgressVisible = value > 0 && value < 100;
    }

    public string GetLogText()
    {
        return string.Join(Environment.NewLine, Messages.Select(m => $"[{m.Timestamp}] [{m.Level}] {m.Text}"));
    }
}
