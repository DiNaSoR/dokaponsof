import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import numpy as np

@dataclass
class MonsterModel:
    id: int  # E### number
    vertices: List[tuple]
    indices: List[int]
    normals: List[tuple]
    bounds: Dict[str, tuple]  # min/max for x,y,z
    animation_data: bool
    texture_coords: bool

class MonsterAnalyzer:
    def __init__(self):
        self.model_markers = {
            'vertex': bytes.fromhex('0000c000'),
            'index': bytes.fromhex('00004000'),
            'normal': bytes.fromhex('000040c1'),
            'animation': bytes.fromhex('000080b9'),
            'texture': bytes.fromhex('00002000')
        }
    
    def analyze_model(self, filename: str) -> MonsterModel:
        model_id = int(Path(filename).stem[1:])  # Get ### from E###
        
        with open(filename, 'rb') as f:
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            print(f"\nAnalyzing Monster Model E{model_id:03d}")
            print(f"Decompressed size: {decomp_size:,} bytes")
            print(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Process geometry blocks
            vertices = []
            indices = []
            normals = []
            has_animation = False
            has_textures = False
            
            # Read blocks
            pos = 16
            while pos < Path(filename).stat().st_size:
                f.seek(pos)
                marker = f.read(4)
                if not marker:
                    break
                
                # Check for block markers
                if marker in self.model_markers.values():
                    data_start = f.tell()
                    block_data = bytearray()
                    
                    # Read until next marker
                    while True:
                        b = f.read(1)
                        if not b:
                            break
                        if len(block_data) >= 4:
                            last_four = bytes(block_data[-4:])
                            if last_four in self.model_markers.values():
                                block_data = block_data[:-4]
                                f.seek(-4, 1)
                                break
                        block_data.extend(b)
                    
                    # Process block data
                    if marker == self.model_markers['vertex']:
                        # Read vertices (3 floats per vertex)
                        for i in range(0, len(block_data) - 11, 12):
                            try:
                                x, y, z = struct.unpack('<3f', block_data[i:i+12])
                                if all(abs(v) < 10000.0 for v in (x,y,z)):  # Reasonable bounds
                                    vertices.append((x, y, z))
                            except struct.error:
                                continue
                    
                    elif marker == self.model_markers['index']:
                        # Read indices (2 bytes per index)
                        for i in range(0, len(block_data) - 1, 2):
                            try:
                                idx, = struct.unpack('<H', block_data[i:i+2])
                                if idx < 65535:  # Valid index
                                    indices.append(idx)
                            except struct.error:
                                continue
                    
                    elif marker == self.model_markers['normal']:
                        # Read normals (3 floats per normal)
                        for i in range(0, len(block_data) - 11, 12):
                            try:
                                nx, ny, nz = struct.unpack('<3f', block_data[i:i+12])
                                if all(abs(v) <= 1.0 for v in (nx,ny,nz)):  # Unit normals
                                    normals.append((nx, ny, nz))
                            except struct.error:
                                continue
                    
                    elif marker == self.model_markers['animation']:
                        has_animation = True
                    
                    elif marker == self.model_markers['texture']:
                        has_textures = True
                    
                    pos = f.tell()
                else:
                    pos += 1
            
            # Calculate bounds
            if vertices:
                verts = np.array(vertices)
                bounds = {
                    'x': (float(verts[:,0].min()), float(verts[:,0].max())),
                    'y': (float(verts[:,1].min()), float(verts[:,1].max())),
                    'z': (float(verts[:,2].min()), float(verts[:,2].max()))
                }
            else:
                bounds = {'x':(0,0), 'y':(0,0), 'z':(0,0)}
            
            # Analyze vertex distribution
            if vertices:
                print("\nVertex Analysis:")
                vert_array = np.array(vertices)
                clusters = {}
                for i, v in enumerate(vertices):
                    # Group vertices by position to find common features
                    key = tuple(np.round(v, 1))  # Round to 0.1 precision
                    if key not in clusters:
                        clusters[key] = []
                    clusters[key].append(i)
                
                # Find major features (vertices used multiple times)
                features = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
                print("\nCommon Features:")
                for pos, vert_indices in features[:5]:
                    print(f"  Position {pos}: used {len(vert_indices)} times")
            
            # Analyze symmetry
            if vertices:
                print("\nSymmetry Analysis:")
                vert_array = np.array(vertices)
                
                # Check for mirror symmetry
                x_mirror = np.sum(np.abs(vert_array[:,0])) / len(vertices)
                y_mirror = np.sum(np.abs(vert_array[:,1])) / len(vertices)
                z_mirror = np.sum(np.abs(vert_array[:,2])) / len(vertices)
                
                print("Mirror Symmetry Scores:")
                print(f"  X-axis: {x_mirror:.2f}")
                print(f"  Y-axis: {y_mirror:.2f}")
                print(f"  Z-axis: {z_mirror:.2f}")
                
                # Check for radial symmetry
                xy_dist = np.sqrt(vert_array[:,0]**2 + vert_array[:,1]**2)
                xz_dist = np.sqrt(vert_array[:,0]**2 + vert_array[:,2]**2)
                yz_dist = np.sqrt(vert_array[:,1]**2 + vert_array[:,2]**2)
                
                print("\nRadial Distribution:")
                print(f"  XY-plane: {np.mean(xy_dist):.2f}")
                print(f"  XZ-plane: {np.mean(xz_dist):.2f}")
                print(f"  YZ-plane: {np.mean(yz_dist):.2f}")
            
            # Analyze animation data if present
            if has_animation:
                print("\nAnimation Data:")
                # Count animation blocks
                anim_blocks = sum(1 for marker in self.model_markers.values() 
                                 if marker.startswith(bytes.fromhex('000080')))
                print(f"  Animation blocks: {anim_blocks}")
            
            # Analyze topology
            if indices:
                print("\nTopology Analysis:")
                # Calculate faces from indices
                face_count = len(indices) // 3
                print(f"  Estimated faces: {face_count}")
                
                # Check for strips/fans
                strips = []
                current_strip = []
                for i in range(len(indices)-2):
                    if indices[i] == indices[i+1] or indices[i+1] == indices[i+2]:
                        if current_strip:
                            strips.append(current_strip)
                        current_strip = []
                    else:
                        current_strip.append((indices[i], indices[i+1], indices[i+2]))
                if current_strip:
                    strips.append(current_strip)
                
                print(f"  Triangle strips: {len(strips)}")
                if strips:
                    print(f"  Longest strip: {max(len(s) for s in strips)} triangles")
            
            return MonsterModel(
                id=model_id,
                vertices=vertices,
                indices=indices,
                normals=normals,
                bounds=bounds,
                animation_data=has_animation,
                texture_coords=has_textures
            )

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('files', nargs='+', help='E###.mdl files to analyze')
    args = parser.parse_args()
    
    analyzer = MonsterAnalyzer()
    for file in args.files:
        model = analyzer.analyze_model(file)
        
        print("\nModel Statistics:")
        print(f"  Vertices: {len(model.vertices)}")
        print(f"  Indices: {len(model.indices)}")
        print(f"  Normals: {len(model.normals)}")
        print(f"  Has Animation: {model.animation_data}")
        print(f"  Has Textures: {model.texture_coords}")
        print("\nModel Bounds:")
        print(f"  Width:  {model.bounds['x'][1] - model.bounds['x'][0]:.1f}")
        print(f"  Height: {model.bounds['y'][1] - model.bounds['y'][0]:.1f}")
        print(f"  Depth:  {model.bounds['z'][1] - model.bounds['z'][0]:.1f}")

if __name__ == '__main__':
    main() 