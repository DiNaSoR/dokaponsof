#!/usr/bin/env python3
"""Build complete mesh with triangles from MDL data"""
import struct
import sys

def find_vertex_blocks(data, scale=100.0, min_verts=20):
    """Find contiguous vertex blocks with their exact positions"""
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
        
        if len(verts) >= min_verts:
            blocks.append({
                'start': block_start,
                'end': i,
                'vertices': verts,
                'count': len(verts)
            })
            # Don't re-scan this block
        else:
            i = block_start + 2
    
    return blocks

def find_index_blocks(data, max_idx=65535, min_tris=5):
    """Find triangle index blocks"""
    blocks = []
    
    i = 0
    while i < len(data) - 6:
        block_start = i
        tris = []
        max_found = 0
        
        while i < len(data) - 6:
            try:
                i0, i1, i2 = struct.unpack("<3H", data[i:i+6])
                
                if all(idx < max_idx for idx in (i0, i1, i2)):
                    if not (i0 == i1 == i2 == 0):  # Not all zeros
                        max_found = max(max_found, i0, i1, i2)
                        tris.append((i0, i1, i2))
                        i += 6
                    else:
                        break
                else:
                    break
            except:
                break
        
        if len(tris) >= min_tris and max_found > 2:
            blocks.append({
                'start': block_start,
                'end': i,
                'triangles': tris,
                'count': len(tris),
                'max_idx': max_found
            })
        else:
            i = block_start + 2
    
    return blocks

def match_indices_to_vertices(vertex_blocks, index_blocks):
    """Try to match index blocks with appropriate vertex blocks"""
    matches = []
    
    for idx_block in index_blocks:
        max_idx = idx_block['max_idx']
        
        # Find vertex blocks that could satisfy these indices
        for v_block in vertex_blocks:
            if v_block['count'] > max_idx:
                # This vertex block could work
                matches.append({
                    'vertices': v_block,
                    'indices': idx_block,
                    'valid': True
                })
                break
    
    return matches

def build_mesh(filename, output_obj, scale=100.0):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Find all vertex blocks
    print("\n=== Finding vertex blocks ===")
    vertex_blocks = find_vertex_blocks(data, scale, min_verts=50)
    print(f"Found {len(vertex_blocks)} vertex blocks (50+ verts)")
    
    total_verts = sum(b['count'] for b in vertex_blocks)
    print(f"Total vertices: {total_verts}")
    
    for i, block in enumerate(vertex_blocks[:10]):
        print(f"  [{i}] 0x{block['start']:06x}: {block['count']} verts")
    
    # Find all index blocks
    print("\n=== Finding index blocks ===")
    index_blocks = find_index_blocks(data, max_idx=total_verts, min_tris=10)
    print(f"Found {len(index_blocks)} index blocks (10+ tris, max_idx < {total_verts})")
    
    total_tris = sum(b['count'] for b in index_blocks)
    print(f"Total triangles: {total_tris}")
    
    for i, block in enumerate(index_blocks[:10]):
        print(f"  [{i}] 0x{block['start']:06x}: {block['count']} tris, max_idx={block['max_idx']}")
    
    # Build combined vertex array (all blocks in file order)
    print("\n=== Building combined mesh ===")
    all_vertices = []
    vertex_offset_map = {}  # Map block start to vertex offset
    
    for block in vertex_blocks:
        vertex_offset_map[block['start']] = len(all_vertices)
        all_vertices.extend(block['vertices'])
    
    print(f"Combined vertex count: {len(all_vertices)}")
    
    # Try to use indices that fit within our vertex count
    all_triangles = []
    for idx_block in index_blocks:
        if idx_block['max_idx'] < len(all_vertices):
            # These indices are valid for our vertex array
            all_triangles.extend(idx_block['triangles'])
    
    print(f"Valid triangles: {len(all_triangles)}")
    
    # Export
    if all_vertices:
        with open(output_obj, 'w') as f:
            f.write(f"# MDL mesh: {len(all_vertices)} vertices, {len(all_triangles)} triangles\n")
            
            for x, y, z in all_vertices:
                f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            
            f.write("\n")
            
            for i0, i1, i2 in all_triangles:
                f.write(f"f {i0+1} {i1+1} {i2+1}\n")  # OBJ is 1-indexed
        
        print(f"\nExported to {output_obj}")
        
        # Calculate bounds
        xs = [v[0] for v in all_vertices]
        ys = [v[1] for v in all_vertices]
        zs = [v[2] for v in all_vertices]
        print(f"Bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python build_mesh.py input.bin output.obj [scale]")
        sys.exit(1)
    
    scale = float(sys.argv[3]) if len(sys.argv) > 3 else 100.0
    build_mesh(sys.argv[1], sys.argv[2], scale)

