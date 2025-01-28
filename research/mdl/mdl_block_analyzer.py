import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional
import sys

@dataclass
class Block:
    type: str
    offset: int
    size: int
    marker: bytes
    data: bytes
    next_block: Optional['Block'] = None

class MDLAnalyzer:
    def __init__(self):
        self.block_patterns = {
            'animation': [
                (b'\x00\x80\xb9', 64, 128),  # Animation data
                (b'\x00\xc1\x00', 64, 128)   # Animation frames
            ],
            'geometry': [
                (b'\x00\xc0\x00', 128, 8000),  # Vertex data
                (b'\x00\x40\x00', 128, 8000)   # Face data
            ],
            'metadata': [
                (b'\x00\x80\x3f', 4, 64),    # Float values (1.0f)
                (b'\x00\x00\x00', 4, 64)     # Zero values
            ]
        }
    
    def analyze_blocks(self, filename: str):
        """Analyze block structure and relationships"""
        file_size = Path(filename).stat().st_size
        blocks = []
        
        with open(filename, 'rb') as f:
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            print(f"\nAnalyzing {filename}")
            print(f"File size: {file_size:,} bytes")
            print(f"Magic: {magic}")
            print(f"Decompressed size: {decomp_size:,}")
            print(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Read blocks
            pos = 16
            while pos < file_size:
                progress = pos * 100 // file_size
                print(f"\rAnalyzing blocks: {progress}%", end='')
                
                f.seek(pos)
                marker = f.read(4)
                if not marker:
                    break
                
                # Check for block start
                is_block = False
                if all(b == marker[0] for b in marker):
                    is_block = True
                elif marker[0] in (0x00, 0xFF) and marker[1] == marker[0]:
                    is_block = True
                
                if is_block:
                    # Read block data
                    data_start = f.tell()
                    block_data = bytearray()
                    
                    while f.tell() < file_size:
                        byte = f.read(1)
                        if not byte:
                            break
                            
                        # Check for next block marker
                        if len(block_data) >= 4:
                            last_four = bytes(block_data[-4:])
                            if (all(b == last_four[0] for b in last_four) or
                                (last_four[0] in (0x00, 0xFF) and last_four[1] == last_four[0])):
                                block_data = block_data[:-4]
                                f.seek(-4, 1)
                                break
                        
                        block_data.extend(byte)
                    
                    if block_data:
                        # Classify block
                        block_type = 'unknown'
                        for type_name, patterns in self.block_patterns.items():
                            for prefix, min_size, max_size in patterns:
                                if (len(block_data) >= min_size and 
                                    len(block_data) <= max_size and
                                    block_data.startswith(prefix)):
                                    block_type = type_name
                                    break
                        
                        blocks.append(Block(
                            type=block_type,
                            offset=pos,
                            size=len(block_data),
                            marker=marker,
                            data=bytes(block_data)
                        ))
                    
                    pos = f.tell()
                else:
                    pos += 1
            
            print("\n\nBlock Analysis:")
            
            # Analyze block relationships
            block_sequences = []
            current_sequence = []
            
            for i, block in enumerate(blocks):
                if i > 0:
                    prev_block = blocks[i-1]
                    spacing = block.offset - (prev_block.offset + prev_block.size)
                    if spacing <= 16:  # Blocks are related if close together
                        current_sequence.append(block)
                    else:
                        if current_sequence:
                            block_sequences.append(current_sequence)
                        current_sequence = [block]
                else:
                    current_sequence.append(block)
            
            if current_sequence:
                block_sequences.append(current_sequence)
            
            # Print sequences
            print(f"\nFound {len(block_sequences)} block sequences:")
            for i, sequence in enumerate(block_sequences):
                if len(sequence) >= 3:  # Show interesting sequences
                    print(f"\nSequence {i} ({len(sequence)} blocks):")
                    for block in sequence:
                        print(f"  {block.type:10} @ 0x{block.offset:06x} [{block.size:6,} bytes] "
                              f"Marker: {block.marker.hex()}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze MDL block structure')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    analyzer = MDLAnalyzer()
    for file in args.files:
        analyzer.analyze_blocks(file)

if __name__ == '__main__':
    main()