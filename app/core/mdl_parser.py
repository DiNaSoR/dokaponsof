"""
MDL (3D Model) file parser for Dokapon game files.
Extracts geometry data (vertices, normals, indices) from decompressed MDL data.
"""

import struct
from typing import Optional, Tuple, List, Dict
from dataclasses import dataclass
import numpy as np


@dataclass
class MDLGeometry:
    """Container for parsed MDL geometry data."""
    vertices: np.ndarray  # Nx3 float array
    normals: Optional[np.ndarray]  # Nx3 float array or None
    indices: Optional[np.ndarray]  # Mx3 int array (triangles) or None
    bounds: Tuple[np.ndarray, np.ndarray]  # (min_bounds, max_bounds)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices) if self.vertices is not None else 0
    
    @property
    def face_count(self) -> int:
        return len(self.indices) if self.indices is not None else 0


class MDLParser:
    """
    Parser for Dokapon MDL (3D model) files.
    
    Based on research analysis of the file format:
    - Geometry blocks marked with 0x0000c000
    - Normal blocks marked with 0x000040c1
    - Vertex data: 12 bytes per vertex (3 floats)
    - Normal data: 12 bytes per normal (3 floats)
    - Index data: 2 bytes per index (uint16)
    """
    
    # Block type markers (little-endian)
    MARKERS = {
        b'\x00\x00\xc0\x00': 'geometry',    # 0x0000c000
        b'\x00\x00\x40\xc1': 'normal',      # 0x000040c1
        b'\x00\x00\x40\x00': 'index',       # 0x00004000
        b'\x00\x00\x80\xb9': 'animation',   # 0x000080b9
        b'\x00\x00\x80\x3f': 'float',       # 0x0000803f (1.0f)
        b'\xAA\xAA\xAA\xAA': 'align',       # Alignment
        b'\x55\x55\x55\x55': 'structure',   # Structure
    }
    
    def __init__(self):
        self.debug = False
    
    def parse(self, data: bytes) -> Optional[MDLGeometry]:
        """
        Parse MDL data and extract geometry.
        
        Args:
            data: Decompressed MDL file data
            
        Returns:
            MDLGeometry object or None if parsing failed
        """
        try:
            # Strategy 1: Look for float patterns that look like vertices
            vertices = self._extract_vertices_heuristic(data)
            
            if vertices is None or len(vertices) < 3:
                return None
            
            # Try to find normals
            normals = self._extract_normals_heuristic(data, len(vertices))
            
            # Try to find indices
            indices = self._extract_indices_heuristic(data, len(vertices))
            
            # Calculate bounds
            min_bounds = np.min(vertices, axis=0)
            max_bounds = np.max(vertices, axis=0)
            
            return MDLGeometry(
                vertices=vertices,
                normals=normals,
                indices=indices,
                bounds=(min_bounds, max_bounds)
            )
            
        except Exception as e:
            if self.debug:
                print(f"MDL parse error: {e}")
            return None
    
    def _extract_vertices_heuristic(self, data: bytes) -> Optional[np.ndarray]:
        """
        Extract vertices using heuristic pattern matching.
        Looks for geometry blocks marked with 0x0000c000.
        """
        all_vertices = []
        
        # Find all geometry block markers
        marker = b'\x00\xc0\x00\x00'  # 0x0000c000 little-endian
        pos = 0
        
        while True:
            marker_pos = data.find(marker, pos)
            if marker_pos == -1:
                break
            
            # Extract vertices from this geometry block
            block_vertices = self._extract_block_vertices(data, marker_pos + 4)
            if block_vertices:
                all_vertices.extend(block_vertices)
            
            pos = marker_pos + 4
            
            # Limit total vertices
            if len(all_vertices) > 10000:
                break
        
        # If no marker found, try alternative approach
        if not all_vertices:
            # Look for 0x0000803f (float 1.0) which often precedes vertex data
            float_marker = b'\x00\x00\x80\x3f'
            pos = data.find(float_marker)
            if pos != -1:
                block_vertices = self._extract_block_vertices(data, pos + 4)
                if block_vertices:
                    all_vertices = block_vertices
        
        if len(all_vertices) < 3:
            return None
        
        return np.array(all_vertices, dtype=np.float32)
    
    def _extract_block_vertices(self, data: bytes, start_pos: int, max_vertices: int = 2000) -> List:
        """Extract vertices from a specific block position."""
        vertices = []
        pos = start_pos
        consecutive_invalid = 0
        
        while pos + 12 <= len(data) and len(vertices) < max_vertices:
            try:
                x, y, z = struct.unpack('<fff', data[pos:pos+12])
                
                if self._is_valid_vertex(x, y, z):
                    vertices.append([x, y, z])
                    pos += 12
                    consecutive_invalid = 0
                else:
                    consecutive_invalid += 1
                    pos += 4
                    
                    # Stop if we hit too many invalid values (left the vertex block)
                    if consecutive_invalid > 10:
                        break
                        
            except struct.error:
                break
        
        return vertices if len(vertices) >= 3 else []
    
    def _is_valid_vertex(self, x: float, y: float, z: float) -> bool:
        """Check if values look like valid vertex coordinates."""
        import math
        
        # Check for NaN or infinity
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            return False
        if math.isinf(x) or math.isinf(y) or math.isinf(z):
            return False
        
        # Check reasonable range for game models
        # Based on research: models typically range from -10000 to +10000
        max_coord = 10000
        if abs(x) > max_coord or abs(y) > max_coord or abs(z) > max_coord:
            return False
        
        # Very small values (close to zero but not exactly) are suspicious
        # if they're denormalized floats
        min_significant = 0.0001
        for v in [x, y, z]:
            if v != 0 and abs(v) < min_significant:
                return False
        
        return True
    
    def _extract_normals_heuristic(self, data: bytes, vertex_count: int) -> Optional[np.ndarray]:
        """
        Try to extract normal vectors.
        Normals are unit vectors, so |n| ≈ 1.0
        """
        import math
        
        # Look for normal marker
        marker_pos = data.find(b'\x00\x00\x40\xc1')
        if marker_pos == -1:
            return None
        
        normals = []
        pos = marker_pos + 4
        
        while pos + 12 <= len(data) and len(normals) < vertex_count:
            try:
                nx, ny, nz = struct.unpack('<fff', data[pos:pos+12])
                
                # Check if it looks like a unit normal
                length = math.sqrt(nx*nx + ny*ny + nz*nz)
                if 0.9 < length < 1.1:  # Approximately unit length
                    normals.append([nx, ny, nz])
                    pos += 12
                else:
                    pos += 4
                    
            except struct.error:
                pos += 1
        
        return np.array(normals, dtype=np.float32) if len(normals) >= 3 else None
    
    def _extract_indices_heuristic(self, data: bytes, vertex_count: int) -> Optional[np.ndarray]:
        """
        Try to extract triangle indices.
        Indices are uint16 values pointing to vertices.
        """
        # Look for sequences of valid indices
        indices = []
        pos = 0
        
        # Find index marker or scan for patterns
        marker_pos = data.find(b'\x00\x00\x40\x00')
        if marker_pos != -1:
            pos = marker_pos + 4
        
        while pos + 6 <= len(data):  # Need 3 uint16 for a triangle
            try:
                i0, i1, i2 = struct.unpack('<HHH', data[pos:pos+6])
                
                # Valid indices should be less than vertex count
                if i0 < vertex_count and i1 < vertex_count and i2 < vertex_count:
                    # Avoid degenerate triangles
                    if i0 != i1 and i1 != i2 and i0 != i2:
                        indices.append([i0, i1, i2])
                        pos += 6
                        
                        if len(indices) > 100000:
                            break
                        continue
                
                pos += 2
                
            except struct.error:
                pos += 1
        
        return np.array(indices, dtype=np.int32) if len(indices) >= 1 else None
    
    def get_info(self, data: bytes) -> Dict:
        """
        Get information about MDL data without full parsing.
        """
        info = {
            'size': len(data),
            'markers_found': [],
            'estimated_vertices': 0,
            'has_normals': False,
            'has_indices': False,
        }
        
        # Count markers
        for marker, name in self.MARKERS.items():
            count = data.count(marker)
            if count > 0:
                info['markers_found'].append((name, count))
        
        # Estimate vertex count from geometry marker regions
        geo_pos = data.find(b'\x00\x00\xc0\x00')
        if geo_pos != -1:
            # Count consecutive valid floats
            pos = geo_pos + 4
            count = 0
            while pos + 12 <= len(data) and count < 10000:
                try:
                    x, y, z = struct.unpack('<fff', data[pos:pos+12])
                    if self._is_valid_vertex(x, y, z):
                        count += 1
                        pos += 12
                    else:
                        break
                except:
                    break
            info['estimated_vertices'] = count
        
        info['has_normals'] = b'\x00\x00\x40\xc1' in data
        info['has_indices'] = b'\x00\x00\x40\x00' in data
        
        return info


def parse_mdl(data: bytes) -> Optional[MDLGeometry]:
    """
    Convenience function to parse MDL data.
    
    Args:
        data: Decompressed MDL file data
        
    Returns:
        MDLGeometry object or None
    """
    parser = MDLParser()
    return parser.parse(data)

