import struct
import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from io import BytesIO
import logging

def decompress_lz77(data):
    """Decompress LZ77 compressed data."""
    output = bytearray()
    pos = 0

    # Skip LZ77 header (4C 5A 37 37 => "LZ77")
    if data[:4] == b'LZ77':
        pos = 4
        # Read decompressed size
        decomp_size = struct.unpack('<I', data[pos:pos+4])[0]
        pos += 4

    while pos < len(data):
        if pos >= len(data):
            break
        flag = data[pos]
        pos += 1

        for bit in range(8):
            if pos >= len(data):
                break
            if flag & (1 << bit):
                # Copy-from-previous block
                if pos+2 > len(data):
                    break
                info = struct.unpack('>H', data[pos:pos+2])[0]
                pos += 2
                length = ((info >> 12) & 0xF) + 3
                offset = (info & 0xFFF)
                start = len(output) - offset
                if start < 0:
                    continue
                for i in range(length):
                    if (start + i) < len(output):
                        output.append(output[start + i])
                    else:
                        break
            else:
                # Direct copy
                if pos < len(data):
                    output.append(data[pos])
                    pos += 1
                else:
                    break

    print(f"Decompressed size: {len(output)} bytes")
    return bytes(output)

def hex_dump(data, offset=0, length=128):
    """Helper to dump hex data with offset"""
    for i in range(0, min(length, len(data)), 16):
        chunk = data[i:i+16]
        hex_line = ' '.join(f'{b:02x}' for b in chunk)
        ascii_line = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{i+offset:04x}: {hex_line:<48} {ascii_line}")

class MDLHeader:
    def __init__(self):
        self.id = 0
        self.version = 0
        self.name = ""
        self.length = 0

    def read(self, f):
        self.id = struct.unpack('I', f.read(4))[0]
        self.version = struct.unpack('I', f.read(4))[0]
        name_bytes = f.read(64)
        try:
            self.name = name_bytes.decode('shift-jis').rstrip('\x00')
        except UnicodeDecodeError:
            self.name = name_bytes.hex()
        self.length = struct.unpack('I', f.read(4))[0]
        print(f"Model ID: 0x{self.id:x}")
        print(f"Version: 0x{self.version:x}")
        print(f"Name: {self.name}")
        print(f"Length: {self.length}")

class MDLLump:
    def __init__(self, id_str, offset, size):
        self.id = id_str
        self.offset = offset
        self.size = size

class MDLMaterial:
    def __init__(self):
        self.name = ""
        self.texture_path = ""
        self.properties = {}  # shader properties

class MDLBone:
    def __init__(self):
        self.name = ""
        self.parent_id = -1
        self.position = [0, 0, 0]
        self.rotation = [0, 0, 0]

class MDLMesh:
    def __init__(self):
        self.vertices = []
        self.normals = []
        self.uvs = []
        self.faces = []
        self.material_id = 0
        self.bone_weights = []  # [(bone_id, weight), ...]

class MDLAnimation:
    def __init__(self):
        self.name = ""
        self.frames = []
        self.duration = 0
        self.bone_tracks = {}  # bone_id -> list of transforms

class MDLViewer:
    def __init__(self, filename):
        self.filename = filename
        self.header = MDLHeader()
        self.lumps = {}  # id -> MDLLump
        self.meshes = []  # list of MDLMesh
        self.materials = []  # list of MDLMaterial
        self.bones = []  # list of MDLBone
        self.animations = []  # list of MDLAnimation
        self.current_animation = None
        self.animation_time = 0.0
        self.debug = True  # Enable debug output

    def find_chunks(self, data):
        chunks = []
        i = 0
        while i < len(data):
            if data[i:i+2] == b'\x55\xaa':
                size = int.from_bytes(data[i+2:i+4], byteorder='little')
                print(f"\nFound chunk at offset 0x{i:x}")
                print(f"Chunk size: {size} bytes")
                print("First 16 bytes of chunk:")
                hex_dump(data[i:i+16])
                if 0 < size < len(data) - i:
                    chunk_data = data[i:i+size]
                    chunks.append(('data', i, chunk_data))
                    i += size
                else:
                    # Skip this marker if size is invalid
                    i += 2
            elif data[i:i+2] == b'\xaa\xaa' or data[i:i+2] == b'\x55\x55':
                # Repetitive sequence, possibly padding or delimiter
                j = i + 2
                while j < len(data) and data[j:j+2] == data[i:i+2]:
                    j += 2
                chunks.append(('padding', i, data[i:j]))
                i = j
            else:
                # Unknown data, try to skip to the next potential marker
                j = i + 1
                while j < len(data):
                    if data[j:j+2] == b'\x55\xaa' or data[j:j+2] == b'\xaa\xaa' or data[j:j+2] == b'\x55\x55':
                        break
                    j += 1
                chunks.append(('unknown', i, data[i:j]))
                i = j
        return chunks

    def try_parse_vertices(self, chunk_data):
        """Parse vertices from a chunk"""
        self.vertices = []
        self.faces = []
        
        # First try to find vertex count
        if len(chunk_data) < 4:
            return None
        
        # Try different vertex formats
        vertex_formats = [
            # (stride, format, scale, description)
            (6, '<hhh', 4096.0, 'int16_normalized'),
            (6, '<hhh', 256.0, 'int16_scaled'),
            (12, '<fff', 1.0, 'float32'),
        ]
        
        best_vertices = None
        best_format = None
        
        for stride, fmt, scale, desc in vertex_formats:
            try:
                pos = 0
                vertices = []
                valid = True
                
                # Try to read vertex count if present
                vert_count = struct.unpack('<H', chunk_data[0:2])[0]
                if vert_count > 1000:  # Probably not a count
                    vert_count = len(chunk_data) // stride
                pos = 2
                
                for _ in range(min(vert_count, len(chunk_data) // stride)):
                    if pos + stride > len(chunk_data):
                        break
                    
                    x, y, z = struct.unpack(fmt, chunk_data[pos:pos+stride])
                    if scale != 1.0:
                        x, y, z = x/scale, y/scale, z/scale
                    
                    # Basic validation
                    if abs(x) > 100 or abs(y) > 100 or abs(z) > 100:
                        valid = False
                        break
                    
                    vertices.append([x, y, z])
                    pos += stride
                
                if valid and len(vertices) > 10:
                    if self.debug:
                        print(f"\nFormat {desc} found {len(vertices)} valid vertices:")
                        for i, v in enumerate(vertices[:5]):
                            print(f"  V{i}: ({v[0]:.2f}, {v[1]:.2f}, {v[2]:.2f})")
                    
                    if best_vertices is None or len(vertices) > len(best_vertices):
                        best_vertices = vertices
                        best_format = desc
                    
            except struct.error:
                continue
        
        if best_vertices:
            print(f"\nUsing {best_format} format, found {len(best_vertices)} vertices")
            self.vertices = best_vertices
            
            # Try to find face data in remaining chunk data
            self.try_parse_faces(chunk_data[pos:])
        
        return self.vertices

    def try_parse_faces(self, data):
        """Try to parse face indices from data"""
        if len(data) < 6:
            return
        
        try:
            # Try to read face count
            face_count = struct.unpack('<H', data[0:2])[0]
            if face_count > 5000:  # Probably not a count
                return
            
            pos = 2
            faces = []
            
            for _ in range(face_count):
                if pos + 6 > len(data):
                    break
                
                i1, i2, i3 = struct.unpack('<HHH', data[pos:pos+6])
                if i1 < len(self.vertices) and i2 < len(self.vertices) and i3 < len(self.vertices):
                    faces.append([i1, i2, i3])
                pos += 6
            
            if faces:
                print(f"Found {len(faces)} faces")
                self.faces = faces
                return
            
        except struct.error:
            pass
        
        # Fallback: create triangle strip
        print("Creating triangle strip faces")
        for i in range(len(self.vertices) - 2):
            self.faces.append([i, i+1, i+2])

    def try_parse_header(self, chunk_data):
        # Example header parsing logic (adjust based on observed patterns)
        if len(chunk_data) >= 16 and chunk_data[0:4] == b'\x50\x06\xc2\x70':
            header = {
                'magic': chunk_data[0:4],
                'version': int.from_bytes(chunk_data[4:6], byteorder='little'),
                'vertex_count': int.from_bytes(chunk_data[6:8], byteorder='little'),
                'face_count': int.from_bytes(chunk_data[8:10], byteorder='little'),
                # Add other fields as needed
            }
            print(f"  Found header: {header}")
            return header
        return None

    def load(self):
        with open(self.filename, 'rb') as f:
            data = f.read()
            print(f"\nReading file: {self.filename}")
            print(f"File size: {len(data)} bytes")
            
            # Show compressed header
            print("\nCompressed header:")
            hex_dump(data[:32])
            
            # Decompress if needed
            if data[:4] == b'LZ77':
                print("\nFound LZ77 compression")
                data = decompress_lz77(data)
                print(f"Decompressed size: {len(data)} bytes")
                
                # Show decompressed data sections
                print("\nDecompressed header (first 64 bytes):")
                hex_dump(data[:64])
                
                # Show potential vertex data start (looking for patterns)
                print("\nPotential vertex data (at offset 0x80):")
                hex_dump(data[0x80:0x80+64])
                
                # Show some data from the middle of the file
                mid_point = len(data) // 2
                print(f"\nMid-file data (at offset 0x{mid_point:x}):")
                hex_dump(data[mid_point:mid_point+64])
                
                # Show potential face data (after vertex data)
                vertex_end = 0x80 + (7281 * 6)  # Assuming 6 bytes per vertex
                print(f"\nPotential face data (at offset 0x{vertex_end:x}):")
                hex_dump(data[vertex_end:vertex_end+64])

            # Read header
            if len(data) < 16:
                print("File too small")
                return
            
            self.model_id = struct.unpack('<I', data[0:4])[0]
            self.version = struct.unpack('<I', data[4:8])[0]
            
            # Try to read name (assuming null-terminated)
            name_end = data[8:].find(b'\0')
            if name_end != -1:
                self.name = data[8:8+name_end].decode('shift-jis', errors='ignore')
            
            print(f"Model ID: 0x{self.model_id:08x}")
            print(f"Version: 0x{self.version:08x}")
            print(f"Name: {self.name}")
            
            # Find and process chunks
            chunks = self.find_chunks(data)
            for chunk_type, offset, chunk_data in chunks:
                if chunk_type == 'data':
                    # Try to parse vertices from data chunks
                    vertices = self.try_parse_vertices(chunk_data)
                    if vertices:
                        print(f"Found {len(vertices)} vertices")
                        
                    # Try to parse faces if we have vertices
                    if self.vertices:
                        faces = self.try_parse_faces(chunk_data)
                        if faces:
                            print(f"Found {len(faces)} faces")
                
                elif chunk_type == 'padding':
                    if self.debug:
                        print(f"Found padding at offset {offset}")
                    
                else:
                    if self.debug:
                        print(f"Unknown chunk type at offset {offset}")

        # Update the scene after loading
        self.update_scene()

    def parse_lumps(self, data):
        """Parse the lump directory structure"""
        pos = 0x80  # Start after header area
        while pos < len(data):
            # Check for lump signature (usually 4 bytes)
            if pos + 8 > len(data):
                break
                
            lump_id = data[pos:pos+4]
            if all(x == 0 for x in lump_id):  # Skip empty sections
                pos += 4
                continue
                
            lump_size = struct.unpack('<I', data[pos+4:pos+8])[0]
            
            # Known lump IDs (based on hex analysis)
            if lump_id == b'VERT':  # Vertex data
                self.parse_vertex_lump(data[pos+8:pos+8+lump_size])
            elif lump_id == b'NORM':  # Normal data
                self.parse_normal_lump(data[pos+8:pos+8+lump_size])
            elif lump_id == b'TEXC':  # UV coordinates
                self.parse_uv_lump(data[pos+8:pos+8+lump_size])
            elif lump_id == b'BONE':  # Skeleton data
                self.parse_bone_lump(data[pos+8:pos+8+lump_size])
            elif lump_id == b'ANIM':  # Animation data
                self.parse_animation_lump(data[pos+8:pos+8+lump_size])
            elif lump_id == b'MATL':  # Material data
                self.parse_material_lump(data[pos+8:pos+8+lump_size])
                
            pos += 8 + lump_size

    def parse_vertex_lump(self, data):
        """Parse vertex data with improved format detection"""
        mesh = MDLMesh()
        pos = 0
        
        # Try to detect vertex format
        vertex_count = struct.unpack('<H', data[pos:pos+2])[0]
        pos += 2
        
        for _ in range(vertex_count):
            if pos + 12 > len(data):
                break
                
            # Try float32 format first
            try:
                x = struct.unpack('<f', data[pos:pos+4])[0]
                y = struct.unpack('<f', data[pos+4:pos+8])[0]
                z = struct.unpack('<f', data[pos+8:pos+12])[0]
                pos += 12
            except struct.error:
                # Fallback to int16 format
                x = struct.unpack('<h', data[pos:pos+2])[0] / 256.0
                y = struct.unpack('<h', data[pos+2:pos+4])[0] / 256.0
                z = struct.unpack('<h', data[pos+4:pos+6])[0] / 256.0
                pos += 6
                
            mesh.vertices.append([x, y, z])
            
        self.meshes.append(mesh)

    def parse_normal_lump(self, data):
        """Parse vertex normals"""
        if not self.meshes:
            return
            
        mesh = self.meshes[-1]  # Add to current mesh
        pos = 0
        
        while pos + 12 <= len(data):
            nx = struct.unpack('<f', data[pos:pos+4])[0]
            ny = struct.unpack('<f', data[pos+4:pos+8])[0]
            nz = struct.unpack('<f', data[pos+8:pos+12])[0]
            mesh.normals.append([nx, ny, nz])
            pos += 12

    def parse_uv_lump(self, data):
        """Parse UV coordinates"""
        if not self.meshes:
            return
            
        mesh = self.meshes[-1]
        pos = 0
        
        while pos + 8 <= len(data):
            u = struct.unpack('<f', data[pos:pos+4])[0]
            v = struct.unpack('<f', data[pos+4:pos+8])[0]
            mesh.uvs.append([u, v])
            pos += 8

    def parse_bone_lump(self, data):
        """Parse bone data"""
        # Implementation needed
        pass

    def parse_animation_lump(self, data):
        """Parse animation data"""
        # Implementation needed
        pass

    def parse_material_lump(self, data):
        """Parse material data"""
        # Implementation needed
        pass

    def parse_mdl_data(self, data):
        chunks = self.find_chunks(data)
        for chunk_type, offset, chunk_data in chunks:
            print(f"Chunk type: {chunk_type} at offset {offset} with size {len(chunk_data)}")
            if chunk_type == 'data':
                header = self.try_parse_header(chunk_data)
                if header:
                    # Process header information
                    pass
                # Further processing of data chunks
                self.try_parse_vertices(chunk_data)
                self.try_parse_faces(chunk_data)
            elif chunk_type == 'padding':
                print("  Found padding sequence")
            else:
                print("  Found unknown data")
        self.update_scene()

    def render(self):
        pygame.init()
        display = (800, 600)
        screen = pygame.display.set_mode(display, pygame.DOUBLEBUF|pygame.OPENGL)
        font = pygame.font.Font(None, 36)

        # Create a separate surface for text overlay
        info_display = pygame.Surface(display, pygame.SRCALPHA)
        
        # Add camera control variables
        camera_distance = 15.0
        camera_x = 0
        camera_y = 2
        rotation_x = 20
        rotation_y = 0
        move_speed = 0.5
        rotate_speed = 2

        # Center and scale the model
        if hasattr(self, 'vertices') and self.vertices:
            min_x = min(v[0] for v in self.vertices)
            max_x = max(v[0] for v in self.vertices)
            min_y = min(v[1] for v in self.vertices)
            max_y = max(v[1] for v in self.vertices)
            min_z = min(v[2] for v in self.vertices)
            max_z = max(v[2] for v in self.vertices)
            
            # center & scale
            cx = (min_x+max_x)/2
            cy = (min_y+max_y)/2
            cz = (min_z+max_z)/2
            size = max(max_x-min_x, max_y-min_y, max_z-min_z)
            scale = 8.0 / size if size > 0 else 1.0
            
            # shift & scale vertices
            for i in range(len(self.vertices)):
                self.vertices[i] = [
                    (self.vertices[i][0] - cx)*scale,
                    (self.vertices[i][1] - cy)*scale,
                    (self.vertices[i][2] - cz)*scale
                ]

        gluPerspective(45, display[0]/display[1], 0.1, 1000.0)
        glTranslatef(0, 0, -camera_distance)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        glLightfv(GL_LIGHT0, GL_POSITION, [1.0,1.0,1.0,0.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3,0.3,0.3,1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.7,0.7,0.7,1.0])
        glClearColor(0.1,0.1,0.1,1.0)

        # Add texture support
        glEnable(GL_TEXTURE_2D)
        
        # Render meshes with materials
        for mesh in self.meshes:
            if mesh.material_id < len(self.materials):
                material = self.materials[mesh.material_id]
                # Bind texture if available
                if hasattr(material, 'texture_id'):
                    glBindTexture(GL_TEXTURE_2D, material.texture_id)
            
            glBegin(GL_TRIANGLES)
            for i, face in enumerate(mesh.faces):
                for j, vertex_id in enumerate(face):
                    # Normal
                    if mesh.normals and vertex_id < len(mesh.normals):
                        glNormal3fv(mesh.normals[vertex_id])
                    
                    # UV coordinate
                    if mesh.uvs and vertex_id < len(mesh.uvs):
                        glTexCoord2fv(mesh.uvs[vertex_id])
                    
                    # Vertex
                    if vertex_id < len(mesh.vertices):
                        glVertex3fv(mesh.vertices[vertex_id])
            glEnd()

        # Update animation if active
        if self.current_animation:
            self.update_animation()

        while True:
            for evt in pygame.event.get():
                if evt.type == pygame.QUIT:
                    pygame.quit()
                    return

            # Handle keyboard input
            keys = pygame.key.get_pressed()
            if keys[pygame.K_LEFT]:
                camera_x -= move_speed
            if keys[pygame.K_RIGHT]:
                camera_x += move_speed
            if keys[pygame.K_UP]:
                camera_y += move_speed
            if keys[pygame.K_DOWN]:
                camera_y -= move_speed
            if keys[pygame.K_a]:
                rotation_y -= rotate_speed
            if keys[pygame.K_d]:
                rotation_y += rotate_speed
            if keys[pygame.K_w]:
                rotation_x -= rotate_speed
            if keys[pygame.K_s]:
                rotation_x += rotate_speed
            if keys[pygame.K_q]:
                camera_distance += move_speed
            if keys[pygame.K_e]:
                camera_distance = max(5.0, camera_distance - move_speed)

            # Clear everything
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

            # 3D Scene rendering
            glEnable(GL_DEPTH_TEST)
            glEnable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            gluPerspective(45, display[0]/display[1], 0.1, 1000.0)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()
            glTranslatef(camera_x, camera_y, -camera_distance)
            glRotatef(rotation_x, 1, 0, 0)
            glRotatef(rotation_y, 0, 1, 0)

            # ground plane
            glPolygonMode(GL_FRONT_AND_BACK, GL_FILL)
            glBegin(GL_QUADS)
            glColor3f(0.8,0.8,0.0)
            ground=20
            glVertex3f(-ground,-5,-ground)
            glVertex3f(-ground,-5, ground)
            glVertex3f( ground,-5, ground)
            glVertex3f( ground,-5,-ground)
            glEnd()

            # grid lines
            glBegin(GL_LINES)
            glColor3f(1,1,0.2)
            for i in range(-20,21,2):
                glVertex3f(i,-4.99,-20)
                glVertex3f(i,-4.99, 20)
                glVertex3f(-20,-4.99,i)
                glVertex3f( 20,-4.99,i)
            glEnd()

            # model
            glLineWidth(2.0)
            glPolygonMode(GL_FRONT_AND_BACK, GL_LINE)
            glBegin(GL_TRIANGLES)
            glColor3f(0,1,1)
            if hasattr(self, 'faces') and hasattr(self, 'vertices'):
                for face in self.faces:
                    for vid in face:
                        if 0 <= vid < len(self.vertices):
                            glVertex3fv(self.vertices[vid])
            glEnd()
            glLineWidth(1.0)

            # Prepare for 2D rendering
            glDisable(GL_DEPTH_TEST)
            glDisable(GL_LIGHTING)
            glMatrixMode(GL_PROJECTION)
            glLoadIdentity()
            glOrtho(0, display[0], display[1], 0, -1, 1)
            glMatrixMode(GL_MODELVIEW)
            glLoadIdentity()

            # Clear the info display
            info_display.fill((0,0,0,0))

            # Render text to info display
            text_lines = [
                f"Camera: X={camera_x:.1f} Y={camera_y:.1f} Z={camera_distance:.1f}",
                f"Rotation: X={rotation_x:.1f} Y={rotation_y:.1f}",
                "Controls:",
                "Arrows: Move camera   W/S: Tilt up/down",
                "A/D: Rotate left/right   Q/E: Zoom in/out"
            ]
            
            y_offset = 10
            for line in text_lines:
                # Add black outline/shadow for better visibility
                for dx, dy in [(-1,-1), (-1,1), (1,-1), (1,1)]:
                    text = font.render(line, True, (0, 0, 0))
                    info_display.blit(text, (10 + dx, y_offset + dy))
                
                # Render the actual text in bright cyan
                text = font.render(line, True, (0, 255, 255))
                info_display.blit(text, (10, y_offset))
                y_offset += 30

            # Enable blending for text
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
            
            # Draw the text overlay
            text_data = pygame.image.tostring(info_display, 'RGBA', True)
            glRasterPos2i(0, 0)
            glDrawPixels(display[0], display[1], GL_RGBA, GL_UNSIGNED_BYTE, text_data)

            # Single buffer flip at the end
            pygame.display.flip()
            pygame.time.wait(10)

    def update_animation(self):
        """Update bone transforms for current animation frame"""
        if not self.current_animation:
            return
            
        self.animation_time += 0.016  # ~60fps
        if self.animation_time > self.current_animation.duration:
            self.animation_time = 0.0
            
        # Update bone matrices
        for bone_id, track in self.current_animation.bone_tracks.items():
            if bone_id < len(self.bones):
                # Interpolate between keyframes
                frame_idx = int(self.animation_time * 30)  # assuming 30fps
                if frame_idx < len(track):
                    self.bones[bone_id].position = track[frame_idx].position
                    self.bones[bone_id].rotation = track[frame_idx].rotation

    def update_scene(self):
        """Update the scene after loading new data"""
        # Center and scale the model if we have vertices
        if hasattr(self, 'vertices') and self.vertices:
            # Find model bounds
            min_x = min(v[0] for v in self.vertices)
            max_x = max(v[0] for v in self.vertices)
            min_y = min(v[1] for v in self.vertices)
            max_y = max(v[1] for v in self.vertices)
            min_z = min(v[2] for v in self.vertices)
            max_z = max(v[2] for v in self.vertices)
            
            # Calculate center and scale
            cx = (min_x + max_x) / 2
            cy = (min_y + max_y) / 2
            cz = (min_z + max_z) / 2
            
            # Calculate model size and scaling factor
            size = max(max_x - min_x, max_y - min_y, max_z - min_z)
            scale = 8.0 / size if size > 0 else 1.0
            
            # Update vertices to be centered and scaled
            for i in range(len(self.vertices)):
                self.vertices[i] = [
                    (self.vertices[i][0] - cx) * scale,
                    (self.vertices[i][1] - cy) * scale,
                    (self.vertices[i][2] - cz) * scale
                ]
            
            if self.debug:
                print(f"Model centered and scaled (scale factor: {scale:.2f})")

if __name__ == "__main__":
    viewer = MDLViewer("Tools/Testing/E002.mdl")
    viewer.load()
    viewer.render()
