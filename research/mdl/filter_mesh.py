#!/usr/bin/env python3
"""Filter and clean up MDL mesh, removing invalid vertices"""
import sys

def filter_mesh(input_obj, output_obj):
    # Read input
    vertices = []
    faces = []
    
    with open(input_obj, 'r') as f:
        for line in f:
            if line.startswith('v '):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append((x, y, z))
            elif line.startswith('f '):
                parts = line.split()
                i0, i1, i2 = int(parts[1])-1, int(parts[2])-1, int(parts[3])-1
                faces.append((i0, i1, i2))
    
    print(f"Input: {len(vertices)} vertices, {len(faces)} faces")
    
    # Find valid vertices (non-zero)
    valid_mask = []
    for x, y, z in vertices:
        is_valid = abs(x) > 0.001 or abs(y) > 0.001 or abs(z) > 0.001
        valid_mask.append(is_valid)
    
    valid_count = sum(valid_mask)
    print(f"Valid (non-zero) vertices: {valid_count}")
    
    # Create remapping
    old_to_new = {}
    new_vertices = []
    for i, (valid, vert) in enumerate(zip(valid_mask, vertices)):
        if valid:
            old_to_new[i] = len(new_vertices)
            new_vertices.append(vert)
    
    # Filter faces - only keep faces where all vertices are valid
    new_faces = []
    for i0, i1, i2 in faces:
        if i0 in old_to_new and i1 in old_to_new and i2 in old_to_new:
            new_faces.append((old_to_new[i0], old_to_new[i1], old_to_new[i2]))
    
    print(f"Valid faces: {len(new_faces)}")
    
    # Remove degenerate faces (all same vertex)
    clean_faces = []
    for i0, i1, i2 in new_faces:
        if not (i0 == i1 == i2):
            clean_faces.append((i0, i1, i2))
    
    print(f"Non-degenerate faces: {len(clean_faces)}")
    
    # Calculate bounds
    if new_vertices:
        xs = [v[0] for v in new_vertices]
        ys = [v[1] for v in new_vertices]
        zs = [v[2] for v in new_vertices]
        print(f"Bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
    
    # Export
    with open(output_obj, 'w') as f:
        f.write(f"# Filtered mesh: {len(new_vertices)} vertices, {len(clean_faces)} triangles\n")
        
        for x, y, z in new_vertices:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        
        f.write("\n")
        
        for i0, i1, i2 in clean_faces:
            f.write(f"f {i0+1} {i1+1} {i2+1}\n")
    
    print(f"\nExported to {output_obj}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python filter_mesh.py input.obj output.obj")
        sys.exit(1)
    
    filter_mesh(sys.argv[1], sys.argv[2])

