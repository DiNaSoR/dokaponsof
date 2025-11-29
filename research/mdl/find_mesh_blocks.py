#!/usr/bin/env python3
"""Find mesh blocks in decompressed MDL file using known patterns"""
import struct
import sys

def find_mesh_blocks(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Look for 0x55555555 structure markers
    print("\n=== STRUCTURE MARKERS (0x55555555) ===")
    pos = 0
    structure_blocks = []
    while True:
        pos = data.find(b'\x55\x55\x55\x55', pos)
        if pos == -1:
            break
        # Look for extended patterns
        if pos + 20 <= len(data):
            ext = data[pos:pos+20]
            if ext[:8] == b'\x55\x55\x55\x55\x55\x55\x55\x55':
                structure_blocks.append(pos)
        pos += 1
    
    print(f"Found {len(structure_blocks)} structure block starts")
    for p in structure_blocks[:10]:
        print(f"  0x{p:06x}: {data[p:p+32].hex()}")
    
    # Look for mesh headers - typically have vertex count, index count, etc.
    print("\n=== LOOKING FOR MESH HEADERS ===")
    
    # Pattern: header with reasonable vertex/index counts
    mesh_candidates = []
    for i in range(0, len(data) - 32, 4):
        try:
            # Read potential header fields
            v1, v2, v3, v4 = struct.unpack("<4I", data[i:i+16])
            
            # Check for reasonable vertex count (10-50000) followed by reasonable index count
            if 10 <= v1 <= 50000 and 10 <= v2 <= 150000:
                # Could be vertexCount, indexCount
                mesh_candidates.append((i, v1, v2, v3, v4))
            elif 10 <= v2 <= 50000 and 10 <= v3 <= 150000:
                # Could be offset, vertexCount, indexCount
                mesh_candidates.append((i, v1, v2, v3, v4))
        except:
            pass
    
    print(f"Found {len(mesh_candidates)} potential mesh headers")
    for i, (off, a, b, c, d) in enumerate(mesh_candidates[:20]):
        print(f"  0x{off:06x}: {a:6d}, {b:6d}, {c:6d}, {d:6d}")
    
    # Look at regions after structure markers
    print("\n=== DATA AFTER STRUCTURE MARKERS ===")
    for block_start in structure_blocks[:5]:
        # Find end of 0x55 pattern
        end = block_start
        while end < len(data) and data[end] == 0x55:
            end += 1
        
        print(f"\nBlock at 0x{block_start:06x}, ends at 0x{end:06x}")
        if end + 64 <= len(data):
            # Show data after marker
            post_data = data[end:end+64]
            print(f"  Data after: {post_data[:32].hex()}")
            
            # Try interpreting as floats
            if end + 48 <= len(data):
                floats = struct.unpack("<12f", data[end:end+48])
                valid_floats = [f for f in floats if -1000 < f < 1000 and f != 0]
                if valid_floats:
                    print(f"  As floats: {[f'{f:.3f}' for f in floats[:6]]}")
    
    # Look for specific mesh data patterns from common 3D formats
    print("\n=== FLOAT SEQUENCES (potential vertex data) ===")
    
    # Find sequences of varied floats (not just zeros or repeated values)
    i = 0
    vertex_sequences = []
    while i < len(data) - 48:
        try:
            floats = struct.unpack("<12f", data[i:i+48])
            # Check for varied values in reasonable range
            unique_vals = len(set(floats))
            in_range = all(-1000 < f < 1000 for f in floats)
            
            if unique_vals >= 8 and in_range:
                # Found varied float sequence, extend it
                start = i
                end = i + 48
                while end + 12 <= len(data):
                    x, y, z = struct.unpack("<3f", data[end:end+12])
                    if all(-1000 < v < 1000 for v in (x, y, z)):
                        end += 12
                    else:
                        break
                
                verts = (end - start) // 12
                if verts >= 20:
                    vertex_sequences.append((start, end, verts))
                    i = end
                    continue
        except:
            pass
        i += 4
    
    print(f"Found {len(vertex_sequences)} potential vertex sequences:")
    for start, end, count in vertex_sequences[:15]:
        print(f"\n  0x{start:06x} - 0x{end:06x}: {count} potential vertices")
        # Show some sample vertices
        for j in range(min(5, count)):
            off = start + j * 12
            x, y, z = struct.unpack("<3f", data[off:off+12])
            print(f"    [{j:3d}]: ({x:10.4f}, {y:10.4f}, {z:10.4f})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_mesh_blocks.py file.bin")
        sys.exit(1)
    find_mesh_blocks(sys.argv[1])

