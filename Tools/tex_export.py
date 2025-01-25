import os
import struct
import glob
import binascii

def decompress_lz77(data):
    """Decompress LZ77 formatted data"""
    if not data.startswith(b'LZ77'):
        return None
    
    # Skip LZ77 header (8 bytes)
    compressed_size = struct.unpack('<I', data[8:12])[0]
    decompressed_size = struct.unpack('<I', data[12:16])[0]
    
    result = bytearray()
    pos = 16  # Start after header
    
    try:
        while pos < len(data) and len(result) < decompressed_size:
            flag = data[pos]
            pos += 1
            
            for bit in range(8):
                if pos >= len(data) or len(result) >= decompressed_size:
                    break
                    
                if flag & (0x80 >> bit):
                    # Copy from previous output
                    if pos + 2 > len(data):
                        break
                    
                    info = struct.unpack('>H', data[pos:pos+2])[0]
                    pos += 2
                    
                    length = ((info >> 12) & 0xF) + 3
                    offset = (info & 0xFFF) + 1
                    
                    # Copy bytes, allowing for overlapping copies
                    start = len(result) - offset
                    for i in range(length):
                        result.append(result[start + i])
                else:
                    # Copy byte directly
                    result.append(data[pos])
                    pos += 1
                    
        return bytes(result)
        
    except Exception as e:
        print(f"Error decompressing: {str(e)}")
        return None

def extract_tex(file_path, output_dir):
    """Extract PNG data from a .tex file"""
    with open(file_path, 'rb') as file:
        data = file.read()
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            png_data = data[png_start:]
            output_path = os.path.join(output_dir, os.path.basename(file_path).replace('.tex', '.png'))
            with open(output_path, 'wb') as out_file:
                out_file.write(png_data)
            print(f"Successfully extracted: {os.path.basename(output_path)}")
            return True
        return False

def extract_spranm(data, output_path):
    """Extract and save animation data from a .spranm file"""
    # Check if data starts with "Sequ" magic
    if data.startswith(b'Sequ'):
        # This is an uncompressed animation file
        with open(output_path, 'wb') as f:
            f.write(data)
        print(f"Successfully extracted animation data: {os.path.basename(output_path)}")
        print(f"Animation data size: {len(data)} bytes")
        return True
        
    # Try LZ77 decompression for compressed files
    try:
        decompressed = decompress_lz77(data)
        with open(output_path, 'wb') as f:
            f.write(decompressed)
        print(f"Successfully extracted animation data: {os.path.basename(output_path)}")
        print(f"Animation data size: {len(decompressed)} bytes")
        return True
    except:
        print(f"Error: {os.path.basename(output_path)} is not in LZ77 format")
        return False

def process_directory():
    """Process all .tex and .spranm files in the current directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Get both .tex and .spranm files
    tex_files = glob.glob(os.path.join(script_dir, '*.tex'))
    spranm_files = glob.glob(os.path.join(script_dir, '*.spranm'))
    
    if not tex_files and not spranm_files:
        print("No .tex or .spranm files found in the current directory")
        return
    
    print(f"Found {len(tex_files)} .tex files and {len(spranm_files)} .spranm files")
    print(f"Extracting to: {output_dir}")
    
    success_count = 0
    total_files = len(tex_files) + len(spranm_files)
    
    # Process .tex files
    for tex_path in tex_files:
        if extract_tex(tex_path, output_dir):
            success_count += 1
            
    # Process .spranm files
    for spranm_path in spranm_files:
        with open(spranm_path, 'rb') as f:
            data = f.read()
            
        output_path = os.path.join(output_dir, os.path.basename(spranm_path) + ".bin")
        if extract_spranm(data, output_path):
            success_count += 1
    
    print(f"\nProcessing complete: {success_count}/{total_files} files converted successfully")

if __name__ == '__main__':
    try:
        process_directory()
    except Exception as e:
        print(f"Fatal error: {str(e)}") 