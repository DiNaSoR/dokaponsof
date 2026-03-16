using System.Windows.Controls;
using System.Windows.Input;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class AnimationViewerView : UserControl
{
    public AnimationViewerView()
    {
        InitializeComponent();
        Loaded += (_, _) => Focus();
    }

    private void OnPreviewKeyDown(object sender, KeyEventArgs e)
    {
        if (DataContext is not AnimationViewerViewModel vm) return;

        switch (e.Key)
        {
            case Key.Space:
                vm.TogglePlayStopCommand.Execute(null);
                e.Handled = true;
                break;
            case Key.Left:
                vm.PreviousFrameCommand.Execute(null);
                e.Handled = true;
                break;
            case Key.Right:
                vm.NextFrameCommand.Execute(null);
                e.Handled = true;
                break;
            case Key.C when Keyboard.Modifiers == ModifierKeys.Control:
                vm.CopyFrameToClipboardCommand.Execute(null);
                e.Handled = true;
                break;
        }
    }
}
