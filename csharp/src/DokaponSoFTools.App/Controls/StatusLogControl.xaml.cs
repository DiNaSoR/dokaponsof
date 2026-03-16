using System.Windows;
using System.Windows.Controls;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.Controls;

public partial class StatusLogControl : UserControl
{
    public StatusLogControl()
    {
        InitializeComponent();
    }

    private void BtnSave_Click(object sender, RoutedEventArgs e)
    {
        string? path = DialogService.SaveFile("Save Log", "Text files|*.txt", "dokapon_tools_log.txt");
        if (path is not null)
        {
            System.IO.File.WriteAllText(path, StatusLogService.Instance.GetLogText());
            StatusLogService.Instance.Info($"Log saved to {path}");
        }
    }

    private void BtnClear_Click(object sender, RoutedEventArgs e)
    {
        StatusLogService.Instance.Clear();
    }
}
