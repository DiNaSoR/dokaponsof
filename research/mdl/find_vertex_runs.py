#!/usr/bin/env python3
"""Find vertex-like sequences in decompressed MDL"""
import struct
import sys

def find_vertex_runs(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Look at the float array at 0x01b8bc
    print("=== Float Array at 0x01b8bc ===")
    for i in range(20):
        off = 0x01b8bc + i * 12
        if off + 12 <= len(data):
            x, y, z = struct.unpack("<3f", data[off:off+12])
            print(f"  [{i:2d}]: ({x:10.4f}, {y:10.4f}, {z:10.4f})")
    
    # Look for non-zero consecutive floats
    print("\n=== Scanning for vertex-like sequences ===")
    best_runs = []
    i = 0
    while i < len(data) - 48:
        floats = []
        start = i
        while i < len(data) - 12:
            try:
                x, y, z = struct.unpack("<3f", data[i:i+12])
                if all(-500 < v < 500 for v in (x, y, z)):
                    if any(abs(v) > 0.5 for v in (x, y, z)):
                        floats.append((x, y, z))
                        i += 12
                    else:
                        break
                else:
                    break
            except:
                break
        if len(floats) >= 10:
            best_runs.append((start, floats))
        i = start + 4
    
    best_runs.sort(key=lambda x: -len(x[1]))
    
    print(f"\nTop 10 vertex sequences:")
    for start, verts in best_runs[:10]:
        print(f"\n  0x{start:06x}: {len(verts)} vertices")
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        zs = [v[2] for v in verts]
        print(f"    Bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
        for j in range(min(5, len(verts))):
            x, y, z = verts[j]
            print(f"    [{j}]: ({x:8.3f}, {y:8.3f}, {z:8.3f})")
    
    return best_runs

def export_obj(verts, filename):
    """Export vertices as OBJ"""
    with open(filename, 'w') as f:
        f.write(f"# {len(verts)} vertices\n")
        for x, y, z in verts:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
    print(f"\nExported {len(verts)} vertices to {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_vertex_runs.py input.bin [output.obj]")
        sys.exit(1)
    
    runs = find_vertex_runs(sys.argv[1])
    
    if len(sys.argv) >= 3 and runs:
        # Export largest run
        _, verts = runs[0]
        export_obj(verts, sys.argv[2])

