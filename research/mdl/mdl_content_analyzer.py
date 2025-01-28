import struct
from pathlib import Path
from dataclasses import dataclass
import sys

@dataclass
class BlockContent:
    type: str
    offset: int
    size: int
    marker: bytes
    header: bytes
    data_type: str
    values: list

class MDLContentAnalyzer:
    def __init__(self):
        self.data_patterns = {
            'float3': (12, lambda d: struct.unpack('<3f', d[:12])),
            'float4': (16, lambda d: struct.unpack('<4f', d[:16])),
            'vertex': (12, lambda d: struct.unpack('<3f', d[:12])),
            'normal': (12, lambda d: struct.unpack('<3f', d[:12])),
            'uv': (8, lambda d: struct.unpack('<2f', d[:8])),
            'index': (2, lambda d: struct.unpack('<H', d[:2])),
        }
    
    def analyze_block_content(self, data: bytes, marker: bytes) -> BlockContent:
        """Analyze the content type of a block"""
        content_type = 'unknown'
        values = []
        
        try:
            # Check for known patterns
            if len(data) >= 4:
                if all(x == 0 for x in data[:4]):
                    content_type = 'zero_block'
                elif len(data) >= 12:
                    # Try to read as float data
                    try:
                        first_float = struct.unpack('<f', data[:4])[0]
                        if abs(first_float) < 100.0:  # Reasonable float value
                            content_type = 'float_data'
                            # Read complete float values only
                            num_floats = len(data) // 4
                            values = [struct.unpack('<f', data[i:i+4])[0] 
                                    for i in range(0, num_floats * 4, 4)]
                    except struct.error:
                        pass
                        
                if marker == bytes.fromhex('0000c000'):
                    content_type = 'geometry'
                    # Read complete vertex data only
                    if len(data) >= 12:
                        num_vertices = len(data) // 12
                        try:
                            values = [struct.unpack('<3f', data[i:i+12]) 
                                    for i in range(0, num_vertices * 12, 12)]
                        except struct.error:
                            pass
        except Exception as e:
            print(f"Warning: Error analyzing block: {e}")
            
        return BlockContent(
            type=content_type,
            offset=0,
            size=len(data),
            marker=marker,
            header=data[:min(16, len(data))],
            data_type='float' if content_type == 'float_data' else 'bytes',
            values=values
        )
    
    def save_analysis_text(self, filename: str, blocks: list, header_info: dict):
        """Save analysis results to a text file"""
        output_file = Path(filename).stem + "_content.txt"
        with open(output_file, 'w') as f:
            f.write(f"MDL Content Analysis: {filename}\n")
            f.write("=" * 50 + "\n\n")
            
            # Write header info
            f.write("Header Information:\n")
            f.write(f"  Magic: {header_info['magic']}\n")
            f.write(f"  Decompressed size: {header_info['decomp_size']:,} bytes\n")
            f.write(f"  Flag1: 0x{header_info['flag1']:08x}\n")
            f.write(f"  Flag2: 0x{header_info['flag2']:08x}\n\n")
            
            # Write block analysis
            f.write(f"Block Analysis ({len(blocks)} blocks):\n")
            f.write("-" * 30 + "\n\n")
            
            # Group blocks by type
            block_types = {}
            for block in blocks:
                if block.type not in block_types:
                    block_types[block.type] = []
                block_types[block.type].append(block)
            
            # Write summary
            f.write("Type Summary:\n")
            for type_name, type_blocks in block_types.items():
                f.write(f"  {type_name}: {len(type_blocks)} blocks\n")
            f.write("\n")
            
            # Write detailed block info
            f.write("Block Details:\n")
            for i, block in enumerate(blocks):
                if block.values:  # Only show interesting blocks
                    f.write(f"\nBlock {i} ({block.type}):\n")
                    f.write(f"  Size: {block.size:,} bytes\n")
                    f.write(f"  Marker: {block.marker.hex()}\n")
                    f.write(f"  Header: {block.header.hex()}\n")
                    if len(block.values) <= 4:
                        f.write(f"  Values: {block.values}\n")
                    else:
                        f.write(f"  Values: {block.values[:4]}...\n")
                        f.write(f"  Total values: {len(block.values)}\n")

    def analyze_file(self, filename: str, output_text: bool = False):
        """Analyze MDL file contents"""
        with open(filename, 'rb') as f:
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            header_info = {
                'magic': magic,
                'decomp_size': decomp_size,
                'flag1': flag1,
                'flag2': flag2
            }
            
            print(f"\nAnalyzing {filename}")
            print(f"Magic: {magic}")
            print(f"Decompressed size: {decomp_size:,}")
            print(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Track interesting blocks
            blocks = []
            pos = 16
            
            while pos < Path(filename).stat().st_size:
                f.seek(pos)
                marker = f.read(4)
                if not marker:
                    break
                
                # Look for block markers
                if (all(b == marker[0] for b in marker) or
                    marker[0] in (0x00, 0xFF) and marker[1] == marker[0]):
                    
                    # Read block data
                    data = bytearray()
                    while True:
                        b = f.read(1)
                        if not b:
                            break
                        if len(data) >= 4:
                            last_four = bytes(data[-4:])
                            if (all(x == last_four[0] for x in last_four) or
                                last_four[0] in (0x00, 0xFF) and last_four[1] == last_four[0]):
                                data = data[:-4]
                                break
                        data.extend(b)
                    
                    if data:
                        content = self.analyze_block_content(bytes(data), marker)
                        if content.type != 'unknown':
                            blocks.append(content)
                            print(f"\rAnalyzing: {pos * 100 // Path(filename).stat().st_size}% "
                                  f"({len(blocks)} blocks found)", end='')
                    
                    pos = f.tell()
                else:
                    pos += 1
            
            if output_text:
                self.save_analysis_text(filename, blocks, header_info)
                print(f"\nAnalysis saved to {Path(filename).stem}_content.txt")
            else:
                print("\n\nBlock Content Analysis:")
                for i, block in enumerate(blocks):
                    if block.values:  # Only show interesting blocks
                        print(f"\nBlock {i} ({block.type}):")
                        print(f"  Size: {block.size:,} bytes")
                        print(f"  Marker: {block.marker.hex()}")
                        print(f"  Header: {block.header.hex()}")
                        if len(block.values) <= 4:
                            print(f"  Values: {block.values}")
                        else:
                            print(f"  Values: {block.values[:4]}...")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze MDL file contents')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    parser.add_argument('--outtext', action='store_true', help='Save analysis to text files')
    args = parser.parse_args()
    
    analyzer = MDLContentAnalyzer()
    for file in args.files:
        analyzer.analyze_file(file, args.outtext)

if __name__ == '__main__':
    main() 