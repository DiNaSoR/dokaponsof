using System;
using System.Globalization;
using Avalonia.Data.Converters;
using Avalonia.Media;
using DokaponSoFTools.App.Services;

namespace DokaponSoFTools.App.Converters;

/// <summary>Maps a <see cref="LogLevel"/> to its status colour brush.</summary>
public sealed class LevelToBrushConverter : IValueConverter
{
    public static readonly LevelToBrushConverter Instance = new();

    private static readonly IBrush Info = new SolidColorBrush(Color.Parse("#B8C0CC"));
    private static readonly IBrush Success = new SolidColorBrush(Color.Parse("#46C46A"));
    private static readonly IBrush Warning = new SolidColorBrush(Color.Parse("#E0B341"));
    private static readonly IBrush Error = new SolidColorBrush(Color.Parse("#E5534B"));

    public object Convert(object? value, Type targetType, object? parameter, CultureInfo culture)
        => value is LogLevel lvl
            ? lvl switch
            {
                LogLevel.Success => Success,
                LogLevel.Warning => Warning,
                LogLevel.Error => Error,
                _ => Info
            }
            : Info;

    public object ConvertBack(object? value, Type targetType, object? parameter, CultureInfo culture)
        => throw new NotSupportedException();
}
