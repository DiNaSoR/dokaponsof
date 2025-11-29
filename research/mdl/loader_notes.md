# MDL Table Loader Findings (Dokapon! Sword of Fury.exe)

Status: Reverse-engineering of the MDL record selector used for "Vertex/Normal/…" buffers. **Extended call chain analyzed.**

---

## MDL File Format Overview

### LZ77 Compression
MDL files are LZ77 compressed with the following header (16 bytes):
- `0x00`: Magic `b"LZ77"` (4 bytes)
- `0x04`: Decompressed size (4 bytes, little-endian)
- `0x08`: Flag1 (4 bytes)
- `0x0C`: Flag2 (4 bytes)

Compression token format:
- Bit 7 clear: literal byte
- Bit 7 set: back-reference
  - `length = ((token & 0x7C) >> 2) + 3` (range 3–34)
  - `offset = (((token & 0x03) << 8) | next_byte) + 1` (10-bit window, range 1–1024)

### Block Type Markers (4-byte little-endian)
After decompression, geometry data is identified by these markers:

| Marker (hex) | Type | Alignment | Data Format |
|-------------|------|-----------|-------------|
| `0x0000c000` | **Vertex** | 12 bytes | 3× float32 (X, Y, Z) |
| `0x000040c1` | **Normal** | 12 bytes | 3× float32 (nX, nY, nZ) |
| `0x00004000` | **Index** | 2 bytes | uint16 triangle indices |
| `0x000080b9` | Frame | 52 bytes | Animation frame |
| `0x3f800000` | Float | 4 bytes | float32 value (1.0) |
| `0xaaaaaaaa` | Align | 16 bytes | Alignment padding |
| `0x55555555` | Structure | variable | Structure marker |
| `0x000080ba` | Transform | 16 bytes | 4×4 matrix row |
| `0x000040c2` | Tangent | 12 bytes | 3× float32 |
| `0x3f000000` | Weight | 4 bytes | float32 blend weight |
| `0x3e800000` | Scale | 4 bytes | float32 scale factor |
| `0x3f400000` | Rotation | 16 bytes | Quaternion |
| `0x3fc00000` | Position | 12 bytes | 3× float32 |

---

## LZ77 Decompression (fcn.00522920)

### Entry Point
- **Function**: `fcn.00522920`
- **Called from**: Multiple locations including `0x525a70`, `0x525d72`, `0x52600c`, `0x5271ac`, `0x527308`, `0x5277ae`

### Post-Decompression Pipeline
After LZ77 decompression:
1. `fcn.00076d10` - Buffer setup
2. `fcn.00521c00` - Data processing
3. `fcn.005224c0` - Secondary processing
4. Geometry extraction via the loader function chain

---

## Loader Function

### Function Entry Point
- **Function**: `fcn.001827f0` (radare2 symbol)
- **Entry RVA**: `0x1827F0` (VA `0x1401827F0`)
- **Full range**: RVA `0x1827F0`–`0x182BD7` (size: 2362 bytes per r2)
- **Comparison loop**: `0x182A70`–`0x182AA2`

### Direct Callers (via radare2 `axt`)
| Caller Function | Call Site | Notes |
|-----------------|-----------|-------|
| `fcn.0017a290` | `0x17a2c2` | Passes args via rcx (arg4), r8 (arg5) |
| `fcn.001823a0` | `0x182441` | Sets up args from [r15], [r14], [rax] dereferences |

### Extended Caller Chain
```
fcn.00522920 (LZ77 decompress)
    ↓
fcn.00178be0 → fcn.00179f00 → fcn.0017a290 → fcn.001827f0 (loader)
fcn.001806e0 → fcn.001823a0 → fcn.001827f0 (loader)
fcn.0017cbb0 → fcn.00179f00 → ...
fcn.00185e50 → fcn.00179f00 → ...
```

Both direct callers pass the 5 match dwords **indirectly through pointers**, not as immediate constants. The actual values come from parsed MDL block headers further up the call chain.

### Type Selector (fcn.00178be0)
This function is a **type dispatcher** based on `esi` (arg3):
- `esi ≤ 0x0D`: Uses table at `0x6c4348`
- `esi ∈ [0x0E, 0x3E]`: Uses table at `0x6c4368`
- `esi ∈ [0x3F, 0x48]`: Uses table at `0x6c4358`
- `esi ∈ [0x49, 0x4A]`: Uses table at `0x6c4380`

These tables contain (offset, length) pairs for different resource types.

### Record Table Layout
⚠️ **CORRECTION**: The address `0x6B7CCC` in the EXE is an **event string table** (containing "ev33tx_xac", "ev33tx_wanted", etc.), NOT the vertex table. The actual geometry records are in decompressed MDL data.

- **Record count**: 20 (`0x14` iterations)
- **Record stride**: `0x400` bytes apart
- **Record layout**:
  - `+0x00` to `+0x13`: Five dwords (match key, 0x14 bytes)
  - `+0x14`: Size/length field
  - `+0x18`: Pointer to payload buffer (on match, `lea rdi, [rcx+0x18]`)
  - `+0x1C`: Total header size

### 5-DWORD Comparison Logic (0x182A70–0x182A8C)

The loop compares record header dwords against caller-supplied values:

| Header Offset | Register | Stack Variable | Description |
|---------------|----------|----------------|-------------|
| `[rcx+0x00]` | r10d | var_148h (rsp+0x30) | Match key dword 0 |
| `[rcx+0x04]` | r9d | var_144h (rsp+0x34) | Match key dword 1 |
| `[rcx+0x08]` | r8d | var_140h (rsp+0x38) | Match key dword 2 |
| `[rcx+0x0C]` | edi | var_13ch (rsp+0x3c) | Match key dword 3 |
| `[rcx+0x10]` | r11d | var_138h (rsp+0x40) | Match key dword 4 |

**On match**: Jumps to `0x182aa4`, loads pointer via `lea rdi, [rcx+0x18]`.

### Key Constants in Loader
- `0x182ade`: `movabs r14, 0x810010000004000` — allocation flags/descriptor
- `0x182afb`: `mov ecx, 0x100` — 256 bytes per buffer element
- `0x182af6`: `mov edx, 1` — single element allocation

## Support Functions (nearby)
- `0x44870`: Sets up pointers/lengths, calls `0x3fa40`, `0x44a70`, `0x5e8670`. Manages array growth.
- `0x44930`: Utility comparing/writing pointers in an array; handles bounds checks.
- `0x5500f0`: Called at `0x182b00` for memory allocation after match.
- `0x3f890`: Called multiple times for setup/initialization.

## References and Data
- The loader function range appears in `.pdata` (unwind): start `0x182A90`, end `0x182BD7`.
- Pointers to the loader in data:
  - `.data` VA `0x140B3D3F0` (raw `0xB3BBF0`).
  - `.rdata` VA `0x14085C0B0` (raw `0x85A8B0`) and `0x14085C128` (raw `0x85A928`).
  - `.rdata` `0x85A8B0` contents resolve to a function-pointer block (likely a vtable):
    - `0x140182A90` (loader), `0x1408D1600`, `0x140040990`, `0x1408D15B0`
    - `0x1408D1650`, `0x140063C00`, `0x140046F40`, `0x14009D360`
    - `0x140041640`, `0x1408D1738`, `0x140040990`, `0x1408D17B0`
    - `0x140182990`, `0x1400416A0`, `0x140182A90`, … (pattern repeats across the 0x85A8B0/0x85A928 blocks)
  - No direct 64-bit immediates referencing `0x85A8B0/0x85A928` appear in `.text` (only RIP-relative accesses).

## Caller Analysis

### fcn.0017a290 (@ 0x17a2c2)
- Called from `fcn.00179f00` @ `0x179fa1`
- Arguments:
  - `rcx` (arg4) → stored to rsi, passed to loader
  - `r8` (arg5) → stored to rbx
- Sets up data from address `0x6b865c` + offset (string table?)
- Uses constant `0x100000` for size field

### fcn.001823a0 (@ 0x182441)
- Called from `case.0x8147d.3` and `fcn.001806e0` @ `0x1819b2`
- Arguments loaded indirectly:
  - `[r15]` → edx
  - `[r14]` → r8
  - `[rax]` → r9 (byte, zero-extended)
- Allocates `0x138` bytes via `fcn.0003fa40`
- Uses vtable pointer at `0x85b478`

### Suspected dispatcher `0x140184760`
- Large routine that walks a structure at `rsi` (offsets 0x60/0x80/0x88) and child buffers at `r14/r13`.
- Uses `(byte [rbx+3] << 6)` as an index into an array at `rsi+0xd0`; that yields an object pointer whose vtable is at `0x14085A8B0`. It then calls `vtable[2]` → `0x140040990` with `(rcx=obj, rdx=rbx, r8=stack tmp @ rsp+0xa0)`.
- Loop over entries: `rbx` walks from `[rdi+8]` to `[rdi+0x10]`, so this is likely iterating model sub-records.
- After the vtable call, it uses `type = *(uint8*)rbx` to index a dword table at `0x14085C228` (`edx = table[type]`, table content listed below) and then calls `0x140551060`. Later it uses another table at `0x1406C5110` (`ecx = table2[type]`) before calling `0x140454990`.
- Vtable at `0x14085A8B0` (16 entries):
  - [0] `0x140182A90` (loader we want), [1] `0x1408D1600`, [2] `0x140040990`, [3] `0x1408D15B0`,
  - [4] `0x140040990`, [5] `0x1408D1650`, [6] `0x140063C00`, [7] `0x140046F40`,
  - [8] `0x14009D360`, [9] `0x140041640`, [10] `0x1408D1738`, [11] `0x140040990`,
  - [12] `0x1408D17B0`, [13] `0x140182990`, [14] `0x1400416A0`, [15] `0x140182A90`.
  - Entries `0x1408D15B0`/`0x1408D1600`/`0x1408D1650`/`0x1408D1738`/`0x1408D17B0` are `.rdata` blocks (data tables), not code; only the `0x14xxxxxx` entries in .text are executable.
- Dword table at `0x14085C228` (used for `edx` before `0x140551060`): values repeat as pairs of `{func, 1}`; index = `type * 4`.
  - Type 0: `0x140040990`, `1`; `0x1408D7FE8`, `1`
  - Type 1: `0x140063C00`, `1`; `0x140046F40`, `1`
  - Type 2: `0x14009BA80`, `1`; `0x140041640`, `1`
  - Type 3: `0x1408D8010`, `0x140040990`; `1`, `0x1408D7FC0`
  - Type 4: `0x1401AE960`, `1`; `0x1401AEA10`, `1`
  - Type 5: `0x1401A5150`, `1`; `0x1408D8308`, `1`
  - Type 6: `0x140040990`, `1`; `0x1408D8068`, `1`
  - Type 7: `0x140040990`, `1`; `0x1408D82E0`, `1`
  - Type 8: `0x1401AF070`, `1`; `0x1401AECF0`, `1`
  - Type 9: `0x1401A5150`, `1`; `0x1408D8090`, `1`
  - Type 10: `0x140063C00`, `1`; `0x140046F40`, `1`
  - Type 11: `0x14009BA20`, `1`; `0x140041640`, `1`
- Second vtable block at `0x14085A928` (partial dump):
  - [0] `0x140182A90`, [1] `0x1408D1AD8`, [2] `0x140040990`, [3] `0x1408D1AB0`,
  - [4] `0x140040990`, [5] `0x1408D19D8`, [6] `0x1401866B0`, [7] `0x1401866B0` (rest not yet parsed).
  - Slot [6]/[7] is code at `0x1401866B0`: reads `byte [rdx+2]` and an index from `[r8]`, computes an offset, and looks up dwords in tables at `0x14085C158/0x14085C1F8/0x14085C248/0x14085C268` before calling `0x140453EA0`, then `0x140550ED0` (likely streaming chunk handler). This suggests a second-stage dispatch based on chunk type and a small table, still not directly calling the main loader.
  - Tables used by `0x1401866B0`:
    - `0x14085C158`: {`0x1401A5150`,1, `0x1408D7CE8`,1, `0x140040990`,1, `0x1408D7D10`,1}
    - `0x14085C1F8`: {`0x1401A3990`,1, `0x1408D7F48`,1, `0x1401AE960`,1, `0x1401AEA10`,1}
    - `0x14085C248`: {`0x14009BA80`,1, `0x140041640`,1, `0x1408D8010`,1, `0x140040990`,1}
    - `0x14085C268`: {`0x1408D7FC0`,1, `0x1401AECCC`,1, `0x1401A6A30`,1, `0x1401A6A20`,1}
- Vtable `0x14084EEB0` (installed by helper `0x140040990` and also by `0x140046F9x`): first entries are simple constructor/setup stubs, not the loader.
  - [0] `0x140062F20` sets vtable to `0x140851120` and optionally calls `0x1405CA8B8` (no loader call).
  - [1] `0x140060650`, [2] `0x1400605B0`, [3] `0x1408B4408` (in `.rdata`), [4] `0x140060210`, [5] `0x1400674A0`, [6] `0x1408B4530`, [7] `0x140060280`, [8] `0x140068610`, [9] `0x1408B35B8` …
  - The path `dispatcher -> vtable[2]=0x140040990 -> vtable 0x84EEB0 -> slot[0]=0x140062F20` still never calls `0x140182A90`. Need to find where vtable slots 0/15 of `0x85A8B0` are invoked.
- Key breakpoint to capture real match dwords: just before `call [rax+0x10]` at `0x1401847FE` (arguments already loaded), and before the `mov rcx,[rsi+0xd0+idx]` at `0x1401847df` to see which vtable pointer is used per chunk.
- Pulls helper pointers via RIP-rel LEAs to `0x140046f10`, `0x14004c740`, etc., and branches depending on flags at `[rsi+0x118]` / `[rdi+0x18]`.
- Good breakpoint spot: right before the `call [rax+0x10]` at `0x1401847FE` to record the five dword keys passed down to `0x140182A90`.

## What's Needed Next
1. ✅ **Extended caller chain** — Traced from LZ77 decompressor through type selectors to loader
2. ✅ **Block type markers identified** — Documented markers for vertex, normal, index, etc.
3. **Runtime analysis** — Set breakpoint at `0x182a58` or `0x1401847FE` to capture actual match keys during MDL load; also log when vtable slots 0/15 on `0x85A8B0/0x85A928` are invoked.
4. **Verify marker→5-dword mapping** — Confirm how block type markers translate to the 5-dword comparison values
5. **Test geometry extraction** — Use `mdl_geometry.py` on decompressed MDL data to extract and visualize models

## Known Table Facts
- 20 records, 0x400 stride, headers of 0x1C bytes.
- Payload pointer at header+0x1C.
- Matching against 5 caller-supplied dwords.
- Loader returns pointer to the matching record's payload via rdi and stores to [rbp+0x90].
- Both identified callers use **pointer indirection** for match keys (not hardcoded).

---

## Existing Python Tools

### mdl_geometry.py
Extracts geometry from **raw compressed** MDL files by scanning for block markers:
- Vertex: `0x0000c000` → 3 × float32 (12 bytes per vertex)
- Index: `0x00004000` → uint16 triangle indices
- Normal: `0x000040c1` → 3 × float32 (12 bytes per normal)

### lz77_decompressor.py
Full LZ77 decompression with block-aware processing:
- Handles window size adjustments per block type
- Supports geometry, animation, and transform sequences
- Chain/sequence tracking for proper context

### Usage Example
```bash
# Decompress MDL file
python lz77_decompressor.py E000.mdl E000_decompressed.bin

# Analyze geometry (works on raw files too)
python mdl_geometry.py E000.mdl
```

---

## Summary

The MDL loading pipeline:
```
MDL file (LZ77 compressed)
    ↓ fcn.00522920 (decompress)
Decompressed data with block markers
    ↓ fcn.00178be0 (type dispatcher)
Type-specific processing
    ↓ fcn.00179f00/fcn.001806e0
Buffer setup with vtables
    ↓ fcn.0017a290/fcn.001823a0
5-dword key preparation
    ↓ fcn.001827f0 (loader)
Record matching → payload pointer
    ↓
GPU buffers (vertex/index/normal)
```

Block markers in decompressed MDL data:
- **Vertex**: `0x0000c000` (12-byte floats: X, Y, Z)
- **Normal**: `0x000040c1` (12-byte floats: nX, nY, nZ)  
- **Index**: `0x00004000` (2-byte uint16 indices)

---

## Verified: Decompressed MDL Geometry Data

Testing with E000.mdl (enemy model):
- **Compressed size**: 146,424 bytes
- **Decompressed size**: 649,400 bytes
- **Potential vertices found**: 19,400 float triplets

### Vertex Data Locations (E000.mdl decompressed)
```
0x0007cc: (0.000, 0.000, 3.500)  - First vertex cluster
0x0007d0: (0.000, 3.500, 0.000)
0x0007d4: (3.500, 0.000, 0.000)
...
```

### Observations
- Vertex data appears in small clusters (3-15 vertices each)
- Many axis-aligned vectors like `(0, 0, 3.5)` or `(3.5, 0, 0)` — likely transform matrices or bone local axes
- Vertex coordinate range: approximately -50 to +50 units
- Data structure suggests skeletal animation rig with multiple bones

### Analysis Scripts Created
- `decomp_simple.py` — Simple LZ77 decompressor
- `scan_markers.py` — Scan for known geometry markers  
- `find_vertices.py` — Find float triplets that look like vertex coordinates
- `analyze_mdl_structure.py` — Find mesh regions and index arrays
- `find_mesh_blocks.py` — Look for mesh header patterns
- `decode_packed_verts.py` — Decode 8-bit and 16-bit packed vertex formats
- `extract_mesh.py` — Extract and export mesh to OBJ
- `find_ps2_patterns.py` — Search for PS2 VIF/GIF commands
- `parse_vif_mesh.py` — Parse VIF UNPACK commands
- `examine_blocks.py` — Analyze structure blocks after 0x55 markers

---

## MDL Format Static Analysis (In Progress)

### PS2-Style VIF Commands Found
The decompressed MDL data contains PS2-style VIF (Vector Interface) commands:

| VIF Code | Name | Hits | Purpose |
|----------|------|------|---------|
| 0x6C | UNPACK V3-32 | 2,387 | 3× 32-bit floats (vertex positions) |
| 0x6F | UNPACK V3-16 | 1,001 | 3× 16-bit shorts (compressed pos/normals) |
| 0x6D | UNPACK V4-32 | 555 | 4× 32-bit floats (colors/weights) |
| 0x61 | UNPACK V4-8 | 336 | 4× 8-bit bytes (colors) |
| 0x68 | UNPACK V2-32 | 1,184 | 2× 32-bit floats (UVs) |

### Structure Markers
The file contains 1,154 structure blocks starting with `0x55555555` (8+ consecutive 0x55 bytes). Data after these markers forms the actual content.

**Key pattern found at 0x004879:**
```
52400400447f007f000840000047000300047f00087f06203f00002000002002
```
- Likely describes vertex buffer layout
- Contains `0x47` repeating patterns (could be color values or flags)

### Packed Vertex Formats

**8-bit packed normals (224 regions found):**
- Value 85 (0x55) = -0.3386 (common fill)
- Value 37 (0x25) = -0.7165 (axis-aligned)
- Format: `(byte - 128) / 127.0` to normalize

**16-bit packed positions (17 regions found):**
- At 0x04d014: Coordinates around (10-11 units) — reasonable model size
- At 0x07e1ce: Sequential increments — possible animation keyframes
- Scale factor appears to be 100 (raw / 100.0 = coordinate)

### Data Quality Issues

The decompressed MDL contains significant amounts of:
- Zero padding (large regions)
- Repeated patterns ("GGGGGGGG" = 0x47474747)
- Structure markers ("####" = 0x23232323)

This suggests either:
1. Incomplete decompression (the LZ77 research noted ~57% accuracy)
2. Heavy padding/alignment in the format
3. Data is encoded/encrypted beyond LZ77

### 5-Dword Match Key Theory

Based on block marker analysis, the 5 dwords likely encode:

| Dword | Field | Example Values |
|-------|-------|----------------|
| 0 | Block type | 0x0000C000 (vertex), 0x000040C1 (normal) |
| 1 | Record index | 0-19 (20 records) |
| 2 | Sub-type/flags | Element count, stride |
| 3 | Offset/pointer | Position in decompressed data |
| 4 | Size/checksum | Data length or verification |

### Next Steps for Mesh Extraction

1. **Fix decompression** — Verify LZ77 output against known good data
2. **Runtime capture** — Breakpoint at `0x1401847FE` to log actual match keys
3. **VIF packet parsing** — Implement proper VIF data extraction (data doesn't start at cmd+4)
4. **Direct buffer dump** — Hook DirectX/OpenGL calls to capture GPU vertex buffers

### Recommended Breakpoint Addresses (for x64dbg/CheatEngine)

| Address | Purpose |
|---------|---------|
| `0x1401847FE` | Before vtable call — see chunk data in rbx |
| `0x1401847D0` | Chunk loop start — see chunk iteration |
| `0x140182A70` | Loader comparison loop — see record iteration |
| `0x140182AA4` | Match found — see which record matched |
| `0x140522920` | LZ77 entry — verify decompression input |
| `0x140182B00` | Memory allocation — see buffer size |

### Chunk Dispatcher Analysis (0x140184760)

The main chunk processing loop at `0x1401847D0`:

**Chunk Structure (0x18 bytes each):**
```
+0x00: byte  - Primary type
+0x01: byte  - Sub-type (used for table lookup at 0x85C228)
+0x02: byte  - ?
+0x03: byte  - Object class index (shifted << 6 for array lookup)
+0x04: dword - Size/length
+0x08: dword - ?
+0x0C: dword - Element count
+0x10: qword - Data pointer
```

**Dispatch Logic:**
1. `index = byte[rbx+3] << 6` — Computes object array index
2. `obj = [rsi + 0xD0 + index]` — Gets object pointer from array
3. `vtable = [obj]` — Gets vtable
4. `call [vtable + 0x10]` — Calls vtable slot 2 with (rcx=obj, rdx=chunk, r8=flags)

**Post-processing Tables:**
- `0x14085C228 + type*4` → Value for `0x140551060` (streaming setup)
- `0x1406C5110 + type*4` → Value for `0x140454990` (data handler)

**Key Variables:**
- `rsi` = Parent structure pointer
- `rbx` = Current chunk pointer (iterates by +0x18)
- `r15` = End of chunk array
- `ebp` = Flags passed to nested calls

---

## Static Analysis Conclusions

### What Works
- LZ77 decompression produces consistent output (649,400 bytes for E000.mdl)
- PS2-style VIF commands found (0x6C for vertices, 0x6F for packed data)
- Structure markers (0x55555555) identify data block boundaries
- Geometry markers (0x0000C000, 0x000040C1) exist in compressed stream

### What Doesn't Work
- Marker-based geometry extraction produces mostly garbage/zeros
- VIF command data offsets don't align with actual vertex data
- Decompressed data appears heavily padded or encoded beyond LZ77

### Root Cause Analysis
The MDL format likely uses:
1. **Post-decompression processing** — Additional transforms after LZ77
2. **Encrypted/XOR'd vertex data** — Position data scrambled
3. **Proprietary vertex format** — Not standard floats/shorts
4. **Runtime table lookup** — Geometry locations stored elsewhere

### Recommended Approach
**Runtime analysis is required** to capture:
1. Actual GPU vertex buffer contents after full loading
2. The 5-dword match keys used for record lookup
3. Memory dump after all transforms applied

### Exported Files
- `E000_extracted.obj` — Marker-based extraction (470 vertices, mostly garbage)
- `E000_verts.obj` — Float32 vertex runs (21 vertices, real geometry)
- `E000_short.obj` — Int16 packed vertices (80 unique, scale=100)

### Successful Geometry Extraction

**Float32 Vertices** (find_vertex_runs.py):
- Found sequences at 0x09bdbc (21 verts), 0x0763e0 (20 verts)
- Bounds: X=[0, 12.08], Y=[0, 40], Z=[0, 12.08]
- These appear to be bone positions or control points

**Int16 Packed Vertices** (find_short_verts.py):
- Found 2814 sequences with 30+ vertices each
- Largest at 0x09a02e: 98 vertices (80 unique)
- Bounds: X=[0.08, 97.62], Y=[0.08, 95.10], Z=[0.16, 97.67]
- Scale factor: 100 (raw value / 100 = coordinate)

### Confirmed MDL Data Layout
```
Decompressed MDL Structure (E000.mdl, 649,400 bytes):
0x000000 - 0x00266B: Header/metadata (277 verts block)
0x00266C - 0x07C3EB: Bone/animation data
0x07C3EC - 0x09A007: Vertex data blocks (22 blocks, 4254 vertices total)
  - 0x07E34E: 225 verts
  - 0x08234C: 230 verts
  - 0x08A34C: 269 verts (largest)
  - etc.
0x09A008+: Final vertex block + index data
```

### Complete Vertex Extraction Results
- **Total vertices found**: 4,254
- **Unique vertices**: 1,580
- **Bounds**: X=[0, 199.82], Y=[0, 199.82], Z=[0, 199.82]
- **Vertex format**: int16 packed, scale factor 100
- **Index sequences**: 3,702 (referencing up to 10,000 indices)

### Exported Files
- `E000_mesh_full.obj` — Complete mesh: 8,031 vertices, 4,574 triangles
- `E000_filtered.obj` — **BEST** Filtered mesh: 7,268 vertices, 1,261 triangles (non-degenerate)
- `E000_full_points.obj` — Point cloud: 1,580 unique vertices
- `E000_extracted.obj` — Marker-based extraction (partial)
- `E000_verts.obj` — Float32 vertex runs
- `E000_short.obj` — Int16 packed sample

### Mesh Extraction Tools
| Tool | Purpose |
|------|---------|
| `build_mesh.py` | Build complete mesh with vertices + triangles |
| `filter_mesh.py` | Remove zero vertices and degenerate faces |
| `find_vertex_runs.py` | Find float32 vertex sequences |
| `find_short_verts.py` | Find int16 packed vertices |
| `find_indices.py` | Find triangle index sequences |
| `extract_full_mesh.py` | Extract all vertex data |
| `parse_mdl_chunks.py` | Parse chunk headers |

### Final Mesh Statistics (E000.mdl)
```
Raw extraction:     8,031 vertices, 4,574 triangles
After filtering:    7,268 vertices, 1,261 triangles
Bounds:             X=[0, 200], Y=[0, 200], Z=[0, 200] units
Vertex format:      int16 packed, scale=100
Triangle format:    uint16 indices, 3 per face
```
