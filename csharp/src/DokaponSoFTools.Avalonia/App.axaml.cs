using Avalonia;
using Avalonia.Controls.ApplicationLifetimes;
using Avalonia.Markup.Xaml;
using DokaponSoFTools.App.Services;
using DokaponSoFTools.App.ViewModels;
using DokaponSoFTools.App.Views;

namespace DokaponSoFTools.App;

public partial class App : Application
{
    public override void Initialize() => AvaloniaXamlLoader.Load(this);

    public override void OnFrameworkInitializationCompleted()
    {
        // Apply the saved accent colour before the window is built.
        SettingsViewModel.ApplyAccent(SettingsService.Instance.AccentColor);

        if (ApplicationLifetime is IClassicDesktopStyleApplicationLifetime desktop)
        {
            desktop.MainWindow = new MainWindow();
        }

        base.OnFrameworkInitializationCompleted();
    }
}
