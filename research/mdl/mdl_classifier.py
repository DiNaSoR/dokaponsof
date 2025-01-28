import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict
import logging
import sys

@dataclass
class BlockType:
    name: str
    description: str
    markers: List[bytes]
    size_range: tuple

class MDLClassifier:
    def __init__(self):
        self.block_types = {
            'header': BlockType(
                'Header Block',
                'File structure information',
                [bytes.fromhex('aaaaaaaa'), bytes.fromhex('55555555')],
                (1, 16)
            ),
            'metadata': BlockType(
                'Metadata Block',
                'Model properties/attributes',
                [bytes.fromhex('0000803f'), bytes.fromhex('00000000')],
                (4, 64)
            ),
            'geometry': BlockType(
                'Geometry Block',
                'Vertex/face data',
                [bytes.fromhex('0000c000'), bytes.fromhex('00004000')],
                (128, 13000)
            ),
            'animation': BlockType(
                'Animation Block',
                'Animation data',
                [bytes.fromhex('000080b9'), bytes.fromhex('0000c100')],
                (64, 1024)
            ),
            'texture': BlockType(
                'Texture Block',
                'Texture coordinates/data',
                [bytes.fromhex('00002000'), bytes.fromhex('00004000')],
                (256, 4096)
            )
        }
    
    def classify_block(self, marker: bytes, size: int) -> str:
        """Classify a block based on its marker and size"""
        for type_id, block_type in self.block_types.items():
            if marker in block_type.markers:
                return type_id
            if size >= block_type.size_range[0] and size <= block_type.size_range[1]:
                return type_id
        return 'unknown'
    
    def analyze_file(self, filename: str):
        """Analyze MDL file block structure"""
        file_size = Path(filename).stat().st_size
        
        with open(filename, 'rb') as f:
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            print(f"\nAnalyzing {filename}")
            print(f"File size: {file_size:,} bytes")
            print(f"Magic: {magic}")
            print(f"Decompressed size: {decomp_size:,}")
            print(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Track block types
            block_counts = {}
            block_sizes = {}
            
            # Read file in chunks
            chunk_size = 4096
            pos = 16
            buffer = bytearray()
            
            while pos < file_size:
                # Show progress
                progress = pos * 100 // file_size
                print(f"\rAnalyzing: {progress}% complete...", end='')
                sys.stdout.flush()
                
                # Fill buffer
                if len(buffer) < 4096:
                    chunk = f.read(min(chunk_size, file_size - f.tell()))
                    if not chunk:
                        break
                    buffer.extend(chunk)
                
                # Look for block markers
                if len(buffer) >= 4:
                    marker = buffer[:4]
                    is_marker = False
                    
                    # Check marker patterns
                    if all(b == marker[0] for b in marker):
                        is_marker = True
                    elif marker[0] in (0x00, 0xFF) and marker[1] == marker[0]:
                        is_marker = True
                    
                    if is_marker:
                        # Found a block, read until next marker
                        buffer = buffer[4:]
                        block_data = bytearray()
                        pos += 4
                        
                        while len(buffer) > 0:
                            if len(buffer) >= 4:
                                next_four = buffer[:4]
                                if (all(b == next_four[0] for b in next_four) or 
                                    (next_four[0] in (0x00, 0xFF) and next_four[1] == next_four[0])):
                                    break
                            
                            block_data.append(buffer[0])
                            buffer = buffer[1:]
                            pos += 1
                        
                        if block_data:
                            block_type = self.classify_block(marker, len(block_data))
                            block_counts[block_type] = block_counts.get(block_type, 0) + 1
                            
                            if block_type not in block_sizes:
                                block_sizes[block_type] = []
                            block_sizes[block_type].append(len(block_data))
                    else:
                        buffer = buffer[1:]
                        pos += 1
                else:
                    buffer = buffer[1:]
                    pos += 1
            
            print("\n\nBlock Type Analysis:")
            for type_id, count in sorted(block_counts.items()):
                sizes = block_sizes[type_id]
                print(f"\n{self.block_types.get(type_id, BlockType(type_id,'Unknown',[],())).name}:")
                print(f"  Count: {count}")
                print(f"  Size range: {min(sizes):,} - {max(sizes):,} bytes")
                print(f"  Average size: {sum(sizes)/len(sizes):,.1f} bytes")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Classify MDL file blocks')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    classifier = MDLClassifier()
    for file in args.files:
        classifier.analyze_file(file)

if __name__ == '__main__':
    main() 