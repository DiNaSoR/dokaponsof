using Avalonia;
using Avalonia.Controls;
using Avalonia.Controls.Notifications;
using Avalonia.Interactivity;
using Avalonia.Threading;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.Views;

public partial class MainWindow : Window
{
    private WindowNotificationManager? _notifier;

    public MainWindow()
    {
        InitializeComponent();
#if DEBUG
        this.AttachDevTools();
#endif
        StorageService.TopLevel = this;
        RestoreWindowState();
        Closing += (_, _) => SaveWindowState();
        Loaded += OnLoaded;
    }

    private void OnLoaded(object? sender, RoutedEventArgs e)
    {
        _notifier = new WindowNotificationManager(this)
        {
            Position = NotificationPosition.BottomRight,
            MaxItems = 3
        };
        StatusLogService.Instance.MessageLogged += OnStatusMessage;
    }

    private void OnStatusMessage(StatusMessage m)
    {
        if (m.Level == LogLevel.Info) return; // info stays in the log panel only

        var type = m.Level switch
        {
            LogLevel.Success => NotificationType.Success,
            LogLevel.Warning => NotificationType.Warning,
            LogLevel.Error => NotificationType.Error,
            _ => NotificationType.Information
        };

        Dispatcher.UIThread.Post(() => _notifier?.Show(new Notification(m.Level.ToString(), m.Text, type)));
    }

    private void RestoreWindowState()
    {
        var s = SettingsService.Instance;
        if (s.WindowWidth > 0) Width = s.WindowWidth;
        if (s.WindowHeight > 0) Height = s.WindowHeight;

        if (!double.IsNaN(s.WindowLeft) && !double.IsNaN(s.WindowTop))
        {
            WindowStartupLocation = WindowStartupLocation.Manual;
            Position = new PixelPoint((int)s.WindowLeft, (int)s.WindowTop);
        }

        if (s.WindowMaximized) WindowState = WindowState.Maximized;
    }

    private void SaveWindowState()
    {
        var s = SettingsService.Instance;
        s.WindowMaximized = WindowState == WindowState.Maximized;
        if (WindowState == WindowState.Normal)
        {
            s.WindowLeft = Position.X;
            s.WindowTop = Position.Y;
            s.WindowWidth = Width;
            s.WindowHeight = Height;
        }
    }
}
