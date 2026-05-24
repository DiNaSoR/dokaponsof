using System;
using Avalonia.Controls;
using Avalonia.Controls.Templates;
using CommunityToolkit.Mvvm.ComponentModel;

namespace DokaponSoFTools.App;

/// <summary>
/// Convention-based view resolution: a ViewModel type name maps to the matching
/// View type by replacing "ViewModel" with "View"
/// (e.g. ViewModels.GameScannerViewModel -> Views.GameScannerView).
/// </summary>
public sealed class ViewLocator : IDataTemplate
{
    public Control Build(object? param)
    {
        if (param is null)
            return new TextBlock { Text = "null" };

        var name = param.GetType().FullName!.Replace("ViewModel", "View", StringComparison.Ordinal);
        var type = Type.GetType(name);

        return type is not null
            ? (Control)Activator.CreateInstance(type)!
            : new TextBlock { Text = $"View not found: {name}" };
    }

    public bool Match(object? data) => data is ObservableObject;
}
