import struct
from pathlib import Path
import binascii
import re
from collections import defaultdict

def find_compression_patterns(exe_data: bytes) -> list:
    """Look for potential LZ77 decompression code patterns in executable"""
    patterns = {
        'lz77_magic': rb'LZ77',
        'copy_ops': rb'[\x00-\xFF][\x00-\xFF].{2,6}(?:\x83|\x81|\x8B)',  # Common x86 MOV/LEA patterns
        'length_masks': rb'[\x0F\x1F\x3F\x7F\xFF]',  # Common bit masks
        'window_size': rb'\x00\x10|\x00\x20|\x00\x40',  # Common window sizes (4KB, 8KB, 16KB)
    }
    
    results = defaultdict(list)
    
    for name, pattern in patterns.items():
        for match in re.finditer(pattern, exe_data):
            offset = match.start()
            context = exe_data[max(0, offset-16):offset+32]
            results[name].append({
                'offset': offset,
                'context': binascii.hexlify(context).decode(),
                'data': binascii.hexlify(match.group()).decode()
            })
    
    return results

def analyze_mdl_structure(mdl_data: bytes) -> dict:
    """Analyze MDL file structure and compression format"""
    header = mdl_data[:32]
    
    analysis = {
        'header': {
            'magic': header[0:4],
            'decompressed_size': struct.unpack('<I', header[4:8])[0] if len(header) >= 8 else 0,
            'flags': [
                struct.unpack('<I', header[8:12])[0] if len(header) >= 12 else 0,
                struct.unpack('<I', header[12:16])[0] if len(header) >= 16 else 0
            ],
            'header_hex': binascii.hexlify(header).decode()
        },
        'compression': {
            'block_markers': [],
            'potential_tables': [],
            'patterns': []
        }
    }
    
    # Look for compression block markers
    for i in range(0, len(mdl_data), 2048):
        block = mdl_data[i:i+16]
        if any(marker in block for marker in [b'\xFF\xFF\xFF\xFF', b'\x00\x00\x00\x00', b'\xAA\xAA\xAA\xAA']):
            analysis['compression']['block_markers'].append({
                'offset': i,
                'data': binascii.hexlify(block).decode()
            })
    
    # Look for potential lookup tables
    for i in range(0, len(mdl_data)-256, 16):
        block = mdl_data[i:i+256]
        if len(set(block)) > 200:  # Likely a lookup table if many unique values
            analysis['compression']['potential_tables'].append({
                'offset': i,
                'entropy': len(set(block)),
                'sample': binascii.hexlify(block[:16]).decode()
            })
    
    return analysis

def analyze_block_structure(data: bytes) -> list:
    """Analyze potential compression block structure"""
    blocks = []
    current_pos = 0
    
    while current_pos < len(data):
        # Look for block markers
        for marker in [b'\xAA\xAA\xAA\xAA', b'\xFF\xFF\xFF\xFF']:
            marker_pos = data.find(marker, current_pos)
            if marker_pos >= 0:
                # Found potential block
                block_start = marker_pos & ~0x7FF  # Align to 2048 bytes
                next_block = data.find(marker, marker_pos + 4)
                block_size = next_block - block_start if next_block > 0 else len(data) - block_start
                
                blocks.append({
                    'offset': block_start,
                    'size': block_size,
                    'marker': binascii.hexlify(marker).decode(),
                    'header': binascii.hexlify(data[block_start:block_start+16]).decode()
                })
                current_pos = marker_pos + 4
                break
        else:
            current_pos += 2048
    
    return blocks

def main():
    import argparse
    import sys
    from pathlib import Path
    
    # Use Path for proper path handling
    parser = argparse.ArgumentParser(description='Dokapon MDL/EXE Analyzer')
    parser.add_argument('files', nargs='+', help='Files to analyze (MDL or EXE)', type=Path)
    parser.add_argument('--deep', action='store_true', help='Perform deep analysis')
    args = parser.parse_args()
    
    for file_path in args.files:
        try:
            print(f"\nAnalyzing: {file_path}")
            
            if not file_path.exists():
                print(f"Error: File not found: {file_path}")
                continue
                
            with open(file_path, 'rb') as f:
                data = f.read()
                
            if file_path.suffix.lower() == '.exe':
                print("\n=== Executable Analysis ===")
                patterns = find_compression_patterns(data)
                
                print("\nPotential LZ77 related code locations:")
                for pattern_type, matches in patterns.items():
                    print(f"\n{pattern_type}:")
                    for match in matches[:5]:  # Show first 5 matches
                        print(f"  Offset: 0x{match['offset']:08x}")
                        print(f"  Context: {match['context']}")
                        
            elif file_path.suffix.lower() == '.mdl':
                print("\n=== MDL File Analysis ===")
                analysis = analyze_mdl_structure(data)
                
                print("\nHeader Information:")
                print(f"Magic: {analysis['header']['magic']}")
                print(f"Decompressed Size: {analysis['header']['decompressed_size']:,} bytes")
                print(f"Flags: 0x{analysis['header']['flags'][0]:08x}, 0x{analysis['header']['flags'][1]:08x}")
                
                print("\nCompression Blocks:")
                for block in analysis['compression']['block_markers']:
                    print(f"Block at 0x{block['offset']:08x}: {block['data']}")
                
                if args.deep:
                    print("\nPotential Lookup Tables:")
                    for table in analysis['compression']['potential_tables']:
                        print(f"Table at 0x{table['offset']:08x} (entropy: {table['entropy']})")
                        print(f"Sample: {table['sample']}")
            else:
                print(f"Warning: Unknown file type: {file_path.suffix}")
                
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            if args.deep:
                import traceback
                traceback.print_exc()

if __name__ == '__main__':
    main() 