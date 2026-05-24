using System.Collections.ObjectModel;
using Avalonia.Threading;
using CommunityToolkit.Mvvm.ComponentModel;

namespace DokaponSoFTools.App.Services;

public enum LogLevel { Info, Success, Warning, Error }

public sealed record StatusMessage(string Timestamp, string Text, LogLevel Level);

/// <summary>
/// Centralised UI log. Ported from WPF: the message colour is no longer baked
/// into the record (a UI concern); messages carry a <see cref="LogLevel"/> and
/// the view maps it to a brush. Marshalling uses Avalonia's UI dispatcher.
/// </summary>
public sealed partial class StatusLogService : ObservableObject
{
    public static StatusLogService Instance { get; } = new();

    public ObservableCollection<StatusMessage> Messages { get; } = [];

    /// <summary>Raised (on the UI thread) for every logged message — used to surface toasts.</summary>
    public event Action<StatusMessage>? MessageLogged;

    [ObservableProperty] private double _progress;
    [ObservableProperty] private bool _isProgressVisible;

    public void Log(string message, LogLevel level = LogLevel.Info)
    {
        var msg = new StatusMessage(DateTime.Now.ToString("HH:mm:ss"), message, level);

        void Apply()
        {
            Messages.Insert(0, msg); // newest first
            MessageLogged?.Invoke(msg);
        }

        if (Dispatcher.UIThread.CheckAccess())
            Apply();
        else
            Dispatcher.UIThread.Post(Apply);
    }

    public void Info(string message) => Log(message, LogLevel.Info);
    public void Success(string message) => Log(message, LogLevel.Success);
    public void Warning(string message) => Log(message, LogLevel.Warning);
    public void Error(string message) => Log(message, LogLevel.Error);

    public void Clear() => Messages.Clear();

    public void SetProgress(double value)
    {
        Progress = Math.Clamp(value, 0, 100);
        IsProgressVisible = value > 0 && value < 100;
    }

    public string GetLogText() =>
        // Messages are stored newest-first; write the file oldest-first (chronological).
        string.Join(Environment.NewLine,
            Messages.Reverse().Select(m => $"[{m.Timestamp}] [{m.Level.ToString().ToLowerInvariant()}] {m.Text}"));
}
