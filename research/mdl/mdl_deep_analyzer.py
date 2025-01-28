import struct
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def analyze_mdl_structure(data: bytes) -> dict:
    """Deep analysis of MDL file structure"""
    # Header analysis
    header = {
        'magic': data[0:4],
        'decomp_size': struct.unpack('<I', data[4:8])[0],
        'flag1': struct.unpack('<I', data[8:12])[0],
        'flag2': struct.unpack('<I', data[12:16])[0]
    }
    
    # Find potential block boundaries
    blocks = []
    current_pos = 16
    block_start = current_pos
    
    while current_pos < len(data):
        # Look for block markers or boundaries
        is_boundary = False
        
        # Check for alignment patterns
        if current_pos % 2048 == 0 and current_pos + 16 <= len(data):
            block = data[current_pos:current_pos+16]
            if any(all(b == m for b in block) for m in [0xAA, 0xFF, 0x00]):
                is_boundary = True
        
        # Check for compression flag patterns
        if current_pos + 3 <= len(data):
            flag = data[current_pos]
            if flag in [0xFF, 0x00] and data[current_pos+1] == flag:
                is_boundary = True
        
        if is_boundary and current_pos > block_start:
            blocks.append({
                'start': block_start,
                'size': current_pos - block_start,
                'alignment': block_start % 2048,
                'marker': data[current_pos:current_pos+4].hex()
            })
            block_start = current_pos
            
        current_pos += 1
    
    # Add final block
    if block_start < len(data):
        blocks.append({
            'start': block_start,
            'size': len(data) - block_start,
            'alignment': block_start % 2048,
            'marker': 'end'
        })
    
    # Analyze each block's compression
    for block in blocks:
        start = block['start']
        end = start + block['size']
        block_data = data[start:end]
        
        offsets = []
        lengths = []
        pos = 0
        
        while pos < len(block_data):
            if pos + 1 >= len(block_data):
                break
                
            flag = block_data[pos]
            pos += 1
            
            for bit in range(8):
                if pos >= len(block_data):
                    break
                    
                if flag & (1 << bit):
                    if pos + 2 > len(block_data):
                        break
                    info = struct.unpack('>H', block_data[pos:pos+2])[0]
                    length = ((info >> 12) & 0xF) + 3
                    offset = info & 0xFFF
                    offsets.append(offset)
                    lengths.append(length)
                    pos += 2
                else:
                    pos += 1
        
        block['compression'] = {
            'offsets': offsets,
            'lengths': lengths,
            'avg_offset': np.mean(offsets) if offsets else 0,
            'avg_length': np.mean(lengths) if lengths else 0
        }
    
    return {'header': header, 'blocks': blocks}

def save_analysis_text(analysis, filename):
    """Save analysis results to a text file"""
    output_file = Path(filename).stem + '_analysis.txt'
    with open(output_file, 'w') as f:
        f.write(f"MDL Analysis for: {filename}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write("Header:\n")
        for k, v in analysis['header'].items():
            if isinstance(v, bytes):
                f.write(f"  {k}: {v.hex()}\n")
            else:
                f.write(f"  {k}: 0x{v:x}\n")
        
        f.write(f"\nBlocks: {len(analysis['blocks'])}\n")
        for i, block in enumerate(analysis['blocks']):
            f.write(f"\nBlock {i}:\n")
            f.write(f"  Offset: 0x{block['start']:x}\n")
            f.write(f"  Size: {block['size']:,} bytes\n")
            f.write(f"  Alignment: {block['alignment']}\n")
            f.write(f"  Marker: {block['marker']}\n")
            if 'compression' in block:
                c = block['compression']
                f.write(f"  Avg offset: {c['avg_offset']:.1f}\n")
                f.write(f"  Avg length: {c['avg_length']:.1f}\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Deep analysis of MDL files')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    parser.add_argument('--outputtext', action='store_true', help='Save analysis to text files')
    args = parser.parse_args()
    
    for file in args.files:
        print(f"\nAnalyzing: {file}")
        with open(file, 'rb') as f:
            data = f.read()
        
        analysis = analyze_mdl_structure(data)
        
        if args.outputtext:
            save_analysis_text(analysis, file)
            print(f"Analysis saved to {Path(file).stem}_analysis.txt")
        else:
            print("\nHeader:")
            for k, v in analysis['header'].items():
                if isinstance(v, bytes):
                    print(f"  {k}: {v.hex()}")
                else:
                    print(f"  {k}: {v:x}")
            
            print(f"\nBlocks: {len(analysis['blocks'])}")
            for i, block in enumerate(analysis['blocks']):
                print(f"\nBlock {i}:")
                print(f"  Offset: 0x{block['start']:x}")
                print(f"  Size: {block['size']:,} bytes")
                print(f"  Alignment: {block['alignment']}")
                print(f"  Marker: {block['marker']}")
                if 'compression' in block:
                    c = block['compression']
                    print(f"  Avg offset: {c['avg_offset']:.1f}")
                    print(f"  Avg length: {c['avg_length']:.1f}")

if __name__ == '__main__':
    main() 