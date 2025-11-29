#!/usr/bin/env python3
"""Analyze MDL file header structure"""
import struct
import sys

def analyze_header(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("\n=== HEADER ANALYSIS ===")
    
    # First 256 bytes as hex dump
    print("\nFirst 256 bytes:")
    for i in range(0, min(256, len(data)), 16):
        addr = f"{i:04x}"
        hex_str = ' '.join(f'{data[i+j]:02x}' for j in range(min(16, len(data)-i)))
        ascii_str = ''.join(chr(data[i+j]) if 32 <= data[i+j] < 127 else '.' 
                          for j in range(min(16, len(data)-i)))
        print(f"  {addr}: {hex_str:47s} {ascii_str}")
    
    # Try to find offset table or section markers
    print("\n=== LOOKING FOR OFFSET TABLE ===")
    
    # Read first 64 dwords and check if any look like offsets
    offsets_found = []
    for i in range(0, min(256, len(data)), 4):
        val = struct.unpack("<I", data[i:i+4])[0]
        # Check if value could be an offset into the file
        if 256 <= val < len(data):
            offsets_found.append((i, val))
    
    print(f"Potential offsets in first 256 bytes:")
    for pos, val in offsets_found[:20]:
        # Show what's at that offset
        marker = data[val:val+8].hex() if val + 8 <= len(data) else "N/A"
        print(f"  0x{pos:04x}: 0x{val:08x} -> data: {marker}")
    
    # Look for string markers
    print("\n=== STRING MARKERS ===")
    strings = []
    i = 0
    while i < len(data) - 4:
        # Look for printable string sequences
        if 32 <= data[i] < 127:
            end = i
            while end < len(data) and 32 <= data[end] < 127:
                end += 1
            if end - i >= 4:
                s = data[i:end].decode('ascii', errors='ignore')
                strings.append((i, s))
            i = end
        else:
            i += 1
    
    print(f"Found {len(strings)} strings")
    for pos, s in strings[:30]:
        print(f"  0x{pos:06x}: '{s[:60]}'")
    
    # Look for float arrays (potential vertex data)
    print("\n=== FLOAT ARRAY SEARCH ===")
    
    float_starts = []
    for start in range(0, min(len(data) - 48, 0x100000), 4):
        # Read 4 consecutive vec3
        try:
            vecs = []
            valid = True
            for j in range(4):
                x, y, z = struct.unpack("<3f", data[start+j*12:start+j*12+12])
                # Check if valid model coordinates (small, non-denormalized)
                if not (abs(x) < 100 and abs(y) < 100 and abs(z) < 100):
                    valid = False
                    break
                if any(1e-38 < abs(v) < 1e-10 for v in (x, y, z) if v != 0):
                    # Likely denormalized/garbage
                    valid = False
                    break
                vecs.append((x, y, z))
            
            if valid and any(any(v != 0 for v in vec) for vec in vecs):
                float_starts.append((start, vecs))
        except:
            pass
    
    print(f"Found {len(float_starts)} potential float arrays")
    for pos, vecs in float_starts[:15]:
        print(f"\n  0x{pos:06x}:")
        for i, (x, y, z) in enumerate(vecs):
            print(f"    [{i}]: ({x:8.4f}, {y:8.4f}, {z:8.4f})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_mdl_header.py file.bin")
        sys.exit(1)
    analyze_header(sys.argv[1])

