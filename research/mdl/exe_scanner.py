"""
Executable Scanner for Decompression Code Analysis
===============================================

This tool scans executable files for patterns commonly associated with decompression
routines, including LZ77 signatures, function prologues/epilogues, and common assembly patterns.

Usage:
------
python exe_scanner.py <exe_path> [--start START_OFFSET] [--range RANGE_SIZE]

Arguments:
  exe_path          Path to the executable file to scan
  --start           Start offset in hex (default: 0x522f00)
  --range           Range size to scan in hex (default: 0x1000)

Example:
  python exe_scanner.py game.exe --start 0x400000 --range 0x2000

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: GNU General Public License v3.0 (GPL-3.0)
"""

import struct
import binascii
from pathlib import Path

def scan_for_decompression(exe_path: str, start_offset: int = 0x522f00, range_size: int = 0x1000):
    """Scan a range of the executable for decompression-related code"""
    with open(exe_path, 'rb') as f:
        f.seek(start_offset)
        data = f.read(range_size)
        
    # Look for common patterns
    patterns = {
        'lz77_header': b'LZ77',
        'function_prologue': b'\x55\x48\x89\xe5',  # push rbp; mov rbp, rsp
        'function_epilogue': b'\x5d\xc3',          # pop rbp; ret
        'bit_operations': [
            b'\x48\xc1',  # shift operations
            b'\x48\x83',  # and/or operations
            b'\x0f\xb6',  # movzx
        ],
        'loop_constructs': [
            b'\x0f\x84',  # je
            b'\x0f\x85',  # jne
            b'\xe8',      # call
        ]
    }
    
    print(f"\nScanning range 0x{start_offset:x} to 0x{start_offset + range_size:x}")
    
    for name, pattern in patterns.items():
        if isinstance(pattern, bytes):
            pattern = [pattern]
        
        print(f"\n{name} matches:")
        for p in pattern:
            pos = 0
            while True:
                pos = data.find(p, pos)
                if pos < 0:
                    break
                    
                context_start = max(0, pos - 16)
                context_end = min(len(data), pos + 32)
                context = data[context_start:context_end]
                
                print(f"  At offset +0x{pos:04x} (0x{start_offset + pos:x}):")
                for i in range(0, len(context), 16):
                    chunk = context[i:i+16]
                    hex_str = " ".join(f"{b:02x}" for b in chunk)
                    ascii_str = "".join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                    rel_offset = context_start + i
                    print(f"    {rel_offset:04x}: {hex_str:48} {ascii_str}")
                
                pos += 1

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scan executable for decompression code')
    parser.add_argument('exe', type=Path, help='Path to the executable')
    parser.add_argument('--start', type=lambda x: int(x,0), default=0x522f00,
                      help='Start offset (default: 0x522f00)')
    parser.add_argument('--range', type=lambda x: int(x,0), default=0x1000,
                      help='Range to scan (default: 0x1000)')
    
    args = parser.parse_args()
    
    if not args.exe.exists():
        print(f"Error: File not found: {args.exe}")
        return
        
    scan_for_decompression(args.exe, args.start, args.range)

if __name__ == '__main__':
    main() 