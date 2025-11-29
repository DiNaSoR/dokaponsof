#!/usr/bin/env python3
"""Parse PS2 VIF commands to extract mesh data from MDL"""
import struct
import sys

def parse_vif_unpack(data, offset):
    """Parse VIF UNPACK command and extract data"""
    if offset + 4 > len(data):
        return None, 0
    
    word = struct.unpack("<I", data[offset:offset+4])[0]
    cmd = (word >> 24) & 0x7F
    
    # UNPACK command format:
    # [31:25] = 0x60-0x7F (UNPACK)
    # [24] = USN (unsigned/signed)
    # [23:16] = NUM (count)
    # [15:14] = VN (vector size: 1-4)
    # [13:12] = VL (component size: 32/16/8/5 bits)
    # [11:0] = ADDR
    
    if cmd < 0x60:
        return None, 0
    
    usn = (word >> 24) & 0x80
    num = (word >> 16) & 0xFF
    vn = ((cmd >> 2) & 0x3) + 1  # 1-4 components
    vl_code = cmd & 0x3
    
    # Component sizes
    vl_sizes = {0: 32, 1: 16, 2: 8, 3: 5}
    vl = vl_sizes.get(vl_code, 32)
    
    # Calculate data size
    component_bytes = (vl + 7) // 8
    row_bytes = vn * component_bytes
    # Round up to 4-byte alignment
    row_bytes_aligned = (row_bytes + 3) & ~3
    total_bytes = num * row_bytes_aligned
    
    return {
        'cmd': cmd,
        'num': num,
        'vn': vn,
        'vl': vl,
        'usn': usn,
        'row_bytes': row_bytes_aligned,
        'total_bytes': total_bytes
    }, 4

def extract_vif_data(data, offset, info):
    """Extract vertex data following VIF UNPACK command"""
    vertices = []
    
    num = info['num']
    vn = info['vn']
    vl = info['vl']
    row_bytes = info['row_bytes']
    
    data_start = offset + 4
    
    for i in range(num):
        row_offset = data_start + i * row_bytes
        if row_offset + row_bytes > len(data):
            break
        
        components = []
        for j in range(vn):
            comp_offset = row_offset + j * (vl // 8 if vl >= 8 else 1)
            
            if vl == 32:
                val = struct.unpack("<f", data[comp_offset:comp_offset+4])[0]
            elif vl == 16:
                val = struct.unpack("<h", data[comp_offset:comp_offset+2])[0]
            elif vl == 8:
                val = struct.unpack("<b", data[comp_offset:comp_offset+1])[0]
            else:
                val = 0
            
            components.append(val)
        
        vertices.append(tuple(components))
    
    return vertices

def find_and_extract_meshes(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("\n=== PARSING VIF UNPACK V3-32 COMMANDS (0x6C) ===")
    
    # Find UNPACK V3-32 commands (vertex positions)
    meshes = []
    i = 0
    while i < len(data) - 4:
        word = struct.unpack("<I", data[i:i+4])[0]
        cmd = (word >> 24) & 0x7F
        
        if cmd == 0x6C:  # UNPACK V3-32
            info, _ = parse_vif_unpack(data, i)
            if info and info['num'] >= 3:
                vertices = extract_vif_data(data, i, info)
                
                # Filter valid vertices (must have exactly 3 components)
                valid = []
                for v in vertices:
                    if len(v) >= 3:
                        x, y, z = v[0], v[1], v[2]
                        if all(-1000 < val < 1000 for val in (x, y, z)):
                            valid.append((x, y, z))
                
                if len(valid) >= 10:
                    meshes.append((i, info, valid))
        
        i += 4
    
    print(f"Found {len(meshes)} mesh regions with valid vertices")
    
    # Show details of first few
    all_vertices = []
    for offset, info, vertices in meshes[:20]:
        if len(vertices) >= 10:
            print(f"\n  Offset 0x{offset:06x}: {len(vertices)} vertices (VIF num={info['num']})")
            
            # Calculate bounds
            xs = [v[0] for v in vertices]
            ys = [v[1] for v in vertices]
            zs = [v[2] for v in vertices]
            
            # Only show if has varied values
            unique = len(set(vertices))
            if unique >= len(vertices) // 2:
                print(f"    Bounds: X=[{min(xs):.2f}, {max(xs):.2f}]")
                print(f"            Y=[{min(ys):.2f}, {max(ys):.2f}]")
                print(f"            Z=[{min(zs):.2f}, {max(zs):.2f}]")
                print(f"    First 3: {vertices[:3]}")
                all_vertices.extend(vertices)
    
    return all_vertices, meshes

def export_point_cloud(vertices, filename):
    """Export vertices as OBJ point cloud"""
    # Remove duplicates and zeros
    unique_verts = list(set(vertices))
    valid_verts = [(x, y, z) for x, y, z in unique_verts 
                   if any(abs(v) > 0.01 for v in (x, y, z))]
    
    with open(filename, 'w') as f:
        f.write(f"# Dokapon MDL vertex point cloud\n")
        f.write(f"# {len(valid_verts)} vertices\n\n")
        for x, y, z in valid_verts:
            f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
    
    print(f"\nExported {len(valid_verts)} unique vertices to {filename}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_vif_mesh.py input.bin [output.obj]")
        sys.exit(1)
    
    vertices, meshes = find_and_extract_meshes(sys.argv[1])
    
    if len(sys.argv) >= 3 and vertices:
        export_point_cloud(vertices, sys.argv[2])

if __name__ == "__main__":
    main()

