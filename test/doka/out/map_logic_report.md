# Dokapon Map Logic Findings

## Confirmed Structures
- `Cell` contains a 12-byte record table followed by named chunks such as `TextureParts`, `Palette`, `Map`, and `ConvertInfo`.
- `Map` chunk payload starts with `width` and `height` as `u16`, followed by `width * height` values of `u32`.
- `Map` values usually reference record indices through `low16`; `high16` behaves like an extra flag/variant field in some files.
- `TextureParts` contains a nested texture atlas plus a `Parts` table of 32-byte entries with UV rectangles.

## Dimensions
### MD_00
- `40x38`: `15`
- `128x128`: `4`
- `32x28`: `2`
- `21x28`: `1`
- `23x20`: `1`
- `23x60`: `1`
- `25x44`: `1`
- `27x40`: `1`
- `30x28`: `1`
- `31x28`: `1`
- `32x29`: `1`
- `39x40`: `1`
- `40x28`: `1`
- `40x68`: `1`
- `42x38`: `1`
- `48x48`: `1`
### MD_01
- `14x10`: `9`
- `15x12`: `8`
- `16x12`: `7`
- `13x10`: `5`
- `5x4`: `3`
- `10x8`: `1`
- `18x14`: `1`
### CHIZU
- `20x20`: `5`
- `10x8`: `1`

## Inference
- `record.value_a_low16` is very likely a direct `Part` index into `TextureParts`. Evidence: `Parts.count` matches the valid low16 range used by records in tested files, and the first records map cleanly to the first atlas tiles.
- `MD_01` is likely a compact logic/template layer. Evidence: its map grids are small, direct record references are common, and many files have uniform record flags such as `value_b=0x10`, `value_b=0x30`, or `value_c=0x00010000/0x00020000/0x00030000`.
- `MD_00` is likely the larger terrain/placement layer. Evidence: grids are much larger, every tested file keeps record refs in `low16`, and many cells carry non-zero `high16` flags.
- `CHIZU` is likely a world-map index layer. Evidence: it uses a small `20x20` or `10x8` grid and record IDs form structured blocks with repeated border sentinels.
- Placeholder or degenerate `MD_01` files exist. Evidence: some maps reference only a single record even when the file defines more records.

## Flagged MD_00
- `GameData\app\Field\Map\F_00_MD_00.mpd high16_nonzero=2080 a_high16=186`
- `GameData\app\Field\Map\F_01_MD_00.mpd high16_nonzero=2080 a_high16=186`
- `GameData\app\Field\Map\F_02_MD_00.mpd high16_nonzero=2080 a_high16=186`
- `GameData\app\Field\Map\F_03_MD_00.mpd high16_nonzero=2080 a_high16=186`
- `GameData\app\Field\Map\F_04_MD_00.mpd high16_nonzero=148 a_high16=0`
- `GameData\app\Field\Map\F_05_MD_00.mpd high16_nonzero=106 a_high16=62`
- `GameData\app\Field\Map\F_06_MD_00.mpd high16_nonzero=50 a_high16=67`
- `GameData\app\Field\Map\F_07_MD_00.mpd high16_nonzero=208 a_high16=0`
- `GameData\app\Field\Map\F_08_MD_00.mpd high16_nonzero=122 a_high16=42`
- `GameData\app\Field\Map\F_09_MD_00.mpd high16_nonzero=78 a_high16=30`
- `GameData\app\Field\Map\F_10_MD_00.mpd high16_nonzero=38 a_high16=16`
- `GameData\app\Field\Map\F_11_MD_00.mpd high16_nonzero=152 a_high16=51`
- `GameData\app\Field\Map\F_12_MD_00.mpd high16_nonzero=107 a_high16=38`
- `GameData\app\Field\Map\F_13_MD_00.mpd high16_nonzero=35 a_high16=21`
- `GameData\app\Field\Map\F_14_MD_00.mpd high16_nonzero=79 a_high16=39`
- `GameData\app\Field\Map\F_15_MD_00.mpd high16_nonzero=153 a_high16=0`
- `GameData\app\Field\Map\F_16_MD_00.mpd high16_nonzero=159 a_high16=0`
- `GameData\app\Field\Map\F_17_MD_00.mpd high16_nonzero=181 a_high16=0`
- `GameData\app\Field\Map\F_18_MD_00.mpd high16_nonzero=54 a_high16=0`
- `GameData\app\Field\Map\F_19_MD_00.mpd high16_nonzero=299 a_high16=25`

## Flagged MD_01
- `GameData\app\Field\Map\F_00_MD_01.mpd value_b_nonzero=9 value_c_nondefault=3`
- `GameData\app\Field\Map\F_01_MD_01.mpd value_b_nonzero=9 value_c_nondefault=3`
- `GameData\app\Field\Map\F_02_MD_01.mpd value_b_nonzero=8 value_c_nondefault=12`
- `GameData\app\Field\Map\F_03_MD_01.mpd value_b_nonzero=9 value_c_nondefault=12`
- `GameData\app\Field\Map\F_04_MD_01.mpd value_b_nonzero=0 value_c_nondefault=9`
- `GameData\app\Field\Map\F_05_MD_01.mpd value_b_nonzero=0 value_c_nondefault=4`
- `GameData\app\Field\Map\F_06_MD_01.mpd value_b_nonzero=24 value_c_nondefault=33`
- `GameData\app\Field\Map\F_07_MD_01.mpd value_b_nonzero=0 value_c_nondefault=22`
- `GameData\app\Field\Map\F_08_MD_01.mpd value_b_nonzero=0 value_c_nondefault=10`
- `GameData\app\Field\Map\F_09_MD_01.mpd value_b_nonzero=0 value_c_nondefault=10`
- `GameData\app\Field\Map\F_10_MD_01.mpd value_b_nonzero=0 value_c_nondefault=10`
- `GameData\app\Field\Map\F_11_MD_01.mpd value_b_nonzero=0 value_c_nondefault=17`
- `GameData\app\Field\Map\F_12_MD_01.mpd value_b_nonzero=0 value_c_nondefault=17`
- `GameData\app\Field\Map\F_13_MD_01.mpd value_b_nonzero=0 value_c_nondefault=1`
- `GameData\app\Field\Map\F_14_MD_01.mpd value_b_nonzero=0 value_c_nondefault=1`
- `GameData\app\Field\Map\F_15_MD_01.mpd value_b_nonzero=0 value_c_nondefault=1`
- `GameData\app\Field\Map\F_16_MD_01.mpd value_b_nonzero=0 value_c_nondefault=9`
- `GameData\app\Field\Map\F_17_MD_01.mpd value_b_nonzero=0 value_c_nondefault=9`
- `GameData\app\Field\Map\F_18_MD_01.mpd value_b_nonzero=0 value_c_nondefault=9`
- `GameData\app\Field\Map\F_19_MD_01.mpd value_b_nonzero=16 value_c_nondefault=0`

## Placeholder MD_01
- `GameData\app\Field\Map\F_13_MD_01.mpd`
- `GameData\app\Field\Map\F_14_MD_01.mpd`
- `GameData\app\Field\Map\F_15_MD_01.mpd`
- `GameData\app\Field\Map\F_24_MD_01.mpd`
- `GameData\app\Field\Map\F_25_MD_01.mpd`

## Next Reverse-Engineering Targets
- Name the semantics of record `value_b` and `value_c` by comparing flagged files in-game.
- Decode `TextureParts` entries to map record indices to actual tiles or atlas pages.
- Correlate `MD_01` record refs with `RD_*.mdl` and `RD_*.spranm` to identify map objects and events.
- Compare localized `CHIZU` and `Map` variants to separate logic from presentation.