import struct
import numpy as np
import pygame
from OpenGL.GL import *
from OpenGL.GLU import *
from io import BytesIO

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

class MDLViewer:
    def __init__(self, filename):
        self.filename = filename
        self.header = MDLHeader()
        self.vertices = []
        self.faces = []

    def load(self):
        # 1) Read & decompress
        with open(self.filename, 'rb') as f:
            data = f.read()
        decompressed = decompress_lz77(data)
        # We still read the MDL header from the front:
        header_f = BytesIO(decompressed)
        self.header.read(header_f)

        # The entire decompressed chunk:
        model_data = header_f.read()  # after header

        # For clarity, let's show first 128 bytes after header:
        print("\nFirst 128 bytes after MDL header:")
        for i in range(0, min(128, len(model_data)), 16):
            chunk = model_data[i:i+16]
            hex_line = ' '.join(f'{b:02x}' for b in chunk)
            ascii_line = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            print(f"{i+0x00:04x}: {hex_line:<48} {ascii_line}")

        # 2) Hard-coded offsets for lumps in the DECOMPRESSED data
        #    (based on your offsets from hex analysis):
        vertex_lump_offset    = 0x7044   # Where the "vertex" lump seemed to begin
        primitive_lump_offset = 0x6fdc   # Where the "primitive" lump seemed to begin

        # We also assume that each lump has an 8-byte header
        # (4 bytes ID like 'vertex', 4 bytes length, etc.)
        # If that's not correct, we may need to adjust.

        ### Read Vertex Lump ###
        # We'll do a naive approach: skip the lump's 8-byte header,
        # then read 2 bytes for the number of vertices, then read that many (x,y,z) pairs.
        if vertex_lump_offset + 8 >= len(model_data):
            print("\nERROR: The vertex lump offset is out of range!")
            return
        vert_data_offset = vertex_lump_offset + 8

        # Read vertex count (2 bytes, little-endian)
        if vert_data_offset + 2 > len(model_data):
            print("\nERROR: Not enough data to read vertex count.")
            return
        num_vertices = struct.unpack('<H', model_data[vert_data_offset:vert_data_offset+2])[0]
        print(f"\n[Vertex Lump] Reported vertex count: {num_vertices}")

        offset = vert_data_offset + 2
        self.vertices = []
        for i in range(num_vertices):
            if (offset + 6) > len(model_data):
                print(f"Ran out of data at vertex {i}")
                break
            # Possibly 16-bit coords with scale = 256
            # or scale = 1, or something else. We'll try 256 first.
            x = struct.unpack('<h', model_data[offset:offset+2])[0] / 256.0
            y = struct.unpack('<h', model_data[offset+2:offset+4])[0] / 256.0
            z = struct.unpack('<h', model_data[offset+4:offset+6])[0] / 256.0
            offset += 6
            # Debug print the first ~5
            if i < 5:
                print(f"  Vertex {i}: ({x:.2f}, {y:.2f}, {z:.2f})")
            self.vertices.append([x, y, z])
        print(f"Loaded {len(self.vertices)} vertices total from vertex lump.")

        ### Read Primitive Lump (faces) ###
        if primitive_lump_offset + 8 >= len(model_data):
            print("\nERROR: The primitive lump offset is out of range!")
            return
        face_data_offset = primitive_lump_offset + 8

        # Let's guess there's a 2-byte face count:
        if face_data_offset + 2 > len(model_data):
            print("\nERROR: Not enough data to read face count.")
            return
        num_faces = struct.unpack('<H', model_data[face_data_offset:face_data_offset+2])[0]
        offset = face_data_offset + 2
        print(f"\n[Primitive Lump] Potential face count: {num_faces}")

        self.faces = []
        for i in range(num_faces):
            if (offset + 6) > len(model_data):
                print(f"Ran out of data at face {i}")
                break
            i1 = struct.unpack('<H', model_data[offset:offset+2])[0]
            i2 = struct.unpack('<H', model_data[offset+2:offset+4])[0]
            i3 = struct.unpack('<H', model_data[offset+4:offset+6])[0]
            offset += 6
            # Debug print first few
            if i < 5:
                print(f"  Face {i}: {i1}, {i2}, {i3}")
            if i1 < len(self.vertices) and i2 < len(self.vertices) and i3 < len(self.vertices):
                self.faces.append([i1, i2, i3])

        print(f"Loaded {len(self.faces)} faces total from primitive lump.")

        # If no faces, fallback to naive triangle strip approach
        if not self.faces and self.vertices:
            print("\nNo faces loaded. Attempting naive triangle strip fallback.")
            for i in range(len(self.vertices) - 2):
                self.faces.append([i, i+1, i+2])
            print(f"Created {len(self.faces)} faces from strip fallback.")

        # Print basic stats
        if self.vertices:
            xs = [v[0] for v in self.vertices]
            ys = [v[1] for v in self.vertices]
            zs = [v[2] for v in self.vertices]
            print("\nModel Statistics:")
            print(f"  Vert range X: {min(xs):.2f} to {max(xs):.2f}")
            print(f"  Vert range Y: {min(ys):.2f} to {max(ys):.2f}")
            print(f"  Vert range Z: {min(zs):.2f} to {max(zs):.2f}")
            print(f"  Vertex count: {len(self.vertices)}")
            print(f"  Face count:   {len(self.faces)}")

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

        if self.vertices:
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
            # shift & scale
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

if __name__ == "__main__":
    viewer = MDLViewer("E002.mdl")
    viewer.load()
    viewer.render()
