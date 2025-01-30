import struct
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
import os

def analyze_mdl_structure(data: bytes, verbose=False) -> dict:
    """Deep analysis of MDL file structure"""
    # Header analysis
    header = {
        'magic': data[0:4],
        'decomp_size': struct.unpack('<I', data[4:8])[0],
        'flag1': struct.unpack('<I', data[8:12])[0],
        'flag2': struct.unpack('<I', data[12:16])[0]
    }
    
    if verbose:
        print("\nDetailed Header Analysis:")
        print(f"Magic: {header['magic'].hex()}")
        print(f"Decompressed Size: {header['decomp_size']:,} bytes")
        print(f"Flag1: 0x{header['flag1']:08x}")
        print(f"Flag2: 0x{header['flag2']:08x}\n")
    
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
                if verbose:
                    print(f"Found alignment boundary at 0x{current_pos:x}")
        
        # Check for compression flag patterns
        if current_pos + 3 <= len(data):
            flag = data[current_pos]
            if flag in [0xFF, 0x00] and data[current_pos+1] == flag:
                is_boundary = True
                if verbose:
                    print(f"Found compression boundary at 0x{current_pos:x}")
        
        if is_boundary and current_pos > block_start:
            block_data = data[block_start:current_pos]
            block_info = {
                'start': block_start,
                'size': current_pos - block_start,
                'alignment': block_start % 2048,
                'marker': data[current_pos:current_pos+4].hex(),
                'type': analyze_block_type(block_data)
            }
            blocks.append(block_info)
            if verbose:
                print(f"\nBlock at 0x{block_start:x}:")
                print(f"  Size: {block_info['size']:,} bytes")
                print(f"  Type: {block_info['type']}")
                print(f"  Marker: {block_info['marker']}")
            block_start = current_pos
            
        current_pos += 1
    
    # Add final block
    if block_start < len(data):
        block_data = data[block_start:]
        block_info = {
            'start': block_start,
            'size': len(data) - block_start,
            'alignment': block_start % 2048,
            'marker': 'end',
            'type': analyze_block_type(block_data)
        }
        blocks.append(block_info)
        if verbose:
            print(f"\nFinal Block at 0x{block_start:x}:")
            print(f"  Size: {block_info['size']:,} bytes")
            print(f"  Type: {block_info['type']}")
    
    # Analyze each block's content
    for block in blocks:
        start = block['start']
        end = start + block['size']
        block_data = data[start:end]
        
        block['content'] = analyze_block_content(block_data, block['type'])
        if verbose and block['content']:
            print(f"\nDetailed content for block at 0x{start:x}:")
            for k, v in block['content'].items():
                print(f"  {k}: {v}")
    
    return {'header': header, 'blocks': blocks}

def analyze_block_type(data: bytes) -> str:
    """Determine the type of a data block"""
    if len(data) < 4:
        return 'unknown'
    
    # Check for float data
    try:
        float_val = struct.unpack('f', data[:4])[0]
        if -1e10 < float_val < 1e10:  # Reasonable float range
            return 'float_data'
    except:
        pass
    
    # Check for animation data
    if data[:2] in [b'\x00\x0c', b'\x02\x18', b'\x03\x24']:
        return 'animation'
    
    # Check for lookup table
    if all(x < 0x20 for x in data[:16]):
        return 'lookup_table'
    
    # Check for transform data
    if len(data) >= 16 and all(abs(struct.unpack('f', data[i:i+4])[0]) < 100 for i in range(0, 16, 4)):
        return 'transform'
    
    return 'unknown'

def interpret_matrix(matrix):
    """Interpret what a transform matrix does"""
    if len(matrix) != 4:
        return "Invalid matrix"
        
    interpretation = []
    
    # Check for translation
    if abs(matrix[2]) > 100:
        interpretation.append(f"Translation: {matrix[2]:.2f} units")
        
    # Check for scaling
    if 0 < abs(matrix[0]) < 1:
        interpretation.append(f"Scale: {matrix[0]:.3f}x")
    elif abs(matrix[0]) > 1:
        interpretation.append(f"Scale: {matrix[0]:.2f}x")
        
    # Check for rotation (look for small values that might be sin/cos)
    if -1 < matrix[1] < 1 and matrix[1] != 0:
        interpretation.append(f"Rotation: {matrix[1]:.3f} rad")
        
    return ", ".join(interpretation) if interpretation else "Identity/Unknown"

def analyze_animation_sequence(sequences, timings):
    """Analyze an animation sequence and its timing"""
    analysis = []
    
    for i, seq in enumerate(sequences):
        seq_analysis = {
            'frame': i,
            'action': [],
            'duration': None
        }
        
        # Analyze index patterns
        if seq['index'] == 0:
            seq_analysis['action'].append("Initial state")
        elif seq['index'] < 0x10:
            seq_analysis['action'].append(f"Animation state {seq['index']}")
        elif seq['index'] < 0x20:
            seq_analysis['action'].append(f"Transition {seq['index'] - 0x10}")
            
        # Analyze flags
        if seq['flags'] & 0x80:
            seq_analysis['action'].append("Loop")
        if seq['flags'] & 0x40:
            seq_analysis['action'].append("Reverse")
        if seq['flags'] & 0x20:
            seq_analysis['action'].append("Ping-pong")
            
        # Match timing if available
        if timings and i < len(timings):
            timing = timings[i]
            seq_analysis['duration'] = timing['duration']
            if timing['flags'] & 0x01:
                seq_analysis['action'].append("Wait for completion")
            if timing['flags'] & 0x02:
                seq_analysis['action'].append("Synchronize")
                
        analysis.append(seq_analysis)
        
    return analysis

def analyze_block_content(data: bytes, block_type: str) -> dict:
    """Analyze the content of a block based on its type"""
    content = {}
    
    if block_type == 'float_data':
        floats = []
        matrices = []
        # Look for transform matrices (4x4 float patterns)
        for i in range(0, min(len(data), 64), 16):
            if i + 16 <= len(data):
                matrix = []
                valid_matrix = True
                for j in range(0, 16, 4):
                    try:
                        val = struct.unpack('f', data[i+j:i+j+4])[0]
                        if abs(val) > 1e10:  # Unreasonable value
                            valid_matrix = False
                            break
                        matrix.append(val)
                    except:
                        valid_matrix = False
                        break
                if valid_matrix:
                    matrices.append(matrix)
                    content.setdefault('matrix_interpretations', []).append(
                        interpret_matrix(matrix)
                    )
        
        # Look for individual float values
        for i in range(0, min(len(data), 64), 4):
            try:
                val = struct.unpack('f', data[i:i+4])[0]
                if abs(val) < 1e10:  # Reasonable float range
                    floats.append(val)
            except:
                break
        
        content['float_values'] = floats
        if matrices:
            content['transform_matrices'] = matrices
    
    elif block_type == 'animation':
        sequences = []
        for i in range(0, min(len(data), 128), 8):
            if i + 8 <= len(data):
                seq = {
                    'index': data[i],
                    'offset': data[i+1],
                    'length': data[i+2],
                    'flags': data[i+3],
                    'timing': data[i+4],
                    'params': data[i+5:i+8].hex()
                }
                sequences.append(seq)
        content['sequences'] = sequences
        
        # Look for timing patterns
        timings = []
        for i in range(0, min(len(data), 64), 4):
            if i + 4 <= len(data):
                timing = {
                    'duration': data[i],
                    'flags': data[i+1],
                    'start_frame': data[i+2],
                    'end_frame': data[i+3]
                }
                timings.append(timing)
        if timings:
            content['timing_data'] = timings
            
        # Analyze sequences if we have both sequences and timing
        if sequences and timings:
            content['animation_analysis'] = analyze_animation_sequence(sequences, timings)
    
    elif block_type == 'lookup_table':
        entries = []
        for i in range(0, min(len(data), 96), 3):
            if i + 3 <= len(data):
                entry = {
                    'index': data[i],
                    'offset': data[i+1],
                    'length': data[i+2]
                }
                entries.append(entry)
        content['entries'] = entries
        
        # Look for sequence patterns
        sequences = []
        pos = 0
        while pos < len(data) - 2:
            if data[pos] < 0x20 and data[pos+1] < 0xFF and data[pos+2] in [0x06, 0x08]:
                sequences.append({
                    'index': data[pos],
                    'offset': data[pos+1],
                    'length': data[pos+2]
                })
                pos += 3
            else:
                pos += 1
        if sequences:
            content['sequence_patterns'] = sequences
    
    elif block_type == 'transform':
        matrices = []
        for i in range(0, min(len(data), 64), 16):
            if i + 16 <= len(data):
                matrix = [struct.unpack('f', data[i+j:i+j+4])[0] for j in range(0, 16, 4)]
                matrices.append(matrix)
                content.setdefault('matrix_interpretations', []).append(
                    interpret_matrix(matrix)
                )
        content['matrices'] = matrices
        
        # Look for scale/rotation patterns
        transforms = []
        for i in range(0, min(len(data), 32), 8):
            if i + 8 <= len(data):
                try:
                    transform = {
                        'scale_x': struct.unpack('f', data[i:i+4])[0],
                        'scale_y': struct.unpack('f', data[i+4:i+8])[0]
                    }
                    if -100 < transform['scale_x'] < 100 and -100 < transform['scale_y'] < 100:
                        transforms.append(transform)
                except:
                    pass
        if transforms:
            content['scale_transforms'] = transforms
    
    # Check for graphics data patterns
    if len(data) > 64:
        # Look for possible sprite/texture data
        sprite_sections = []
        pos = 0
        while pos < len(data) - 16:
            # Check for common sprite header patterns
            if (data[pos] == 0x00 and data[pos+1] in [0x80, 0xC0] and 
                data[pos+2] < 0x20 and data[pos+3] == 0x00):
                section_start = pos
                # Look for section end
                pos += 4
                while pos < len(data) - 4:
                    if data[pos:pos+4] == b'\x00\x00\x00\x00':
                        sprite_sections.append({
                            'offset': section_start,
                            'size': pos - section_start,
                            'header': data[section_start:section_start+8].hex()
                        })
                        break
                    pos += 1
            pos += 1
        if sprite_sections:
            content['sprite_sections'] = sprite_sections
    
    return content

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

def save_extracted_data(block, output_dir):
    """Save extracted data from a block to files"""
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    block_id = f"{block['start']:04x}"
    
    # Save transform matrices
    if 'content' in block and 'transform_matrices' in block['content']:
        matrices_file = os.path.join(output_dir, f"matrices_{block_id}.txt")
        with open(matrices_file, 'w') as f:
            f.write(f"Transform matrices from block at 0x{block['start']:x}\n")
            f.write("=" * 50 + "\n\n")
            for i, matrix in enumerate(block['content']['transform_matrices']):
                f.write(f"Matrix {i}:\n")
                f.write(f"  Values: {matrix}\n")
                if 'matrix_interpretations' in block['content']:
                    f.write(f"  Interpretation: {block['content']['matrix_interpretations'][i]}\n")
                f.write("\n")
    
    # Save animation sequences
    if 'content' in block and 'sequences' in block['content']:
        sequences_file = os.path.join(output_dir, f"animation_{block_id}.txt")
        with open(sequences_file, 'w') as f:
            f.write(f"Animation sequences from block at 0x{block['start']:x}\n")
            f.write("=" * 50 + "\n\n")
            for i, seq in enumerate(block['content']['sequences']):
                f.write(f"Sequence {i}:\n")
                for k, v in seq.items():
                    f.write(f"  {k}: {v}\n")
                if 'animation_analysis' in block['content']:
                    f.write(f"  Analysis: {block['content']['animation_analysis'][i]}\n")
                f.write("\n")
    
    # Save raw data for potential texture/sprite data
    if 'content' in block and 'sprite_sections' in block['content']:
        for i, section in enumerate(block['content']['sprite_sections']):
            data_file = os.path.join(output_dir, f"sprite_{block_id}_{i:02d}.bin")
            with open(data_file, 'wb') as f:
                start = section['offset']
                size = section['size']
                f.write(block['raw_data'][start:start+size])

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Deep analysis of MDL files')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    parser.add_argument('--outputtext', action='store_true', help='Save analysis to text files')
    parser.add_argument('--verbose', action='store_true', help='Show detailed analysis')
    parser.add_argument('--extract', action='store_true', help='Extract animation and transform data')
    parser.add_argument('--output-dir', default='extracted_data', help='Directory for extracted data')
    args = parser.parse_args()
    
    for file in args.files:
        print(f"\nAnalyzing: {file}")
        with open(file, 'rb') as f:
            data = f.read()
        
        analysis = analyze_mdl_structure(data, verbose=args.verbose)
        
        if args.extract:
            output_dir = os.path.join(args.output_dir, Path(file).stem)
            print(f"\nExtracting data to: {output_dir}")
            for block in analysis['blocks']:
                save_extracted_data(block, output_dir)
        
        # Focus on important blocks
        print("\nKey Block Analysis:")
        for block in analysis['blocks']:
            if block['size'] > 64:  # Skip tiny blocks
                if 'content' in block:
                    content = block['content']
                    if 'sequences' in content or 'sprite_sections' in content or 'transform_matrices' in content:
                        print(f"\nBlock at 0x{block['start']:x}:")
                        print(f"  Size: {block['size']:,} bytes")
                        print(f"  Type: {block['type']}")
                        print(f"  Marker: {block['marker']}")
                        print("  Content:")
                        for k, v in content.items():
                            print(f"    {k}:")
                            if isinstance(v, list):
                                for i, item in enumerate(v):
                                    print(f"      {i}: {item}")
                            else:
                                print(f"      {v}")
        
        if args.outputtext:
            save_analysis_text(analysis, file)
            print(f"\nFull analysis saved to {Path(file).stem}_analysis.txt")

if __name__ == '__main__':
    main() 