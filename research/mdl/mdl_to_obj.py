#!/usr/bin/env python3
"""Extract geometry from MDL files and export to OBJ format"""
import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
import sys

@dataclass
class Vertex:
    x: float
    y: float
    z: float

@dataclass
class GeometryBlock:
    offset: int
    marker: bytes
    vertices: List[Vertex]
    indices: List[int]
    normals: List[Vertex]

class MDLToOBJ:
    def __init__(self):
        self.geometry_markers = [
            bytes.fromhex('0000c000'),  # Vertex data
            bytes.fromhex('00004000'),  # Index data
            bytes.fromhex('000040c1')   # Normal data
        ]
    
    def read_vertices(self, data: bytes) -> List[Vertex]:
        vertices = []
        for i in range(0, len(data) - 11, 12):
            try:
                x, y, z = struct.unpack('<3f', data[i:i+12])
                if all(abs(v) < 10000.0 for v in (x, y, z)):
                    vertices.append(Vertex(x, y, z))
            except struct.error:
                continue
        return vertices
    
    def read_indices(self, data: bytes) -> List[int]:
        indices = []
        for i in range(0, len(data) - 1, 2):
            try:
                idx, = struct.unpack('<H', data[i:i+2])
                if idx < 65535:
                    indices.append(idx)
            except struct.error:
                continue
        return indices
    
    def extract_geometry(self, filename: str) -> List[GeometryBlock]:
        geometry_blocks = []
        
        with open(filename, 'rb') as f:
            # Skip LZ77 header
            f.seek(16)
            
            while True:
                marker = f.read(4)
                if not marker or len(marker) < 4:
                    break
                    
                if marker in self.geometry_markers:
                    offset = f.tell() - 4
                    data = bytearray()
                    
                    # Read until next marker
                    while True:
                        b = f.read(1)
                        if not b:
                            break
                        data.extend(b)
                        if len(data) >= 4:
                            last_four = bytes(data[-4:])
                            if last_four in self.geometry_markers:
                                data = data[:-4]
                                f.seek(-4, 1)
                                break
                    
                    if marker == bytes.fromhex('0000c000'):
                        vertices = self.read_vertices(bytes(data))
                        if vertices:
                            geometry_blocks.append(GeometryBlock(
                                offset=offset,
                                marker=marker,
                                vertices=vertices,
                                indices=[],
                                normals=[]
                            ))
                    elif marker == bytes.fromhex('00004000'):
                        if geometry_blocks:
                            geometry_blocks[-1].indices = self.read_indices(bytes(data))
                    elif marker == bytes.fromhex('000040c1'):
                        if geometry_blocks:
                            geometry_blocks[-1].normals = self.read_vertices(bytes(data))
                else:
                    f.seek(-3, 1)
        
        return geometry_blocks
    
    def export_obj(self, geometry_blocks: List[GeometryBlock], output_file: str):
        """Export all geometry blocks to a single OBJ file"""
        all_vertices = []
        all_normals = []
        all_faces = []
        
        vertex_offset = 0
        normal_offset = 0
        
        for block in geometry_blocks:
            # Add vertices
            for v in block.vertices:
                all_vertices.append((v.x, v.y, v.z))
            
            # Add normals
            for n in block.normals:
                all_normals.append((n.x, n.y, n.z))
            
            # Convert indices to triangles
            indices = block.indices
            num_verts = len(block.vertices)
            
            if len(indices) >= 3 and num_verts > 0:
                # Find valid indices that reference our vertices
                valid_indices = [i for i in indices if 0 <= i < num_verts]
                
                if len(valid_indices) >= 3:
                    # Try as triangle list
                    for i in range(0, len(valid_indices) - 2, 3):
                        i0, i1, i2 = valid_indices[i], valid_indices[i+1], valid_indices[i+2]
                        # OBJ is 1-indexed
                        all_faces.append((
                            vertex_offset + i0 + 1,
                            vertex_offset + i1 + 1,
                            vertex_offset + i2 + 1
                        ))
                else:
                    # Generate simple triangle fan from vertices if no valid indices
                    for i in range(1, num_verts - 1):
                        all_faces.append((
                            vertex_offset + 1,  # Center vertex
                            vertex_offset + i + 1,
                            vertex_offset + i + 2
                        ))
            
            vertex_offset += len(block.vertices)
            normal_offset += len(block.normals)
        
        # Write OBJ file
        with open(output_file, 'w') as f:
            f.write(f"# Dokapon MDL Export\n")
            f.write(f"# Vertices: {len(all_vertices)}\n")
            f.write(f"# Normals: {len(all_normals)}\n")
            f.write(f"# Faces: {len(all_faces)}\n\n")
            
            # Write vertices
            for x, y, z in all_vertices:
                f.write(f"v {x:.6f} {y:.6f} {z:.6f}\n")
            
            f.write("\n")
            
            # Write normals
            for x, y, z in all_normals:
                f.write(f"vn {x:.6f} {y:.6f} {z:.6f}\n")
            
            f.write("\n")
            
            # Write faces
            for i0, i1, i2 in all_faces:
                f.write(f"f {i0} {i1} {i2}\n")
        
        print(f"Exported {len(all_vertices)} vertices, {len(all_normals)} normals, {len(all_faces)} faces to {output_file}")
        
        return len(all_vertices), len(all_faces)

def main():
    if len(sys.argv) < 2:
        print("Usage: python mdl_to_obj.py input.mdl [output.obj]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.mdl', '.obj')
    
    converter = MDLToOBJ()
    
    print(f"Extracting geometry from {input_file}...")
    geometry = converter.extract_geometry(input_file)
    
    print(f"Found {len(geometry)} geometry blocks:")
    for i, block in enumerate(geometry):
        print(f"  Block {i}: {len(block.vertices)} vertices, {len(block.indices)} indices, {len(block.normals)} normals")
    
    if geometry:
        converter.export_obj(geometry, output_file)
    else:
        print("No geometry found!")

if __name__ == '__main__':
    main()

