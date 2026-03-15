# Dokapon Explorer

Small reverse-engineering helpers for `DOKAPON! Sword of Fury`.

Current focus:

- detect debug-related evidence in the executable
- fingerprint patched vs backup executables
- inspect `Field/Map` and `Field/Chizu`
- parse `LZ77` headers and attempt decompression
- summarize map-related assets into JSON and Markdown reports
- decode `Cell` containers and export `Map` grids to `JSON/CSV/TXT`
- launch a desktop UI for atlas, map, record, and parts inspection

## Usage

```bash
python explore_dokapon.py --game-dir "D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~" --out out
```

This writes:

- `out/scan_report.json`
- `out/scan_report.md`
- `out/map_logic_report.md`

## Desktop UI

```bash
python dokapon_devtools.py --game-dir "D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~"
```

```bash
python decode_cells.py ^
  "D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\GameData\app\Field\Map\F_00_MD_00.mpd" ^
  "D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\GameData\app\Field\Map\F_00_MD_01.mpd" ^
  "D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\GameData\app\Field\Chizu\CHIZU1_00.mpd" ^
  --out out\cells ^
  --export-map ^
  --export-texture
```
