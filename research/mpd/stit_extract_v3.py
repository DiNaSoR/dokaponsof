#!/usr/bin/env python3
"""
S_TIT File Format Extractor V3
Corrected header structure and extraction logic
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
        # Fixed header size
        self.header_size = 0x44
        
        # Validate magic number
        magic = data[0:4]
        if magic != b'STIT':
            # Check for magic number at 0x0A
            magic2 = data[0x0A:0x11]
            if magic2 != bytes([0x35] + [0x55] * 6):
                raise ValueError(f"Invalid magic number: {magic} and {magic2}")
            
        # Parse version
        self.version = struct.unpack("<I", data[4:8])[0]
        
        # Parse palette offset
        self.palette_offset = struct.unpack("<I", data[0x18:0x1C])[0]
        if self.palette_offset == 0:
            self.palette_offset = self.header_size  # Default to header size if 0
            
        # Parse dimensions
        # Width is 16 pixels (fixed)
        self.width = 16
        
        # Calculate height based on file size
        data_size = len(data) - self.header_size
        # Each row takes 32 bytes (8 bytes per plane * 4 planes)
        self.height = data_size // (8 * 4)
        
        # Fixed stride of 8 bytes per plane (16 pixels in 4-bit format)
        self.stride = 8
        
        print(f"DEBUG: Header size: {self.header_size}")
        print(f"DEBUG: Palette offset: {self.palette_offset}")
        print(f"DEBUG: Width: {self.width}")
        print(f"DEBUG: Height: {self.height}")
        print(f"DEBUG: Stride: {self.stride}")

def decode_color(value):
    """Decode a BGR555 color value to RGB."""
    b = ((value >> 10) & 0x1F) << 3
    g = ((value >> 5) & 0x1F) << 3
    r = (value & 0x1F) << 3
    return (r, g, b)

def read_palette(data, offset):
    """Read the 16-color palette."""
    palette = []
    logger.debug(f"Reading palette from offset 0x{offset:04x}")
    
    # Read the palette from the file
    all_black = True
    for i in range(16):
        color_offset = offset + i * 2
        if color_offset + 2 > len(data):
            logger.warning(f"Palette truncated at color {i}")
            break
            
        color = struct.unpack('<H', data[color_offset:color_offset + 2])[0]
        r, g, b = decode_color(color)
        palette.extend([r, g, b])
        logger.debug(f"Color {i:2d}: RGB({r:3d},{g:3d},{b:3d})")
        if r != 0 or g != 0 or b != 0:
            all_black = False
    
    # If all colors are black (except maybe one), use a grayscale palette instead
    if all_black:
        logger.info("Using grayscale palette since original palette is all black")
        palette = []
        for i in range(16):
            val = (i * 16)  # Scale 0-15 to 0-240
            palette.extend([val, val, val])
    
    # Fill remaining entries if needed
    while len(palette) < 48:
        val = (len(palette) // 3) * 16
        palette.extend([val, val, val])
    
    return palette

def extract_planar_data(data, header):
    """Extract image data in planar format."""
    width = header.width
    height = header.height
    stride = header.stride
    pixels = np.zeros((height, width), dtype=np.uint8)
    
    logger.debug(f"Extracting {width}x{height} image with stride {stride}")
    
    # Process 4 bit planes (16 colors = 4 bits per pixel)
    for y in range(height):
        for plane in range(4):
            plane_offset = header.header_size + (y * stride * 4) + (plane * stride)
            if plane_offset + stride > len(data):
                logger.warning(f"Data truncated at y={y}, plane={plane}")
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
    
    # Debug pixel value distribution
    values, counts = np.unique(pixels, return_counts=True)
    logger.debug("Pixel value distribution:")
    for value, count in zip(values, counts):
        logger.debug(f"Value {value:2d}: {count:6d} pixels ({count/(width*height)*100:5.1f}%)")
    
    return pixels

def extract_stit_file(filename):
    """Extract a S_TIT file to PNG."""
    with open(filename, 'rb') as f:
        data = f.read()
    
    logger.info(f"Processing file: {filename} ({len(data)} bytes)")
    
    # Parse header
    header = STITHeader(data)
    
    # Extract image data
    pixels = extract_planar_data(data, header)
    
    # Create grayscale version
    grayscale = Image.fromarray(pixels * 16, 'L')  # Scale 0-15 to 0-240
    gray_path = os.path.splitext(filename)[0] + '_gray.png'
    grayscale.save(gray_path)
    logger.info(f"Saved grayscale image to: {gray_path}")
    
    # Create color version
    img = Image.fromarray(pixels, 'P')
    palette = read_palette(data, header.palette_offset)
    img.putpalette(palette)
    output_path = os.path.splitext(filename)[0] + '_extracted.png'
    img.save(output_path)
    logger.info(f"Saved color image to: {output_path}")
    
    # Save raw pixel data for analysis
    raw_path = os.path.splitext(filename)[0] + '_raw.bin'
    with open(raw_path, 'wb') as f:
        f.write(pixels.tobytes())
    logger.info(f"Saved raw pixel data to: {raw_path}")
    
    # Save cropped versions
    non_zero_rows = np.any(pixels != 0, axis=1)
    if np.any(non_zero_rows):
        first_row = np.argmax(non_zero_rows)
        last_row = len(non_zero_rows) - np.argmax(non_zero_rows[::-1]) - 1
        logger.debug(f"Content rows: {first_row} to {last_row} (height: {last_row - first_row + 1})")
        
        # Crop grayscale
        cropped_gray = grayscale.crop((0, first_row, header.width, last_row + 1))
        crop_gray_path = os.path.splitext(filename)[0] + '_cropped_gray.png'
        cropped_gray.save(crop_gray_path)
        logger.info(f"Saved cropped grayscale to: {crop_gray_path}")
        
        # Crop color
        cropped = img.crop((0, first_row, header.width, last_row + 1))
        crop_path = os.path.splitext(filename)[0] + '_cropped.png'
        cropped.save(crop_path)
        logger.info(f"Saved cropped color image to: {crop_path}")
        
        # Debug info about content
        content_rows = [i for i in range(len(pixels)) if np.any(pixels[i] != 0)]
        gaps = np.diff(content_rows)
        logger.debug(f"First 10 content rows: {content_rows[:10]}")
        logger.debug(f"Gaps between content rows: {gaps[:10]}")

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
