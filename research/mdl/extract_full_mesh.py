#!/usr/bin/env python3
"""Extract full mesh from decompressed MDL"""
import struct
import sys

def find_all_vertices(data, scale=100.0):
    """Find all 16-bit packed vertices in the file"""
    all_verts = []
    
    # Scan for any valid coordinate triplets
    for i in range(0, len(data) - 6, 2):
        try:
            x, y, z = struct.unpack("<3h", data[i:i+6])
            xs, ys, zs = x/scale, y/scale, z/scale
            
            # Valid coordinate range
            if all(-200 < v < 200 for v in (xs, ys, zs)):
                if any(abs(v) > 0.01 for v in (xs, ys, zs)):
                    all_verts.append((i, xs, ys, zs))
        except:
            pass
    
    return all_verts

def find_contiguous_vertex_blocks(data, scale=100.0):
    """Find contiguous blocks of vertex data"""
    blocks = []
    
    i = 0
    while i < len(data) - 6:
        block_start = i
        verts = []
        
        while i < len(data) - 6:
            try:
                x, y, z = struct.unpack("<3h", data[i:i+6])
                xs, ys, zs = x/scale, y/scale, z/scale
                
                if all(-200 < v < 200 for v in (xs, ys, zs)):
                    verts.append((xs, ys, zs))
                    i += 6
                else:
                    break
            except:
                break
        
        if len(verts) >= 100:  # At least 100 vertices
            blocks.append((block_start, verts))
        
        i = block_start + 2 if len(verts) == 0 else i
    
    return blocks

def extract_mesh(filename, output_obj, scale=100.0):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print(f"Scale: {scale}")
    
    # Find large vertex blocks
    print("\n=== Finding vertex blocks ===")
    blocks = find_contiguous_vertex_blocks(data, scale)
    
    print(f"Found {len(blocks)} vertex blocks with 100+ vertices")
    
    all_vertices = []
    for start, verts in blocks:
        print(f"  0x{start:06x}: {len(verts)} vertices")
        all_vertices.extend(verts)
    
    if not all_vertices:
        print("No large vertex blocks found, scanning entire file...")
        vertex_data = find_all_vertices(data, scale)
        all_vertices = [(v[1], v[2], v[3]) for v in vertex_data]
    
    # Remove duplicates and export
    unique = list(set(all_vertices))
    print(f"\nTotal: {len(all_vertices)} vertices, {len(unique)} unique")
    
    # Find bounds
    if unique:
        xs = [v[0] for v in unique]
        ys = [v[1] for v in unique]
        zs = [v[2] for v in unique]
        print(f"Bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
    
    # Export
    with open(output_obj, 'w') as f:
        f.write(f"# {len(unique)} unique vertices\n")
        for x, y, z in unique:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
    
    print(f"\nExported {len(unique)} vertices to {output_obj}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python extract_full_mesh.py input.bin output.obj [scale]")
        sys.exit(1)
    
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
    extract_mesh(sys.argv[1], sys.argv[2], scale)

