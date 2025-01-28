import struct
from pathlib import Path
from dataclasses import dataclass
from typing import List, BinaryIO
import logging
import sys

@dataclass
class MDLBlock:
    offset: int
    size: int
    data: bytes
    marker: bytes

class MDLExtractor:
    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("MDLExtractor")
        if debug:
            logging.basicConfig(level=logging.DEBUG)
            
    def is_block_marker(self, data: bytes) -> bool:
        """Check if bytes look like a block marker"""
        if len(data) < 4:
            return False
            
        # Check for repeated patterns
        if all(b == data[0] for b in data[:4]):
            return True
            
        # Check for common markers
        if data[0] in (0x00, 0xFF) and data[1] == data[0]:
            return True
            
        return False
    
    def read_blocks(self, f: BinaryIO, file_size: int) -> List[MDLBlock]:
        """Read all blocks from MDL file"""
        blocks = []
        pos = 16  # Skip header
        f.seek(pos)
        
        # Read in larger chunks for efficiency
        chunk_size = 4096
        buffer = bytearray()
        
        while pos < file_size:
            if len(buffer) < 4096:
                chunk = f.read(min(chunk_size, file_size - f.tell()))
                if not chunk:
                    break
                buffer.extend(chunk)
            
            # Look for block markers
            if len(buffer) >= 4 and self.is_block_marker(buffer[:4]):
                marker = buffer[:4]
                buffer = buffer[4:]
                block_data = bytearray()
                block_start = pos
                pos += 4
                
                # Read until next marker
                while buffer or f.tell() < file_size:
                    if len(buffer) < 4:
                        chunk = f.read(min(chunk_size, file_size - f.tell()))
                        if not chunk:
                            break
                        buffer.extend(chunk)
                    
                    if len(buffer) >= 4 and self.is_block_marker(buffer[:4]):
                        break
                        
                    block_data.append(buffer[0])
                    buffer = buffer[1:]
                    pos += 1
                
                if block_data:
                    blocks.append(MDLBlock(
                        offset=block_start,
                        size=len(block_data),
                        data=bytes(block_data),
                        marker=marker
                    ))
                    
                    # Progress indicator
                    progress = pos * 100 // file_size
                    print(f"\rAnalyzing: {progress}% ({len(blocks)} blocks found)", end='')
                    sys.stdout.flush()
            else:
                buffer = buffer[1:]
                pos += 1
                
        print()  # New line after progress
        return blocks
    
    def extract_blocks(self, filename: str, output_dir: str = None, output_text: bool = False):
        """Extract all blocks from MDL file"""
        if output_dir is None:
            output_dir = Path(filename).stem + "_blocks"
        
        Path(output_dir).mkdir(exist_ok=True)
        
        with open(filename, 'rb') as f:
            # Get file size
            f.seek(0, 2)
            file_size = f.tell()
            f.seek(0)
            
            # Read header
            header = f.read(16)
            magic, decomp_size, flag1, flag2 = struct.unpack('<4sIII', header)
            
            self.logger.info(f"File: {filename}")
            self.logger.info(f"Size: {file_size:,} bytes")
            self.logger.info(f"Magic: {magic}")
            self.logger.info(f"Decompressed size: {decomp_size:,}")
            self.logger.info(f"Flags: 0x{flag1:08x}, 0x{flag2:08x}")
            
            # Extract blocks
            print(f"\nAnalyzing {filename}...")
            blocks = self.read_blocks(f, file_size)
            self.logger.info(f"Found {len(blocks)} blocks")
            
            # Save blocks
            print(f"\nExtracting blocks to {output_dir}...")
            for i, block in enumerate(blocks):
                block_file = Path(output_dir) / f"block_{i:04d}_{block.marker.hex()}.bin"
                with open(block_file, 'wb') as bf:
                    bf.write(block.data)
                self.logger.debug(f"Saved block {i}: {block_file.name} ({block.size:,} bytes)")
            
            # Save block info
            info_file = Path(output_dir) / "blocks.txt"
            with open(info_file, 'w') as f:
                f.write(f"MDL File: {filename}\n")
                f.write(f"Total blocks: {len(blocks)}\n\n")
                
                for i, block in enumerate(blocks):
                    f.write(f"Block {i}:\n")
                    f.write(f"  Offset: 0x{block.offset:x}\n")
                    f.write(f"  Size: {block.size:,} bytes\n")
                    f.write(f"  Marker: {block.marker.hex()}\n\n")
            
            # Save detailed text output if requested
            if output_text:
                text_file = Path(filename).stem + "_analysis.txt"
                with open(text_file, 'w') as f:
                    f.write(f"MDL File Analysis: {filename}\n")
                    f.write("=" * 50 + "\n\n")
                    
                    f.write("Header Information:\n")
                    f.write(f"  File size: {file_size:,} bytes\n")
                    f.write(f"  Magic: {magic}\n")
                    f.write(f"  Decompressed size: {decomp_size:,} bytes\n")
                    f.write(f"  Flag1: 0x{flag1:08x}\n")
                    f.write(f"  Flag2: 0x{flag2:08x}\n\n")
                    
                    f.write(f"Block Analysis ({len(blocks)} blocks):\n")
                    f.write("-" * 30 + "\n")
                    
                    # Block statistics
                    sizes = [b.size for b in blocks]
                    markers = [b.marker for b in blocks]
                    
                    f.write(f"Size Statistics:\n")
                    f.write(f"  Minimum: {min(sizes):,} bytes\n")
                    f.write(f"  Maximum: {max(sizes):,} bytes\n")
                    f.write(f"  Average: {sum(sizes)/len(sizes):,.1f} bytes\n\n")
                    
                    # Marker frequency
                    marker_counts = {}
                    for m in markers:
                        # Convert bytearray to bytes for hashing
                        marker_key = bytes(m) if isinstance(m, bytearray) else m
                        marker_counts[marker_key] = marker_counts.get(marker_key, 0) + 1
                    
                    f.write("Common Markers:\n")
                    for marker, count in sorted(marker_counts.items(), key=lambda x: x[1], reverse=True):
                        f.write(f"  {marker.hex()}: {count} times\n")
                    f.write("\n")
                    
                    # Block pattern analysis
                    f.write("\nBlock Pattern Analysis:\n")
                    f.write("-" * 30 + "\n")
                    
                    # Look for repeating patterns
                    pattern_sizes = []
                    last_size = None
                    pattern_count = 1
                    
                    for block in blocks:
                        if block.size == last_size:
                            pattern_count += 1
                        else:
                            if pattern_count > 1:
                                pattern_sizes.append((last_size, pattern_count))
                            pattern_count = 1
                            last_size = block.size
                    
                    if pattern_count > 1:
                        pattern_sizes.append((last_size, pattern_count))
                    
                    f.write("\nRepeating Block Sizes:\n")
                    for size, count in sorted(pattern_sizes, key=lambda x: x[1], reverse=True)[:10]:
                        f.write(f"  {size:,} bytes: {count} times\n")
                    
                    # Analyze block spacing
                    f.write("\nBlock Spacing:\n")
                    spacings = []
                    for i in range(1, len(blocks)):
                        spacing = blocks[i].offset - (blocks[i-1].offset + blocks[i-1].size)
                        spacings.append(spacing)
                    
                    if spacings:
                        f.write(f"  Minimum spacing: {min(spacings):,} bytes\n")
                        f.write(f"  Maximum spacing: {max(spacings):,} bytes\n")
                        f.write(f"  Average spacing: {sum(spacings)/len(spacings):,.1f} bytes\n")
                        
                        # Look for common alignments
                        alignments = [s for s in spacings if s > 0]
                        if alignments:
                            common_align = max(set(alignments), key=alignments.count)
                            f.write(f"  Most common alignment: {common_align:,} bytes\n")
                    
                    # Detailed block listing
                    f.write("\nBlock Details:\n")
                    for i, block in enumerate(blocks):
                        f.write(f"\nBlock {i}:\n")
                        f.write(f"  Offset: 0x{block.offset:x}\n")
                        f.write(f"  Size: {block.size:,} bytes\n")
                        f.write(f"  Marker: {block.marker.hex()}\n")
                        f.write(f"  First 16 bytes: {block.data[:16].hex()}\n")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract blocks from MDL files')
    parser.add_argument('files', nargs='+', help='MDL files to extract')
    parser.add_argument('--outdir', help='Output directory')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--outtext', action='store_true', help='Generate detailed text analysis')
    args = parser.parse_args()
    
    extractor = MDLExtractor(debug=args.debug)
    for file in args.files:
        extractor.extract_blocks(file, args.outdir, args.outtext)

if __name__ == '__main__':
    main() 