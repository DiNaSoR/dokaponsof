"""
LZ77 MDL File Analyzer
======================

A tool for analyzing MDL file structure and compression patterns used in Dokapon Sword of Fury.
This analyzer helps understand the LZ77 compression implementation and file format.

Usage:
    python lz77_analyzer.py <mdl_file1> [mdl_file2 ...]

Arguments:
    mdl_file(s) - One or more MDL files to analyze

Output:
    - Prints detailed analysis of file structure and compression patterns
    - Generates visualization plots saved as <filename>_analysis.png
    - Shows statistics about compression ratios and patterns

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: GNU General Public License v3.0 (GPL-3.0)
"""

import struct
from pathlib import Path
import logging
from collections import Counter
import matplotlib.pyplot as plt
import numpy as np

def analyze_mdl(filename: str):
    """Analyze MDL file structure and compression patterns"""
    with open(filename, 'rb') as f:
        data = f.read()
        
    print(f"\nAnalyzing: {filename}")
    print(f"File size: {len(data):,} bytes")
    
    # 1. Analyze header
    print("\n=== Header Analysis ===")
    header = data[:16]
    magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
    print(f"Magic: {magic}")
    print(f"Decompressed size: {decomp_size:,}")
    print(f"Flag1: 0x{flag1:08x}")
    print(f"Flag2: 0x{flag2:08x}")
    
    # 2. Analyze compression patterns
    print("\n=== Compression Pattern Analysis ===")
    pos = 16
    flag_bytes = []
    offsets = []
    lengths = []
    output_size = 0
    operations = []  # Track each operation (literal or copy)
    
    while pos < len(data):
        if pos + 1 > len(data):
            break
            
        flag = data[pos]
        pos += 1
        flag_bytes.append(flag)
        
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
                operations.append(('copy', length))
                output_size += length
                pos += 2
            else:
                # Literal byte
                if pos < len(data):
                    operations.append(('literal', 1))
                    output_size += 1
                    pos += 1
    
    # 3. Generate statistics
    print("\n=== Statistics ===")
    print(f"Total flags processed: {len(flag_bytes):,}")
    print(f"Total copy operations: {len(offsets):,}")
    print(f"Total output size: {output_size:,}")
    print(f"Compression ratio: {len(data)/output_size*100:.1f}%")
    
    if offsets:
        print(f"\nOffset statistics:")
        print(f"Min offset: {min(offsets):,}")
        print(f"Max offset: {max(offsets):,}")
        print(f"Avg offset: {sum(offsets)/len(offsets):.1f}")
        
        print(f"\nLength statistics:")
        print(f"Min length: {min(lengths):,}")
        print(f"Max length: {max(lengths):,}")
        print(f"Avg length: {sum(lengths)/len(lengths):.1f}")
        
        # Calculate most common patterns
        print("\nMost common copy lengths:")
        length_counts = Counter(lengths)
        for length, count in length_counts.most_common(5):
            print(f"Length {length}: {count:,} times")
            
        print("\nMost common offsets:")
        offset_ranges = [(0, 16), (16, 256), (256, 1024), (1024, 4096)]
        for start, end in offset_ranges:
            count = sum(1 for x in offsets if start <= x < end)
            print(f"Offset {start}-{end}: {count:,} times")
    
    # 4. Plot distributions
    if offsets:
        plt.figure(figsize=(15, 10))
        
        # Offset distribution
        plt.subplot(2, 2, 1)
        plt.hist(offsets, bins=50)
        plt.title('Offset Distribution')
        plt.xlabel('Offset Value')
        plt.ylabel('Frequency')
        
        # Length distribution
        plt.subplot(2, 2, 2)
        plt.hist(lengths, bins=max(lengths)-min(lengths))
        plt.title('Length Distribution')
        plt.xlabel('Length Value')
        plt.ylabel('Frequency')
        
        # Flag byte patterns
        plt.subplot(2, 2, 3)
        plt.hist(flag_bytes, bins=256)
        plt.title('Flag Byte Distribution')
        plt.xlabel('Flag Value')
        plt.ylabel('Frequency')
        
        # Decompression progress
        plt.subplot(2, 2, 4)
        progress = []
        current_size = 0
        for op, size in operations:
            current_size += size
            progress.append(current_size)
        
        plt.plot(progress)
        plt.title('Decompression Progress')
        plt.xlabel('Operation #')
        plt.ylabel('Output Size')
        
        plt.tight_layout()
        plt.savefig(f"{Path(filename).stem}_analysis.png")
        print(f"\nAnalysis plots saved to {Path(filename).stem}_analysis.png")
        
        # 5. Look for patterns near end of file
        print("\n=== End of File Analysis ===")
        last_pos = max(0, len(data) - 128)
        print(f"Last 128 bytes pattern counts:")
        pattern_counts = Counter(data[last_pos:])
        for byte, count in pattern_counts.most_common(10):
            print(f"0x{byte:02x}: {count} times")
            
        # 6. Analyze potential file boundaries
        print("\n=== Boundary Analysis ===")
        # Look for potential end markers or patterns
        boundary_sequences = [b'\xFF\xFF', b'\x00\x00', b'\xAA\xAA', b'\x55\x55']
        for seq in boundary_sequences:
            positions = []
            pos = 0
            while True:
                pos = data.find(seq, pos)
                if pos == -1:
                    break
                positions.append(pos)
                pos += 1
            if positions:
                print(f"Sequence {seq.hex()}: found at positions {', '.join(str(p) for p in positions[-5:])}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MDL File Analyzer')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    for file in args.files:
        analyze_mdl(file)

if __name__ == '__main__':
    main() 