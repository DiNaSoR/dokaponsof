using Avalonia.Controls;
using Avalonia.Input;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class VoiceToolsView : UserControl
{
    public VoiceToolsView() => InitializeComponent();

    private void OnSoundDoubleTapped(object? sender, TappedEventArgs e)
    {
        if (DataContext is VoiceToolsViewModel vm)
            vm.PlaySelectedCommand.Execute(null);
    }
}
