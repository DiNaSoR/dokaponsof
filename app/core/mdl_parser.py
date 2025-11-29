"""
MDL (3D Model) file parser for Dokapon game files.
Extracts geometry data (vertices, normals, indices) from decompressed MDL data.
"""

import struct
from typing import Optional, Tuple, List, Dict, Sequence, Any
from dataclasses import dataclass

try:
    import numpy as np  # type: ignore
except ImportError:  # Numpy may not be installed in minimal setups
    np = None  # type: ignore


@dataclass
class MDLGeometry:
    """Container for parsed MDL geometry data."""
    vertices: Sequence[Any]  # Nx3 array-like
    normals: Optional[Sequence[Any]]  # Nx3 array-like or None
    indices: Optional[Sequence[Any]]  # Mx3 array-like (triangles) or None
    bounds: Tuple[Sequence[Any], Sequence[Any]]  # (min_bounds, max_bounds)
    
    @property
    def vertex_count(self) -> int:
        return len(self.vertices) if self.vertices is not None else 0
    
    @property
    def face_count(self) -> int:
        return len(self.indices) if self.indices is not None else 0


class MDLParser:
    """
    Parser for Dokapon MDL (3D model) files.
    
    For enemy MDL files, the layout is a small table following the literal
    string "Vertex". That table stores 32-bit words, each packing two 16-bit
    values: (offset << 16) | size. The first entry points to the position
    buffer stored as int16 with a bias of 0x4000 and a scale of 1/128.
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
        self.np_available = np is not None
    
    def parse(self, data: bytes) -> Optional[MDLGeometry]:
        """
        Parse MDL data and extract geometry.
        
        Args:
            data: Decompressed MDL file data
            
        Returns:
            MDLGeometry object or None if parsing failed
        """
        try:
            # Strategy 1: Try structured table following the "Vertex" label
            vertices, indices, normals = self._extract_structured_geometry(data)

            # Strategy 2: Look for float32 vertex buffers
            if vertices is None:
                vertices = self._extract_vertices_heuristic(data)

            # Strategy 3: Fall back to packed uint16 positions (fixed-point)
            if vertices is None:
                vertices = self._extract_vertices_uint16(data)
            
            if vertices is None or len(vertices) < 3:
                return None
            
            # Try to find normals if not already found
            if normals is None:
                normals = self._extract_normals_heuristic(data, len(vertices))
            
            # Try to find indices if not already found
            if indices is None:
                indices = self._extract_indices_heuristic(data, len(vertices))
            
            # Calculate bounds
            min_bounds, max_bounds = self._compute_bounds(vertices)
            
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
    
    def _extract_vertices_heuristic(self, data: bytes) -> Optional[Sequence[Any]]:
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
        
        return self._to_array(all_vertices)

    def _extract_vertices_uint16(self, data: bytes, scale: float = 1024.0) -> Optional[Sequence[Any]]:
        """
        Extract vertices stored as packed uint16 triples (fixed-point).
        Picks the longest reasonable run after the header region and scales down.
        """
        best_run = []
        best_start = None

        pos = 0
        data_len = len(data)
        min_start = 0x1000  # skip early header tables
        max_val = 40000     # allow headroom but avoid obvious garbage
        min_run = 20
        max_run = 5000

        while pos + 6 <= data_len:
            x = struct.unpack_from('<H', data, pos)[0]
            y = struct.unpack_from('<H', data, pos + 2)[0]
            z = struct.unpack_from('<H', data, pos + 4)[0]

            if x < max_val and y < max_val and z < max_val:
                run_start = pos
                run = []
                bad = 0
                while pos + 6 <= data_len:
                    x = struct.unpack_from('<H', data, pos)[0]
                    y = struct.unpack_from('<H', data, pos + 2)[0]
                    z = struct.unpack_from('<H', data, pos + 4)[0]
                    if x < max_val and y < max_val and z < max_val:
                        run.append((x / scale, y / scale, z / scale))
                        pos += 6
                        if len(run) >= max_run:
                            break
                    else:
                        bad += 1
                        pos += 2
                        if bad > 5:
                            break

                # Prefer runs that start past the header region and are within size bounds
                if run_start >= min_start and min_run <= len(run) <= max_run and len(run) > len(best_run):
                    best_run = run
                    best_start = run_start
            else:
                pos += 2

            if len(best_run) > 0 and len(best_run) > 5000:
                # Stop searching once we have a very large block
                break

        if len(best_run) < min_run:
            return None

        vertices = self._to_array(best_run)

        # Filter out degenerate runs with tiny bounding boxes
        bounds_min, bounds_max = self._compute_bounds(vertices)
        if all((bmax - bmin) < 0.001 for bmin, bmax in zip(bounds_min, bounds_max)):
            return None

        return vertices

    def _extract_structured_geometry(self, data: bytes):
        """
        Parse the vertex table following the literal 'Vertex' string.
        The table contains 32-bit words where high 16 bits are offset,
        low 16 bits are size. The first entry appears to be positions
        stored as int16 with bias 0x4000 and scale 1/128.
        """
        label_pos = data.find(b'Vertex')
        if label_pos == -1:
            return None, None, None

        pos = label_pos + len(b'Vertex')
        while pos < len(data) and data[pos] == 0x20:
            pos += 1  # skip spaces
        base_offset = pos  # offsets may be relative to this table

        # Read up to 32 u32 entries (first is header/flags, skip it)
        table = []
        for _ in range(32):
            if pos + 4 > len(data):
                break
            val = struct.unpack_from('<I', data, pos)[0]
            pos += 4
            table.append(val)

        if len(table) < 2:
            return None, None, None

        # First entry after header
        pairs = [(val >> 16, val & 0xFFFF) for val in table[1:] if val != 0]
        if not pairs:
            return None, None, None

        # Collect candidate vertex buffers
        vertex_candidates = []
        for off_raw, size in pairs:
            for off in (off_raw, base_offset + off_raw):
                if size == 0 or size % 6 != 0 or off + size > len(data):
                    continue
                buf = data[off:off + size]
                count = size // 6
                if count < 10 or count > 20000:
                    continue
                verts = []
                for i in range(count):
                    x, y, z = struct.unpack_from('<hhh', buf, i * 6)
                    verts.append(((x - 0x4000) / 128.0, (y - 0x4000) / 128.0, (z - 0x4000) / 128.0))
                bounds = self._compute_bounds(verts)
                if bounds[0] and bounds[1]:
                    span = sum(abs(bounds[1][i] - bounds[0][i]) for i in range(3))
                    if 1.0 < span < 2000.0:
                        vertex_candidates.append((off, verts))
        if not vertex_candidates:
            return None, None, None

        # Choose first candidate as default
        vertices = self._to_array(vertex_candidates[0][1])
        vcount = len(vertices)

        # Try to locate an index buffer among the remaining pairs: brute-force mask/shift for best triangle validity
        best_indices = None
        best_quality = 0.0
        masks = (0x1FF, 0x3FF, 0x7FF, 0xFFF)
        shifts = (0, 4, 8, 12)

        for off_raw, size in pairs:
            if size == 0 or size % 2 != 0:
                continue
            for off in (off_raw, base_offset + off_raw):
                if off + size > len(data):
                    continue
                buf = data[off:off + size]
                raw_indices = struct.unpack_from('<' + 'H' * (len(buf) // 2), buf, 0)

                for mask in masks:
                    for shift in shifts:
                        decoded = [((i >> shift) & mask) for i in raw_indices]
                        tri_list = []
                        good = 0
                        total = 0
                        for i in range(0, len(decoded) - 2, 3):
                            a, b, c = decoded[i], decoded[i + 1], decoded[i + 2]
                            total += 1
                            if a == b or b == c or a == c:
                                continue
                            if a >= vcount or b >= vcount or c >= vcount:
                                continue
                            good += 1
                            tri_list.append([a, b, c])
                        if total == 0:
                            continue
                        quality = good / total
                        if tri_list and quality > best_quality:
                            best_quality = quality
                            best_indices = self._to_array(tri_list, dtype='int32')
                if best_quality >= 0.6:
                    break  # good enough
            if best_quality >= 0.6:
                break

        indices = best_indices
        normals = None
        return vertices, indices, normals
    
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
    
    def _extract_normals_heuristic(self, data: bytes, vertex_count: int) -> Optional[Sequence[Any]]:
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
        
        return self._to_array(normals) if len(normals) >= 3 else None
    
    def _extract_indices_heuristic(self, data: bytes, vertex_count: int) -> Optional[Sequence[Any]]:
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
        
        return self._to_array(indices, dtype='int32') if len(indices) >= 1 else None
    
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
                except Exception:
                    break
            info['estimated_vertices'] = count
        info['has_normals'] = b'\x00\x00\x40\xc1' in data
        info['has_indices'] = b'\x00\x00\x40\x00' in data

        return info

    def _to_array(self, values: List[List[float]], dtype: str = 'float32') -> Sequence[Any]:
        """Convert list of lists to numpy array when available, otherwise return list."""
        if self.np_available and np is not None:
            return np.array(values, dtype=dtype)  # type: ignore
        return values

    def _compute_bounds(self, vertices: Sequence[Any]) -> Tuple[Sequence[Any], Sequence[Any]]:
        """Compute bounding box for vertices with or without numpy."""
        if vertices is None or len(vertices) == 0:
            return ([], [])

        if self.np_available and np is not None:
            arr = vertices if isinstance(vertices, np.ndarray) else np.array(vertices, dtype=np.float32)  # type: ignore
            min_bounds = np.min(arr, axis=0)  # type: ignore
            max_bounds = np.max(arr, axis=0)  # type: ignore
            return (min_bounds, max_bounds)

        # Pure-Python fallback
        xs = [v[0] for v in vertices]
        ys = [v[1] for v in vertices]
        zs = [v[2] for v in vertices]
        return ([min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)])


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

