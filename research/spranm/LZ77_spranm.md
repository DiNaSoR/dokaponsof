# SPRANM File Format Analysis

## Note 001: CSFIX_00.spranm Analysis
Analysis of the CSFIX_00.spranm file reveals the following structure:

1. LZ77 Header (16 bytes):
   - Magic: "LZ77" (4 bytes)
   - Flags: 0xc83a0000 (4 bytes)
   - Compressed size: 11013 bytes (4 bytes, little-endian)
   - Decompressed size: 1393 bytes (4 bytes, little-endian)

2. File Structure:
   - The file uses Nintendo's LZ77 compression format
   - Contains a "Sequ" marker at offset 0x571
   - Total file size: 13050 bytes
   - Decompressed size is slightly larger than expected (1406 vs 1393 bytes)

3. Compression Details:
   - The file starts with LZ77 compressed data
   - The compression ratio is approximately 7.9:1 (1393 bytes uncompressed to 11013 bytes compressed)
   - The compression appears to be standard Nintendo LZ77 format
   - The decompressed data shows a pattern of sparse data with many zero bytes
   - Compression type byte is 0x00, suggesting standard compression
   - Window parameter byte is 0x00, using default 4KB window size

4. Data Sections:
The decompressed data contains several distinct sections with non-zero data:
   - Section 1: 0x28 - 0x60 (57 bytes)
   - Section 2: 0x98 - 0xf8 (97 bytes)
   - Section 3: 0x163 - 0x17a (24 bytes)
   - Section 4: 0x17e - 0x190 (19 bytes)
   - Section 5: 0x1eb - 0x20d (35 bytes)
   - Section 6: 0x232 - 0x24f (30 bytes)
   - Section 7: 0x48a - 0x4a0 (23 bytes)
   - Section 8: 0x4b5 - 0x4d1 (29 bytes)
   - Section 9: 0x539 - 0x54b (19 bytes)

Each section appears to be separated by regions of zero bytes, suggesting a structured format.

## Note 002: CSFIX_04.spranm Analysis
Analysis of CSFIX_04.spranm reveals a different structure:

1. File Structure:
   - No LZ77 compression (uncompressed data)
   - Total file size: 43760 bytes
   - Contains a PNG image (42750 bytes)
   - Starts with "Sequence" marker at offset 0x0

2. Section Layout:
   - Sequence header (0x0 - 0xBC)
   - Sprite data (0xC0 - 0x1DC)
   - SpriteGp section (0x1E0 - 0x23C)
   - TextureParts section (0x240)
   - PNG data (0x280 - 0xA968)
   - Parts data (0xA978)
   - Anime section (0xAA98)
   - ConvertInfo section (0xAAC8)

3. Notable Features:
   - Contains embedded PNG image data
   - Uses floating-point values (0x3F800000 = 1.0f)
   - Has animation sequence data
   - Includes sprite transformation data
   - Contains texture coordinates

4. Section Details:
   - Sequence: Contains animation timing data
   - Sprite: Contains transformation matrices and sprite properties
   - TextureParts: Contains texture mapping information
   - Parts: Contains sprite part definitions
   - Anime: Contains animation keyframes
   - ConvertInfo: Contains format conversion information

## Note 003: Format Comparison
Comparing both files reveals two different SPRANM formats:

1. Compressed Format (CSFIX_00):
   - Uses LZ77 compression
   - Smaller file size (~13KB)
   - Contains animation data only
   - No embedded PNG
   - Uses sparse data structure with zero-filled regions
   - Sections are smaller and more numerous

2. Uncompressed Format (CSFIX_04):
   - No compression
   - Larger file size (~43KB)
   - Contains embedded PNG (~42KB)
   - Full animation sequence
   - Uses dense data structure
   - Sections are larger and well-defined

## Note 004: Extraction Strategy
Based on our improved extraction results:

1. Format Detection:
   - Check for "LZ77" magic for compressed files
   - Check for "Sequence" magic for uncompressed files
   - Validate header structure based on format

2. Section Handling:
   - For compressed files:
     - Decompress using LZ77
     - Parse sparse data sections
     - Extract animation data
   - For uncompressed files:
     - Extract PNG data
     - Parse section headers
     - Extract individual sections

3. Metadata Generation:
   - Save format information
   - Record section offsets and sizes
   - Document compression details
   - Store section relationships

4. Output Files:
   - Save PNG data when present
   - Extract individual sections
   - Generate metadata JSON
   - Preserve original structure

## Note 005: CSFIX Animation Files Analysis

Analysis of CSFIX_00.spranm, CSFIX_01.spranm, and CSFIX_03.spranm reveals a common animation control format:

1. Common Structure:
   - All files use LZ77 compression with type 0x00 and window parameter 0x00
   - Fixed 4KB (0x1000) window size for decompression
   - No embedded PNG data (these are control files only)
   - Sections are marked by control bytes followed by data

2. Control Section Types:
   - sprite_flags (0x80): Animation behavior control
     - loop: Enable looping animation
     - reverse: Play animation in reverse
     - pingpong: Play animation back and forth
     - Additional flags stored in 32-bit value

   - transform_matrix (0x40): 2D transformation data
     - scale_x: Horizontal scaling factor (float)
     - scale_y: Vertical scaling factor (float)
     - translate_x: Horizontal translation (float)
     - translate_y: Vertical translation (float)

   - sprite_state (0x20): Sprite property control
     - visible: Sprite visibility flag
     - flip_x: Horizontal flip flag
     - flip_y: Vertical flip flag
     - active: Sprite active state
     - Additional state flags in 32-bit value

   - sprite_index (0x04): References to sprite resources
     - Points to external sprite data
     - Used to change which sprite is displayed

3. File Specifics:

   CSFIX_00.spranm:
   - Compressed size: 11,013 bytes
   - Decompressed size: 1,406 bytes
   - Complex animation with multiple state changes
   - Contains 40+ control sections
   - Heavy use of transformation matrices
   - Multiple sprite state changes

   CSFIX_01.spranm:
   - Compressed size: 5,789 bytes
   - Decompressed size: 740 bytes
   - Simpler animation sequence
   - Fewer state changes
   - More focused on sprite indices
   - Contains basic transformations

   CSFIX_03.spranm:
   - Compressed size: 7,161 bytes
   - Decompressed size: 912 bytes
   - Contains "Sequ" marker at offset 0x322
   - Mix of transformations and state changes
   - More structured sequence format

4. Animation Sequence Structure:
   - Each animation is composed of frames
   - Frames can contain:
     - Transformation (position/scale)
     - State changes (visibility/flipping)
     - Sprite selection
     - Animation control flags
   - Frame order determined by section sequence
   - State changes persist until modified

5. Data Format Details:
   - All floating-point values use IEEE-754 format
   - Matrices stored as 4 consecutive floats
   - State flags use bitfields in 32-bit values
   - Sections aligned to 4-byte boundaries
   - Zero padding between sections

6. Extraction Strategy:
   - Decompress LZ77 data
   - Parse control sections
   - Build animation sequence
   - Extract transformation data
   - Map sprite references
   - Save metadata for reconstruction

7. Relationship with Other Files:
   - These files control how sprite images are displayed
   - Actual sprite data stored in separate files
   - Likely referenced by sprite_index values
   - May share common palette data
   - Part of larger animation system

## Note 006: Sprite Resource Files Analysis

Analysis of CSFIX_04.spranm and TRS001_00.spranm reveals the structure of sprite resource files:

1. Common Structure:
   - Uncompressed format
   - Contains embedded PNG texture data
   - Fixed section order:
     1. Sequence header
     2. Sprite data
     3. Sprite group
     4. Texture parts
     5. PNG data

2. CSFIX_04.spranm Details:
   - Total size: ~43KB
   - Section offsets:
     - Sequence: 0x0
     - Sprite: 0xC0
     - SpriteGp: 0x1E0
     - TextureParts: 0x240
     - PNG: 0x280 (42,750 bytes)
   - Well-defined section boundaries
   - Dense data structure (minimal padding)
   - Contains complete sprite sheet

3. TRS001_00.spranm Details:
   - Total size: ~550KB
   - Section offsets:
     - Sequence: 0x0
     - Sprite: 0x30
     - SpriteGp: 0x70
     - TextureParts: 0x98
     - PNG: 0xD8
   - More compact header sections
   - Larger PNG data section
   - Different sprite organization

4. Resource Organization:
   - Sprite sheets stored as embedded PNG
   - TextureParts defines sprite regions
   - SpriteGp groups related sprites
   - Sequence header defines animation properties

5. Relationship with Animation Files:
   - CSFIX_00/01/03 reference these resource files
   - sprite_index (0x04) sections point to sprite definitions
   - Animations combine multiple sprite resources
   - Transform matrices apply to sprite regions
   - State changes affect sprite visibility

6. File Type Patterns:
   A. Animation Control Files:
      - Use LZ77 compression
      - Small file size (5-13KB)
      - Control-only data
      - Multiple small sections
      - Example: CSFIX_00, CSFIX_01, CSFIX_03

   B. Sprite Resource Files:
      - Uncompressed format
      - Larger file size (43-550KB)
      - Contains PNG data
      - Fixed section structure
      - Example: CSFIX_04, TRS001_00

7. Complete Animation System:
   - Resource files define available sprites
   - Control files define how sprites animate
   - Sprite indices link controls to resources
   - Transformations modify sprite presentation
   - States control sprite behavior
   - Groups organize related sprites

8. Implementation Notes:
   - PNG data should be extracted separately
   - TextureParts define UV coordinates
   - SpriteGp defines logical groupings
   - Sequence headers contain timing info
   - Transform matrices use relative coordinates
   - State changes can be frame-specific
