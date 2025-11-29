#!/usr/bin/env python3
"""Find 16-bit packed vertex sequences in decompressed MDL"""
import struct
import sys

def find_short_vertex_runs(filename, scale=100.0):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print(f"Scale factor: {scale}")
    
    # Look for consecutive short triplets that form valid coordinates
    print("\n=== Scanning for 16-bit vertex sequences ===")
    
    best_runs = []
    i = 0
    while i < len(data) - 12:
        verts = []
        start = i
        
        while i < len(data) - 6:
            try:
                x, y, z = struct.unpack("<3h", data[i:i+6])
                # Scale and check bounds
                xs, ys, zs = x/scale, y/scale, z/scale
                
                # Valid coordinate range for a model
                if all(-100 < v < 100 for v in (xs, ys, zs)):
                    if any(abs(v) > 0.1 for v in (xs, ys, zs)):
                        verts.append((xs, ys, zs))
                        i += 6
                    else:
                        break
                else:
                    break
            except:
                break
        
        if len(verts) >= 30:  # At least 30 vertices
            best_runs.append((start, verts))
        
        i = start + 2
    
    best_runs.sort(key=lambda x: -len(x[1]))
    
    print(f"\nFound {len(best_runs)} vertex sequences (30+ verts)")
    
    for start, verts in best_runs[:10]:
        print(f"\n  0x{start:06x}: {len(verts)} vertices")
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        print(f"    Bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
        unique = len(set(verts))
        print(f"    Unique vertices: {unique}/{len(verts)}")
        for j in range(min(5, len(verts))):
            x, y, z = verts[j]
            print(f"    [{j}]: ({x:8.3f}, {y:8.3f}, {z:8.3f})")
    
    return best_runs

def export_obj(verts, filename):
    """Export vertices as OBJ point cloud"""
    unique_verts = list(set(verts))
    with open(filename, 'w') as f:
        f.write(f"# {len(unique_verts)} unique vertices from {len(verts)} total\n")
        for x, y, z in unique_verts:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
    print(f"\nExported {len(unique_verts)} unique vertices to {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_short_verts.py input.bin [output.obj] [scale]")
        sys.exit(1)
    
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
    runs = find_short_vertex_runs(sys.argv[1], scale)
    
    if len(sys.argv) >= 3 and runs:
        _, verts = runs[0]
        export_obj(verts, sys.argv[2])

