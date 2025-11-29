# Repository Guidelines

## Project Structure & Module Organization
- `main.py` launches the PyQt6 GUI; `build_exe.py` packages a single-file build.
- `core/` holds extraction logic: `dokapon_extract.py` (PNG extract/repack, LZ77), `mdl_parser.py`/`mdl_handler.py` (MDL mesh parsing), `text_extract_repack.py`, and `voice_pck_extractor.py`. Keep new asset helpers here and split heavy logic into testable functions.
- `gui/` contains the interface: `main_window.py`, `tabs/` (Asset/Text/Voice/About views), `widgets/` (shared UI pieces like `file_browser.py`, `file_tree.py`, `viewer_3d.py`, `worker.py`).
- `resources/` stores packaged assets (icon, bgm). Future automated tests should live under `tests/` mirroring module paths.

## Build, Test, and Development Commands
- `python -m venv .venv && .venv\Scripts\activate` then `pip install -r requirements.txt` to set up dependencies.
- `python main.py` runs the GUI for local smoke checks.
- `python build_exe.py` builds `build/DokaponSoFTools.exe` via PyInstaller.
- `python core\dokapon_extract.py -i <input_dir> -o <output_dir> -t all` runs the CLI extractor; update examples when flags change.

## Coding Style & Naming Conventions
- Python 3 with 4-space indentation and type hints (see `core/` dataclasses).
- Use `snake_case` for functions/locals, `PascalCase` for classes/widgets, and UPPER_SNAKE_CASE for constants (e.g., `gui/styles.py`).
- Keep long operations off the GUI thread (use `gui/widgets/worker.py`); prefer small, pure helpers in `core/` and thin UI glue.
- Format with `black` and lint with `pylint` when available; avoid trailing whitespace.

## Testing Guidelines
- No automated suite yet; add `pytest`-style tests under `tests/` for new parsing logic.
- Manual verification: run `python main.py`, exercise Asset/Text/Voice tabs, confirm status updates and previews render.
- For extractor changes, run sample CLI commands against known assets and check output structure/logs.

## Commit & Pull Request Guidelines
- Commits use short, present-tense imperatives (e.g., "Enhance MDL preview functionality"); keep each commit focused.
- PRs should include a concise summary, before/after notes or screenshots for UI changes, steps to reproduce fixes, and any sample assets used for testing.
- Link issues when available and call out follow-up TODOs explicitly.
