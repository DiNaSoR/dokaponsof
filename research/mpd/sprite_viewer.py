"""
Sprite Viewer for S_TIT format files
Extracts and visualizes sprite data from the game's custom format.
"""

import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageSequence
import os

class SpriteHeader:
    def __init__(self, data):
        values = struct.unpack('<11I', data[:44])
        self.magic = values[2]  # 0x55350000
        self.marker = values[3]  # 0x55555555
        self.width = values[4]   # 85
        self.height = values[5]  # 768
        self.offset = values[7]  # 0x4400
        self.format = values[8]  # 0x100000
        self.flags = values[10]  # 0x1c000800

def decode_color(value):
    """Decode a 15/16-bit color value to RGB."""
    # Game uses BGR555 format (based on executable analysis)
    r = (value & 0x001F) << 3       # 5 bits red
    g = ((value >> 5) & 0x1F) << 3  # 5 bits green
    b = ((value >> 10) & 0x1F) << 3 # 5 bits blue
    return [r, g, b]

def extract_palette(data, offset):
    """Extract and decode the color palette."""
    palette_data = data[offset:offset + 32]  # 16 colors * 2 bytes
    print(f"\nPalette at offset 0x{offset:04x}:")
    print("Raw data:", " ".join(f"{b:02x}" for b in palette_data))
    
    palette = []
    for i in range(0, 32, 2):
        # Game uses little-endian color values
        color = struct.unpack('<H', palette_data[i:i+2])[0]
        print(f"Color {i//2:2d}: 0x{color:04x}")
        
        if color == 0:
            # Color 0 is transparent/black
            if i == 0:
                palette.extend([0, 0, 0])
            else:
                # Make unused colors visible for debugging
                h = (i / 32) * 360  # Hue
                s = 0.8  # Saturation
                v = 0.5  # Value (dimmer to match game style)
                
                # HSV to RGB conversion
                c = v * s
                x = c * (1 - abs((h / 60) % 2 - 1))
                m = v - c
                
                if h < 60:
                    r,g,b = c,x,0
                elif h < 120:
                    r,g,b = x,c,0
                elif h < 180:
                    r,g,b = 0,c,x
                elif h < 240:
                    r,g,b = 0,x,c
                elif h < 300:
                    r,g,b = x,0,c
                else:
                    r,g,b = c,0,x
                
                palette.extend([
                    int((r + m) * 255),
                    int((g + m) * 255),
                    int((b + m) * 255)
                ])
        else:
            rgb = decode_color(color)
            print(f"       RGB: ({rgb[0]:3d}, {rgb[1]:3d}, {rgb[2]:3d})")
            palette.extend(rgb)
    
    return palette

def extract_pixels(data, header, palette_offset):
    """Extract pixel data with proper alignment."""
    # Game uses 4-byte aligned rows
    bytes_per_row = (header.width + 1) // 2  # 4-bit pixels packed
    row_stride = (bytes_per_row + 3) & ~3    # 4-byte alignment
    
    pixel_start = palette_offset + 32  # Palette is 32 bytes
    pixels = []
    
    # Process each row
    for y in range(header.height):
        row_offset = pixel_start + (y * row_stride)
        if row_offset + bytes_per_row > len(data):
            break
        
        row = data[row_offset:row_offset + bytes_per_row]
        if y < 4:  # Show first few rows
            print(f"Row {y:3d}: " + " ".join(f"{b:02x}" for b in row))
        
        # Process each pixel in the row
        row_pixels = []
        for x in range(header.width):
            byte_offset = x // 2
            if byte_offset >= len(row):
                row_pixels.append(0)
                continue
            
            byte = row[byte_offset]
            if x % 2 == 0:
                # Game reads high nibble first
                row_pixels.append(byte >> 4)
            else:
                row_pixels.append(byte & 0x0F)
        
        pixels.extend(row_pixels)
    
    # Show pixel distribution
    counts = [0] * 16
    for p in pixels:
        counts[p] += 1
    print("\nPixel value distribution:")
    for i, count in enumerate(counts):
        if count > 0:
            print(f"Color {i:2d}: {count:6d} pixels ({count/len(pixels)*100:5.1f}%)")
    
    return pixels

def detect_sprites(pixels, width, height):
    """Detect individual sprites in the image based on empty rows."""
    sprites = []
    start_y = 0
    empty_count = 0
    
    # Convert pixels to 2D array
    try:
        pixel_array = np.array([pixels[i:i+width] for i in range(0, len(pixels), width)])
    except Exception as e:
        print(f"Warning: Could not reshape pixels: {str(e)}")
        return []
    
    # Scan for empty rows (all zeros or same color)
    for y in range(len(pixel_array)):
        row = pixel_array[y]
        if len(set(row)) <= 1:  # Row is empty or single color
            empty_count += 1
            if empty_count >= 3 and y - start_y > 10:  # At least 3 empty rows and minimum sprite height
                sprites.append((start_y, y))
                start_y = y + 1
        else:
            empty_count = 0
    
    # Add last sprite if needed
    if len(pixel_array) - start_y > 10:
        sprites.append((start_y, len(pixel_array)))
    
    return sprites

def analyze_file_structure(data):
    """Analyze the file structure and look for patterns."""
    print("\nFile Structure Analysis:")
    print(f"Total size: {len(data)} bytes")
    
    # Look for common markers
    markers = {
        0x55350000: "Magic number",
        0x55555555: "Section marker",
        0x00100000: "Format marker",
    }
    
    print("\nMarkers found:")
    for i in range(0, len(data)-4, 4):
        value = struct.unpack('<I', data[i:i+4])[0]
        if value in markers:
            print(f"0x{i:04x}: 0x{value:08x} ({markers[value]})")
    
    # Look for potential palettes (sequences of color values)
    print("\nPotential palette locations:")
    for i in range(0, len(data)-32, 16):
        # Check if this could be a palette (16 colors × 2 bytes)
        palette_data = data[i:i+32]
        colors = struct.unpack('<16H', palette_data)
        valid_colors = sum(1 for c in colors if 0 <= c <= 0x7FFF)
        if valid_colors >= 2:  # At least 2 valid colors
            print(f"\nOffset 0x{i:04x}:")
            for j, color in enumerate(colors):
                if 0 < color <= 0x7FFF:
                    r = (color & 0x001F) << 3
                    g = ((color >> 5) & 0x1F) << 3
                    b = ((color >> 10) & 0x1F) << 3
                    print(f"  Color {j:2d}: 0x{color:04x} = RGB({r:3d},{g:3d},{b:3d})")

def extract_pixels_from_offset(data, header, palette_offset):
    """Extract pixels starting from the header's data offset."""
    pixels = []
    
    # Start from the header's data offset
    data_start = header.offset
    print(f"\nReading pixel data from offset 0x{data_start:04x}")
    
    # Try to determine format from the format field
    is_planar = (header.format & 0x100000) != 0
    bits_per_pixel = 4 if (header.format & 0x200000) == 0 else 8
    
    print(f"Format analysis:")
    print(f"  Planar: {is_planar}")
    print(f"  Bits per pixel: {bits_per_pixel}")
    
    if is_planar:
        # Planar format (like PC-98)
        bytes_per_plane = (header.width + 7) // 8
        plane_stride = (bytes_per_plane + 3) & ~3
        planes = bits_per_pixel
        
        # Try both MSB and LSB first arrangements
        arrangements = [
            ('MSB first', lambda b, p: (b & (0x80 >> p)) >> (7-p)),
            ('LSB first', lambda b, p: (b & (1 << p)) >> p)
        ]
        
        for arr_name, bit_extract in arrangements:
            print(f"\nTrying {arr_name} bit arrangement:")
            row_pixels = []
            
            for y in range(header.height):
                pixel_row = [0] * header.width
                
                for plane in range(planes):
                    plane_offset = data_start + (y * plane_stride * planes) + (plane * plane_stride)
                    if plane_offset >= len(data):
                        continue
                        
                    plane_data = data[plane_offset:plane_offset + bytes_per_plane]
                    if y < 4:
                        print(f"Row {y:3d} Plane {plane}: " + " ".join(f"{b:02x}" for b in plane_data))
                    
                    for byte_idx, byte in enumerate(plane_data):
                        for bit in range(8):
                            pixel_idx = byte_idx * 8 + bit
                            if pixel_idx >= header.width:
                                break
                            pixel_row[pixel_idx] |= bit_extract(byte, bit) << plane
                
                row_pixels.extend(pixel_row)
                
                if y < 4:
                    print(f"Row {y:3d} pixels: " + " ".join(f"{p:x}" for p in pixel_row[:16]) + "...")
            
            # Show color distribution
            counts = [0] * 16
            for p in row_pixels:
                counts[p] += 1
            print(f"\nPixel value distribution ({arr_name}):")
            for i, count in enumerate(counts):
                if count > 0:
                    print(f"Color {i:2d}: {count:6d} pixels ({count/len(row_pixels)*100:5.1f}%)")
            
            pixels.append((arr_name, row_pixels))
    else:
        # Linear format
        bytes_per_row = (header.width * bits_per_pixel + 7) // 8
        row_stride = (bytes_per_row + 3) & ~3
        row_pixels = []
        
        for y in range(header.height):
            row_offset = data_start + (y * row_stride)
            if row_offset >= len(data):
                break
                
            row = data[row_offset:row_offset + bytes_per_row]
            if y < 4:
                print(f"Row {y:3d}: " + " ".join(f"{b:02x}" for b in row))
            
            if bits_per_pixel == 4:
                # 4-bit packed pixels
                for x in range(header.width):
                    byte_offset = x // 2
                    if byte_offset >= len(row):
                        row_pixels.append(0)
                        continue
                    
                    byte = row[byte_offset]
                    row_pixels.append(byte >> 4 if x % 2 == 0 else byte & 0x0F)
            else:
                # 8-bit pixels
                row_pixels.extend(row[:header.width])
        
        pixels.append(('linear', row_pixels))
    
    return pixels

def read_s_tit_header(data):
    """Read and parse the S_TIT file header."""
    # Parse header values
    values = struct.unpack('<11I', data[:44])
    magic = values[2]      # 0x55350000
    marker = values[3]     # 0x55555555
    width = values[4]      # 85
    height = values[5]     # 768
    data_offset = values[7]  # 0x4400
    format_field = values[8] # 0x100000
    flags = values[10]     # 0x1c000800
    
    # Determine format
    is_planar = (format_field & 0x00100000) != 0
    bits_per_pixel = 4 if is_planar else 8
    
    # Find palette offset
    palette_offset = 0x002c  # Default palette location
    if data[palette_offset+4:palette_offset+8] == b'\x18\x00\x24\x00':
        # Verified palette with expected red colors
        pass
    elif data[0x43e0:0x43e0+4] == b'\x00\x00\x1c\x00':
        palette_offset = 0x43e0
    elif data[0x43c0:0x43c0+4] == b'\x00\x00\x1d\x6c':
        palette_offset = 0x43c0
    
    print(f"\nFile Analysis:")
    print(f"Magic: 0x{magic:08x}")
    print(f"Marker: 0x{marker:08x}")
    print(f"Dimensions: {width}x{height}")
    print(f"Data offset: 0x{data_offset:08x}")
    print(f"Format: 0x{format_field:08x}")
    print(f"Flags: 0x{flags:08x}")
    print(f"Palette offset: 0x{palette_offset:04x}")
    
    return {
        'width': width,
        'height': height,
        'data_offset': data_offset,
        'format': format_field,
        'flags': flags,
        'is_planar': is_planar,
        'bits_per_pixel': bits_per_pixel,
        'palette_offset': palette_offset,
        'magic': magic,
        'marker': marker
    }

def extract_planar_pixels(data, header):
    """Extract pixels from planar format data."""
    width = header['width']
    height = header['height']
    data_offset = header['data_offset']
    
    # Calculate row alignment (11 bytes per plane based on analysis)
    bytes_per_plane = (width + 7) // 8
    if bytes_per_plane % 11 != 0:
        bytes_per_plane = ((bytes_per_plane + 10) // 11) * 11
    
    print(f"\nExtracting planar pixels:")
    print(f"Bytes per plane: {bytes_per_plane}")
    
    pixels = []
    for y in range(height):
        row = []
        for x in range(width):
            pixel = 0
            byte_offset = data_offset + y * (bytes_per_plane * 4) + (x // 8)
            bit_mask = 0x80 >> (x % 8)
            
            # Extract bits from each plane
            for plane in range(4):
                plane_offset = byte_offset + (plane * bytes_per_plane)
                if plane_offset < len(data):
                    bit = 1 if (data[plane_offset] & bit_mask) else 0
                    pixel |= (bit << plane)
            
            row.append(pixel)
            
            # Print first few pixels of first few rows for debugging
            if y < 2 and x < 16:
                if x == 0:
                    print(f"\nRow {y:3d} pixels: ", end='')
                print(f"{pixel:x}", end=' ')
        
        pixels.extend(row)
    
    return pixels

def analyze_sprite_relationships(sprites, pixels, width, height, palette):
    """Analyze relationships between sprites to detect animation frames."""
    relationships = []
    
    for i, (start1, end1) in enumerate(sprites):
        sprite1_height = end1 - start1
        sprite1_pixels = []
        for y in range(sprite1_height):
            sprite1_pixels.extend(pixels[(start1 + y) * width:(start1 + y) * width + width])
        
        similar_sprites = []
        for j, (start2, end2) in enumerate(sprites):
            if i == j:
                continue
                
            sprite2_height = end2 - start2
            # Only compare sprites of similar height (within 20%)
            if abs(sprite2_height - sprite1_height) > sprite1_height * 0.2:
                continue
                
            sprite2_pixels = []
            for y in range(sprite2_height):
                sprite2_pixels.extend(pixels[(start2 + y) * width:(start2 + y) * width + width])
            
            # Compare color usage and pixel patterns
            similarity = calculate_sprite_similarity(sprite1_pixels, sprite2_pixels, width)
            if similarity > 0.7:  # 70% similarity threshold
                similar_sprites.append((j, similarity))
        
        if similar_sprites:
            relationships.append((i, similar_sprites))
    
    return relationships

def calculate_sprite_similarity(pixels1, pixels2, width):
    """Calculate similarity between two sprites."""
    # Normalize lengths
    min_len = min(len(pixels1), len(pixels2))
    pixels1 = pixels1[:min_len]
    pixels2 = pixels2[:min_len]
    
    # Compare non-transparent pixels
    matching_pixels = 0
    total_pixels = 0
    
    for p1, p2 in zip(pixels1, pixels2):
        if p1 != 0 or p2 != 0:  # At least one non-transparent
            total_pixels += 1
            if p1 == p2:
                matching_pixels += 1
    
    return matching_pixels / total_pixels if total_pixels > 0 else 0

def generate_sprite_sheet(sprites, img, base_name):
    """Generate a sprite sheet with detected sprites."""
    if not sprites:
        return
    
    # Calculate sprite sheet dimensions
    max_width = max(end - start for start, end in sprites)
    total_height = sum(end - start for start, end in sprites)
    
    # Create sprite sheet
    sheet = Image.new('RGBA', (img.width, total_height), (0,0,0,0))
    y_offset = 0
    
    for start, end in sprites:
        height = end - start
        sprite = img.crop((0, start, img.width, end))
        sheet.paste(sprite, (0, y_offset))
        y_offset += height
    
    sheet.save(f'{base_name}_sprite_sheet.png')
    print(f"\nSaved sprite sheet as {base_name}_sprite_sheet.png")

def generate_animation_preview(sprites, relationships, img, base_name):
    """Generate animation preview GIFs for related sprites."""
    if not relationships:
        return
    
    # Group related sprites into potential animations
    animations = []
    processed = set()
    
    for sprite_id, similar in relationships:
        if sprite_id in processed:
            continue
            
        # Create animation group
        group = [sprite_id]
        processed.add(sprite_id)
        
        for similar_id, similarity in similar:
            if similar_id not in processed:
                group.append(similar_id)
                processed.add(similar_id)
        
        if len(group) > 1:
            animations.append(sorted(group))
    
    # Generate preview GIFs
    for i, group in enumerate(animations):
        frames = []
        for sprite_id in group:
            start, end = sprites[sprite_id]
            sprite = img.crop((0, start, img.width, end))
            frames.append(sprite)
        
        if frames:
            # Save as GIF
            gif_path = f'{base_name}_animation_{i:02d}.gif'
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=200,  # 200ms per frame
                loop=0,
                transparency=0,
                disposal=2
            )
            print(f"Saved animation preview as {gif_path}")

def convert_to_image(filename):
    """Convert S_TIT file to PNG image with enhanced sprite detection and analysis."""
    with open(filename, 'rb') as f:
        data = f.read()
    
    header = read_s_tit_header(data)
    width = header['width']
    height = header['height']
    
    # Read palette
    palette = []
    print(f"\nPalette at offset 0x{header['palette_offset']:04x}:")
    for i in range(16):
        color = struct.unpack_from('<H', data, header['palette_offset'] + i*2)[0]
        r = ((color >> 0) & 0x1F) << 3
        g = ((color >> 5) & 0x1F) << 3
        b = ((color >> 10) & 0x1F) << 3
        palette.append((r, g, b))
        print(f"Color {i:2d}: RGB({r:3d},{g:3d},{b:3d})")
    
    # Extract pixels
    pixels = extract_planar_pixels(data, header)
    
    # Show color distribution
    counts = [0] * 16
    for p in pixels:
        if p < len(counts):
            counts[p] += 1
    
    print("\nPixel value distribution:")
    total_pixels = len(pixels)
    for i, count in enumerate(counts):
        if count > 0:
            print(f"Color {i:2d}: {count:6d} pixels ({count/total_pixels*100:5.1f}%)")
    
    # Create RGBA image with transparency
    img = Image.new('RGBA', (width, height), (0,0,0,0))
    for y in range(height):
        for x in range(width):
            pixel = pixels[y * width + x]
            if pixel < len(palette):
                if pixel == 0:  # Transparent
                    img.putpixel((x, y), (0,0,0,0))
                else:
                    color = palette[pixel]
                    img.putpixel((x, y), (color[0], color[1], color[2], 255))
    
    # Save full image
    base_name = os.path.splitext(filename)[0]
    img.save(f'{base_name}_planar.png')
    print(f"\nSaved {base_name}_planar.png")
    
    # Enhanced sprite detection with pattern analysis
    empty_rows = []
    row_patterns = []
    
    for y in range(height):
        row_pixels = pixels[y * width:(y + 1) * width]
        colors_used = set(row_pixels)
        pattern = {
            'colors': colors_used,
            'transitions': sum(1 for i in range(width-1) if row_pixels[i] != row_pixels[i+1])
        }
        row_patterns.append(pattern)
        
        # A row is empty if it's all transparent or very simple
        if len(colors_used) <= 2 and (0 in colors_used or pattern['transitions'] < 3):
            empty_rows.append(y)
    
    # Find sprite boundaries with pattern analysis
    sprite_ranges = []
    start = 0
    empty_streak = 0
    
    for y in range(height):
        if y in empty_rows:
            empty_streak += 1
            if empty_streak >= 3 and y - start > 4:  # Minimum sprite height
                # Verify this is a real sprite boundary
                pre_patterns = row_patterns[max(0, start-3):start]
                post_patterns = row_patterns[y:min(height, y+3)]
                
                pattern_change = True
                if pre_patterns and post_patterns:
                    pre_complexity = sum(p['transitions'] for p in pre_patterns) / len(pre_patterns)
                    post_complexity = sum(p['transitions'] for p in post_patterns) / len(post_patterns)
                    pattern_change = abs(pre_complexity - post_complexity) > 2
                
                if pattern_change:
                    sprite_ranges.append((start, y - empty_streak + 1))
                    start = y + 1
        else:
            if empty_streak >= 3:
                start = y
            empty_streak = 0
    
    # Add last sprite if needed
    if height - start > 4 and empty_streak < 3:
        sprite_ranges.append((start, height))
    
    # Generate sprite sheet
    generate_sprite_sheet(sprite_ranges, img, base_name)
    
    # Analyze sprite relationships
    relationships = analyze_sprite_relationships(sprite_ranges, pixels, width, height, palette)
    
    # Generate animation previews
    generate_animation_preview(sprite_ranges, relationships, img, base_name)
    
    # Save and analyze individual sprites
    if sprite_ranges:
        print(f"\nDetected {len(sprite_ranges)} sprites:")
        
    for i, (start, end) in enumerate(sprite_ranges):
        sprite_height = end - start
        if sprite_height > 4:  # Skip very small sprites
            # Crop sprite
            sprite = img.crop((0, start, width, end))
            
            # Analyze sprite
            sprite_pixels = []
            for y in range(sprite_height):
                sprite_pixels.extend(pixels[(start + y) * width:(start + y) * width + width])
            
            # Count colors used
            sprite_colors = set(sprite_pixels) - {0}  # Exclude transparent
            color_counts = {}
            for color in sprite_colors:
                count = sprite_pixels.count(color)
                color_counts[color] = count
            
            # Calculate bounding box
            left = width
            right = 0
            top = sprite_height
            bottom = 0
            
            for y in range(sprite_height):
                row_has_pixels = False
                for x in range(width):
                    pixel = pixels[(start + y) * width + x]
                    if pixel != 0:
                        left = min(left, x)
                        right = max(right, x)
                        row_has_pixels = True
                if row_has_pixels:
                    top = min(top, y)
                    bottom = max(bottom, y)
            
            # Print analysis
            print(f"\nSprite {i:2d}:")
            print(f"  Height: {sprite_height} pixels")
            print(f"  Bounding box: ({left},{top}) to ({right},{bottom})")
            print(f"  Effective size: {right-left+1}x{bottom-top+1}")
            print(f"  Colors used: {len(sprite_colors)}")
            
            # Show color usage
            for color, count in sorted(color_counts.items(), key=lambda x: x[1], reverse=True):
                rgb = palette[color]
                pct = count / (sprite_height * width) * 100
                print(f"    Color {color:2d}: RGB({rgb[0]:3d},{rgb[1]:3d},{rgb[2]:3d}) - {count:6d} pixels ({pct:5.1f}%)")
            
            # Show related sprites
            related = [r for r in relationships if r[0] == i]
            if related:
                print("  Related sprites:")
                for _, similar in related[0][1]:
                    print(f"    Sprite {similar[0]:2d} (similarity: {similar[1]*100:.1f}%)")
            
            # Save with transparency
            sprite_path = f'{base_name}_planar_sprite{i:02d}.png'
            sprite.save(sprite_path)
            print(f"  Saved as: {sprite_path}")
            
            # Save tight crop if significantly smaller
            if (right-left+1) * (bottom-top+1) < sprite_height * width * 0.8:
                crop = sprite.crop((left, top, right+1, bottom+1))
                crop_path = f'{base_name}_planar_sprite{i:02d}_crop.png'
                crop.save(crop_path)
                print(f"  Saved cropped version as: {crop_path}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python sprite_viewer.py <input_file>")
        sys.exit(1)
    
    convert_to_image(sys.argv[1]) 
