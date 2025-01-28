"""
Dokapon Extract Tool
A versatile tool for extracting and repacking various game assets from DOKAPON! Sword of Fury.

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: GNU General Public License v3.0 (GPL-3.0)

Features:
- Extract embedded PNG images from multiple game file formats
- Handle LZ77 compression with improved validation and error handling
- Preserve file metadata and compression info for repacking
- Support for .tex, .mpd, .spranm, and .fnt files
- Maintain directory structure during batch processing
- Deep analysis of file structure and compression patterns
- Advanced sprite animation sequence parsing
- Repack modified PNG files back into original format
- Detailed section analysis for SPRANM files
- Hex dump visualization for binary analysis

Usage: python dokapon_extract.py [-h] [-i INPUT] [-o OUTPUT] [-t {tex,mpd,spranm,fnt,all}] [-v] [--repack] [--analyze]

Arguments:
  -h, --help            Show this help message and exit
  -i, --input          Input file or directory (default: current directory)
  -o, --output         Output directory (default: ./output)
  -t, --type           File type to process: tex, mpd, spranm, fnt, all (default: all)
  -v, --verbose        Show detailed processing information
  --repack            Repack a modified PNG using JSON metadata
  --analyze           Analyze file structure without extracting

Examples:
  # Extract all supported files from current directory
  python dokapon_extract.py

  # Extract specific file type with verbose output
  python dokapon_extract.py -i game/data -o extracted -t tex -v

  # Analyze file structure with hex dump
  python dokapon_extract.py -i file.spranm --analyze

  # Repack modified PNG with metadata preservation
  python dokapon_extract.py --repack

File Format Support:
- .tex: Texture files with optional LZ77 compression
- .mpd: Multi-part data files with embedded PNG images
- .spranm: Sprite animation files with sequence data
- .fnt: Font data files with optional compression

Note: This tool includes enhanced error handling, validation checks,
and detailed analysis capabilities for understanding file structures.
"""

import os
import struct
import argparse
from dataclasses import dataclass
from typing import Optional
import json
from PIL import Image

@dataclass
class SpriteHeader:
    size: int
    width: int
    height: int
    bpp: int  # bits per pixel
    palette_offset: int

@dataclass
class MPDHeader:
    """Header structure for .mpd files"""
    magic: str          # "Cell" magic string
    data_size: int      # Size of data section
    width: int          # Image width
    height: int         # Image height
    cell_width: int     # Width of each cell
    cell_height: int    # Height of each cell

def decompress_lz77(data: bytes) -> Optional[bytes]:
    """Decompress Nintendo-style LZ77 data with improved offset handling and validation."""
    if not data.startswith(b'LZ77'):
        return None
    
    # Parse full header (16 bytes)
    flags = struct.unpack('<I', data[4:8])[0]
    compressed_size = struct.unpack('<I', data[8:12])[0]
    decompressed_size = struct.unpack('<I', data[12:16])[0]
    
    # Parse flags
    compression_type = (flags >> 24) & 0xFF  # High byte
    window_param = (flags >> 16) & 0xFF      # Second byte
    
    print(f"\nLZ77 Header Analysis:")
    print(f"  Compression type: 0x{compression_type:02x}")
    print(f"  Window parameter: 0x{window_param:02x}")
    print(f"  Compressed size: {compressed_size} bytes")
    print(f"  Decompressed size: {decompressed_size} bytes")
    
    # Validate sizes
    if decompressed_size > 10_000_000:  # 10MB sanity check
        print(f"Warning: Suspicious decompressed size: {decompressed_size}")
        return None
        
    if compressed_size > len(data):
        print(f"Error: Compressed size {compressed_size} larger than data size {len(data)}")
        return None
    
    # Fixed window size of 4KB for SPRANM format
    window_size = 0x1000
    
    result = bytearray()
    pos = 16  # Start after header
    window = bytearray(window_size)
    window_pos = 0
    
    # Track section boundaries and data
    sections = []
    section_start = -1
    last_nonzero = -1
    current_section_data = bytearray()

    try:
        while pos < len(data) and len(result) < decompressed_size:
            flag = data[pos]
            pos += 1

            for bit in range(8):
                if pos >= len(data) or len(result) >= decompressed_size:
                    break

                if flag & (0x80 >> bit):
                    # LZ77 backreference
                    if pos + 1 >= len(data):
                        break
                        
                    info = (data[pos] << 8) | data[pos + 1]
                    pos += 2

                    length = ((info >> 12) & 0xF) + 3
                    offset = (info & 0xFFF) + 1

                    # Validate offset
                    if offset > window_size:
                        print(f"Warning: Invalid offset {offset} at position {pos-2}")
                        offset = offset % window_size
                    
                    # Handle overlapping copies correctly
                    for i in range(length):
                        if len(result) - offset < 0:
                            # Invalid offset - treat as literal
                            byte = 0
                        else:
                            byte = result[len(result) - offset]
                            
                        result.append(byte)
                        window[window_pos % window_size] = byte
                        window_pos += 1
                        
                        # Track non-zero bytes for section analysis
                        if byte != 0:
                            if section_start == -1:
                                section_start = len(result) - 1
                            last_nonzero = len(result) - 1
                            current_section_data.append(byte)
                        elif section_start != -1 and len(result) - last_nonzero > 16:
                            # End of section
                            if len(current_section_data) > 8:  # Minimum section size
                                sections.append({
                                    'start': section_start,
                                    'end': last_nonzero,
                                    'size': last_nonzero - section_start + 1,
                                    'data': bytes(current_section_data)
                                })
                            section_start = -1
                            current_section_data = bytearray()
                else:
                    # Literal byte
                    if pos >= len(data):
                        break
                    byte = data[pos]
                    result.append(byte)
                    window[window_pos % window_size] = byte
                    window_pos += 1
                    pos += 1
                    
                    # Track non-zero bytes
                    if byte != 0:
                        if section_start == -1:
                            section_start = len(result) - 1
                        last_nonzero = len(result) - 1
                        current_section_data.append(byte)
                    elif section_start != -1 and len(result) - last_nonzero > 16:
                        # End of section
                        if len(current_section_data) > 8:  # Minimum section size
                            sections.append({
                                'start': section_start,
                                'end': last_nonzero,
                                'size': last_nonzero - section_start + 1,
                                'data': bytes(current_section_data)
                            })
                        section_start = -1
                        current_section_data = bytearray()

        # Add final section if any
        if section_start != -1 and len(current_section_data) > 8:
            sections.append({
                'start': section_start,
                'end': last_nonzero,
                'size': last_nonzero - section_start + 1,
                'data': bytes(current_section_data)
            })

        # Validate final size
        if len(result) != decompressed_size:
            print(f"Warning: Size mismatch - got {len(result)}, expected {decompressed_size}")
            
        # Look for known markers in result
        for marker in [b'Sequ', b'Palett', b'ConvertInfo']:
            pos = result.find(marker)
            if pos >= 0:
                print(f"Found {marker.decode()} marker at offset 0x{pos:x}")
                
        # Analyze sections
        if sections:
            print("\nData sections found:")
            for section in sections:
                print(f"  0x{section['start']:x} - 0x{section['end']:x} ({section['size']} bytes)")
                # Show first 16 bytes of section
                print(f"  First bytes: {section['data'][:16].hex()}")
                # Try to identify section type
                if section['data'].startswith(b'Sequ'):
                    print("  Type: Sequence header")
                elif section['data'].startswith(b'Palett'):
                    print("  Type: Palette data")
                elif section['data'].startswith(b'ConvertInfo'):
                    print("  Type: Convert info")
                elif any(b for b in section['data'][:4] if b in [0x40, 0x80, 0x04, 0x20]):
                    print("  Type: Control data")

        return bytes(result) if len(result) > 0 else None

    except Exception as e:
        print(f"Decompression error: {str(e)}")
        return None

def save_metadata(output_path: str, png_start: int, png_data: bytes, original_file: str = None, extra_info: dict = None) -> None:
    """Save metadata for any extracted PNG file."""
    # Get original file extension from the input file, not the output PNG
    if original_file:
        original_ext = os.path.splitext(original_file)[1].lower()
    else:
        # If no original file provided, try to guess from output path
        original_ext = os.path.splitext(output_path)[1].lower()
        # Remove .png from the extension if it's there
        if original_ext == '.png':
            # Try to determine original extension from the base name
            base = os.path.splitext(output_path)[0]
            if base.endswith('.tex'):
                original_ext = '.tex'
            elif base.endswith('.mpd'):
                original_ext = '.mpd'
            elif base.endswith('.spranm'):
                original_ext = '.spranm'
    
    meta_info = {
        "original_file": original_file or os.path.abspath(output_path),
        "original_extension": original_ext,
        "offset": png_start,
        "length": len(png_data)
    }
    
    # Add any extra information (like MPD header)
    if extra_info:
        meta_info.update(extra_info)
        
    json_path = output_path + ".json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=4)
    print(f"Metadata saved to: {os.path.basename(json_path)}")

def parse_transform_matrix(data: bytes) -> dict:
    """Parse a transformation matrix section (0x40)."""
    if len(data) < 20:  # Minimum size for a transform matrix
        return None
        
    try:
        # First 4 bytes are the control bytes (0x40, 0x00, etc)
        matrix_data = data[4:20]  # Next 16 bytes contain 4 float values
        scale_x, scale_y, trans_x, trans_y = struct.unpack('<4f', matrix_data)
        
        return {
            'scale': {'x': scale_x, 'y': scale_y},
            'translation': {'x': trans_x, 'y': trans_y}
        }
    except:
        return None

def parse_sprite_state(data: bytes) -> dict:
    """Parse a sprite state section (0x20)."""
    if len(data) < 8:  # Minimum size for a sprite state
        return None
        
    try:
        # First 4 bytes are the control bytes (0x20, 0x00, etc)
        state_data = data[4:8]  # Next 4 bytes contain state flags
        flags = int.from_bytes(state_data, 'little')
        
        return {
            'visible': bool(flags & 0x1),
            'flip_x': bool(flags & 0x2),
            'flip_y': bool(flags & 0x4),
            'active': bool(flags & 0x8),
            'flags': hex(flags)
        }
    except:
        return None

def parse_sprite_flags(data: bytes) -> dict:
    """Parse sprite flags section (0x80)."""
    if len(data) < 8:
        return None
        
    try:
        # First 4 bytes are control bytes (0x80, 0x00, etc)
        flag_data = data[4:8]  # Next 4 bytes contain flag values
        flags = int.from_bytes(flag_data, 'little')
        
        return {
            'loop': bool(flags & 0x1),
            'reverse': bool(flags & 0x2),
            'pingpong': bool(flags & 0x4),
            'flags': hex(flags)
        }
    except:
        return None

def analyze_compressed_sections(data: bytes) -> list[dict]:
    """Analyze sections in compressed SPRANM data to identify their purpose."""
    sections = []
    current_pos = 0
    
    # Known section types and their markers
    SECTION_TYPES = {
        b'Sequ': 'sequence_header',
        b'Palett': 'palette_data',
        b'ConvertInfo': 'convert_info',
        b'Sprite': 'sprite_data',
        b'SpriteGp': 'sprite_group',
        b'TextureParts': 'texture_parts',
        b'Parts': 'parts_data',
        b'Anime': 'animation_data'
    }
    
    # Control byte patterns
    CONTROL_PATTERNS = {
        bytes([0x40, 0x00]): 'transform_matrix',
        bytes([0x80, 0x00]): 'sprite_flags',
        bytes([0x04, 0x00]): 'sprite_index',
        bytes([0x20, 0x00]): 'sprite_state',
        bytes([0x3F, 0x80]): 'float_value'  # 1.0f in IEEE-754
    }
    
    # Find all potential section starts
    while current_pos < len(data):
        # Look for section markers
        found_marker = False
        for marker, section_type in SECTION_TYPES.items():
            if data[current_pos:].startswith(marker):
                # Found a known section
                section_start = current_pos
                # Look for next section marker or end of data
                next_pos = len(data)
                for next_marker in SECTION_TYPES.keys():
                    pos = data[current_pos + len(marker):].find(next_marker)
                    if pos != -1:
                        next_pos = min(next_pos, current_pos + len(marker) + pos)
                
                section_data = data[section_start:next_pos]
                section_info = {
                    'offset': hex(section_start),
                    'size': len(section_data),
                    'type': section_type,
                    'raw_data': section_data.hex(),
                    'has_png': b'\x89PNG' in section_data
                }
                
                # Parse sequence header if found
                if section_type == 'sequence_header':
                    try:
                        section_info['frame_count'] = struct.unpack('<I', section_data[4:8])[0]
                        section_info['flags'] = hex(struct.unpack('<I', section_data[8:12])[0])
                    except:
                        pass
                
                sections.append(section_info)
                current_pos = next_pos
                found_marker = True
                break
        
        if not found_marker:
            # Look for control patterns
            found_pattern = False
            for pattern, pattern_type in CONTROL_PATTERNS.items():
                if data[current_pos:].startswith(pattern):
                    # Found a control section
                    section_start = current_pos
                    # Look for next non-zero byte after some zeros
                    next_pos = current_pos + 2
                    while next_pos < len(data) and (data[next_pos] == 0 or next_pos - section_start < 16):
                        next_pos += 1
                    
                    section_data = data[section_start:next_pos]
                    if len(section_data) > 4:  # Minimum control section size
                        section_info = {
                            'offset': hex(section_start),
                            'size': len(section_data),
                            'type': pattern_type,
                            'raw_data': section_data.hex(),
                            'has_png': False
                        }
                        
                        # Parse specific control section types
                        if pattern_type == 'transform_matrix':
                            matrix = parse_transform_matrix(section_data)
                            if matrix:
                                section_info['transform'] = matrix
                        elif pattern_type == 'sprite_state':
                            state = parse_sprite_state(section_data)
                            if state:
                                section_info['state'] = state
                        elif pattern_type == 'sprite_flags':
                            flags = parse_sprite_flags(section_data)
                            if flags:
                                section_info['flags'] = flags
                        
                        sections.append(section_info)
                    current_pos = next_pos
                    found_pattern = True
                    break
            
            if not found_pattern:
                # Look for PNG data
                if data[current_pos:].startswith(b'\x89PNG'):
                    section_start = current_pos
                    # Find PNG end marker
                    iend_pos = data[current_pos:].find(b'IEND') + 8
                    if iend_pos > 8:
                        png_data = data[section_start:current_pos + iend_pos]
                        sections.append({
                            'offset': hex(section_start),
                            'size': len(png_data),
                            'type': 'png_data',
                            'raw_data': png_data.hex(),
                            'has_png': True
                        })
                        current_pos += iend_pos
                    else:
                        current_pos += 1
                else:
                    current_pos += 1
    
    # Analyze section relationships and build animation sequence
    animation_sequence = []
    current_frame = {}
    
    for section in sections:
        if section['type'] == 'sequence_header':
            animation_sequence.append({
                'type': 'sequence_start',
                'frame_count': section.get('frame_count', 0),
                'flags': section.get('flags', '0x0')
            })
        elif section['type'] == 'transform_matrix':
            if 'transform' in section:
                current_frame['transform'] = section['transform']
        elif section['type'] == 'sprite_state':
            if 'state' in section:
                current_frame['state'] = section['state']
        elif section['type'] == 'sprite_flags':
            if 'flags' in section:
                current_frame['flags'] = section['flags']
                # End of frame, add to sequence
                if current_frame:
                    animation_sequence.append(current_frame)
                    current_frame = {}
    
    # Add animation sequence to result
    if animation_sequence:
        sections.append({
            'type': 'animation_sequence',
            'sequence': animation_sequence
        })
    
    return sections

def try_reconstruct_sprite(data: bytes, start: int, size: int, palette: list = None) -> Optional[Image.Image]:
    """Attempt to reconstruct a sprite from data using various methods."""
    if not palette:
        # Default grayscale palette
        palette = [(i, i, i, 255) for i in range(256)]
        
    # Skip 32-byte header
    sprite_data = data[start+32:start+size]
    
    # Try different common sprite dimensions
    dimensions = [
        (16, 16), (32, 32), (64, 64),  # Square sprites
        (32, 16), (64, 32), (128, 64),  # 2:1 ratio
        (16, 32), (32, 64), (64, 128)   # 1:2 ratio
    ]
    
    best_image = None
    best_score = -1
    
    for width, height in dimensions:
        if width * height > len(sprite_data):
            continue
            
        # Create image with these dimensions
        img = Image.new('RGBA', (width, height))
        pixels = []
        
        # Fill pixels
        for i in range(width * height):
            if i < len(sprite_data):
                color_idx = sprite_data[i]
                if color_idx < len(palette):
                    pixels.append(palette[color_idx])
                else:
                    pixels.append((0, 0, 0, 0))
            else:
                pixels.append((0, 0, 0, 0))
                
        img.putdata(pixels)
        
        # Score the image based on non-empty pixels and edge detection
        score = 0
        non_empty = sum(1 for p in pixels if p[3] > 0)
        if non_empty > 0:
            score = non_empty / (width * height)  # Favor images with more content
            
        if score > best_score:
            best_score = score
            best_image = img
            
    return best_image

def parse_texture_parts(data: bytes) -> dict:
    """Parse TextureParts section to extract sprite region definitions."""
    if len(data) < 16:  # Minimum header size
        return None
        
    try:
        # Parse section header
        magic = data[0:12].rstrip(b'\x00').decode('ascii')
        count = struct.unpack('<I', data[12:16])[0]
        
        parts = []
        offset = 16  # Start after header
        
        # Parse each texture part entry
        for i in range(count):
            if offset + 32 > len(data):  # Each entry is 32 bytes
                break
                
            # Parse entry fields (8 x 4-byte values)
            entry_data = data[offset:offset+32]
            values = struct.unpack('<8f', entry_data)
            
            # Store the raw values in a simple list
            parts.append(values)
            
            offset += 32
            
        print(f"Found {len(parts)} texture parts:")
        for i, part in enumerate(parts):
            print(f"  Part {i}:")
            print(f"    Values: {part}")
        
        return {
            'magic': magic,
            'count': count,
            'parts': parts
        }
    except Exception as e:
        print(f"Error parsing TextureParts: {str(e)}")
        return None

def parse_sprite_group(data: bytes) -> dict:
    """Parse SpriteGp section to understand sprite grouping."""
    if len(data) < 16:  # Minimum header size
        return None
        
    try:
        # Parse section header
        magic = data[0:8].rstrip(b'\x00').decode('ascii')
        count = struct.unpack('<I', data[8:12])[0]
        flags = struct.unpack('<I', data[12:16])[0]
        
        groups = []
        offset = 16  # Start after header
        
        # Parse each sprite group entry
        for i in range(count):
            if offset + 16 > len(data):  # Each entry is at least 16 bytes
                break
                
            # Parse group header
            group_size, part_count = struct.unpack('<2I', data[offset:offset+8])
            name = data[offset+8:offset+16].rstrip(b'\x00').decode('ascii', errors='ignore')
            
            # Parse part references
            parts = []
            part_offset = offset + 16
            for j in range(part_count):
                if part_offset + 4 > len(data):
                    break
                part_index = struct.unpack('<I', data[part_offset:part_offset+4])[0]
                parts.append(part_index)
                part_offset += 4
                
            groups.append({
                'index': i,
                'name': name,
                'size': group_size,
                'part_count': part_count,
                'parts': parts
            })
            
            offset += group_size
            
        return {
            'magic': magic,
            'count': count,
            'flags': hex(flags),
            'groups': groups
        }
    except Exception as e:
        print(f"Error parsing SpriteGp: {str(e)}")
        return None

def analyze_sprite_resources(data: bytes) -> dict:
    """Analyze sprite resource file structure and extract sprite information."""
    resources = {
        'format': 'unknown',
        'sections': {}
    }
    
    # Check format
    if data.startswith(b'Sequ'):
        resources['format'] = 'uncompressed'
    elif data.startswith(b'LZ77'):
        resources['format'] = 'compressed'
        decompressed = decompress_lz77(data)
        if decompressed:
            data = decompressed
        else:
            return resources
            
    # Look for sections
    sections = {
        b'Sequ': ('sequence', parse_sequence_header),
        b'Sprite': ('sprite', None),
        b'SpriteGp': ('sprite_group', parse_sprite_group),
        b'TextureParts': ('texture_parts', parse_texture_parts),
        b'\x89PNG': ('png', None)
    }
    
    for marker, (name, parser) in sections.items():
        pos = data.find(marker)
        if pos >= 0:
            section_data = data[pos:]
            resources['sections'][name] = {
                'offset': pos,
                'marker': marker.decode('ascii', errors='replace')
            }
            
            if parser:
                parsed = parser(section_data)
                if parsed:
                    resources['sections'][name].update(parsed)
                    
            # For PNG data, find end marker
            if marker == b'\x89PNG':
                iend_pos = data.find(b'IEND', pos)
                if iend_pos > 0:
                    resources['sections'][name]['size'] = (iend_pos + 8) - pos
                    
    return resources

def extract_spranm(data: bytes, output_path: str = None) -> tuple[bool, bool, bytes, Optional[int]]:
    """Extract .spranm data with improved handling of both compressed and uncompressed formats."""
    try:
        # Check for LZ77 compression
        is_compressed = data.startswith(b'LZ77')
        is_uncompressed = data.startswith(b'Sequ')
        
        if not (is_compressed or is_uncompressed):
            print("Error: Not a valid SPRANM file (missing LZ77 or Sequence header)")
            return (False, False, b'', None)
            
        if is_compressed:
            print("Found compressed SPRANM format")
            decompressed = decompress_lz77(data)
            if decompressed:
                data = decompressed
                print("Successfully decompressed LZ77 data")
                print(f"Decompressed size: {len(data)} bytes")
                
                # Analyze compressed sections
                sections = analyze_compressed_sections(data)
                print("\nAnalyzed sections:")
                for section in sections:
                    if section['type'] == 'animation_sequence':
                        print("\nAnimation Sequence:")
                        for frame in section['sequence']:
                            print(f"  Frame:")
                            if 'transform' in frame:
                                t = frame['transform']
                                print(f"    Transform: scale({t['scale']['x']}, {t['scale']['y']}) translate({t['translation']['x']}, {t['translation']['y']})")
                            if 'state' in frame:
                                s = frame['state']
                                print(f"    State: visible={s['visible']}, flip_x={s['flip_x']}, flip_y={s['flip_y']}, active={s['active']}")
                            if 'flags' in frame:
                                f = frame['flags']
                                print(f"    Flags: loop={f['loop']}, reverse={f['reverse']}, pingpong={f['pingpong']}")
                    else:
                        offset = int(section['offset'], 16)  # Convert hex string to int
                        print(f"  {section['type']} at offset 0x{offset:x} ({section['size']} bytes)")
                        if 'transform' in section:
                            t = section['transform']
                            print(f"    Transform: scale({t['scale']['x']}, {t['scale']['y']}) translate({t['translation']['x']}, {t['translation']['y']})")
                        if 'state' in section:
                            s = section['state']
                            print(f"    State: visible={s['visible']}, flip_x={s['flip_x']}, flip_y={s['flip_y']}, active={s['active']}")
                        if 'flags' in section:
                            f = section['flags']
                            print(f"    Flags: loop={f['loop']}, reverse={f['reverse']}, pingpong={f['pingpong']}")
                        print(f"    First bytes: {section['raw_data'][:32]}")
                    
                if output_path:
                    # Save section analysis to metadata
                    meta_path = output_path + '.json'
                    meta_info = {
                        'format': 'compressed',
                        'total_size': len(data),
                        'sections': sections
                    }
                    with open(meta_path, 'w', encoding='utf-8') as f:
                        json.dump(meta_info, f, indent=2)
                    print(f"Saved section analysis to: {os.path.basename(meta_path)}")
        else:
            print("Found uncompressed SPRANM format")
            
            # Analyze sprite resources
            resources = analyze_sprite_resources(data)
            print("\nFound sections:")
            for name, info in resources['sections'].items():
                print(f"  {name} at offset 0x{info['offset']:x}")
                
                if name == 'texture_parts' and 'parts' in info:
                    print(f"Found {len(info['parts'])} texture parts:")
                    for i, part in enumerate(info['parts']):
                        print(f"  Part {i}:")
                        print(f"    Values: {part}")
                        
                elif name == 'sprite_group' and 'groups' in info:
                    print("\nSprite Groups:")
                    for group in info['groups']:
                        print(f"  Group {group['index']}: {group['name']}")
                        print(f"    Parts: {group['parts']}")
                        
                if name == 'png':
                    print(f"    PNG size: {info.get('size', 0)} bytes")
                    
                    if output_path:
                        png_data = data[info['offset']:info['offset'] + info['size']]
                        png_path = output_path + '.png'
                        with open(png_path, 'wb') as f:
                            f.write(png_data)
                        print(f"    Extracted PNG to: {os.path.basename(png_path)}")
                        
                        # Save metadata
                        save_metadata(png_path, info['offset'], png_data)
                        
            if output_path:
                # Save resource analysis
                meta_path = output_path + '.json'
                with open(meta_path, 'w', encoding='utf-8') as f:
                    json.dump(resources, f, indent=2)
                print(f"Saved resource analysis to: {os.path.basename(meta_path)}")
            
        return (True, False, data, None)

    except Exception as e:
        print(f"Error processing SPRANM: {str(e)}")
        return (False, False, b'', None)

def extract_tex(data: bytes, output_path: str, original_file: str = None) -> bool:
    """Extract PNG data from a .tex file (optionally LZ77-compressed)."""
    # Attempt LZ77 decompression
    if data.startswith(b'LZ77'):
        decompressed = decompress_lz77(data)
        if decompressed:
            data = decompressed
            print("Successfully decompressed LZ77 data (tex)")

    # Find PNG signature
    png_start = data.find(b'\x89PNG\r\n\x1a\n')
    if png_start >= 0:
        png_data = data[png_start:]
        
        # Save the PNG data
        with open(output_path, 'wb') as out_file:
            out_file.write(png_data)
            
        # Save metadata using common function with original file path
        save_metadata(output_path, png_start, png_data, original_file)
            
        print(f"Successfully extracted: {os.path.basename(output_path)}")
        return True

    return False

def strip_metadata_png(png_data: bytes) -> bytes:
    """Strip unnecessary metadata from PNG while preserving core image data"""
    from PIL import Image
    import io
    
    # Load and resave through PIL to strip metadata
    img = Image.open(io.BytesIO(png_data))
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    stripped_data = output.getvalue()
    
    # Ensure IHDR follows PNG signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    ihdr_start = stripped_data.find(b'IHDR')
    if ihdr_start > 8:
        ihdr_chunk = stripped_data[ihdr_start-4:ihdr_start+17]
        return png_sig + ihdr_chunk + stripped_data[ihdr_start+17:]
    return stripped_data

def repack_png(json_path: str, modified_png_path: str, output_path: str) -> bool:
    """Repack a modified PNG file using stored metadata."""
    try:
        if not os.path.exists(json_path):
            print(f"Error: JSON metadata file not found: {json_path}")
            return False
            
        if not os.path.exists(modified_png_path):
            print(f"Error: Modified PNG file not found: {modified_png_path}")
            return False
            
        with open(json_path, 'r', encoding='utf-8') as meta_file:
            meta_info = json.load(meta_file)
            
        original_file = meta_info.get("original_file")
        if not original_file or not os.path.exists(original_file):
            print("Error: Original file path not found in metadata")
            return False
            
        with open(modified_png_path, 'rb') as png_file:
            png_data = png_file.read()
            
        with open(original_file, 'rb') as orig_file:
            original_data = orig_file.read()
            
        offset = meta_info["offset"]
        length = meta_info["length"]
        
        if not png_data.startswith(b'\x89PNG\r\n\x1a\n'):
            print("Error: Modified file is not a valid PNG")
            return False
            
        # Strip metadata from PNG
        stripped_png = strip_metadata_png(png_data)
        
        # Handle size differences
        if len(stripped_png) < length:
            stripped_png += b'\x00' * (length - len(stripped_png))
        elif len(stripped_png) > length:
            print(f"Warning: Stripped PNG still larger than original ({len(stripped_png)} > {length} bytes)")
            print("The file will be truncated, which may cause corruption")
            stripped_png = stripped_png[:length]
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        new_data = original_data[:offset] + stripped_png + original_data[offset + length:]
        
        with open(output_path, 'wb') as out_file:
            out_file.write(new_data)
            
        print(f"Successfully repacked stripped PNG to: {output_path}")
        print(f"Original size: {length} bytes")
        print(f"New size: {len(stripped_png)} bytes")
        return True
        
    except Exception as e:
        print(f"Error repacking PNG: {str(e)}")
        return False

def extract_fnt(data: bytes, output_path: str) -> bool:
    """Extract font data with improved error handling."""
    try:
        if data.startswith(b'LZ77'):
            decompressed = decompress_lz77(data)
            if decompressed:
                data = decompressed
                print("Successfully decompressed LZ77 data (fnt)")

        with open(output_path, 'wb') as f:
            f.write(data)
        print(f"Successfully extracted font data: {os.path.basename(output_path)}")
        return True

    except Exception as e:
        print(f"Error extracting font data: {str(e)}")
        return False

def extract_mpd(data: bytes, output_path: str, original_file: str = None) -> bool:
    """Extract PNG data from a .mpd file."""
    try:
        # Check magic "Cell" string with proper spacing
        if not data.startswith(b'Cell        '):
            print("Not a valid MPD file (missing Cell magic)")
            return False
            
        # Parse header (first 40 bytes)
        header = MPDHeader(
            magic=data[0:4].decode('ascii'),
            data_size=int.from_bytes(data[0x14:0x18], 'little'),
            width=int.from_bytes(data[0x18:0x1C], 'little'),
            height=int.from_bytes(data[0x1C:0x20], 'little'),
            cell_width=int.from_bytes(data[0x20:0x24], 'little'),
            cell_height=int.from_bytes(data[0x24:0x28], 'little')
        )
        
        # Find embedded PNG data
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start < 0:
            print("PNG signature not found in MPD file.")
            return False
            
        # Find PNG end
        iend_pos = data.find(b'IEND', png_start)
        if iend_pos < 0:
            print("Incomplete PNG data in MPD file")
            return False
            
        # Include IEND chunk and CRC
        png_end = iend_pos + 8
        png_data = data[png_start:png_end]
        
        # Save PNG file
        with open(output_path, 'wb') as f:
            f.write(png_data)
            
        # Save metadata using common function with MPD header info and original file path
        save_metadata(output_path, png_start, png_data, original_file, extra_info={
            "mpd_header": {
                "data_size": header.data_size,
                "width": header.width,
                "height": header.height,
                "cell_width": header.cell_width,
                "cell_height": header.cell_height
            }
        })
            
        print(f"Successfully extracted PNG from MPD: {os.path.basename(output_path)}")
        return True
        
    except Exception as e:
        print(f"Error extracting MPD file: {str(e)}")
        return False

def process_file(input_path: str, output_dir: str, file_type: str = "all") -> bool:
    """Process a single file with improved error handling."""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        with open(input_path, 'rb') as f:
            data = f.read()

        file_ext = os.path.splitext(input_path)[1].lower()
        base_name = os.path.basename(input_path)

        if file_type != "all" and not file_ext.endswith(file_type):
            print(f"Skipping {base_name} - not a {file_type} file")
            return False

        if file_ext == '.tex':
            out_png = os.path.join(output_dir, base_name.replace('.tex', '.png'))
            return extract_tex(data, out_png, input_path)
            
        elif file_ext == '.mpd':
            out_png = os.path.join(output_dir, base_name.replace('.mpd', '.png'))
            return extract_mpd(data, out_png, input_path)

        elif file_ext == '.spranm':
            out_png = os.path.join(output_dir, base_name + '.png')
            out_bin = os.path.join(output_dir, base_name + '.bin')
            
            success, found_png, final_data, png_start = extract_spranm(data, out_png)
            if not success:
                print(f"Failed to extract: {base_name}")
                return False

            if found_png:
                with open(out_png, 'wb') as f:
                    f.write(final_data)
                save_metadata(out_png, png_start, final_data, input_path)
                print(f"Extracted animation PNG: {os.path.basename(out_png)}")
            else:
                with open(out_bin, 'wb') as f:
                    f.write(final_data)
                print(f"No PNG found. Saved raw data: {os.path.basename(out_bin)}")

            return True

        elif file_ext == '.fnt':
            out_path = os.path.join(output_dir, base_name + '.bin')
            return extract_fnt(data, out_path)

        else:
            print(f"Unsupported file type: {file_ext}")
            return False

    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")
        return False

def find_files(input_dir: str, exts: list[str], verbose: bool) -> list[str]:
    """Recursively find files with given extensions in directory and subdirectories."""
    all_files = []
    
    for root, _, files in os.walk(input_dir):
        for ext in exts:
            matches = [os.path.join(root, f) for f in files if f.lower().endswith(ext)]
            if verbose and matches:
                rel_path = os.path.relpath(root, input_dir)
                print(f"Found {len(matches)} {ext} files in {rel_path}")
            all_files.extend(matches)
            
    return all_files

def hex_dump(data: bytes, start: int = 0, length: int = None, show_ascii: bool = True) -> str:
    """Create a formatted hex dump of binary data."""
    if length is None:
        length = len(data)
    result = []
    
    for i in range(0, length, 16):
        chunk = data[i:i+16]
        hex_line = ' '.join(f'{b:02x}' for b in chunk)
        
        if show_ascii:
            ascii_line = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            result.append(f'{start+i:08x}:  {hex_line:<48}  |{ascii_line}|')
        else:
            result.append(f'{start+i:08x}:  {hex_line}')
            
    return '\n'.join(result)

def analyze_spranm(data: bytes, output_path: str = None) -> dict:
    """Analyze .spranm file structure and return findings."""
    findings = {
        'size': len(data),
        'compression': 'None',
        'markers': [],
        'png_data': None,
        'sections': []
    }
    
    # Check for LZ77 compression
    if data.startswith(b'LZ77'):
        findings['compression'] = 'LZ77'
        findings['lz77_header'] = {
            'magic': data[0:4].hex(),
            'size': int.from_bytes(data[8:12], 'little'),
            'decompressed_size': int.from_bytes(data[12:16], 'little'),
            'flags': data[4:8].hex()
        }
        
        # Try to decompress
        decompressed = decompress_lz77(data)
        if decompressed:
            findings['decompressed'] = {
                'size': len(decompressed),
                'first_bytes': decompressed[:32].hex(),
                'sections': []
            }
            
            # Look for sections in decompressed data
            for marker in [b'Sequ', b'Palett', b'ConvertInfo', b'\x89PNG']:
                pos = decompressed.find(marker)
                if pos >= 0:
                    findings['decompressed']['sections'].append((marker.decode('ascii', errors='replace'), pos))
                    
            # Add hex dump of first 256 bytes of decompressed data
            findings['decompressed']['hex_dump'] = hex_dump(decompressed[:256])
    
    # Look for Sequ marker
    sequ_pos = data.find(b'Sequ')
    if sequ_pos >= 0:
        findings['markers'].append(('Sequ', sequ_pos))
    
    # Look for PNG signature
    png_start = data.find(b'\x89PNG\r\n\x1a\n')
    if png_start >= 0:
        findings['png_data'] = {
            'offset': png_start,
            'signature': data[png_start:png_start+8].hex()
        }
        # Find IEND to get PNG size
        iend_pos = data.find(b'IEND', png_start)
        if iend_pos >= 0:
            findings['png_data']['size'] = (iend_pos + 8) - png_start
    
    return findings

def print_analysis(filename: str, findings: dict):
    """Print analysis findings in a formatted way."""
    print(f"\nAnalysis of {filename}")
    print("=" * 60)
    print(f"File size: {findings['size']} bytes")
    print(f"Compression: {findings['compression']}")
    
    if findings['compression'] == 'LZ77':
        print("\nLZ77 Header:")
        print(f"  Magic: {findings['lz77_header']['magic']}")
        print(f"  Flags: {findings['lz77_header']['flags']}")
        print(f"  Compressed size: {findings['lz77_header']['size']} bytes")
        print(f"  Decompressed size: {findings['lz77_header']['decompressed_size']} bytes")
        
        if 'decompressed' in findings:
            print("\nDecompressed Data:")
            print(f"  Actual size: {findings['decompressed']['size']} bytes")
            print(f"  First 32 bytes: {findings['decompressed']['first_bytes']}")
            
            if findings['decompressed']['sections']:
                print("\nDecompressed Sections:")
                for name, pos in findings['decompressed']['sections']:
                    print(f"  {name} at offset 0x{pos:x}")
                    
            print("\nFirst 256 bytes of decompressed data:")
            print(findings['decompressed']['hex_dump'])
    
    if findings['markers']:
        print("\nMarkers found in original data:")
        for marker, pos in findings['markers']:
            print(f"  {marker} at offset 0x{pos:x}")
    
    if findings['png_data']:
        print("\nPNG Data:")
        print(f"  Offset: 0x{findings['png_data']['offset']:x}")
        print(f"  Signature: {findings['png_data']['signature']}")
        print(f"  Size: {findings['png_data']['size']} bytes")

def parse_sequence_header(data: bytes) -> dict:
    """Parse sequence header section to extract animation timing and properties."""
    if len(data) < 16:  # Minimum header size
        return None
        
    try:
        # Parse section header
        magic = data[0:8].rstrip(b'\x00').decode('ascii')
        frame_count = struct.unpack('<I', data[8:12])[0]
        flags = struct.unpack('<I', data[12:16])[0]
        
        # Parse timing data if present
        timing = []
        offset = 16
        while offset + 8 <= len(data):
            duration, frame_flags = struct.unpack('<2I', data[offset:offset+8])
            timing.append({
                'duration': duration,
                'flags': hex(frame_flags),
                'loop': bool(frame_flags & 0x1),
                'reverse': bool(frame_flags & 0x2),
                'pingpong': bool(frame_flags & 0x4)
            })
            offset += 8
            
            # Break if we've read all frames
            if len(timing) >= frame_count:
                break
        
        return {
            'magic': magic,
            'frame_count': frame_count,
            'flags': hex(flags),
            'timing': timing
        }
    except Exception as e:
        print(f"Error parsing sequence header: {str(e)}")
        return None

def main():
    parser = argparse.ArgumentParser(
        description='Extract and decompress Dokapon Kingdom files (.tex, .spranm, .fnt)',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-i', '--input',
                        default='.',
                        help='Input file or directory to process (default: current directory)')

    parser.add_argument('-o', '--output',
                        default='output',
                        help='Output directory (default: ./output)')

    parser.add_argument('-t', '--type',
                        choices=['tex', 'mpd', 'spranm', 'fnt', 'all'],
                        default='all',
                        help=('File type to process (default: all)\n'
                              'tex    - Extract texture files\n'
                              'mpd    - Extract MPD files\n'
                              'spranm - Extract sprite animations\n'
                              'fnt    - Extract font files\n'
                              'all    - Process all supported files'))

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Show detailed processing information')

    parser.add_argument('--repack',
                       action='store_true',
                       help='Repack a modified PNG using JSON metadata')
                       
    parser.add_argument('--analyze',
                       action='store_true',
                       help='Analyze file structure without extracting')

    args = parser.parse_args()

    # Handle direct file analysis
    if args.analyze and os.path.isfile(args.input):
        with open(args.input, 'rb') as f:
            data = f.read()
            
        # Print first 1000 bytes
        print("\nFirst 1000 bytes:")
        print(hex_dump(data[:1000]))
        
        # Print last 1000 bytes
        if len(data) > 1000:
            print("\nLast 1000 bytes:")
            print(hex_dump(data[-1000:], start=len(data)-1000))
        
        # Analyze structure
        findings = analyze_spranm(data)
        print_analysis(args.input, findings)
        return

    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if args.repack:
        print("\n=== Repack PNG File ===")
        print("Enter paths (press Enter to cancel at any prompt)")
        
        json_path = input("Path to JSON metadata file: ").strip()
        if not json_path:
            return
            
        # Load metadata to get original extension
        try:
            with open(json_path, 'r') as f:
                meta_info = json.load(f)
            original_ext = meta_info.get('original_extension', '.bin')
        except:
            original_ext = '.bin'
            
        png_path = input("Path to modified PNG file: ").strip()
        if not png_path:
            return
            
        # Auto-suggest output path using original extension
        suggested_output = os.path.splitext(png_path)[0] + original_ext
            
        output_path = input(f"Output path [{suggested_output}]: ").strip()
        if not output_path:
            output_path = suggested_output
            
        if repack_png(json_path, png_path, output_path):
            print("\nRepacking completed successfully")
        else:
            print("\nRepacking failed")
        return

    try:
        if os.path.isfile(args.input):
            success = process_file(args.input, output_dir, args.type)
            if success:
                if args.verbose:
                    print(f"\nProcessed: {args.input}")
                print("\nProcessing complete: 1 file converted successfully")
            else:
                print("\nProcessing failed")

        else:
            # Handle directory
            if args.type == 'all':
                exts = ['.mpd', '.tex', '.spranm', '.fnt']
            else:
                exts = ['.' + args.type]

            input_dir = os.path.abspath(args.input)
            
            # Use new find_files function instead of glob
            all_files = find_files(input_dir, exts, args.verbose)

            if not all_files:
                print(f"No {', '.join(exts)} files found in {args.input} or its subdirectories")
                return

            print(f"\nProcessing {len(all_files)} files...")
            print(f"Extracting to: {output_dir}")

            success_count = 0
            for fpath in all_files:
                # Pass input_dir to preserve directory structure
                if process_file(fpath, output_dir, args.type):
                    success_count += 1
                    if args.verbose:
                        rel_path = os.path.relpath(fpath, input_dir)
                        print(f"Processed: {rel_path}")

            print(f"\nResults: {success_count}/{len(all_files)} successful")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")

if __name__ == '__main__':
    main()