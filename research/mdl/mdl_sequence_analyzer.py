import struct
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt

def analyze_sequence(files):
    """Analyze a sequence of MDL files to find patterns"""
    results = []
    
    for file in sorted(files):
        with open(file, 'rb') as f:
            data = f.read()
            
        # Basic header info
        magic = data[0:4]
        decomp_size = struct.unpack('<I', data[4:8])[0]
        flag1 = struct.unpack('<I', data[8:12])[0]
        flag2 = struct.unpack('<I', data[12:16])[0]
        
        # Look for block markers
        markers = []
        for i in range(0, len(data), 2048):
            if i + 16 <= len(data):
                block = data[i:i+16]
                if any(all(b == m for b in block) for m in [0xAA, 0xFF, 0x00]):
                    markers.append((i, block[0]))
        
        # Analyze compression patterns
        pos = 16
        offsets = []
        lengths = []
        while pos < len(data):
            if pos + 1 >= len(data):
                break
                
            flag = data[pos]
            pos += 1
            
            for bit in range(8):
                if pos >= len(data):
                    break
                    
                if flag & (1 << bit):
                    if pos + 2 > len(data):
                        break
                    info = struct.unpack('>H', data[pos:pos+2])[0]
                    length = ((info >> 12) & 0xF) + 3
                    offset = info & 0xFFF
                    offsets.append(offset)
                    lengths.append(length)
                    pos += 2
                else:
                    pos += 1
        
        results.append({
            'file': file,
            'size': len(data),
            'decomp_size': decomp_size,
            'flag1': flag1,
            'flag2': flag2,
            'markers': markers,
            'offset_stats': {
                'min': min(offsets),
                'max': max(offsets),
                'mean': np.mean(offsets),
                'common': np.bincount(offsets).argmax()
            },
            'length_stats': {
                'min': min(lengths),
                'max': max(lengths),
                'mean': np.mean(lengths),
                'common': np.bincount(lengths).argmax()
            }
        })
    
    # Print analysis
    print("\nMDL Sequence Analysis:")
    print("=====================")
    
    for r in results:
        print(f"\nFile: {Path(r['file']).name}")
        print(f"Size: {r['size']:,} bytes")
        print(f"Decompressed: {r['decomp_size']:,} bytes")
        print(f"Flags: 0x{r['flag1']:08x}, 0x{r['flag2']:08x}")
        print(f"Block markers: {len(r['markers'])}")
        print(f"Offset range: {r['offset_stats']['min']}-{r['offset_stats']['max']}")
        print(f"Length range: {r['length_stats']['min']}-{r['length_stats']['max']}")
    
    return results

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Analyze MDL file sequence')
    parser.add_argument('files', nargs='+', help='MDL files to analyze')
    args = parser.parse_args()
    
    analyze_sequence(args.files)

if __name__ == '__main__':
    main() 