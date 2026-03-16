using CommunityToolkit.Mvvm.ComponentModel;

namespace DokaponSoFTools.App.Services;

public sealed partial class NavigationService : ObservableObject
{
    public static NavigationService Instance { get; } = new();

    [ObservableProperty]
    private ObservableObject? _currentViewModel;

    private readonly Dictionary<string, Func<ObservableObject>> _viewModelFactories = new();

    public void Register(string key, Func<ObservableObject> factory)
    {
        _viewModelFactories[key] = factory;
    }

    public void NavigateTo(string key)
    {
        if (_viewModelFactories.TryGetValue(key, out var factory))
            CurrentViewModel = factory();
    }
}
