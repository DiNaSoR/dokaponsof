import os
import struct
import sys
from dataclasses import dataclass
from typing import List
from PIL import Image
import numpy as np
from tex_export import decompress_lz77  # Add this import

@dataclass
class SpriteHeader:
    size: int
    width: int
    height: int
    bpp: int  # bits per pixel
    palette_offset: int

@dataclass
class Frame:
    offset: int
    duration: int
    flags: int
    data: bytes

def parse_sprite_header(data):
    """Parse the sprite header section"""
    # First check the actual data
    print("\nFirst 32 bytes:")
    for i in range(0, min(32, len(data)), 4):
        block = data[i:i+4]
        hex_values = ' '.join(f'{b:02x}' for b in block)
        print(f"Offset {i:02x}: {hex_values}")

    # Check for "Sequence" header
    if data.startswith(b'Sequence'):
        # Find the embedded PNG data
        png_start = data.find(b'\x89PNG')
        if png_start != -1:
            # Get PNG dimensions by reading IHDR chunk
            width = struct.unpack('>I', data[png_start+16:png_start+20])[0]
            height = struct.unpack('>I', data[png_start+20:png_start+24])[0]
            
            header = SpriteHeader(
                size=len(data),
                width=width,
                height=height,
                bpp=8,  # PNG uses 8 bits per channel
                palette_offset=0
            )
            return header, png_start
    else:
        # Original CSFIX format parsing
        header = SpriteHeader(
            size=struct.unpack('<H', data[0:2])[0],
            width=struct.unpack('<H', data[2:4])[0], 
            height=struct.unpack('<H', data[4:6])[0],
            bpp=data[6],
            palette_offset=struct.unpack('<H', data[7:9])[0]
        )
        return header, 0

def parse_frame_data(data, offset):
    """Parse a single frame's data"""
    # Debug: print the frame header bytes
    print(f"\nFrame header at offset 0x{offset:04x}:")
    header_bytes = data[offset:offset+8]
    print(' '.join(f'{b:02x}' for b in header_bytes))
    
    frame_header = struct.unpack('<HHH', data[offset:offset+6])
    frame_size = frame_header[2] if frame_header[2] < 1000 else 0  # Sanity check
    
    return Frame(
        offset=offset,
        duration=frame_header[0],
        flags=frame_header[1],
        data=data[offset+6:offset+6+frame_size] if frame_size > 0 else b''
    )

def create_sprite_visualization(sprite_data, header, output_path):
    """Create a visualization of the sprite data"""
    try:
        png_start = sprite_data.find(b'\x89PNG')
        if png_start != -1:
            # Find end of PNG data
            png_end = sprite_data.find(b'IEND', png_start) + 8
            if png_end != -1:
                # Extract and save PNG directly
                png_data = sprite_data[png_start:png_end]
                with open(output_path, 'wb') as f:
                    f.write(png_data)
                return True

        # Original format handling
        if header.bpp == 4:  # 16 colors
            pixels = np.zeros((header.height, header.width), dtype=np.uint8)
            byte_idx = 0
            
            for y in range(header.height):
                for x in range(0, header.width, 2):
                    if byte_idx >= len(sprite_data):
                        break
                    byte = sprite_data[byte_idx]
                    pixels[y,x] = (byte >> 4) & 0x0F
                    if x+1 < header.width:
                        pixels[y,x+1] = byte & 0x0F
                    byte_idx += 1
                    
            # Create grayscale image
            img = Image.fromarray(pixels * 16, mode='L')
            img.save(output_path)
            return True
            
    except Exception as e:
        print(f"Error creating visualization: {str(e)}")
        return False

def parse_sequence_header(data, offset):
    """Parse the sequence header and frames"""
    seq_header = data[offset:offset+16]
    if not seq_header.startswith(b'Sequ'):
        return None
    
    print("\nSequence Header:")
    print("Magic:", seq_header[:4].decode())
    print("Header bytes:", ' '.join(f'{b:02x}' for b in seq_header[4:16]))
    
    # Parse frame count from offset 0x14
    frame_count = data[offset + 0x14]
    print(f"Frame count: {frame_count}")
    
    # Parse frames
    frames = []
    current_offset = offset + 0x20  # Skip header
    
    for i in range(frame_count):
        if current_offset + 4 > len(data):
            break
            
        frame_data = data[current_offset:current_offset+4]
        duration = struct.unpack('<H', frame_data[0:2])[0]
        flags = frame_data[2]
        size = frame_data[3]
        
        frames.append(Frame(
            offset=current_offset,
            duration=duration,
            flags=flags,
            data=data[current_offset+4:current_offset+4+size]
        ))
        
        current_offset += 4 + size
        
    return frames

def parse_spranm(data):
    """Parse and display information about a .spranm file"""
    # Try LZ77 decompression first if needed
    if data.startswith(b'LZ77'):
        decompressed = decompress_lz77(data)
        if decompressed:
            data = decompressed
            print("Successfully decompressed LZ77 data")
            print(f"Decompressed size: {len(data)} bytes")
    
    print("Animation Data Analysis:")
    print("-----------------------")
    
    # Parse sprite header
    sprite_header, png_offset = parse_sprite_header(data)
    print(f"\nSprite Header:")
    print(f"Size: {sprite_header.size} bytes")
    print(f"Dimensions: {sprite_header.width}x{sprite_header.height}")
    print(f"Bits per pixel: {sprite_header.bpp}")
    
    # Extract sprite data
    sprite_data = data[16:sprite_header.size]  # Skip initial header
    print(f"Sprite data size: {len(sprite_data)} bytes")
    
    # Look for sequence data
    seq_offset = data.find(b'Sequ')
    if seq_offset > 0:
        print(f"\nFound sequence data at offset: 0x{seq_offset:04x}")
        frames = parse_sequence_header(data, seq_offset)
        
        if frames:
            print(f"\nFound {len(frames)} frames:")
            for i, frame in enumerate(frames):
                print(f"\nFrame {i}:")
                print(f"  Duration: {frame.duration}")
                print(f"  Flags: 0x{frame.flags:02x}")
                print(f"  Data size: {len(frame.data)} bytes")
    
    # Create visualizations
    try:
        # Save main sprite sheet
        output_path = "sprite_sheet.png"
        if create_sprite_visualization(data, sprite_header, output_path):
            print(f"\nSaved sprite sheet as: {output_path}")
            
    except Exception as e:
        print(f"Error creating visualizations: {str(e)}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python spranm_info.py <spranm_file>")
        return
        
    file_path = sys.argv[1]
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found")
        return
        
    with open(file_path, 'rb') as f:
        data = f.read()
        
    parse_spranm(data)

if __name__ == '__main__':
    main() 