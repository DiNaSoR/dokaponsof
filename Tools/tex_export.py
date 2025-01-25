import os
import struct
import glob

def find_png_header(data):
    """Find the start of PNG data by looking for PNG signature"""
    return data.find(b'\x89PNG\r\n\x1a\n')

def extract_texture(tex_path, output_dir):
    """Extract PNG data from a single .tex file"""
    try:
        with open(tex_path, 'rb') as file:
            data = file.read()
            
            # Find PNG header
            png_start = find_png_header(data)
            if png_start >= 0:
                # Extract from PNG header to end
                png_data = data[png_start:]
                
                # Save as PNG in output directory
                output_path = os.path.join(output_dir, os.path.basename(tex_path).replace('.tex', '.png'))
                with open(output_path, 'wb') as out_file:
                    out_file.write(png_data)
                print(f"Successfully extracted: {os.path.basename(output_path)}")
                return True
            else:
                print(f"No PNG data found in {os.path.basename(tex_path)}")
                return False
    except Exception as e:
        print(f"Error processing {os.path.basename(tex_path)}: {str(e)}")
        return False

def process_directory():
    """Process all .tex files in the current directory"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_dir = os.path.join(script_dir, 'output')
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    tex_files = glob.glob(os.path.join(script_dir, '*.tex'))
    
    if not tex_files:
        print("No .tex files found in the current directory")
        return
    
    success_count = 0
    total_files = len(tex_files)
    
    print(f"Found {total_files} .tex files")
    print(f"Extracting to: {output_dir}")
    
    for tex_path in tex_files:
        if extract_texture(tex_path, output_dir):
            success_count += 1
    
    print(f"\nProcessing complete: {success_count}/{total_files} files converted successfully")

if __name__ == '__main__':
    try:
        process_directory()
    except Exception as e:
        print(f"Fatal error: {str(e)}") 