using System.Windows;
using System.Windows.Threading;

namespace DokaponSoFTools.App;

public partial class App : Application
{
    private void OnUnhandledException(object sender, DispatcherUnhandledExceptionEventArgs e)
    {
        MessageBox.Show($"An unexpected error occurred:\n\n{e.Exception.Message}",
            "DOKAPON! Tools Error", MessageBoxButton.OK, MessageBoxImage.Error);
        e.Handled = true;
    }
}
