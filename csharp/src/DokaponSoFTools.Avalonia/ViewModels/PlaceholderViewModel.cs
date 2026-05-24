using CommunityToolkit.Mvvm.ComponentModel;

namespace DokaponSoFTools.App.ViewModels;

/// <summary>Shown for tools that haven't been ported to the new UI yet.</summary>
public sealed partial class PlaceholderViewModel : ObservableObject
{
    [ObservableProperty] private string _toolName;

    public PlaceholderViewModel(string toolName) => _toolName = toolName;
}
