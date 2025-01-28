import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np

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

class MDLGeometryAnalyzer:
    def __init__(self):
        self.geometry_markers = [
            bytes.fromhex('0000c000'),  # Vertex data
            bytes.fromhex('00004000'),  # Index data
            bytes.fromhex('000040c1')   # Normal data
        ]
    
    def read_vertices(self, data: bytes) -> List[Vertex]:
        vertices = []
        try:
            for i in range(0, len(data) - 11, 12):
                # Try both endianness since we're getting invalid values
                try:
                    x, y, z = struct.unpack('<3f', data[i:i+12])  # Little endian
                except struct.error:
                    x, y, z = struct.unpack('>3f', data[i:i+12])  # Big endian
                
                # Filter out invalid values
                if all(abs(v) < 10000.0 for v in (x,y,z)):  # Reasonable model bounds
                    vertices.append(Vertex(x, y, z))
        except Exception as e:
            print(f"Warning: Error reading vertices: {e}")
        return vertices
    
    def read_indices(self, data: bytes) -> List[int]:
        indices = []
        try:
            for i in range(0, len(data) - 1, 2):
                try:
                    idx, = struct.unpack('<H', data[i:i+2])
                    if idx < 65535:  # Valid index
                        indices.append(idx)
                except struct.error:
                    continue
        except Exception as e:
            print(f"Warning: Error reading indices: {e}")
        return indices
    
    def analyze_geometry(self, filename: str) -> List[GeometryBlock]:
        geometry_blocks = []
        
        with open(filename, 'rb') as f:
            file_size = Path(filename).stat().st_size
            
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            print(f"\nFile Info:")
            print(f"  Size: {file_size:,} bytes")
            print(f"  Decompressed: {decomp_size:,} bytes")
            print(f"  Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Track block stats
            vertex_counts = []
            index_counts = []
            normal_counts = []
            
            # Skip header
            f.seek(16)
            
            while True:
                marker = f.read(4)
                if not marker:
                    break
                    
                if marker in self.geometry_markers:
                    offset = f.tell() - 4
                    data = bytearray()
                    
                    # Read until next marker
                    while True:
                        b = f.read(1)
                        if not b:
                            break
                        if len(data) >= 4:
                            last_four = bytes(data[-4:])
                            if last_four in self.geometry_markers:
                                data = data[:-4]
                                f.seek(-4, 1)
                                break
                        data.extend(b)
                    
                    # Process geometry data
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
                            vertex_counts.append(len(vertices))
                    elif marker == bytes.fromhex('00004000'):
                        if geometry_blocks:
                            geometry_blocks[-1].indices = self.read_indices(bytes(data))
                            index_counts.append(len(geometry_blocks[-1].indices))
                    elif marker == bytes.fromhex('000040c1'):
                        if geometry_blocks:
                            geometry_blocks[-1].normals = self.read_vertices(bytes(data))
                            normal_counts.append(len(geometry_blocks[-1].normals))
                else:
                    f.seek(-3, 1)  # Back up to continue search
        
            # Print statistics
            if vertex_counts:
                print("\nStatistics:")
                print(f"  Vertices per block: {min(vertex_counts)} - {max(vertex_counts)}")
                print(f"  Total vertices: {sum(vertex_counts)}")
                if index_counts:
                    print(f"  Indices per block: {min(index_counts)} - {max(index_counts)}")
                    print(f"  Total indices: {sum(index_counts)}")
                if normal_counts:
                    print(f"  Normals per block: {min(normal_counts)} - {max(normal_counts)}")
                    print(f"  Total normals: {sum(normal_counts)}")
        
        return geometry_blocks

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze MDL geometry')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    analyzer = MDLGeometryAnalyzer()
    for file in args.files:
        print(f"\nAnalyzing geometry in {file}:")
        geometry = analyzer.analyze_geometry(file)
        
        print(f"Found {len(geometry)} geometry blocks:")
        for i, block in enumerate(geometry):
            print(f"\nGeometry Block {i}:")
            print(f"  Offset: 0x{block.offset:x}")
            print(f"  Marker: {block.marker.hex()}")
            print(f"  Vertices: {len(block.vertices)}")
            print(f"  Indices: {len(block.indices)}")
            print(f"  Normals: {len(block.normals)}")
            
            if block.vertices:
                vertices = np.array([(v.x, v.y, v.z) for v in block.vertices])
                print(f"  Vertex bounds:")
                print(f"    X: {vertices[:,0].min():.2f} to {vertices[:,0].max():.2f}")
                print(f"    Y: {vertices[:,1].min():.2f} to {vertices[:,1].max():.2f}")
                print(f"    Z: {vertices[:,2].min():.2f} to {vertices[:,2].max():.2f}")

if __name__ == '__main__':
    main() 