# Contributing to DOKAPON! Sword of Fury Tools

If you find a bug or have an idea, you can open an issue or pull request.

## 🐛 Reporting Bugs

1. Check [existing issues](https://github.com/DiNaSoR/dokaponsof/issues) first
2. Include: steps to reproduce, expected vs actual behavior, screenshots if relevant
3. Mention your OS version and game version

## 💡 Suggesting Features

Open an issue with the `enhancement` label describing:

- What problem it solves
- How you envision it working
- Any format/RE research that supports it

## 🔧 Pull Requests

1. Fork and create a feature branch
2. Follow existing code style (C# conventions, MVVM pattern)
3. Test with the actual game files
4. Keep PRs focused — one feature per PR
5. Update documentation if needed

By submitting a pull request, you agree that your contribution will be licensed under the GNU GPL v3.0 (see [LICENSE](LICENSE)).

## 🏗️ Development Setup

```bash
git clone https://github.com/DiNaSoR/dokaponsof.git
cd dokaponsof/csharp
dotnet build
```

Run the Avalonia UI (cross-platform):

```bash
dotnet run --project src/DokaponSoFTools.Avalonia/DokaponSoFTools.Avalonia.csproj
```

Run the WPF UI (Windows):

```bash
dotnet run --project src/DokaponSoFTools.App/DokaponSoFTools.App.csproj
```

### Project Structure

```
csharp/
├── src/
│   ├── DokaponSoFTools.Core/       # Format parsers, renderers, tools
│   │   ├── Formats/                # GameText, PckArchive, SpranmDocument, etc.
│   │   ├── Imaging/                # MapRenderer, SpranmRenderer, MdlRenderer
│   │   ├── Compression/            # LZ77 variants (FlagByte, TokenStream, Cell)
│   │   ├── Scanning/               # GameScanner, ReportGenerator
│   │   └── Tools/                  # AssetExtractor, VideoConverter
│   ├── DokaponSoFTools.App/        # WPF application (Windows)
│   │   ├── ViewModels/
│   │   ├── Views/
│   │   ├── Services/
│   │   └── Themes/
│   ├── DokaponSoFTools.Avalonia/   # Avalonia application (cross-platform)
│   │   ├── ViewModels/
│   │   ├── Views/
│   │   └── Services/
│   └── DokaponSoFTools.Tests/      # Unit tests (Core only)
├── tools/                          # RE analysis scripts (Python, Frida)
research/                           # Format RE notes and sample outputs
docs/                               # Jekyll documentation site
app/                                # Legacy PyQt6 GUI (pre–C# rewrite)
```

## 📋 Code Guidelines

- Use `CommunityToolkit.Mvvm` for ViewModels (`[ObservableProperty]`, `[RelayCommand]`)
- Keep **Core** free of WPF/Avalonia dependencies
- Binary-safe: never alter raw game data layouts in display-only code
- Handle errors gracefully — log to `StatusLogService`, avoid crashing the UI

## 💖 Acknowledgments

- **Sting Entertainment** — For creating DOKAPON! Sword of Fury
