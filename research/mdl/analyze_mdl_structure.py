#!/usr/bin/env python3
"""Analyze decompressed MDL file structure to find mesh geometry"""
import struct
import sys
from collections import defaultdict

def analyze_structure(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Look at header structure
    print("\n=== HEADER ANALYSIS ===")
    print(f"First 64 bytes:")
    for i in range(0, 64, 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        print(f"  0x{i:04x}: {hex_str}")
    
    # Read potential header fields
    if len(data) >= 32:
        vals = struct.unpack("<8I", data[:32])
        print(f"\nAs dwords: {[f'0x{v:08x}' for v in vals]}")
    
    # Find data sections by looking for patterns
    print("\n=== SECTION MARKERS ===")
    
    # Look for repeated dword patterns (often section headers)
    dword_counts = defaultdict(list)
    for i in range(0, len(data)-4, 4):
        dword = struct.unpack("<I", data[i:i+4])[0]
        if 0x1000 <= dword <= 0x100000:  # Reasonable size values
            dword_counts[dword].append(i)
    
    print("Potential size fields (0x1000-0x100000 range):")
    for dword, positions in sorted(dword_counts.items(), key=lambda x: -len(x[1]))[:10]:
        if len(positions) >= 2:
            print(f"  0x{dword:08x} ({dword:6d}): {len(positions)} times at {[f'0x{p:x}' for p in positions[:5]]}")
    
    # Look for vertex-like data clusters
    print("\n=== VERTEX DATA ANALYSIS ===")
    
    # Find sequences of floats in model coordinate range
    vertex_regions = []
    i = 0
    while i < len(data) - 12:
        try:
            x, y, z = struct.unpack("<3f", data[i:i+12])
            # Real mesh vertices typically have varied values
            if all(-500 < v < 500 for v in (x, y, z)):
                if not (abs(x) < 0.01 and abs(y) < 0.01 and abs(z) < 0.01):
                    # Check if this is part of a vertex array
                    count = 0
                    start = i
                    while i < len(data) - 12:
                        try:
                            x, y, z = struct.unpack("<3f", data[i:i+12])
                            if all(-500 < v < 500 for v in (x, y, z)):
                                count += 1
                                i += 12
                            else:
                                break
                        except:
                            break
                    if count >= 10:  # At least 10 vertices
                        vertex_regions.append((start, i, count))
                    else:
                        i = start + 4
                    continue
        except:
            pass
        i += 4
    
    print(f"Found {len(vertex_regions)} potential vertex arrays:")
    for start, end, count in vertex_regions[:20]:
        print(f"  0x{start:06x} - 0x{end:06x}: {count} vertices ({end-start} bytes)")
        # Show first few vertices
        for j in range(min(3, count)):
            off = start + j * 12
            x, y, z = struct.unpack("<3f", data[off:off+12])
            print(f"    [{j}]: ({x:8.3f}, {y:8.3f}, {z:8.3f})")
    
    # Look for index data (sequences of uint16 in reasonable range)
    print("\n=== INDEX DATA ANALYSIS ===")
    
    index_regions = []
    i = 0
    while i < len(data) - 6:
        # Look for sequences of uint16 that could be triangle indices
        count = 0
        start = i
        max_idx = 0
        while i < len(data) - 2:
            idx = struct.unpack("<H", data[i:i+2])[0]
            if idx < 10000:  # Reasonable vertex index
                count += 1
                max_idx = max(max_idx, idx)
                i += 2
            else:
                break
        if count >= 30 and max_idx > 0:  # At least 10 triangles, and some non-zero indices
            index_regions.append((start, i, count, max_idx))
        else:
            i = start + 2
    
    print(f"Found {len(index_regions)} potential index arrays:")
    for start, end, count, max_idx in index_regions[:15]:
        print(f"  0x{start:06x} - 0x{end:06x}: {count} indices (max: {max_idx})")
        # Show first few triangles
        indices = []
        for j in range(min(12, count)):
            idx = struct.unpack("<H", data[start+j*2:start+j*2+2])[0]
            indices.append(idx)
        print(f"    First indices: {indices}")
    
    # Look for float patterns that might be normals (values near -1 to 1)
    print("\n=== NORMAL DATA ANALYSIS ===")
    
    normal_regions = []
    i = 0
    while i < len(data) - 12:
        try:
            x, y, z = struct.unpack("<3f", data[i:i+12])
            # Normals are typically in -1 to 1 range
            if all(-1.5 < v < 1.5 for v in (x, y, z)):
                length = (x*x + y*y + z*z) ** 0.5
                if 0.9 < length < 1.1:  # Unit-ish vector
                    count = 0
                    start = i
                    while i < len(data) - 12:
                        try:
                            x, y, z = struct.unpack("<3f", data[i:i+12])
                            length = (x*x + y*y + z*z) ** 0.5
                            if all(-1.5 < v < 1.5 for v in (x, y, z)) and 0.5 < length < 1.5:
                                count += 1
                                i += 12
                            else:
                                break
                        except:
                            break
                    if count >= 10:
                        normal_regions.append((start, i, count))
                    else:
                        i = start + 4
                    continue
        except:
            pass
        i += 4
    
    print(f"Found {len(normal_regions)} potential normal arrays:")
    for start, end, count in normal_regions[:10]:
        print(f"  0x{start:06x} - 0x{end:06x}: {count} normals")
        for j in range(min(3, count)):
            off = start + j * 12
            x, y, z = struct.unpack("<3f", data[off:off+12])
            length = (x*x + y*y + z*z) ** 0.5
            print(f"    [{j}]: ({x:6.3f}, {y:6.3f}, {z:6.3f}) len={length:.3f}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_mdl_structure.py file.bin")
        sys.exit(1)
    analyze_structure(sys.argv[1])

