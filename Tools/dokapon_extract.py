"""
Dokapon Extract Tool
A versatile tool for extracting and repacking various game assets from DOKAPON! Sword of Fury.

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: GNU General Public License v3.0 (GPL-3.0)

Features:
- Extract embedded PNG images from multiple game file formats
- Handle LZ77 compression
- Preserve file metadata for repacking
- Support for .tex, .mpd, .spranm, and .fnt files
- Maintain directory structure during batch processing

Usage: python dokapon_extract.py [-h] [-i INPUT] [-o OUTPUT] [-t {tex,spranm,fnt,all}] [-v] [--repack]
"""

import os
import struct
import argparse
from dataclasses import dataclass
from typing import Optional
import json

@dataclass
class SpriteHeader:
    size: int
    width: int
    height: int
    bpp: int  # bits per pixel
    palette_offset: int

@dataclass
class MPDHeader:
    """Header structure for .mpd files"""
    magic: str          # "Cell" magic string
    data_size: int      # Size of data section
    width: int          # Image width
    height: int         # Image height
    cell_width: int     # Width of each cell
    cell_height: int    # Height of each cell

def decompress_lz77(data: bytes) -> Optional[bytes]:
    """Decompress Nintendo-style LZ77 data with improved offset handling."""
    if not data.startswith(b'LZ77'):
        return None
    
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
                    # LZ77 backreference
                    if pos + 1 >= len(data):
                        break
                        
                    info = (data[pos] << 8) | data[pos + 1]
                    pos += 2

                    length = ((info >> 12) & 0xF) + 3
                    offset = (info & 0xFFF) + 1

                    # Handle overlapping copies correctly
                    for i in range(length):
                        if len(result) - offset < 0:
                            # Invalid offset - treat as literal
                            result.append(0)
                        else:
                            result.append(result[len(result) - offset])
                else:
                    # Literal byte
                    if pos >= len(data):
                        break
                    result.append(data[pos])
                    pos += 1

        return bytes(result) if len(result) > 0 else None

    except Exception as e:
        print(f"Decompression error: {str(e)}")
        return None

def save_metadata(output_path: str, png_start: int, png_data: bytes, original_file: str = None, extra_info: dict = None) -> None:
    """Save metadata for any extracted PNG file."""
    # Get original file extension from the input file, not the output PNG
    if original_file:
        original_ext = os.path.splitext(original_file)[1].lower()
    else:
        # If no original file provided, try to guess from output path
        original_ext = os.path.splitext(output_path)[1].lower()
        # Remove .png from the extension if it's there
        if original_ext == '.png':
            # Try to determine original extension from the base name
            base = os.path.splitext(output_path)[0]
            if base.endswith('.tex'):
                original_ext = '.tex'
            elif base.endswith('.mpd'):
                original_ext = '.mpd'
            elif base.endswith('.spranm'):
                original_ext = '.spranm'
    
    meta_info = {
        "original_file": original_file or os.path.abspath(output_path),
        "original_extension": original_ext,
        "offset": png_start,
        "length": len(png_data)
    }
    
    # Add any extra information (like MPD header)
    if extra_info:
        meta_info.update(extra_info)
        
    json_path = output_path + ".json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(meta_info, f, ensure_ascii=False, indent=4)
    print(f"Metadata saved to: {os.path.basename(json_path)}")

def extract_spranm(data: bytes, output_path: str = None) -> tuple[bool, bool, bytes, Optional[int]]:
    """Extract .spranm data with improved error handling."""
    try:
        # Try LZ77 if it starts with "LZ77"
        if data.startswith(b'LZ77'):
            decompressed = decompress_lz77(data)
            if decompressed:
                data = decompressed
                print("Successfully decompressed LZ77 data (spranm)")
                print(f"Decompressed size: {len(data)} bytes")

        # If it starts with "Sequ", check for PNG inside
        if data.startswith(b'Sequ'):
            png_start = data.find(b'\x89PNG')
            if png_start != -1:
                png_end = data.find(b'IEND', png_start)
                if png_end != -1:
                    # Include PNG chunk CRC (4 bytes after IEND)
                    png_end += 8
                    png_data = data[png_start:png_end]
                    
                    # Save metadata if output path is provided
                    if output_path:
                        save_metadata(output_path, png_start, png_data)
                        
                    return (True, True, png_data, png_start)  # Return png_start as well

            # No PNG found, but valid "Sequ" data
            return (True, False, data, None)

    except Exception as e:
        print(f"Error processing SPRANM: {str(e)}")
        return (False, False, b'', None)

    # No "Sequ" or PNG found, return raw data
    return (True, False, data, None)

def extract_tex(data: bytes, output_path: str, original_file: str = None) -> bool:
    """Extract PNG data from a .tex file (optionally LZ77-compressed)."""
    # Attempt LZ77 decompression
    if data.startswith(b'LZ77'):
        decompressed = decompress_lz77(data)
        if decompressed:
            data = decompressed
            print("Successfully decompressed LZ77 data (tex)")

    # Find PNG signature
    png_start = data.find(b'\x89PNG\r\n\x1a\n')
    if png_start >= 0:
        png_data = data[png_start:]
        
        # Save the PNG data
        with open(output_path, 'wb') as out_file:
            out_file.write(png_data)
            
        # Save metadata using common function with original file path
        save_metadata(output_path, png_start, png_data, original_file)
            
        print(f"Successfully extracted: {os.path.basename(output_path)}")
        return True

    return False

def strip_metadata_png(png_data: bytes) -> bytes:
    """Strip unnecessary metadata from PNG while preserving core image data"""
    from PIL import Image
    import io
    
    # Load and resave through PIL to strip metadata
    img = Image.open(io.BytesIO(png_data))
    output = io.BytesIO()
    img.save(output, format='PNG', optimize=True)
    stripped_data = output.getvalue()
    
    # Ensure IHDR follows PNG signature
    png_sig = b'\x89PNG\r\n\x1a\n'
    ihdr_start = stripped_data.find(b'IHDR')
    if ihdr_start > 8:
        ihdr_chunk = stripped_data[ihdr_start-4:ihdr_start+17]
        return png_sig + ihdr_chunk + stripped_data[ihdr_start+17:]
    return stripped_data

def repack_png(json_path: str, modified_png_path: str, output_path: str) -> bool:
    """Repack a modified PNG file using stored metadata."""
    try:
        if not os.path.exists(json_path):
            print(f"Error: JSON metadata file not found: {json_path}")
            return False
            
        if not os.path.exists(modified_png_path):
            print(f"Error: Modified PNG file not found: {modified_png_path}")
            return False
            
        with open(json_path, 'r', encoding='utf-8') as meta_file:
            meta_info = json.load(meta_file)
            
        original_file = meta_info.get("original_file")
        if not original_file or not os.path.exists(original_file):
            print("Error: Original file path not found in metadata")
            return False
            
        with open(modified_png_path, 'rb') as png_file:
            png_data = png_file.read()
            
        with open(original_file, 'rb') as orig_file:
            original_data = orig_file.read()
            
        offset = meta_info["offset"]
        length = meta_info["length"]
        
        if not png_data.startswith(b'\x89PNG\r\n\x1a\n'):
            print("Error: Modified file is not a valid PNG")
            return False
            
        # Strip metadata from PNG
        stripped_png = strip_metadata_png(png_data)
        
        # Handle size differences
        if len(stripped_png) < length:
            stripped_png += b'\x00' * (length - len(stripped_png))
        elif len(stripped_png) > length:
            print(f"Warning: Stripped PNG still larger than original ({len(stripped_png)} > {length} bytes)")
            print("The file will be truncated, which may cause corruption")
            stripped_png = stripped_png[:length]
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        new_data = original_data[:offset] + stripped_png + original_data[offset + length:]
        
        with open(output_path, 'wb') as out_file:
            out_file.write(new_data)
            
        print(f"Successfully repacked stripped PNG to: {output_path}")
        print(f"Original size: {length} bytes")
        print(f"New size: {len(stripped_png)} bytes")
        return True
        
    except Exception as e:
        print(f"Error repacking PNG: {str(e)}")
        return False

def extract_fnt(data: bytes, output_path: str) -> bool:
    """Extract font data with improved error handling."""
    try:
        if data.startswith(b'LZ77'):
            decompressed = decompress_lz77(data)
            if decompressed:
                data = decompressed
                print("Successfully decompressed LZ77 data (fnt)")

        with open(output_path, 'wb') as f:
            f.write(data)
        print(f"Successfully extracted font data: {os.path.basename(output_path)}")
        return True

    except Exception as e:
        print(f"Error extracting font data: {str(e)}")
        return False

def extract_mpd(data: bytes, output_path: str, original_file: str = None) -> bool:
    """Extract PNG data from a .mpd file."""
    try:
        # Check magic "Cell" string with proper spacing
        if not data.startswith(b'Cell        '):
            print("Not a valid MPD file (missing Cell magic)")
            return False
            
        # Parse header (first 40 bytes)
        header = MPDHeader(
            magic=data[0:4].decode('ascii'),
            data_size=int.from_bytes(data[0x14:0x18], 'little'),
            width=int.from_bytes(data[0x18:0x1C], 'little'),
            height=int.from_bytes(data[0x1C:0x20], 'little'),
            cell_width=int.from_bytes(data[0x20:0x24], 'little'),
            cell_height=int.from_bytes(data[0x24:0x28], 'little')
        )
        
        # Find embedded PNG data
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start < 0:
            print("PNG signature not found in MPD file.")
            return False
            
        # Find PNG end
        iend_pos = data.find(b'IEND', png_start)
        if iend_pos < 0:
            print("Incomplete PNG data in MPD file")
            return False
            
        # Include IEND chunk and CRC
        png_end = iend_pos + 8
        png_data = data[png_start:png_end]
        
        # Save PNG file
        with open(output_path, 'wb') as f:
            f.write(png_data)
            
        # Save metadata using common function with MPD header info and original file path
        save_metadata(output_path, png_start, png_data, original_file, extra_info={
            "mpd_header": {
                "data_size": header.data_size,
                "width": header.width,
                "height": header.height,
                "cell_width": header.cell_width,
                "cell_height": header.cell_height
            }
        })
            
        print(f"Successfully extracted PNG from MPD: {os.path.basename(output_path)}")
        return True
        
    except Exception as e:
        print(f"Error extracting MPD file: {str(e)}")
        return False

def process_file(input_path: str, output_dir: str, input_root: str = None) -> bool:
    """Process a single file with improved error handling."""
    try:
        with open(input_path, 'rb') as f:
            data = f.read()

        file_ext = os.path.splitext(input_path)[1].lower()
        
        # Preserve directory structure
        if input_root:
            rel_path = os.path.relpath(input_path, input_root)
            output_subdir = os.path.dirname(rel_path)
            if output_subdir:
                full_output_dir = os.path.join(output_dir, output_subdir)
                os.makedirs(full_output_dir, exist_ok=True)
            else:
                full_output_dir = output_dir
        else:
            full_output_dir = output_dir
            
        base_name = os.path.basename(input_path)

        if file_ext == '.tex':
            out_png = os.path.join(full_output_dir, base_name.replace('.tex', '.png'))
            return extract_tex(data, out_png, input_path)
            
        elif file_ext == '.mpd':
            out_png = os.path.join(full_output_dir, base_name.replace('.mpd', '.png'))
            return extract_mpd(data, out_png, input_path)

        elif file_ext == '.spranm':
            # Define output paths first
            out_png = os.path.join(full_output_dir, base_name + '.png')
            out_bin = os.path.join(full_output_dir, base_name + '.bin')
            
            # Pass the original file path for metadata
            success, found_png, final_data, png_start = extract_spranm(data, out_png)  # Get png_start
            if not success:
                print(f"Failed to extract: {base_name}")
                return False

            if found_png:
                with open(out_png, 'wb') as f:
                    f.write(final_data)
                # Save metadata with original file path
                save_metadata(out_png, png_start, final_data, input_path)
                print(f"Extracted animation PNG: {os.path.basename(out_png)}")
            else:
                with open(out_bin, 'wb') as f:
                    f.write(final_data)
                print(f"No PNG found. Saved raw data: {os.path.basename(out_bin)}")

            return True

        elif file_ext == '.fnt':
            out_path = os.path.join(full_output_dir, base_name + '.bin')
            return extract_fnt(data, out_path)

        else:
            print(f"Unsupported file type: {file_ext}")
            return False

    except Exception as e:
        print(f"Error processing {input_path}: {str(e)}")
        return False

def find_files(input_dir: str, exts: list[str], verbose: bool) -> list[str]:
    """Recursively find files with given extensions in directory and subdirectories."""
    all_files = []
    
    for root, _, files in os.walk(input_dir):
        for ext in exts:
            matches = [os.path.join(root, f) for f in files if f.lower().endswith(ext)]
            if verbose and matches:
                rel_path = os.path.relpath(root, input_dir)
                print(f"Found {len(matches)} {ext} files in {rel_path}")
            all_files.extend(matches)
            
    return all_files

def main():
    parser = argparse.ArgumentParser(
        description='Extract and decompress Dokapon Kingdom files (.tex, .spranm, .fnt)',
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('-i', '--input',
                        default='.',
                        help='Input file or directory to process (default: current directory)')

    parser.add_argument('-o', '--output',
                        default='output',
                        help='Output directory (default: ./output)')

    parser.add_argument('-t', '--type',
                        choices=['tex', 'spranm', 'fnt', 'all'],
                        default='all',
                        help=('File type to process (default: all)\n'
                              'tex    - Extract texture files\n'
                              'spranm - Extract sprite animations\n'
                              'fnt    - Extract font files\n'
                              'all    - Process all supported files'))

    parser.add_argument('-v', '--verbose',
                        action='store_true',
                        help='Show detailed processing information')

    parser.add_argument('--repack',
                       action='store_true',
                       help='Repack a modified PNG using JSON metadata')

    args = parser.parse_args()
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    if args.repack:
        print("\n=== Repack PNG File ===")
        print("Enter paths (press Enter to cancel at any prompt)")
        
        json_path = input("Path to JSON metadata file: ").strip()
        if not json_path:
            return
            
        # Load metadata to get original extension
        try:
            with open(json_path, 'r') as f:
                meta_info = json.load(f)
            original_ext = meta_info.get('original_extension', '.bin')
        except:
            original_ext = '.bin'
            
        png_path = input("Path to modified PNG file: ").strip()
        if not png_path:
            return
            
        # Auto-suggest output path using original extension
        suggested_output = os.path.splitext(png_path)[0] + original_ext
            
        output_path = input(f"Output path [{suggested_output}]: ").strip()
        if not output_path:
            output_path = suggested_output
            
        if repack_png(json_path, png_path, output_path):
            print("\nRepacking completed successfully")
        else:
            print("\nRepacking failed")
        return

    try:
        if os.path.isfile(args.input):
            success = process_file(args.input, output_dir)
            if success:
                if args.verbose:
                    print(f"\nProcessed: {args.input}")
                print("\nProcessing complete: 1 file converted successfully")
            else:
                print("\nProcessing failed")

        else:
            # Handle directory
            if args.type == 'all':
                exts = ['.mpd', '.tex', '.spranm', '.fnt']
            else:
                exts = ['.' + args.type]

            input_dir = os.path.abspath(args.input)
            
            # Use new find_files function instead of glob
            all_files = find_files(input_dir, exts, args.verbose)

            if not all_files:
                print(f"No {', '.join(exts)} files found in {args.input} or its subdirectories")
                return

            print(f"\nProcessing {len(all_files)} files...")
            print(f"Extracting to: {output_dir}")

            success_count = 0
            for fpath in all_files:
                # Pass input_dir to preserve directory structure
                if process_file(fpath, output_dir, input_dir):
                    success_count += 1
                    if args.verbose:
                        rel_path = os.path.relpath(fpath, input_dir)
                        print(f"Processed: {rel_path}")

            print(f"\nResults: {success_count}/{len(all_files)} successful")

    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"Fatal error: {str(e)}")

if __name__ == '__main__':
    main()