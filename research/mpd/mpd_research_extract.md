# MPD Format Research Analysis

## Files Analyzed
- `CREDIT.mpd` (uncompressed reference file)
- `S_TIT00_00_decompressed.bin` (decompressed file for comparison)

## Initial Analysis Steps
1. Compare file sizes and basic structure
2. Look for common patterns and headers
3. Analyze byte patterns and potential format markers
4. Document findings and differences

## File Comparison Results

### File Sizes
- CREDIT.mpd: 208,016 bytes
- S_TIT00_00_decompressed.bin: Present in workspace

### Header Analysis

#### CREDIT.mpd Header (First 128 bytes)
```hex
00000000   43 65 6C 6C 20 20 20 20 20 20 20 20 20 20 20 20  Cell            
00000010   20 20 20 20 A0 04 00 00 60 00 00 00 60 00 60 00      ...`...`.`.
00000020   00 00 00 00 00 00 00 00 00 00 FF FF 01 00 00 00  ................
00000030   00 00 00 00 00 00 FF FF 02 00 00 00 00 00 00 00  ................
00000040   00 00 FF FF 03 00 00 00 00 00 00 00 00 00 FF FF  ................
```

#### S_TIT00_00_decompressed.bin Header (First 128 bytes)
```hex
00000000   00 00 00 00 00 00 00 00 00 00 35 55 55 55 55 55  ..........5UUUUU
00000010   55 00 00 00 00 03 00 00 00 00 00 00 00 44 00 00  U............D..
00000020   00 00 10 00 00 00 00 00 00 08 00 1C 00 00 00 00  ................
00000030   18 00 24 00 00 00 00 00 00 00 00 00 00 00 00 00  ..$.............
```

### Data Section Analysis

#### CREDIT.mpd Middle Section (Offset 1024)
```hex
00000000   00 00 FF FF 53 00 01 00 00 00 00 00 00 00 00 FF FF  ....S...........
00000010   54 00 01 00 00 00 00 00 00 00 FF FF 55 00 01 00  T...........U...
00000020   00 00 00 00 00 00 FF FF 56 00 01 00 00 00 00 00  ........V.......
00000030   00 00 FF FF 57 00 01 00 00 00 00 00 00 00 FF FF  ....W...........
```

#### CREDIT.mpd Later Section (Offset 2048)
```hex
00000000   57 58 11 36 CE 9F 5F 6C AC 12 A9 A9 31 EA B6 B6  WX.6Î_l¬.©©1ê¶¶
00000010   FE D7 CB 77 27 7F B3 74 77 C7 5F CF 5E A9 09 82  þ×Ëw'³twÇ_Ï^©.
00000020   20 08 62 76 59 70 02 DD 55 B6 F6 BB 00 B6 89 6D   .bvYp.ÝU¶ö».¶m
```

#### S_TIT00_00_decompressed.bin Data Sections
Middle section (1024) shows sparse data with power-of-2 values:
```hex
00000000   00 00 00 00 00 00 00 00 00 00 04 00 00 00 00 00  ................
00000010   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 08  ................
```

Later section (2048) shows all zeros:
```hex
00000000   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000010   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
```

## Format Structure Analysis

### CREDIT.mpd Format
1. Header Section:
   - "Cell" text identifier
   - Dimension values (96x96)
   - Initial offset (0x04A0)

2. Index Section:
   - Fixed-length records (12 bytes)
   - FF FF markers between entries
   - Sequential IDs
   - Format: `FF FF XX YY 01 00 00 00 00 00 00 00`

3. Data Section:
   - Contains binary data (possibly compressed or encoded)
   - No clear FF FF markers in data section
   - High entropy data suggesting compressed/encoded content

### S_TIT00_00_decompressed.bin Format
1. Header Section:
   - 10-byte zero padding
   - Magic number (35 55 55 55 55 55 55)
   - Size/offset values

2. Data Organization:
   - Sparse data structure
   - Power-of-2 values (4, 8, 16, 128)
   - Large zero-filled regions
   - Possible alignment or padding sections

## Key Findings

1. Different File Purposes:
   - CREDIT.mpd appears to be a resource table/database
   - S_TIT00_00 appears to be a sprite/image container

2. Structure Differences:
   - CREDIT.mpd has clear record boundaries and index structure
   - S_TIT00_00 has sparse data with power-of-2 alignment

3. Data Organization:
   - CREDIT.mpd uses fixed-length records with markers
   - S_TIT00_00 uses variable-length blocks with padding

4. Content Type:
   - CREDIT.mpd likely contains resource references or metadata
   - S_TIT00_00 likely contains actual sprite/image data

## Conclusions

1. The files serve different purposes in the game's resource system:
   - CREDIT.mpd: Resource index or metadata
   - S_TIT00_00: Actual sprite/image data container

2. The formats are not directly comparable as they serve different functions:
   - One is an index/table format
   - One is a data container format

3. Recommendations for Further Analysis:
   - Focus on understanding the relationship between these formats
   - Map out the complete resource system structure
   - Analyze how the game uses these files together

## Next Steps

1. Analyze more MPD files to confirm patterns
2. Look for references between the formats
3. Map the complete resource system structure
4. Document the relationship between index and data files

## Detailed S_TIT00_00 Format Analysis

### Header Structure (First 256 bytes)
```hex
00000000   00 00 00 00 00 00 00 00 00 00 35 55 55 55 55 55  ..........5UUUUU
00000010   55 00 00 00 00 03 00 00 00 00 00 00 00 44 00 00  U............D..
00000020   00 00 10 00 00 00 00 00 00 08 00 1C 00 00 00 00  ................
00000030   18 00 24 00 00 00 00 00 00 00 00 00 00 00 00 00  ..$.............
00000040   00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00  ................
00000050   00 00 00 00 00 00 00 00 00 00 00 00 00 00 40 00  ..............@.
```

### Header Field Analysis

1. Padding and Magic Number (0x00 - 0x0F):
   - 10 bytes of zero padding
   - Magic number: `35 55 55 55 55 55 55` (0x35 followed by six 0x55 bytes)

2. Size/Type Fields (0x10 - 0x1F):
   - `03 00 00 00` at offset 0x12 (possible format version or type)
   - `44 00 00` at offset 0x1D (possible data offset or size)

3. Dimension/Layout Information (0x20 - 0x2F):
   - `10 00 00 00` at 0x20 (possible width or block size)
   - `08 00` at 0x2A (possible height or count)
   - `1C 00` at 0x2C (possible stride or alignment)

4. Palette/Color Information (0x30 - 0x3F):
   - `18 00 24 00` at 0x30 (possible palette offset or color count)
   - Followed by zeros

5. Additional Header Fields:
   - `40 00` at offset 0x5E (possible data section marker)

### Possible Format Structure

1. File Organization:
```
[Header Section]
- 10 bytes: Zero padding
- 7 bytes: Magic number (35 55 55...)
- 4 bytes: Format version (03 00 00 00)
- 4 bytes: Data offset
[Metadata Section]
- 4 bytes: Width/Block size
- 2 bytes: Height/Count
- 2 bytes: Stride/Alignment
[Palette Section]
- Palette data (if present)
[Data Section]
- Image/Sprite data
```

2. Data Alignment:
   - Values appear to be aligned on 4-byte boundaries
   - Power-of-2 values suggest memory/cache alignment requirements
   - Possible 16-byte block structure (based on recurring patterns)

3. Potential Data Format:
   - May use indexed color (based on palette references)
   - Possible planar data organization (based on stride values)
   - Data might be organized in tiles or blocks

### Extraction Strategy

1. Header Parsing:
   ```python
   class STITHeader:
       def __init__(self, data):
           # Skip 10 bytes padding
           self.magic = data[0x0A:0x11]  # 7 bytes
           self.version = struct.unpack('<I', data[0x12:0x16])[0]
           self.data_offset = struct.unpack('<I', data[0x1D:0x21])[0]
           self.width = struct.unpack('<I', data[0x20:0x24])[0]
           self.height = struct.unpack('<H', data[0x2A:0x2C])[0]
           self.stride = struct.unpack('<H', data[0x2C:0x2E])[0]
           self.palette_offset = struct.unpack('<I', data[0x30:0x34])[0]
   ```

2. Data Extraction Steps:
   a. Validate magic number
   b. Read header fields
   c. Locate palette data (if present)
   d. Calculate data block positions
   e. Extract data using stride and alignment values
   f. Process data based on format version

3. Potential Data Processing:
   ```python
   def extract_data(data, header):
       # Calculate actual data position
       data_start = header.data_offset
       
       # Read palette if present
       if header.palette_offset:
           palette = data[header.palette_offset:header.palette_offset + 512]  # Assuming 256-color palette
           
       # Process data blocks
       block_size = header.width * header.height
       stride = header.stride if header.stride else header.width
       
       # Extract blocks
       blocks = []
       offset = data_start
       while offset < len(data):
           block = []
           for y in range(header.height):
               row_start = offset + y * stride
               row = data[row_start:row_start + header.width]
               block.extend(row)
           blocks.append(block)
           offset += stride * header.height
   ```

### Key Observations for Extraction

1. The file appears to use:
   - Fixed header structure
   - Possible palette-based color indexing
   - Block-based data organization
   - Aligned data storage

2. Critical values for extraction:
   - Data offset (0x44)
   - Block dimensions (from width/height fields)
   - Stride values for proper row alignment
   - Palette information if present

3. Potential challenges:
   - Multiple data block formats possible
   - Alignment requirements must be respected
   - Palette interpretation may vary
   - Data might be interleaved or planar

### Next Steps for Implementation

1. Create a header parser that properly interprets all fields
2. Implement palette reading and color conversion
3. Create data block extraction with proper alignment
4. Add support for different format versions
5. Implement image reconstruction from extracted data

### Validation Approach

1. Extract known values and compare with expected results
2. Check alignment and block boundaries
3. Verify color values against game visuals
4. Test with different S_TIT files to confirm format

## S_TIT00_00 Format Analysis

### Header Structure
- Magic Number: `35 55 55 55 55 55 55` at offset 0x0A
- Data Offset: 0x0044
- Palette Offset: 0x0018
- 16-color palette

### Palette Data
The file uses a 16-color palette:
1. Color 0: Black (0,0,0) - Background
2. Color 2: Dark Blue (0,0,136)
3. Color 5: Red (128,0,0)
4. Color 8: Very Dark Blue (0,0,16)
5. Color 9: Blue (0,0,56)
6. Color 12: Bright Red (192,0,0)
7. Color 13: Brown (32,8,0)
8. Other colors: Black (0,0,0)

### Image Data
- The image data appears to be sparse, with 88.2% of pixels being value 0 (background)
- Remaining pixels are distributed across various values in small percentages
- Two possible formats were attempted:
  1. Planar format (17,266 bytes PNG)
  2. Linear format (970 bytes PNG)
- The significant size difference suggests the planar format may contain more detailed image data

### Extraction Results
Successfully generated:
- `S_TIT00_00_decompressed_planar.png`
- `S_TIT00_00_decompressed_planar_raw.bin`
- `S_TIT00_00_decompressed_linear.png`
- `S_TIT00_00_decompressed_linear_raw.bin`

### Next Steps
1. Visual inspection of both planar and linear outputs to determine which format is correct
2. Analysis of the raw binary files to identify any patterns or structure
3. Refinement of extraction method based on visual results
4. Documentation of the correct format for future reference
