using System;
using Avalonia.Controls;
using Avalonia.Interactivity;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class AboutView : UserControl
{
    public AboutView() => InitializeComponent();

    private async void OnOpenRepo(object? sender, RoutedEventArgs e)
    {
        if (DataContext is AboutViewModel vm)
        {
            var top = TopLevel.GetTopLevel(this);
            if (top is not null)
                await top.Launcher.LaunchUriAsync(new Uri(vm.Repository));
        }
    }
}
