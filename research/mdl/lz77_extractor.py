"""
LZ77 Function Extractor for Dokapon Sword of Fury

This script extracts and analyzes the LZ77 decompression function from the Dokapon Sword of Fury executable.
It identifies key instructions, compression parameters, and bit masks used in the decompression algorithm.

Usage:
    python lz77_extractor.py <exe_path> [--offset OFFSET]

Arguments:
    exe_path    Path to the Dokapon Sword of Fury executable
    --offset    Optional hex offset of LZ77 function (default: 0x522f61)

Example:
    python lz77_extractor.py dokapon.exe --offset 0x522f61

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof

This is free and unencumbered software released into the public domain.
For more information, please refer to <http://unlicense.org/>
"""

import struct
import binascii
from pathlib import Path
from collections import namedtuple

Instruction = namedtuple('Instruction', ['offset', 'bytes', 'disasm'])

def extract_lz77_function(exe_path: str, start_offset: int = 0x522f61):
    """Extract and analyze the LZ77 decompression function"""
    with open(exe_path, 'rb') as f:
        f.seek(start_offset - 0x100)  # Get some context before
        code = f.read(0x400)          # Read enough to get full function
    
    # Key instructions we're looking for
    key_patterns = [
        (b'\x48\x8b\x54\x24', 'mov rdx, [rsp+?]'),    # Buffer access
        (b'\x48\x83\xc2\x10', 'add rdx, 10h'),        # Skip header
        (b'\x4c\x5a\x37\x37', 'LZ77 magic'),          # Magic bytes
        (b'\x48\x83\xec', 'sub rsp, ?'),              # Stack frame
        (b'\x48\x8b\x8c', 'mov rcx, [rsp+?]'),        # Memory operations
        (b'\x0f\x85', 'jne'),                         # Loop control
    ]
    
    print("\nAnalyzing LZ77 decompression function:")
    print("=======================================")
    
    instructions = []
    for pattern, desc in key_patterns:
        pos = 0
        while True:
            pos = code.find(pattern, pos)
            if pos < 0:
                break
            
            # Get instruction context
            context_start = max(0, pos - 8)
            context_end = min(len(code), pos + len(pattern) + 8)
            inst_bytes = code[pos:pos+len(pattern)]
            
            instructions.append(Instruction(
                offset=start_offset - 0x100 + pos,
                bytes=inst_bytes,
                disasm=desc
            ))
            pos += 1
    
    # Sort by offset
    instructions.sort(key=lambda x: x.offset)
    
    # Print analysis
    print("\nKey instructions found:")
    for inst in instructions:
        print(f"0x{inst.offset:08x}: {inst.disasm:20} | {binascii.hexlify(inst.bytes).decode()}")
    
    # Look for compression parameters
    print("\nCompression parameters:")
    window_sizes = [b'\x00\x10\x00\x00', b'\x00\x20\x00\x00', b'\x00\x40\x00\x00']
    for size in window_sizes:
        pos = code.find(size)
        if pos >= 0:
            print(f"Window size: 0x{struct.unpack('<I', size)[0]:x} bytes")
    
    # Look for bit masks
    masks = [b'\x0f\x00', b'\x1f\x00', b'\x3f\x00', b'\x7f\x00', b'\xff\x00']
    for mask in masks:
        pos = code.find(mask)
        if pos >= 0:
            print(f"Bit mask: 0x{mask[0]:02x}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract LZ77 function from Dokapon executable')
    parser.add_argument('exe', type=Path, help='Path to the executable')
    parser.add_argument('--offset', type=lambda x: int(x,0), default=0x522f61,
                      help='Function offset (default: 0x522f61)')
    
    args = parser.parse_args()
    extract_lz77_function(args.exe, args.offset)

if __name__ == '__main__':
    main() 