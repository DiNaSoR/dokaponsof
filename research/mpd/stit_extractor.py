"""
S_TIT File Format Extractor
Attempts to extract sprite/image data from S_TIT format files.
"""

import struct
import os
from pathlib import Path
import numpy as np
from PIL import Image
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class STITHeader:
    def __init__(self, data):
        logger.info("Parsing header...")
        logger.debug(f"First 64 bytes: {data[:64].hex()}")
        
        # Validate magic number
        magic = data[0x0A:0x11]
        expected_magic = bytes([0x35] + [0x55] * 6)
        logger.debug(f"Found magic: {magic.hex()}")
        logger.debug(f"Expected: {expected_magic.hex()}")
        
        if magic != expected_magic:
            raise ValueError(f"Invalid magic number: {magic.hex()}")
        
        # Parse header fields
        self.magic = magic
        self.version = data[0x12]  # Single byte version
        self.data_offset = 0x44  # Fixed offset based on analysis
        
        # Analyze potential dimension fields
        logger.debug("Analyzing potential dimension fields:")
        for i in range(0x14, 0x40, 2):
            val = struct.unpack('<H', data[i:i+2])[0]
            if val > 0 and val < 1024:
                logger.debug(f"Offset 0x{i:02x}: {val}")
        
        # Try different dimension field combinations
        test_offsets = [
            (0x20, 0x22),  # Try these offsets for width/height
            (0x24, 0x26),
            (0x28, 0x2A),
            (0x2C, 0x2E)
        ]
        
        for width_off, height_off in test_offsets:
            width = struct.unpack('<H', data[width_off:width_off+2])[0]
            height = struct.unpack('<H', data[height_off:height_off+2])[0]
            if 0 < width <= 1024 and 0 < height <= 1024:
                logger.debug(f"Found potential dimensions at 0x{width_off:02x}/0x{height_off:02x}: {width}x{height}")
                self.width = width
                self.height = height
                break
        else:
            # If no valid dimensions found, try fixed values
            self.width = 256
            self.height = 256
            logger.warning("Using default dimensions")
        
        # Try to detect stride
        stride_candidates = []
        for i in range(0x20, 0x40, 2):
            stride = struct.unpack('<H', data[i:i+2])[0]
            if stride > 0 and stride <= self.width * 2:  # Reasonable stride values
                stride_candidates.append((i, stride))
        
        if stride_candidates:
            self.stride = stride_candidates[0][1]  # Use first reasonable stride value
            logger.debug(f"Found stride {self.stride} at offset 0x{stride_candidates[0][0]:02x}")
        else:
            self.stride = (self.width + 7) // 8  # Default to width-based stride
            logger.warning(f"Using calculated stride: {self.stride}")
        
        # Look for palette offset
        palette_candidates = []
        for i in range(0x30, 0x40, 2):
            offset = struct.unpack('<H', data[i:i+2])[0]
            if offset > 0 and offset < len(data) - 32:  # Need at least 32 bytes for palette
                # Check if location contains valid-looking color data
                try:
                    color = struct.unpack('<H', data[offset:offset+2])[0]
                    if 0 <= color <= 0x7FFF:  # Valid 15-bit color range
                        palette_candidates.append((i, offset))
                except:
                    continue
        
        if palette_candidates:
            self.palette_offset = palette_candidates[0][1]
            logger.debug(f"Found palette offset 0x{self.palette_offset:04x} at header offset 0x{palette_candidates[0][0]:02x}")
        else:
            self.palette_offset = 0
            logger.warning("No valid palette offset found")
        
        # Debug info
        logger.info("Final header values:")
        logger.info(f"Version: {self.version}")
        logger.info(f"Data Offset: 0x{self.data_offset:04x}")
        logger.info(f"Dimensions: {self.width}x{self.height}")
        logger.info(f"Stride: {self.stride}")
        logger.info(f"Palette Offset: 0x{self.palette_offset:04x}")

def decode_color(value):
    """Decode a 15/16-bit color value to RGB."""
    # Game uses BGR555 format (based on executable analysis)
    r = (value & 0x001F) << 3       # 5 bits red
    g = ((value >> 5) & 0x1F) << 3  # 5 bits green
    b = ((value >> 10) & 0x1F) << 3 # 5 bits blue
    return [r, g, b]

def read_palette(data, offset):
    """Read and decode the color palette."""
    logger.info(f"Reading palette from offset 0x{offset:04x}")
    palette = []
    
    # Read 16 colors (32 bytes, 2 bytes per color)
    for i in range(16):
        color_offset = offset + i * 2
        if color_offset + 2 > len(data):
            logger.warning(f"Palette data truncated at color {i}")
            break
            
        color = struct.unpack('<H', data[color_offset:color_offset + 2])[0]
        if color == 0:
            # Color 0 is transparent
            rgb = [0, 0, 0]
        else:
            rgb = decode_color(color)
            
        palette.extend(rgb)
        logger.debug(f"Color {i:3d}: 0x{color:04x} = RGB({rgb[0]:3d},{rgb[1]:3d},{rgb[2]:3d})")
    
    # Fill remaining palette entries with grayscale for debugging
    while len(palette) < 48:  # 16 colors * 3 channels
        val = (len(palette) // 3) * 16
        palette.extend([val, val, val])
    
    return palette

def extract_planar_data(data, header):
    """Extract data assuming planar organization."""
    logger.info("Attempting planar data extraction...")
    
    width = header.width
    height = header.height
    stride = header.stride if header.stride else ((width + 7) // 8)
    
    # Calculate bytes per plane
    bytes_per_plane = (width + 7) // 8  # 8 pixels per byte
    if bytes_per_plane % 4:  # Align to 4 bytes
        bytes_per_plane = ((bytes_per_plane + 3) & ~3)
    
    logger.info("Planar extraction parameters:")
    logger.info(f"Width: {width} pixels")
    logger.info(f"Height: {height} pixels")
    logger.info(f"Stride: {stride} bytes")
    logger.info(f"Bytes per plane: {bytes_per_plane}")
    
    # Extract 4 bit planes (assuming 16 colors)
    pixels = np.zeros((height, width), dtype=np.uint8)
    
    # Try both MSB and LSB first bit orders
    bit_orders = [
        ('MSB', lambda b, i: (b >> (7-i)) & 1),
        ('LSB', lambda b, i: (b >> i) & 1)
    ]
    
    best_pixels = None
    best_entropy = -1
    
    for bit_order_name, bit_extract in bit_orders:
        logger.info(f"Trying {bit_order_name} first bit order...")
        test_pixels = np.zeros((height, width), dtype=np.uint8)
        
        for y in range(height):
            for plane in range(4):  # 4 planes for 16 colors
                plane_offset = header.data_offset + (y * stride * 4) + (plane * stride)
                if plane_offset >= len(data):
                    logger.warning(f"Data truncated at row {y}, plane {plane}")
                    continue
                    
                plane_data = data[plane_offset:plane_offset + bytes_per_plane]
                if y < 4:  # Debug first few rows
                    logger.debug(f"Row {y} Plane {plane}: " + " ".join(f"{b:02x}" for b in plane_data))
                
                # Process each byte in the plane
                for byte_idx, byte in enumerate(plane_data):
                    for bit in range(8):
                        pixel_x = byte_idx * 8 + bit
                        if pixel_x >= width:
                            break
                        
                        # Extract bit and set in appropriate plane
                        bit_value = bit_extract(byte, bit)
                        test_pixels[y, pixel_x] |= (bit_value << plane)
        
        # Calculate entropy as a measure of image quality
        values, counts = np.unique(test_pixels, return_counts=True)
        entropy = -np.sum((counts/counts.sum()) * np.log2(counts/counts.sum()))
        logger.info(f"{bit_order_name} entropy: {entropy:.2f}")
        
        if entropy > best_entropy:
            best_entropy = entropy
            best_pixels = test_pixels.copy()
    
    if best_pixels is None:
        raise ValueError("Failed to extract valid pixel data")
    
    # Debug pixel value distribution
    unique_values = np.unique(best_pixels)
    logger.info("Pixel value distribution:")
    for value in unique_values:
        count = np.sum(best_pixels == value)
        logger.info(f"Value {value:2d}: {count:6d} pixels ({count/(width*height)*100:5.1f}%)")
    
    return best_pixels

def extract_linear_data(data, header):
    """Extract data assuming linear organization."""
    logger.info("Attempting linear data extraction...")
    
    width = header.width
    height = header.height
    stride = header.stride if header.stride else width
    
    logger.info("Linear extraction parameters:")
    logger.info(f"Width: {width} pixels")
    logger.info(f"Height: {height} pixels")
    logger.info(f"Stride: {stride} bytes")
    
    # Try both byte orders
    orders = [
        ('normal', lambda x: x),
        ('swapped', lambda x: ((x & 0xF0) >> 4) | ((x & 0x0F) << 4))
    ]
    
    best_pixels = None
    best_entropy = -1
    
    for order_name, transform in orders:
        logger.info(f"Trying {order_name} byte order...")
        test_pixels = np.zeros((height, width), dtype=np.uint8)
        
        for y in range(height):
            row_offset = header.data_offset + (y * stride)
            if row_offset >= len(data):
                logger.warning(f"Data truncated at row {y}")
                break
                
            row = data[row_offset:row_offset + width]
            if y < 4:  # Debug first few rows
                logger.debug(f"Row {y}: " + " ".join(f"{b:02x}" for b in row))
            
            for x, pixel in enumerate(row):
                if x < width:
                    test_pixels[y, x] = transform(pixel)
        
        # Calculate entropy
        values, counts = np.unique(test_pixels, return_counts=True)
        entropy = -np.sum((counts/counts.sum()) * np.log2(counts/counts.sum()))
        logger.info(f"{order_name} entropy: {entropy:.2f}")
        
        if entropy > best_entropy:
            best_entropy = entropy
            best_pixels = test_pixels.copy()
    
    if best_pixels is None:
        raise ValueError("Failed to extract valid pixel data")
    
    # Debug pixel value distribution
    unique_values = np.unique(best_pixels)
    logger.info("Pixel value distribution:")
    for value in unique_values:
        count = np.sum(best_pixels == value)
        logger.info(f"Value {value:2d}: {count:6d} pixels ({count/(width*height)*100:5.1f}%)")
    
    return best_pixels

def try_extract_formats(data, header):
    """Try different data format extractions."""
    logger.info("Trying different extraction formats...")
    results = []
    
    # Try planar format
    try:
        logger.info("Attempting planar format extraction...")
        pixels = extract_planar_data(data, header)
        if pixels is not None:
            # Create image
            img = Image.fromarray(pixels, 'P')
            if header.palette_offset:
                palette = read_palette(data, header.palette_offset)
                img.putpalette(palette)
            results.append(('planar', img))
            logger.info("Planar extraction successful")
    except Exception as e:
        logger.error(f"Planar extraction failed: {str(e)}")
        logger.exception(e)
    
    # Try linear format
    try:
        logger.info("Attempting linear format extraction...")
        pixels = extract_linear_data(data, header)
        if pixels is not None:
            # Create image
            img = Image.fromarray(pixels, 'P')
            if header.palette_offset:
                palette = read_palette(data, header.palette_offset)
                img.putpalette(palette)
            results.append(('linear', img))
            logger.info("Linear extraction successful")
    except Exception as e:
        logger.error(f"Linear extraction failed: {str(e)}")
        logger.exception(e)
    
    return results

def extract_stit_file(filename):
    """Extract sprite/image data from an S_TIT file."""
    logger.info(f"Processing file: {filename}")
    
    with open(filename, 'rb') as f:
        data = f.read()
    
    logger.info(f"File size: {len(data)} bytes")
    logger.debug(f"First 64 bytes: {data[:64].hex()}")
    
    # Parse header
    header = STITHeader(data)
    
    # Try different extraction methods
    results = try_extract_formats(data, header)
    
    if not results:
        logger.error("No successful extractions")
        return
    
    # Save results
    base_name = os.path.splitext(filename)[0]
    for format_name, img in results:
        output_path = f"{base_name}_{format_name}.png"
        img.save(output_path)
        logger.info(f"Saved {format_name} version as: {output_path}")
        
        # Save raw pixel data for analysis
        raw_path = f"{base_name}_{format_name}_raw.bin"
        with open(raw_path, 'wb') as f:
            f.write(img.tobytes())
        logger.info(f"Saved raw pixel data as: {raw_path}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract data from S_TIT files')
    parser.add_argument('file', help='S_TIT file to extract')
    args = parser.parse_args()
    
    try:
        extract_stit_file(args.file)
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        logger.exception(e)
        return 1
    
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main()) 