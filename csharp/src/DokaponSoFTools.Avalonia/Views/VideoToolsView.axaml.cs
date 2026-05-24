using Avalonia.Controls;
using Avalonia.Input;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class VideoToolsView : UserControl
{
    public VideoToolsView() => InitializeComponent();

    private void OnVideoDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (DataContext is VideoToolsViewModel vm)
            vm.OpenVideoCommand.Execute(null);
    }
}
