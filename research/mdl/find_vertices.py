#!/usr/bin/env python3
"""Find vertex data in decompressed MDL file"""
import struct
import sys

def find_vertices(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("Looking for potential vertex data (float triplets in reasonable range)...")
    
    vertices = []
    
    for offset in range(0, len(data)-12, 4):
        try:
            x, y, z = struct.unpack("<3f", data[offset:offset+12])
            # Check for reasonable model coordinates
            if all(-1000 < v < 1000 for v in (x, y, z)) and any(v != 0 for v in (x, y, z)):
                if abs(x) > 0.01 or abs(y) > 0.01 or abs(z) > 0.01:
                    # Check if surrounded by similar float patterns
                    has_neighbor = False
                    if offset >= 12:
                        px, py, pz = struct.unpack("<3f", data[offset-12:offset])
                        if all(-1000 < v < 1000 for v in (px, py, pz)):
                            has_neighbor = True
                    if offset + 24 <= len(data):
                        nx, ny, nz = struct.unpack("<3f", data[offset+12:offset+24])
                        if all(-1000 < v < 1000 for v in (nx, ny, nz)):
                            has_neighbor = True
                    
                    if has_neighbor:
                        vertices.append((offset, x, y, z))
        except:
            pass
    
    # Print first 50 and show some statistics
    print(f"\nFound {len(vertices)} potential vertices")
    
    if vertices:
        print("\nFirst 30 vertices:")
        for off, x, y, z in vertices[:30]:
            print(f"  0x{off:06x}: ({x:8.3f}, {y:8.3f}, {z:8.3f})")
        
        # Find clusters
        print("\nVertex clusters (by offset range):")
        ranges = []
        start = vertices[0][0]
        last = start
        for off, _, _, _ in vertices:
            if off - last > 100:  # Gap > 100 bytes = new cluster
                ranges.append((start, last))
                start = off
            last = off
        ranges.append((start, last))
        
        for s, e in ranges[:20]:
            count = sum(1 for v in vertices if s <= v[0] <= e)
            print(f"  0x{s:06x} - 0x{e:06x}: {count} vertices")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_vertices.py file.bin")
        sys.exit(1)
    find_vertices(sys.argv[1])

