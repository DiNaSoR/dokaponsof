using System.Diagnostics;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class VideoToolsView : UserControl
{
    public VideoToolsView()
    {
        InitializeComponent();
    }

    private void VideosGrid_MouseDoubleClick(object sender, MouseButtonEventArgs e)
    {
        if (videosGrid.SelectedItem is GameVideoItem item)
        {
            try
            {
                Process.Start(new ProcessStartInfo(item.Path) { UseShellExecute = true });
            }
            catch { /* ignore */ }
        }
    }
}
