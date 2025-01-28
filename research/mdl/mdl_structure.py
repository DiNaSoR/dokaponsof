import struct
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

@dataclass
class MDLBlock:
    offset: int
    size: int
    alignment: int
    marker: bytes
    compressed_data: bytes

@dataclass
class MDLFile:
    magic: bytes
    decomp_size: int
    flag1: int
    flag2: int
    blocks: List[MDLBlock]

def parse_mdl(filename: str, debug: bool = True) -> MDLFile:
    """Parse MDL file structure"""
    with open(filename, 'rb') as f:
        # Get file size
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)
        
        # Read header
        header = f.read(16)
        magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
        
        if debug:
            print(f"File size: {file_size:,} bytes")
            print(f"Magic: {magic}")
            print(f"Decompressed size: {decomp_size:,}")
            print(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
        
        # Find blocks
        blocks = []
        pos = 16
        
        while pos < file_size:
            # Read potential block header
            f.seek(pos)
            block_start = pos
            
            # Try to find next block marker
            marker = None
            data_size = 0
            
            # Look for common block markers
            chunk = f.read(16)  # Read potential marker
            if not chunk:
                break
                
            # Check for marker patterns
            if len(set(chunk[:4])) == 1:  # Repeated bytes
                marker = chunk[:4]
                data_size = 16
            elif chunk[0] in (0x00, 0xFF) and chunk[1] in (0x00, 0xFF):
                marker = chunk[:4]
                data_size = 16
            
            if marker:
                if debug:
                    print(f"Found block at 0x{pos:x}, marker: {marker.hex()}")
                
                # Read block data until next marker or EOF
                f.seek(pos + data_size)
                block_data = bytearray()
                
                while f.tell() < file_size:
                    byte = f.read(1)
                    if not byte:
                        break
                    
                    # Check if we've hit another marker
                    if len(block_data) >= 4:
                        last_four = bytes(block_data[-4:])
                        if (len(set(last_four)) == 1 and last_four[0] in (0x00, 0xFF, 0xAA)) or \
                           (last_four[0] in (0x00, 0xFF) and last_four[1] in (0x00, 0xFF)):
                            block_data = block_data[:-4]
                            f.seek(-4, 1)
                            break
                    
                    block_data.extend(byte)
                
                if block_data:
                    blocks.append(MDLBlock(
                        offset=block_start,
                        size=len(block_data),
                        alignment=block_start % 2048,
                        marker=marker,
                        compressed_data=bytes(block_data)
                    ))
                
                pos = f.tell()
            else:
                pos += 1
        
        return MDLFile(magic, decomp_size, flag1, flag2, blocks)

def analyze_block_patterns(mdl: MDLFile):
    """Analyze block patterns and relationships"""
    print(f"\nBlock Pattern Analysis:")
    print(f"Total blocks: {len(mdl.blocks)}")
    
    if not mdl.blocks:
        print("No blocks found!")
        return
    
    # Analyze block sizes
    sizes = [b.size for b in mdl.blocks]
    print(f"\nBlock sizes:")
    print(f"Min: {min(sizes):,} bytes")
    print(f"Max: {max(sizes):,} bytes")
    print(f"Avg: {sum(sizes)/len(sizes):,.1f} bytes")
    
    # Analyze alignments
    alignments = [b.alignment for b in mdl.blocks]
    print(f"\nBlock alignments:")
    print(f"Most common: {max(set(alignments), key=alignments.count)}")
    
    # Look for patterns in markers
    markers = [b.marker for b in mdl.blocks]
    marker_counts = {}
    for m in markers:
        marker_counts[m] = marker_counts.get(m, 0) + 1
    
    print(f"\nCommon markers:")
    for marker, count in sorted(marker_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{marker.hex()}: {count} times")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze MDL file structure')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    args = parser.parse_args()
    
    for file in args.files:
        print(f"\nAnalyzing: {file}")
        try:
            mdl = parse_mdl(file, args.debug)
            analyze_block_patterns(mdl)
        except Exception as e:
            print(f"Error analyzing {file}: {e}")

if __name__ == '__main__':
    main() 