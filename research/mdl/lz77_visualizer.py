import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import struct

def visualize_mdl(filename: str):
    """Create visualization of MDL file compression patterns"""
    with open(filename, 'rb') as f:
        data = f.read()
    
    # Parse header
    magic = data[0:4]
    decomp_size = struct.unpack('<I', data[4:8])[0]
    
    # Track compression operations
    offsets = []
    lengths = []
    positions = []
    literals = []
    lit_positions = []
    
    pos = 16  # Skip header
    while pos < len(data):
        if pos + 1 >= len(data):
            break
            
        flag = data[pos]
        pos += 1
        
        for bit in range(8):
            if pos >= len(data):
                break
                
            if flag & (1 << bit):
                # Copy operation
                if pos + 2 > len(data):
                    break
                info = struct.unpack('>H', data[pos:pos+2])[0]
                length = ((info >> 12) & 0xF) + 3
                offset = info & 0xFFF
                
                offsets.append(offset)
                lengths.append(length)
                positions.append(pos)
                pos += 2
            else:
                # Literal byte
                if pos >= len(data):
                    break
                literals.append(data[pos])
                lit_positions.append(pos)
                pos += 1
    
    # Create visualizations
    plt.figure(figsize=(15, 10))
    
    # 1. Offset vs Position
    plt.subplot(2, 2, 1)
    plt.scatter(positions, offsets, alpha=0.5, s=1)
    plt.title('Offset vs Position')
    plt.xlabel('File Position')
    plt.ylabel('Offset Value')
    
    # 2. Length vs Position
    plt.subplot(2, 2, 2)
    plt.scatter(positions, lengths, alpha=0.5, s=1)
    plt.title('Length vs Position')
    plt.xlabel('File Position')
    plt.ylabel('Length Value')
    
    # 3. Offset vs Length
    plt.subplot(2, 2, 3)
    plt.hist2d(offsets, lengths, bins=50)
    plt.title('Offset vs Length Distribution')
    plt.xlabel('Offset')
    plt.ylabel('Length')
    
    # 4. Literal byte distribution
    plt.subplot(2, 2, 4)
    plt.hist(literals, bins=256, range=(0,256))
    plt.title('Literal Byte Distribution')
    plt.xlabel('Byte Value')
    plt.ylabel('Frequency')
    
    plt.tight_layout()
    plt.savefig(f"{Path(filename).stem}_patterns.png")
    
    # Print statistics
    print(f"\nFile: {filename}")
    print(f"Total size: {len(data):,} bytes")
    print(f"Expected decompressed size: {decomp_size:,} bytes")
    print(f"\nCompression Operations:")
    print(f"Copy operations: {len(offsets):,}")
    print(f"Literal bytes: {len(literals):,}")
    print(f"\nOffset Statistics:")
    print(f"Min offset: {min(offsets):,}")
    print(f"Max offset: {max(offsets):,}")
    print(f"Most common offsets: {np.bincount(offsets).argmax():,}")
    print(f"\nLength Statistics:")
    print(f"Min length: {min(lengths):,}")
    print(f"Max length: {max(lengths):,}")
    print(f"Most common length: {np.bincount(lengths).argmax():,}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Visualize MDL compression patterns')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    for file in args.files:
        visualize_mdl(file)

if __name__ == '__main__':
    main() 