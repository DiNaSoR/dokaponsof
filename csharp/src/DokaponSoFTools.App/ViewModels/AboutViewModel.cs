using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace DokaponSoFTools.App.ViewModels;

public sealed partial class AboutViewModel : ObservableObject
{
    [ObservableProperty] private bool _isMuted;
    [ObservableProperty] private int _fPressCount;

    public string Title => "DOKAPON! Sword of Fury Tools";
    public string Version => "v0.4.0";
    public string Author => "DiNaSoR";
    public string License => "GNU General Public License v3.0";
    public string Repository => "https://github.com/DiNaSoR/dokaponsof";

    public string Description => """
        A comprehensive modding toolkit for DOKAPON! Sword of Fury.

        Features:
        - Asset Extractor: Extract PNG from tex, spranm, mpd, fnt files
        - Text Tools: Extract and reimport game text strings
        - Voice Tools: PCK sound archive extraction and replacement
        - Hex Editor: Apply binary patches to the game executable
        - Video Tools: Convert and replace game cutscenes (OGV)
        - Map Explorer: View and analyze game map data
        - Game Scanner: Analyze game directory structure

        Built with C#/.NET 8 and WPF.
        Ported from the original Python/PyQt6 application.
        """;

    public string Credits => """
        DOKAPON! Sword of Fury Tools
        ============================

        Created by DiNaSoR

        Original research and format documentation
        by the Dokapon modding community.

        Special thanks to:
        - q8fft2 (original text extraction)
        - NewDoc (PCK/Hex format docs)
        - The Dokapon Discord community

        Press F to pay respects.
        """;

    [RelayCommand]
    private void ToggleMute()
    {
        IsMuted = !IsMuted;
    }

    [RelayCommand]
    private void PressF()
    {
        FPressCount++;
    }
}
