import struct
import os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def extract_animation_sequence(data: bytes, offset: int, size: int) -> dict:
    """Extract and analyze an animation sequence"""
    sequence = {
        'offset': offset,
        'size': size,
        'transforms': [],
        'keyframes': []
    }
    
    # Extract transform matrices
    for i in range(0, min(size, 64), 16):
        if i + 16 <= size:
            try:
                matrix = []
                for j in range(0, 16, 4):
                    val = struct.unpack('f', data[offset+i+j:offset+i+j+4])[0]
                    matrix.append(val)
                if len(matrix) == 4:
                    transform = {
                        'offset': i,
                        'matrix': matrix,
                        'type': analyze_transform(matrix)
                    }
                    sequence['transforms'].append(transform)
            except:
                pass
    
    # Look for keyframe data
    pos = offset
    while pos < offset + size - 8:
        # Look for keyframe markers
        if data[pos] in [0x00, 0x01, 0x02] and data[pos+1] < 0x20:
            try:
                keyframe = {
                    'offset': pos - offset,
                    'index': data[pos],
                    'flags': data[pos+1],
                    'duration': struct.unpack('f', data[pos+4:pos+8])[0]
                }
                sequence['keyframes'].append(keyframe)
            except:
                pass
        pos += 1
    
    return sequence

def analyze_transform(matrix):
    """Analyze what a transform matrix represents"""
    if len(matrix) != 4:
        return "Invalid"
        
    result = []
    
    # Check for translation
    if abs(matrix[2]) > 100:
        result.append(f"Translation({matrix[2]:.1f})")
        
    # Check for scaling
    if 0 < abs(matrix[0]) < 1:
        result.append(f"Scale({matrix[0]:.3f})")
    elif abs(matrix[0]) > 1:
        result.append(f"Scale({matrix[0]:.1f})")
        
    # Check for rotation
    if -1 < matrix[1] < 1 and matrix[1] != 0:
        angle = np.arcsin(matrix[1])
        result.append(f"Rotation({np.degrees(angle):.1f}°)")
        
    return " + ".join(result) if result else "Identity"

def visualize_sequence(sequence, output_dir, name):
    """Create visualization of the animation sequence"""
    if not sequence['transforms'] and not sequence['keyframes']:
        return
        
    # Create plots directory
    plots_dir = os.path.join(output_dir, 'plots')
    os.makedirs(plots_dir, exist_ok=True)
    
    # Plot transform values
    if sequence['transforms']:
        plt.figure(figsize=(12, 6))
        
        # Plot translation values
        translations = [t['matrix'][2] for t in sequence['transforms']]
        plt.plot(translations, label='Translation', marker='o')
        
        # Plot scale values
        scales = [t['matrix'][0] for t in sequence['transforms']]
        plt.plot(scales, label='Scale', marker='s')
        
        plt.title(f'Transform Values for {name}')
        plt.xlabel('Transform Index')
        plt.ylabel('Value')
        plt.legend()
        plt.grid(True)
        
        plt.savefig(os.path.join(plots_dir, f'{name}_transforms.png'))
        plt.close()
    
    # Plot keyframe timeline
    if sequence['keyframes']:
        plt.figure(figsize=(12, 4))
        
        durations = [k['duration'] for k in sequence['keyframes']]
        indices = list(range(len(durations)))
        
        plt.bar(indices, durations)
        plt.title(f'Keyframe Timeline for {name}')
        plt.xlabel('Keyframe Index')
        plt.ylabel('Duration')
        plt.grid(True)
        
        plt.savefig(os.path.join(plots_dir, f'{name}_keyframes.png'))
        plt.close()

def save_sequence_info(sequence, output_dir, name):
    """Save detailed sequence information to a text file"""
    info_dir = os.path.join(output_dir, 'sequences')
    os.makedirs(info_dir, exist_ok=True)
    
    with open(os.path.join(info_dir, f'{name}.txt'), 'w') as f:
        f.write(f"Animation Sequence Analysis: {name}\n")
        f.write("=" * 50 + "\n\n")
        
        f.write(f"Offset: 0x{sequence['offset']:x}\n")
        f.write(f"Size: {sequence['size']} bytes\n\n")
        
        if sequence['transforms']:
            f.write("Transforms:\n")
            f.write("-" * 20 + "\n")
            for i, transform in enumerate(sequence['transforms']):
                f.write(f"\nTransform {i}:\n")
                f.write(f"  Offset: 0x{transform['offset']:x}\n")
                f.write(f"  Matrix: {transform['matrix']}\n")
                f.write(f"  Type: {transform['type']}\n")
        
        if sequence['keyframes']:
            f.write("\nKeyframes:\n")
            f.write("-" * 20 + "\n")
            for i, keyframe in enumerate(sequence['keyframes']):
                f.write(f"\nKeyframe {i}:\n")
                f.write(f"  Offset: 0x{keyframe['offset']:x}\n")
                f.write(f"  Index: {keyframe['index']}\n")
                f.write(f"  Flags: 0x{keyframe['flags']:02x}\n")
                f.write(f"  Duration: {keyframe['duration']:.2f}\n")

def find_sequences(data: bytes) -> list:
    """Find animation sequences in the data"""
    sequences = []
    pos = 0
    
    while pos < len(data) - 16:
        # Look for transform matrix patterns
        if pos + 16 <= len(data):
            try:
                # Check if we have valid float values
                valid_matrix = True
                matrix = []
                for i in range(0, 16, 4):
                    val = struct.unpack('f', data[pos+i:pos+i+4])[0]
                    if abs(val) > 1e10:  # Unreasonable value
                        valid_matrix = False
                        break
                    matrix.append(val)
                
                if valid_matrix:
                    # Look for sequence end
                    end = pos + 16
                    while end < min(pos + 1024, len(data) - 4):  # Limit search to reasonable size
                        if data[end:end+4] == b'\x00\x00\x00\x00':
                            break
                        end += 1
                    
                    if end > pos + 16:
                        sequences.append({
                            'start': pos,
                            'end': end,
                            'size': end - pos
                        })
                        pos = end
                        continue
            except:
                pass
        pos += 1
    
    return sequences

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract and analyze animation sequences')
    parser.add_argument('file', help='File to analyze')
    parser.add_argument('--output-dir', default='extracted_sequences', help='Output directory')
    args = parser.parse_args()
    
    with open(args.file, 'rb') as f:
        data = f.read()
    
    # Create output directory
    output_dir = os.path.join(args.output_dir, Path(args.file).stem)
    os.makedirs(output_dir, exist_ok=True)
    
    # Find sequences
    sequences = find_sequences(data)
    print(f"\nFound {len(sequences)} potential sequences")
    
    # Extract and analyze each sequence
    for i, seq in enumerate(sequences):
        sequence = extract_animation_sequence(data, seq['start'], seq['size'])
        name = f'sequence_{i:03d}'
        
        # Save sequence information
        save_sequence_info(sequence, output_dir, name)
        
        # Create visualizations
        visualize_sequence(sequence, output_dir, name)
        
        print(f"\nSequence {i}:")
        print(f"  Offset: 0x{seq['start']:x}")
        print(f"  Size: {seq['size']} bytes")
        print(f"  Transforms: {len(sequence['transforms'])}")
        print(f"  Keyframes: {len(sequence['keyframes'])}")
    
    print(f"\nExtracted sequences to {output_dir}")

if __name__ == '__main__':
    main() 
