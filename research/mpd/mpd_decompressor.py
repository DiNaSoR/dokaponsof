"""
MPD File Decompressor
A specialized tool for decompressing MPD files from Dokapon using the LZ77 variant
found in the executable at offset 0x000b7705.

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: Unlicense License

This implementation matches the exact algorithm used in the game for MPD files.
"""

import struct
import logging
from pathlib import Path
from typing import BinaryIO, Optional

class MPDHeader:
    """MPD file header structure"""
    def __init__(self, magic: bytes, decompressed_size: int, compressed_size: int, flags: int):
        self.magic = magic
        self.decompressed_size = decompressed_size
        self.compressed_size = compressed_size
        self.flags = flags
        
    def __str__(self) -> str:
        return f"MPDHeader(magic={self.magic}, decompressed_size={self.decompressed_size}, compressed_size={self.compressed_size}, flags=0x{self.flags:04x})"

class MPDDecompressor:
    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("MPDDecompressor")
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
        # Constants from executable analysis
        self.WINDOW_SIZE = 0x1000  # 4096 bytes
        self.CONTROL_MASK = 0x0F   # From function at 0x000b7705
        
        self.reset_state()
    
    def reset_state(self):
        """Reset decompressor state"""
        self.window = bytearray(self.WINDOW_SIZE)
        self.window_pos = 0
        self.output = bytearray()
        
    def read_header(self, f: BinaryIO) -> Optional[MPDHeader]:
        """Read and validate MPD header"""
        try:
            magic = f.read(4)
            if magic != b'LZ77':
                self.logger.error(f"Invalid magic: {magic}")
                return None
                
            decompressed_size = struct.unpack('<I', f.read(4))[0]
            compressed_size = struct.unpack('<I', f.read(4))[0]
            flags = struct.unpack('<I', f.read(4))[0]
            
            return MPDHeader(magic, decompressed_size, compressed_size, flags)
            
        except struct.error as e:
            self.logger.error(f"Error reading header: {str(e)}")
            return None
    
    def update_window(self, byte: int):
        """Update sliding window buffer"""
        self.window[self.window_pos] = byte
        self.window_pos = (self.window_pos + 1) % self.WINDOW_SIZE
        
    def copy_from_window(self, offset: int, length: int):
        """Copy bytes from window buffer"""
        start_pos = (self.window_pos - offset) % self.WINDOW_SIZE
        for i in range(length):
            byte = self.window[(start_pos + i) % self.WINDOW_SIZE]
            self.output.append(byte)
            self.update_window(byte)
    
    def decompress_data(self, data: bytes, header: MPDHeader) -> bytes:
        """Decompress data using LZ77 variant from 0x000b7705"""
        pos = 0
        control = 0
        bits_left = 0
        compressed_size = header.compressed_size
        
        while pos < compressed_size and len(self.output) < header.decompressed_size:
            # Get next control flags if needed
            if bits_left == 0:
                if pos >= compressed_size:
                    break
                control = data[pos]
                pos += 1
                bits_left = 8
            
            # Check control bit
            if control & 1:  # Changed from 0x80 to check LSB first
                # Back reference
                if pos + 2 > compressed_size:
                    break
                    
                # Get offset and length
                b1 = data[pos]
                b2 = data[pos + 1]
                pos += 2
                
                # Offset is relative to current window position
                offset = ((b2 & 0xF0) << 4) | b1
                length = (b2 & 0x0F) + 3
                
                # Copy from window
                self.copy_from_window(offset, length)
            else:
                # Literal byte
                if pos >= compressed_size:
                    break
                    
                byte = data[pos]
                pos += 1
                
                self.output.append(byte)
                self.update_window(byte)
            
            # Move to next control bit
            control >>= 1  # Changed from <<= 1 to >>= 1
            bits_left -= 1
        
        return bytes(self.output[:header.decompressed_size])
    
    def decompress_file(self, filename: str) -> bytes:
        """Decompress an MPD file"""
        try:
            with open(filename, 'rb') as f:
                # Read and validate header
                header = self.read_header(f)
                if not header:
                    raise ValueError("Invalid header")
                    
                self.logger.debug(f"Header: {header}")
                
                # Read compressed data
                data = f.read(header.compressed_size)  # Only read compressed_size bytes
                if not data:
                    raise ValueError("No data to decompress")
                    
                self.logger.debug(f"Read {len(data)} bytes of compressed data")
                
                # Reset state and decompress
                self.reset_state()
                return self.decompress_data(data, header)
                
        except Exception as e:
            self.logger.error(f"Error during decompression: {str(e)}")
            raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Decompress MPD files from Dokapon')
    parser.add_argument('input', help='Input MPD file')
    parser.add_argument('output', help='Output decompressed file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    try:
        decompressor = MPDDecompressor(debug=args.debug)
        data = decompressor.decompress_file(args.input)
        
        with open(args.output, 'wb') as f:
            f.write(data)
            
        print(f"Successfully decompressed {args.input} to {args.output}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
        
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main()) 