#!/usr/bin/env python3
"""Extract mesh data from decompressed MDL and export to OBJ"""
import struct
import sys

def find_all_mesh_data(data):
    """Find all mesh data regions in the file"""
    meshes = []
    
    # Look for 16-bit packed vertex sequences
    i = 0
    while i < len(data) - 24:
        try:
            # Read 4 potential vec3 (24 bytes)
            vals = []
            valid = True
            for j in range(4):
                x, y, z = struct.unpack("<3h", data[i+j*6:i+j*6+6])
                # Check for reasonable vertex coordinates (scale factor of 100)
                if not all(-3000 < v < 3000 for v in (x, y, z)):
                    valid = False
                    break
                vals.append((x/100.0, y/100.0, z/100.0))
            
            if valid and any(any(abs(v) > 0.1 for v in vec) for vec in vals):
                # Found potential vertex data, extend region
                start = i
                vertices = []
                while i < len(data) - 6:
                    x, y, z = struct.unpack("<3h", data[i:i+6])
                    if all(-3000 < v < 3000 for v in (x, y, z)):
                        vertices.append((x/100.0, y/100.0, z/100.0))
                        i += 6
                    else:
                        break
                
                if len(vertices) >= 20:
                    # Check if vertices have variety (not all same)
                    unique_verts = len(set(vertices))
                    if unique_verts >= len(vertices) // 2:
                        meshes.append(("vertices", start, vertices))
                else:
                    i = start + 2
                continue
        except:
            pass
        i += 2
    
    return meshes

def find_index_data(data, vertex_count, search_start=0):
    """Find index data that references vertices"""
    indices = []
    
    # Search for sequences of uint16 indices
    i = search_start
    while i < len(data) - 6:
        try:
            # Read potential triangle (3 indices)
            i0, i1, i2 = struct.unpack("<3H", data[i:i+6])
            
            # Check if all indices are valid for the vertex count
            if all(idx < vertex_count for idx in (i0, i1, i2)):
                if any(idx > 0 for idx in (i0, i1, i2)):
                    # Found potential triangle, extend region
                    start = i
                    tris = []
                    while i < len(data) - 6:
                        i0, i1, i2 = struct.unpack("<3H", data[i:i+6])
                        if all(idx < vertex_count for idx in (i0, i1, i2)):
                            tris.append((i0, i1, i2))
                            i += 6
                        else:
                            break
                    
                    if len(tris) >= 10:
                        indices.append(("indices", start, tris))
                    else:
                        i = start + 2
                    continue
        except:
            pass
        i += 2
    
    return indices

def export_obj(vertices, faces, filename):
    """Export mesh to OBJ file"""
    with open(filename, 'w') as f:
        f.write(f"# Exported from Dokapon MDL\n")
        f.write(f"# Vertices: {len(vertices)}\n")
        f.write(f"# Faces: {len(faces)}\n\n")
        
        # Write vertices
        for x, y, z in vertices:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
        
        f.write("\n")
        
        # Write faces (OBJ uses 1-indexed)
        for i0, i1, i2 in faces:
            f.write(f"f {i0+1} {i1+1} {i2+1}\n")
    
    print(f"Exported {len(vertices)} vertices and {len(faces)} faces to {filename}")

def analyze_mesh(data):
    """Analyze and extract mesh data"""
    print(f"File size: {len(data)} bytes")
    
    # Find all vertex data
    meshes = find_all_mesh_data(data)
    print(f"\nFound {len(meshes)} potential mesh regions\n")
    
    # Analyze largest mesh regions
    meshes_sorted = sorted(meshes, key=lambda x: len(x[2]), reverse=True)
    
    for i, (dtype, offset, mesh_data) in enumerate(meshes_sorted[:5]):
        print(f"Mesh Region {i+1}: {len(mesh_data)} {dtype} at 0x{offset:06x}")
        
        if dtype == "vertices":
            # Show vertex bounds
            xs = [v[0] for v in mesh_data]
            ys = [v[1] for v in mesh_data]
            zs = [v[2] for v in mesh_data]
            print(f"  Bounds: X=[{min(xs):.2f}, {max(xs):.2f}]")
            print(f"          Y=[{min(ys):.2f}, {max(ys):.2f}]")
            print(f"          Z=[{min(zs):.2f}, {max(zs):.2f}]")
            
            # Show first few vertices
            print(f"  First 5 vertices:")
            for j, (x, y, z) in enumerate(mesh_data[:5]):
                print(f"    {j}: ({x:8.3f}, {y:8.3f}, {z:8.3f})")
            
            # Look for indices near this vertex data
            vert_count = len(mesh_data)
            end_offset = offset + vert_count * 6
            
            print(f"\n  Looking for index data near vertex data...")
            indices = find_index_data(data, vert_count, end_offset)
            
            if indices:
                for _, idx_offset, tris in indices[:3]:
                    print(f"    Found {len(tris)} triangles at 0x{idx_offset:06x}")
                    print(f"    First 3: {tris[:3]}")
        
        print()
    
    return meshes_sorted

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_mesh.py input.bin [output.obj]")
        sys.exit(1)
    
    with open(sys.argv[1], "rb") as f:
        data = f.read()
    
    meshes = analyze_mesh(data)
    
    # If output file specified, export largest mesh
    if len(sys.argv) >= 3 and meshes:
        dtype, offset, vertices = meshes[0]
        if dtype == "vertices":
            # Try to find indices
            end_offset = offset + len(vertices) * 6
            index_data = find_index_data(data, len(vertices), end_offset)
            
            if index_data:
                _, _, faces = index_data[0]
                export_obj(vertices, faces, sys.argv[2])
            else:
                # Export as point cloud (no faces)
                print("No index data found, exporting vertices only")
                export_obj(vertices, [], sys.argv[2])

if __name__ == "__main__":
    main()

