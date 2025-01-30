#!/usr/bin/env python3
"""
S_TIT File Format Extractor V2
Focused extractor for S_TIT format sprite/image files
"""

import struct
import os
from pathlib import Path
import numpy as np
from PIL import Image
import logging
import argparse

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class STITHeader:
    def __init__(self, data):
        # Validate magic number
        if data[0x0A:0x11] != bytes([0x35] + [0x55] * 6):
            raise ValueError("Invalid magic number")
        
        # Fixed header values
        self.data_offset = 0x44
        self.palette_offset = 0x18
        
        # Parse version (at 0x12)
        self.version = data[0x12]
        
        # Parse dimensions
        # Width at 0x20, height at 0x2A, stride at 0x2C
        self.width = struct.unpack('<H', data[0x20:0x22])[0]
        self.height = struct.unpack('<H', data[0x2A:0x2C])[0]
        self.stride = struct.unpack('<H', data[0x2C:0x2E])[0]
        
        # Validate and adjust dimensions
        if self.width == 0 or self.width > 512:
            self.width = 256
        if self.height == 0 or self.height > 512:
            self.height = self.width
        if self.stride == 0:
            self.stride = ((self.width + 31) // 32) * 4
        
        logger.debug(f"Header values: version={self.version}, width={self.width}, height={self.height}, stride={self.stride}")

def decode_color(value):
    """Decode a BGR555 color value to RGB."""
    b = ((value >> 10) & 0x1F) << 3
    g = ((value >> 5) & 0x1F) << 3
    r = (value & 0x1F) << 3
    return (r, g, b)

def read_palette(data, offset):
    """Read the 16-color palette."""
    palette = []
    for i in range(16):
        color = struct.unpack('<H', data[offset + i*2:offset + i*2 + 2])[0]
        r, g, b = decode_color(color)
        palette.extend([r, g, b])
    return palette

def extract_planar_data(data, header):
    """Extract image data in planar format."""
    width = header.width
    height = header.height
    stride = header.stride
    pixels = np.zeros((height, width), dtype=np.uint8)
    
    # Process 4 bit planes (16 colors = 4 bits per pixel)
    for y in range(height):
        for plane in range(4):
            plane_offset = header.data_offset + (y * stride * 4) + (plane * stride)
            if plane_offset >= len(data):
                continue
                
            plane_data = data[plane_offset:plane_offset + stride]
            
            # Process each byte in the plane
            for byte_idx, byte in enumerate(plane_data):
                for bit in range(8):
                    x = byte_idx * 8 + bit
                    if x >= width:
                        break
                    
                    # Extract bit and set in appropriate plane
                    bit_value = (byte >> (7-bit)) & 1
                    pixels[y, x] |= (bit_value << plane)
    
    return pixels

def extract_stit_file(filename):
    """Extract a S_TIT file to PNG."""
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Parse header
    header = STITHeader(data)
    
    # Extract image data
    pixels = extract_planar_data(data, header)
    
    # Create image
    img = Image.fromarray(pixels, 'P')
    
    # Read and apply palette
    palette = read_palette(data, header.palette_offset)
    img.putpalette(palette)
    
    # Save output
    output_path = os.path.splitext(filename)[0] + '_extracted.png'
    img.save(output_path)
    logger.info(f"Saved extracted image to: {output_path}")
    
    # Save raw pixel data for analysis
    raw_path = os.path.splitext(filename)[0] + '_raw.bin'
    with open(raw_path, 'wb') as f:
        f.write(pixels.tobytes())
    logger.info(f"Saved raw pixel data to: {raw_path}")

def main():
    parser = argparse.ArgumentParser(description='Extract S_TIT format files')
    parser.add_argument('file', help='S_TIT file to extract')
    args = parser.parse_args()
    
    try:
        extract_stit_file(args.file)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main()) 