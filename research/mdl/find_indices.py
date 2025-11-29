#!/usr/bin/env python3
"""Find triangle index data in decompressed MDL"""
import struct
import sys

def find_index_runs(filename, max_vertex=1000):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print(f"Max vertex index: {max_vertex}")
    
    # Look for consecutive index triplets
    print("\n=== Scanning for index sequences ===")
    
    index_runs = []
    i = 0
    while i < len(data) - 12:
        indices = []
        start = i
        max_idx_found = 0
        
        while i < len(data) - 6:
            try:
                # Read 3 shorts as triangle indices
                i0, i1, i2 = struct.unpack("<3H", data[i:i+6])
                
                # Valid index range
                if all(idx < max_vertex for idx in (i0, i1, i2)):
                    # At least some non-zero, non-degenerate
                    if not (i0 == i1 == i2):
                        max_idx_found = max(max_idx_found, i0, i1, i2)
                        indices.append((i0, i1, i2))
                        i += 6
                    else:
                        break
                else:
                    break
            except:
                break
        
        # Need at least 10 triangles, and max index > 3 (not all low)
        if len(indices) >= 10 and max_idx_found > 5:
            index_runs.append((start, indices, max_idx_found))
        
        i = start + 2
    
    index_runs.sort(key=lambda x: -len(x[1]))
    
    print(f"\nFound {len(index_runs)} index sequences (10+ triangles)")
    
    for start, tris, max_idx in index_runs[:15]:
        print(f"\n  0x{start:06x}: {len(tris)} triangles, max_idx={max_idx}")
        # Show first few
        for j in range(min(5, len(tris))):
            i0, i1, i2 = tris[j]
            print(f"    [{j}]: ({i0}, {i1}, {i2})")
    
    return index_runs

def export_obj_with_faces(verts_file, indices, output_file):
    """Export vertices with triangle faces"""
    # Read vertices from OBJ
    vertices = []
    with open(verts_file, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append((x, y, z))
    
    # Validate indices
    max_idx = max(max(t) for t in indices)
    if max_idx >= len(vertices):
        print(f"Warning: max index {max_idx} >= vertex count {len(vertices)}")
        return
    
    with open(output_file, 'w') as f:
        f.write(f"# {len(vertices)} vertices, {len(indices)} triangles\n")
        for x, y, z in vertices:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        f.write("\n")
        for i0, i1, i2 in indices:
            f.write(f"f {i0+1} {i1+1} {i2+1}\n")  # OBJ is 1-indexed
    
    print(f"\nExported {len(vertices)} vertices and {len(indices)} triangles to {output_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_indices.py input.bin [max_vertex]")
        sys.exit(1)
    
    max_v = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    find_index_runs(sys.argv[1], max_v)

