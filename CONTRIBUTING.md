# Contributing to DOKAPON! Sword of Fury Tools

Thank you for your interest in contributing! Here's how you can help.

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

## 🏗️ Development Setup

```bash
git clone https://github.com/DiNaSoR/dokaponsof.git
cd dokaponsof/csharp
dotnet build
```

### Project Structure

```
csharp/
├── src/
│   ├── DokaponSoFTools.Core/     # Format parsers, renderers, tools
│   │   ├── Formats/              # GameText, PckArchive, SpranmDocument, etc.
│   │   ├── Imaging/              # MapRenderer, SpranmRenderer, AtlasRenderer
│   │   ├── Compression/          # LZ77 variants
│   │   └── Tools/                # AssetExtractor, VideoConverter
│   ├── DokaponSoFTools.App/      # WPF application
│   │   ├── ViewModels/           # MVVM ViewModels
│   │   ├── Views/                # XAML views
│   │   ├── Services/             # Settings, dialogs, status log
│   │   └── Themes/               # Dark theme resources
│   └── DokaponSoFTools.Tests/    # Unit tests
└── tools/                        # RE analysis scripts (Python)
```

## 📋 Code Guidelines

- Use `CommunityToolkit.Mvvm` for ViewModels (`[ObservableProperty]`, `[RelayCommand]`)
- Keep Core library free of WPF dependencies
- Binary-safe: never modify raw game data formats in display code
- Handle errors gracefully — log to StatusLogService, don't crash

## 📄 License

By contributing, you agree that your contributions will be licensed under the GNU GPL v3.0.
