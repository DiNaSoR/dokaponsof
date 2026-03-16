using System.Windows;
using System.Windows.Controls;
using DokaponSoFTools.App.ViewModels;

namespace DokaponSoFTools.App.Views;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        InitializeComponent();
    }

    private void OnNavSelectionChanged(object sender, SelectionChangedEventArgs e)
    {
        if (DataContext is MainViewModel vm &&
            sender is ListBox lb &&
            lb.SelectedItem is NavItem item)
        {
            vm.NavigateCommand.Execute(item);
        }
    }
}
