#!/usr/bin/env python3
"""Scan decompressed MDL file for geometry markers"""
import struct
import sys

markers = {
    b"\x00\x00\xc0\x00": "vertex",
    b"\x00\x00\x40\xc1": "normal", 
    b"\x00\x00\x40\x00": "index",
    b"\xaa\xaa\xaa\xaa": "align",
    b"\x55\x55\x55\x55": "structure",
}

def scan_file(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("\nSearching for geometry markers...")
    
    found = []
    
    for marker, name in markers.items():
        positions = []
        pos = 0
        while True:
            pos = data.find(marker, pos)
            if pos == -1:
                break
            positions.append(pos)
            pos += 1
        if positions:
            print(f"\n{name}: {len(positions)} occurrences")
            for p in positions[:10]:
                hex_data = data[p:p+20].hex()
                print(f"  0x{p:06x}: {hex_data}")
                found.append((p, name, data[p:p+20]))
            if len(positions) > 10:
                print(f"  ... and {len(positions)-10} more")
    
    # Look for float data (3f800000 = 1.0)
    float_pos = []
    pos = 0
    one_float = struct.pack("<f", 1.0)  # 0x3f800000
    while True:
        pos = data.find(one_float, pos)
        if pos == -1:
            break
        float_pos.append(pos)
        pos += 1
    print(f"\nfloat(1.0) markers: {len(float_pos)} occurrences")
    if float_pos:
        for p in float_pos[:5]:
            # Try reading 3 floats
            if p + 12 <= len(data):
                vals = struct.unpack("<3f", data[p:p+12])
                print(f"  0x{p:06x}: {vals}")
    
    return found

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scan_markers.py file.bin")
        sys.exit(1)
    scan_file(sys.argv[1])

