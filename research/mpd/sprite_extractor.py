import struct
import os
from pathlib import Path
import numpy as np
from PIL import Image
import io
import math

def find_sprite_headers(data: bytes) -> list:
    """Find potential sprite/image data sections"""
    headers = []
    pos = 0
    
    while pos < len(data) - 16:
        # Look for potential image data patterns
        
        # Pattern 1: Standard sprite header
        if (data[pos] == 0x00 and data[pos+1] in [0x80, 0xC0] and 
            data[pos+2] < 0x20 and data[pos+3] == 0x00):
            
            end = pos + 4
            while end < len(data) - 4:
                if data[end:end+4] == b'\x00\x00\x00\x00':
                    break
                end += 1
            
            if end > pos + 16:
                headers.append({
                    'offset': pos,
                    'size': end - pos,
                    'type': 'sprite_standard'
                })
            pos = end
            continue
        
        # Pattern 2: Large data blocks with potential image content
        if pos + 1024 <= len(data):
            # Check for common image data patterns
            block = data[pos:pos+1024]
            
            # Check if block might contain image data
            if any(pattern in block[:32] for pattern in [b'\x89PNG', b'BM', b'\xFF\xD8\xFF']):
                # Look for end of image data
                end = pos + 32
                while end < min(pos + 16384, len(data) - 4):  # Limit search to reasonable size
                    if data[end:end+4] == b'\x00\x00\x00\x00':
                        break
                    end += 1
                
                headers.append({
                    'offset': pos,
                    'size': end - pos,
                    'type': 'embedded_image'
                })
                pos = end
                continue
            
            # Check for raw image data patterns
            if all(b < 0xF0 for b in block[:64]):  # Possible pixel data
                # Look for consistent patterns in the data
                pattern_size = 0
                for size in [8, 16, 32, 64, 128, 256]:
                    if len(block) % size == 0:
                        rows = [block[i:i+size] for i in range(0, len(block), size)]
                        if all(len(set(row)) < 64 for row in rows[:4]):  # Check for palette-like data
                            pattern_size = size
                            break
                
                if pattern_size > 0:
                    end = pos + (len(block) // pattern_size) * pattern_size
                    headers.append({
                        'offset': pos,
                        'size': end - pos,
                        'type': 'raw_image'
                    })
                    pos = end
                    continue
        
        # Pattern 3: Check for transform blocks that might contain texture coordinates
        if pos + 64 <= len(data):
            try:
                # Look for float values that could be texture coordinates
                coords = []
                for i in range(0, 64, 4):
                    val = struct.unpack('f', data[pos+i:pos+i+4])[0]
                    if 0 <= val <= 1:  # Valid texture coordinate range
                        coords.append(val)
                
                if len(coords) >= 4:  # At least 2 texture coordinate pairs
                    # Look for associated image data
                    end = pos + 64
                    while end < min(pos + 4096, len(data) - 4):
                        if data[end:end+4] == b'\x00\x00\x00\x00':
                            break
                        end += 1
                    
                    headers.append({
                        'offset': pos,
                        'size': end - pos,
                        'type': 'textured_geometry'
                    })
                    pos = end
                    continue
            except:
                pass
        
        pos += 1
    
    return headers

def process_texture_coordinates(data: bytes, width: int, height: int) -> np.ndarray:
    """Process texture coordinates and create UV map visualization"""
    # Extract UV coordinates
    coords = []
    for i in range(0, min(len(data), 256), 8):
        try:
            u = struct.unpack('f', data[i:i+4])[0]
            v = struct.unpack('f', data[i+4:i+8])[0]
            if 0 <= u <= 1 and 0 <= v <= 1:
                coords.append((u, v))
        except:
            break
    
    if not coords:
        return None
    
    # Create UV map visualization
    uv_map = np.zeros((height, width, 3), dtype=np.uint8)
    
    # Draw UV grid
    for i in range(0, width, width//8):
        uv_map[:,i] = [32, 32, 32]
    for i in range(0, height, height//8):
        uv_map[i,:] = [32, 32, 32]
    
    # Draw UV points and connections
    if len(coords) >= 3:
        for i in range(len(coords)):
            u, v = coords[i]
            x = int(u * (width-1))
            y = int(v * (height-1))
            
            # Draw point
            for dx in [-1, 0, 1]:
                for dy in [-1, 0, 1]:
                    if 0 <= x+dx < width and 0 <= y+dy < height:
                        uv_map[y+dy, x+dx] = [255, 255, 255]
            
            # Draw lines between points
            if i > 0:
                prev_u, prev_v = coords[i-1]
                prev_x = int(prev_u * (width-1))
                prev_y = int(prev_v * (height-1))
                
                # Simple line drawing
                steps = max(abs(x - prev_x), abs(y - prev_y)) + 1
                for t in range(steps):
                    px = int(prev_x + (x - prev_x) * t / steps)
                    py = int(prev_y + (y - prev_y) * t / steps)
                    if 0 <= px < width and 0 <= py < height:
                        uv_map[py, px] = [0, 255, 0]
    
    return uv_map

def extract_image_data(data: bytes, header: dict) -> tuple:
    """Extract and process image data from a section"""
    offset = header['offset']
    size = header['size']
    section = data[offset:offset+size]
    
    # Different handling based on type
    if header['type'] == 'sprite_standard':
        # Standard sprite format
        width = struct.unpack('<H', section[4:6])[0] if len(section) > 6 else 0
        height = struct.unpack('<H', section[6:8])[0] if len(section) > 8 else 0
        data_offset = 16
    elif header['type'] == 'embedded_image':
        # Try to detect embedded image format
        if section.startswith(b'\x89PNG'):
            # PNG format
            try:
                with io.BytesIO(section) as bio:
                    img = Image.open(bio)
                    width, height = img.size
                    return width, height, section
            except:
                pass
        data_offset = 0
        width = height = 0
    elif header['type'] == 'raw_image':
        # Try to detect dimensions from data patterns
        data_offset = 0
        width = height = 0
        for size in [8, 16, 32, 64, 128, 256]:
            if len(section) % size == 0:
                height = len(section) // size
                if 0.5 <= height/size <= 2:  # Reasonable aspect ratio
                    width = size
                    break
    else:  # textured_geometry
        # Look for dimension info in float data
        data_offset = 64  # Skip transform data
        width = height = 0
        
        # Try to detect texture dimensions from coordinates
        coords = []
        for i in range(0, min(len(section), 256), 8):
            try:
                u = struct.unpack('f', section[i:i+4])[0]
                v = struct.unpack('f', section[i+4:i+8])[0]
                if 0 <= u <= 1 and 0 <= v <= 1:
                    coords.append((u, v))
            except:
                break
        
        if coords:
            # Use coordinate range to estimate dimensions
            u_vals = [u for u,v in coords]
            v_vals = [v for u,v in coords]
            if u_vals and v_vals:
                u_range = max(u_vals) - min(u_vals)
                v_range = max(v_vals) - min(v_vals)
                if u_range > 0 and v_range > 0:
                    aspect = u_range / v_range
                    if 0.25 <= aspect <= 4:  # Reasonable aspect ratio
                        base_size = int(np.sqrt(len(section) - data_offset))
                        width = int(base_size * aspect)
                        height = int(base_size / aspect)
    
    # If dimensions still not found, try common sizes
    if width == 0 or height == 0:
        data_size = len(section) - data_offset
        
        # Try common sprite dimensions
        common_sizes = [
            (8,8), (16,16), (32,32), (64,64), (128,128), (256,256),  # Square
            (32,8), (64,32), (128,64), (256,128),  # Wide
            (8,32), (32,64), (64,128), (128,256)   # Tall
        ]
        
        for test_width, test_height in common_sizes:
            # Try different bits per pixel
            for bpp in [4, 8, 16, 24, 32]:
                if data_size == (test_width * test_height * bpp) // 8:
                    width, height = test_width, test_height
                    break
            if width != 0:
                break
    
    # If still no valid dimensions, make a reasonable guess
    if width == 0 or height == 0:
        # Assume square and 8bpp as fallback
        side = int(np.sqrt(size - data_offset))
        width = height = side if side > 0 else 32
    
    return width, height, section[data_offset:]

def combine_color_channels(ch0: np.ndarray, ch1: np.ndarray, ch2: np.ndarray) -> Image.Image:
    """Combine separate color channels into a single RGB image"""
    if ch0.shape != ch1.shape or ch1.shape != ch2.shape:
        return None
        
    height, width = ch0.shape
    
    # Try different channel combinations
    combinations = [
        # RGB
        (ch0, ch1, ch2),
        # BGR
        (ch2, ch1, ch0),
        # HSV-like
        (ch0, ch2, ch1)
    ]
    
    best_img = None
    best_variance = -1
    
    for r, g, b in combinations:
        # Create RGB image
        rgb_data = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Normalize each channel
        def normalize_channel(channel):
            min_val = np.min(channel)
            max_val = np.max(channel)
            if max_val == min_val:
                return channel
            return ((channel - min_val) * 255 / (max_val - min_val)).astype(np.uint8)
        
        rgb_data[:,:,0] = normalize_channel(r)
        rgb_data[:,:,1] = normalize_channel(g)
        rgb_data[:,:,2] = normalize_channel(b)
        
        # Calculate image variance as a measure of information content
        variance = np.var(rgb_data)
        
        if variance > best_variance:
            best_variance = variance
            best_img = Image.fromarray(rgb_data, 'RGB')
    
    return best_img

def try_decode_formats(data: bytes, width: int, height: int, header_type: str) -> list:
    """Try different image format decodings"""
    images = []
    
    # For textured geometry, try UV map visualization first
    if header_type == 'textured_geometry':
        uv_map = process_texture_coordinates(data, width, height)
        if uv_map is not None:
            img = Image.fromarray(uv_map, 'RGB')
            images.append(('uv_map', img))
    
    # Try 8-bit grayscale and color channels
    try:
        if len(data) >= width * height:
            # Extract each color channel
            channels = []
            for i in range(3):
                start = i * width * height
                end = start + width * height
                if start < len(data):
                    channel_data = np.frombuffer(data[start:end], dtype=np.uint8)
                    if len(channel_data) == width * height:
                        channel = channel_data.reshape((height, width))
                    else:
                        # If channel is incomplete, try to fill with meaningful data
                        channel = np.zeros((height, width), dtype=np.uint8)
                        valid_data = min(len(channel_data), width * height)
                        if valid_data > 0:
                            channel.flat[:valid_data] = channel_data[:valid_data]
                    channels.append(channel)
                else:
                    # If channel is missing, try to derive from other channels
                    if channels:
                        channel = channels[-1].copy()
                    else:
                        channel = np.zeros((height, width), dtype=np.uint8)
                    channels.append(channel)
            
            # Save grayscale version (using first channel)
            img = Image.fromarray(channels[0], 'L')
            images.append(('8bit_gray', img))
            
            # Save individual channels
            for i, channel in enumerate(channels):
                img = Image.fromarray(channel, 'L')
                images.append((f'8bit_color_ch{i}', img))
            
            # Combine channels into RGB
            rgb_img = combine_color_channels(channels[0], channels[1], channels[2])
            if rgb_img:
                # Convert to RGBA to ensure proper saving
                rgba_img = rgb_img.convert('RGBA')
                images.append(('8bit_color', rgba_img))
    except Exception as e:
        print(f"Error processing color channels: {e}")
    
    # Try 4-bit formats
    try:
        if len(data) >= (width * height) // 2:
            img_data = np.zeros((height, width), dtype=np.uint8)
            for i in range(width * height // 2):
                byte = data[i]
                img_data[i*2//width, (i*2)%width] = (byte >> 4) & 0x0F
                img_data[i*2//width, (i*2)%width + 1] = byte & 0x0F
            
            # Standard 4-bit
            img = Image.fromarray(img_data * 16, 'L')
            images.append(('4bit', img))
            
            # Enhanced contrast
            img = Image.fromarray(img_data * 32, 'L')
            images.append(('4bit_contrast', img))
            
            # Try color mapping
            color_map = np.zeros((height, width, 3), dtype=np.uint8)
            for y in range(height):
                for x in range(width):
                    val = img_data[y,x]
                    if val < 4:
                        color_map[y,x] = [val*64, 0, 0]  # Reds
                    elif val < 8:
                        color_map[y,x] = [0, (val-4)*64, 0]  # Greens
                    elif val < 12:
                        color_map[y,x] = [0, 0, (val-8)*64]  # Blues
                    else:
                        color_map[y,x] = [(val-12)*64] * 3  # Grays
            img = Image.fromarray(color_map, 'RGB')
            images.append(('4bit_color_mapped', img))
    except Exception as e:
        print(f"Error processing 4-bit formats: {e}")
    
    return images

def analyze_transform_data(transform_data: bytes) -> dict:
    """Analyze transform matrix data to understand animation parameters"""
    transforms = []
    
    # Transform data is typically stored as 4x4 matrices (16 floats, 64 bytes total)
    matrix = []
    for i in range(0, len(transform_data), 4):
        try:
            value = struct.unpack('f', transform_data[i:i+4])[0]
            matrix.append(value)
        except:
            break
    
    # Analyze what the transform does
    analysis = {
        'translation': [],
        'scale': [],
        'rotation': [],
        'raw_values': matrix
    }
    
    if len(matrix) >= 12:  # Need at least 3x4 matrix for basic transforms
        # Translation is typically in the fourth column
        if abs(matrix[3]) > 0.0001:  # X translation
            analysis['translation'].append(('X', matrix[3]))
        if abs(matrix[7]) > 0.0001:  # Y translation
            analysis['translation'].append(('Y', matrix[7]))
        if abs(matrix[11]) > 0.0001:  # Z translation
            analysis['translation'].append(('Z', matrix[11]))
        
        # Scale can be found in diagonal elements
        if abs(matrix[0] - 1.0) > 0.0001:  # X scale
            analysis['scale'].append(('X', matrix[0]))
        if abs(matrix[5] - 1.0) > 0.0001:  # Y scale
            analysis['scale'].append(('Y', matrix[5]))
        if abs(matrix[10] - 1.0) > 0.0001:  # Z scale
            analysis['scale'].append(('Z', matrix[10]))
        
        # Rotation can be detected by non-zero off-diagonal elements
        if abs(matrix[1]) > 0.0001 or abs(matrix[2]) > 0.0001:
            angle = math.atan2(matrix[1], matrix[2]) * 180 / math.pi
            analysis['rotation'].append(('X', angle))
        if abs(matrix[4]) > 0.0001 or abs(matrix[6]) > 0.0001:
            angle = math.atan2(matrix[4], matrix[6]) * 180 / math.pi
            analysis['rotation'].append(('Y', angle))
        if abs(matrix[8]) > 0.0001 or abs(matrix[9]) > 0.0001:
            angle = math.atan2(matrix[8], matrix[9]) * 180 / math.pi
            analysis['rotation'].append(('Z', angle))
    
    return analysis

def combine_related_textures(data: bytes, headers: list) -> dict:
    """Combine related textures based on their UV maps and data"""
    texture_sets = {}
    print("\nAnalyzing texture data:")
    
    # Group related textures
    for i, header in enumerate(headers):
        if header['type'] != 'textured_geometry':
            continue
            
        print(f"\nProcessing texture {i}:")
        section = data[header['offset']:header['offset']+header['size']]
        print(f"  Section size: {len(section)} bytes")
        
        # Extract and analyze transform data
        transform_data = section[:64]
        print(f"  Transform data size: {len(transform_data)} bytes")
        transform_analysis = analyze_transform_data(transform_data)
        print("\n  Transform Analysis:")
        if transform_analysis['translation']:
            print("    Translations:", transform_analysis['translation'])
        if transform_analysis['scale']:
            print("    Scaling:", transform_analysis['scale'])
        if transform_analysis['rotation']:
            print("    Rotations:", transform_analysis['rotation'])
        
        # Extract UV coordinates
        coords = []
        for j in range(64, min(len(section), 320), 8):
            try:
                u = struct.unpack('f', section[j:j+4])[0]
                v = struct.unpack('f', section[j+4:j+8])[0]
                if 0 <= u <= 1 and 0 <= v <= 1:
                    coords.append((u, v))
            except:
                break
        
        print(f"  Found {len(coords)} UV coordinates:")
        for idx, (u, v) in enumerate(coords):
            print(f"    Point {idx}: U={u:.3f}, V={v:.3f}")
        
        if not coords:
            continue
            
        # Calculate texture size
        tex_width = tex_height = 64  # Default size
        data_start = 64 + len(coords) * 8
        tex_data = section[data_start:]
        print(f"  Texture data starts at offset {data_start}, size: {len(tex_data)} bytes")
        
        # Try to detect actual texture size
        if len(tex_data) >= 32*32:  # Lower minimum size threshold
            # Look for color patterns
            test_data = np.frombuffer(tex_data[:min(len(tex_data), 64*64)], dtype=np.uint8)
            unique_values = len(np.unique(test_data))
            print(f"  Found {unique_values} unique color values")
            
            # Create texture image
            tex_img = np.zeros((tex_height, tex_width), dtype=np.uint8)
            print(f"  Creating {tex_width}x{tex_height} texture image")
            
            # Convert 8-bit data to grayscale
            for y in range(tex_height):
                for x in range(tex_width):
                    if y*tex_width + x < len(tex_data):
                        tex_img[y,x] = tex_data[y*tex_width + x]
            
            # Store texture info
            key = f"texture_set_{len(texture_sets)}"
            if key not in texture_sets:
                texture_sets[key] = {
                    'textures': [],
                    'coords': [],
                    'transforms': [],
                    'analysis': []
                }
            
            texture_sets[key]['textures'].append(tex_img)
            texture_sets[key]['coords'].append(coords)
            texture_sets[key]['transforms'].append(transform_data)
            texture_sets[key]['analysis'].append(transform_analysis)
            print(f"  Added to texture set {key}")
    
    print(f"\nCreated {len(texture_sets)} texture sets")
    return texture_sets

def save_combined_textures(texture_sets: dict, output_dir: str):
    """Save combined texture sets with UV mapping visualization"""
    print("\nSaving combined textures:")
    
    # Create sequences subdirectory
    combined_dir = os.path.join(output_dir, 'combined')
    os.makedirs(combined_dir, exist_ok=True)
    print(f"  Output directory: {combined_dir}")
    
    for set_name, set_data in texture_sets.items():
        print(f"\nProcessing {set_name}:")
        if not set_data['textures']:
            print("  No textures found, skipping")
            continue
            
        print(f"  Found {len(set_data['textures'])} textures")
        print(f"  Found {len(set_data['coords'])} coordinate sets")
        
        # Create combined texture image
        combined_size = 128  # Output size
        combined_img = np.zeros((combined_size, combined_size, 4), dtype=np.uint8)
        print(f"  Creating {combined_size}x{combined_size} combined image")
        
        # For each texture in the set
        for tex_idx, (texture, coords) in enumerate(zip(set_data['textures'], set_data['coords'])):
            print(f"    Processing texture {tex_idx}:")
            print(f"      Texture shape: {texture.shape}")
            print(f"      Coordinates: {len(coords)} points")
            
            # Create UV visualization
            uv_img = np.zeros((combined_size, combined_size, 4), dtype=np.uint8)
            
            # Draw UV grid
            for i in range(0, combined_size, 16):
                uv_img[:,i] = [32, 32, 32, 255]
                uv_img[i,:] = [32, 32, 32, 255]
            
            # Draw texture mapped according to UV coordinates
            if len(coords) >= 1:  # Lower minimum coordinate requirement
                # Convert texture to RGBA if needed
                if len(texture.shape) == 2:
                    print("      Converting grayscale to RGBA")
                    texture = np.dstack((texture, texture, texture, np.full(texture.shape, 255)))
                elif texture.shape[2] == 3:
                    print("      Converting RGB to RGBA")
                    texture = np.dstack((texture, np.full(texture.shape[:2], 255)))
                
                print(f"      Final texture shape: {texture.shape}")
                
                # Draw points and lines for coordinates
                for i, (u, v) in enumerate(coords):
                    x = int(u * (combined_size-1))
                    y = int(v * (combined_size-1))
                    
                    # Draw point
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            if 0 <= x+dx < combined_size and 0 <= y+dy < combined_size:
                                uv_img[y+dy, x+dx] = [255, 255, 255, 255]
                    
                    # Draw line to next point
                    if i > 0:
                        prev_u, prev_v = coords[i-1]
                        prev_x = int(prev_u * (combined_size-1))
                        prev_y = int(prev_v * (combined_size-1))
                        
                        # Simple line drawing
                        steps = max(abs(x - prev_x), abs(y - prev_y)) + 1
                        for t in range(steps):
                            px = int(prev_x + (x - prev_x) * t / steps)
                            py = int(prev_y + (y - prev_y) * t / steps)
                            if 0 <= px < combined_size and 0 <= py < combined_size:
                                uv_img[py, px] = [0, 255, 0, 255]
                
                # Map texture based on coordinates
                if len(coords) >= 3:
                    # Create triangles from UV coordinates
                    tri_count = (len(coords) - 2)
                    print(f"      Creating {tri_count} triangles")
                    
                    for i in range(0, len(coords)-2):
                        tri_uvs = [coords[0], coords[i+1], coords[i+2]]  # Fan triangulation
                        # Convert UV to image coordinates
                        tri_points = [(int(u*combined_size), int(v*combined_size)) 
                                    for u,v in tri_uvs]
                        
                        # Simple triangle rasterization
                        min_x = max(0, min(p[0] for p in tri_points))
                        max_x = min(combined_size-1, max(p[0] for p in tri_points))
                        min_y = max(0, min(p[1] for p in tri_points))
                        max_y = min(combined_size-1, max(p[1] for p in tri_points))
                        
                        for y in range(min_y, max_y+1):
                            for x in range(min_x, max_x+1):
                                # Simple point-in-triangle test
                                p = np.array([x, y])
                                in_tri = True
                                for j in range(3):
                                    p1 = np.array(tri_points[j])
                                    p2 = np.array(tri_points[(j+1)%3])
                                    if np.cross(p2-p1, p-p1) < 0:
                                        in_tri = False
                                        break
                                
                                if in_tri:
                                    # Sample texture using barycentric coordinates
                                    total_area = abs(np.cross(
                                        np.array(tri_points[1])-np.array(tri_points[0]),
                                        np.array(tri_points[2])-np.array(tri_points[0])
                                    ))
                                    if total_area > 0:
                                        w1 = abs(np.cross(
                                            np.array(tri_points[1])-p,
                                            np.array(tri_points[2])-p
                                        )) / total_area
                                        w2 = abs(np.cross(
                                            np.array(tri_points[2])-p,
                                            np.array(tri_points[0])-p
                                        )) / total_area
                                        w3 = 1 - w1 - w2
                                        
                                        # Get texture coordinates
                                        tx = int(w1*texture.shape[1])
                                        ty = int(w2*texture.shape[0])
                                        
                                        if 0 <= tx < texture.shape[1] and 0 <= ty < texture.shape[0]:
                                            uv_img[y,x] = texture[ty,tx]
            
            # Blend with combined image
            alpha = uv_img[:,:,3:4].astype(float) / 255.0
            combined_img = (combined_img * (1-alpha) + uv_img * alpha).astype(np.uint8)
            
            # Save individual texture visualization
            tex_path = os.path.join(combined_dir, f"{set_name}_tex{tex_idx}_combined.png")
            Image.fromarray(combined_img, 'RGBA').save(tex_path)
            print(f"      Saved texture visualization: {tex_path}")
        
        # Save final combined image
        combined_path = os.path.join(combined_dir, f"{set_name}_combined.png")
        Image.fromarray(combined_img, 'RGBA').save(combined_path)
        print(f"  Saved combined texture: {combined_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract sprites/textures from MDL files')
    parser.add_argument('file', help='MDL file to analyze')
    parser.add_argument('--output-dir', default='extracted_sprites', help='Output directory')
    args = parser.parse_args()
    
    with open(args.file, 'rb') as f:
        data = f.read()
    
    # Create output directories
    output_dir = os.path.join(args.output_dir, Path(args.file).stem)
    os.makedirs(output_dir, exist_ok=True)
    combined_dir = os.path.join(output_dir, 'combined')
    os.makedirs(combined_dir, exist_ok=True)
    print(f"\nOutput directory: {output_dir}")
    print(f"Combined directory: {combined_dir}")
    
    # Find potential sprite sections
    headers = find_sprite_headers(data)
    print(f"\nFound {len(headers)} potential sprite/texture sections")
    
    # Process each section
    for i, header in enumerate(headers):
        print(f"\nProcessing section {i} at offset 0x{header['offset']:x}")
        print(f"  Type: {header['type']}")
        print(f"  Size: {header['size']} bytes")
        
        # Extract image data
        width, height, img_data = extract_image_data(data, header)
        print(f"  Dimensions: {width}x{height}")
        
        # Try different format decodings
        images = try_decode_formats(img_data, width, height, header['type'])
        
        # Save successful decodings
        for fmt, img in images:
            filename = f"sprite_{i:03d}_{fmt}.png"
            filepath = os.path.join(output_dir, filename)
            img.save(filepath)
            print(f"  Saved {fmt} version as: {filename}")
        
        # Save raw data for manual analysis
        raw_filename = f"sprite_{i:03d}_raw.bin"
        raw_filepath = os.path.join(output_dir, raw_filename)
        with open(raw_filepath, 'wb') as f:
            f.write(img_data)
        print(f"  Saved raw data as: {raw_filename}")
    
    # After finding headers:
    print("\nCombining related textures...")
    texture_sets = combine_related_textures(data, headers)
    save_combined_textures(texture_sets, output_dir)

if __name__ == '__main__':
    main() 