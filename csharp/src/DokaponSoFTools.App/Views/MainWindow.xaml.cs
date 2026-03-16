using System.Windows;
using System.Windows.Controls;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
        RestoreWindowState();
        Closing += (_, _) => SaveWindowState();
    }

    private void OnNavSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (DataContext is MainViewModel vm &&
            sender is ListBox lb &&
            lb.SelectedItem is NavItem item)
        {
            vm.NavigateCommand.Execute(item);
            SettingsService.Instance.LastNavKey = item.Key;
        }
    }

    private void RestoreWindowState()
    {
        var s = SettingsService.Instance;
        if (!double.IsNaN(s.WindowLeft)) Left = s.WindowLeft;
        if (!double.IsNaN(s.WindowTop)) Top = s.WindowTop;
        Width = s.WindowWidth;
        Height = s.WindowHeight;
        if (s.WindowMaximized) WindowState = WindowState.Maximized;

        // Restore last nav
        Loaded += (_, _) =>
        {
            if (DataContext is MainViewModel vm && !string.IsNullOrEmpty(s.LastNavKey))
            {
                var nav = vm.NavItems.FirstOrDefault(n => n.Key == s.LastNavKey);
                if (nav is not null) vm.NavigateCommand.Execute(nav);
            }
        };
    }

    private void SaveWindowState()
    {
        var s = SettingsService.Instance;
        s.WindowMaximized = WindowState == WindowState.Maximized;
        if (WindowState == WindowState.Normal)
        {
            s.WindowLeft = Left;
            s.WindowTop = Top;
            s.WindowWidth = Width;
            s.WindowHeight = Height;
        }
    }
}
