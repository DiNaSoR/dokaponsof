#!/usr/bin/env python3
"""Decode packed vertex data from MDL files"""
import struct
import sys

def analyze_packed_data(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Look for regions with 0x7f bytes (could be packed signed data)
    print("\n=== LOOKING FOR PACKED VERTEX DATA (0x7f patterns) ===")
    
    # Find regions with repeating 0x7f followed by varied data
    packed_regions = []
    i = 0
    while i < len(data) - 32:
        # Look for sequence of 0x7f bytes
        if data[i:i+4] == b'\x7f\x7f\x7f\x7f':
            start = i
            # Find start of actual data (where 0x7f pattern ends)
            while i < len(data) and data[i] == 0x7f:
                i += 1
            end = i
            if end - start >= 8:
                packed_regions.append((start, end))
            continue
        i += 1
    
    print(f"Found {len(packed_regions)} 0x7f padding regions")
    for start, end in packed_regions[:10]:
        print(f"  0x{start:06x} - 0x{end:06x}: {end-start} bytes")
        # Show data after the padding
        if end + 32 <= len(data):
            print(f"    Data after: {data[end:end+16].hex()}")
    
    # Look for packed 8-bit vertex data (values 0-255 representing -1 to 1)
    print("\n=== LOOKING FOR 8-BIT PACKED VERTICES ===")
    
    # Pattern: sequences of bytes where most are in 64-192 range (centered around 128)
    i = 0
    packed_vert_regions = []
    while i < len(data) - 36:
        # Read 12 bytes and check if they could be 4 packed vec3
        chunk = data[i:i+12]
        
        # Count how many bytes are in "normal-like" range
        centered = sum(1 for b in chunk if 32 <= b <= 224)
        
        if centered >= 9:  # At least 9 of 12 bytes in range
            # Check if it's a run
            start = i
            count = 0
            while i < len(data) - 3:
                b = data[i:i+3]
                if all(32 <= x <= 224 for x in b):
                    count += 1
                    i += 3
                else:
                    break
            if count >= 20:  # At least 20 vec3s
                packed_vert_regions.append((start, i, count))
            else:
                i = start + 4
            continue
        i += 4
    
    print(f"Found {len(packed_vert_regions)} potential 8-bit packed vertex regions:")
    for start, end, count in packed_vert_regions[:10]:
        print(f"\n  0x{start:06x} - 0x{end:06x}: {count} packed vec3s")
        # Decode first few as normalized vectors
        for j in range(min(5, count)):
            off = start + j * 3
            x = (data[off] - 128) / 127.0
            y = (data[off+1] - 128) / 127.0
            z = (data[off+2] - 128) / 127.0
            print(f"    [{j:3d}]: ({x:7.4f}, {y:7.4f}, {z:7.4f}) raw=[{data[off]},{data[off+1]},{data[off+2]}]")
    
    # Look for 16-bit packed vertex data (signed shorts)
    print("\n=== LOOKING FOR 16-BIT PACKED VERTICES ===")
    
    i = 0
    short_regions = []
    while i < len(data) - 24:
        # Try reading as 4 signed shorts (8 bytes for 1.3 vec3 + extra)
        try:
            vals = struct.unpack("<4h", data[i:i+8])
            # Check if values look like scaled coordinates
            if all(-5000 < v < 5000 for v in vals):
                if any(v != 0 for v in vals):
                    # Extend region
                    start = i
                    count = 0
                    while i < len(data) - 6:
                        vals = struct.unpack("<3h", data[i:i+6])
                        if all(-5000 < v < 5000 for v in vals):
                            count += 1
                            i += 6
                        else:
                            break
                    if count >= 30:
                        short_regions.append((start, i, count))
                    else:
                        i = start + 2
                    continue
        except:
            pass
        i += 2
    
    print(f"Found {len(short_regions)} potential 16-bit vertex regions:")
    for start, end, count in short_regions[:10]:
        print(f"\n  0x{start:06x} - 0x{end:06x}: {count} packed vec3s (16-bit)")
        for j in range(min(5, count)):
            off = start + j * 6
            x, y, z = struct.unpack("<3h", data[off:off+6])
            # Scale assuming max coordinate around 100
            xs, ys, zs = x/100.0, y/100.0, z/100.0
            print(f"    [{j:3d}]: ({xs:8.3f}, {ys:8.3f}, {zs:8.3f}) raw=[{x},{y},{z}]")
    
    # Look for the large data blocks (9K-12K mentioned in research)
    print("\n=== ANALYZING LARGE DATA BLOCKS ===")
    
    # Find regions with low entropy (repeated patterns)
    block_size = 2048
    for block_start in range(0, min(len(data), 0x50000), block_size):
        block = data[block_start:block_start+block_size]
        if len(block) < block_size:
            continue
        
        # Check for structure markers at block start
        marker = struct.unpack("<I", block[:4])[0]
        if marker in [0xAAAAAAAA, 0x55555555, 0x0000C000, 0x000040C1]:
            print(f"  Block 0x{block_start:06x}: marker 0x{marker:08x}")
            # Show first 32 bytes
            print(f"    Data: {block[:32].hex()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python decode_packed_verts.py file.bin")
        sys.exit(1)
    analyze_packed_data(sys.argv[1])

