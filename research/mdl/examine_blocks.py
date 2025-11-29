#!/usr/bin/env python3
"""Examine structure blocks in decompressed MDL"""
import struct
import sys

def examine_blocks(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("=== EXAMINING STRUCTURE BLOCKS ===")
    
    # Find all 0x55555555 markers (8+ bytes of 0x55)
    pos = 0
    blocks = []
    while True:
        pos = data.find(b"\x55\x55\x55\x55\x55\x55\x55\x55", pos)
        if pos == -1:
            break
        blocks.append(pos)
        pos += 1
    
    print(f"Found {len(blocks)} 8-byte 0x55 marker positions")
    
    # Examine structure after markers
    unique_patterns = {}
    for block_start in blocks:
        # Find end of 0x55 sequence
        end = block_start
        while end < len(data) and data[end] == 0x55:
            end += 1
        
        marker_len = end - block_start
        if marker_len >= 8:
            # Look at data after marker
            if end + 64 <= len(data):
                post = data[end:end+32]
                pattern = post.hex()
                if pattern not in unique_patterns:
                    unique_patterns[pattern] = []
                unique_patterns[pattern].append((block_start, marker_len))
    
    print(f"\n{len(unique_patterns)} unique patterns after markers:")
    
    # Sort by frequency
    sorted_patterns = sorted(unique_patterns.items(), key=lambda x: -len(x[1]))
    
    for pattern, positions in sorted_patterns[:15]:
        print(f"\n  Pattern (count={len(positions)}):")
        print(f"    {pattern}")
        print(f"    First at: 0x{positions[0][0]:06x}")
        
        # Try to interpret the pattern
        post = bytes.fromhex(pattern)
        try:
            d0, d1, d2, d3 = struct.unpack("<4H", post[:8])
            print(f"    As uint16: [{d0}, {d1}, {d2}, {d3}]")
        except:
            pass
    
    # Look for potential mesh blocks (non-0x55 data after markers)
    print("\n\n=== LOOKING FOR MESH DATA BLOCKS ===")
    
    mesh_candidates = []
    for block_start in blocks[:50]:  # Check first 50 markers
        end = block_start
        while end < len(data) and data[end] == 0x55:
            end += 1
        
        if end + 100 <= len(data):
            # Look for varied data (not mostly zeros)
            post = data[end:end+100]
            non_zero = sum(1 for b in post if b != 0)
            if non_zero > 50:  # More than half non-zero
                mesh_candidates.append((block_start, end, non_zero))
    
    print(f"Found {len(mesh_candidates)} blocks with varied data")
    for block_start, end, non_zero in mesh_candidates[:10]:
        print(f"\n  Block at 0x{block_start:06x}, data starts at 0x{end:06x}")
        print(f"    Non-zero bytes in first 100: {non_zero}")
        print(f"    Data: {data[end:end+32].hex()}")
        
        # Try reading as different formats
        try:
            floats = struct.unpack("<4f", data[end:end+16])
            if all(-1000 < f < 1000 for f in floats):
                print(f"    As floats: {[f'{f:.3f}' for f in floats]}")
        except:
            pass
        
        try:
            shorts = struct.unpack("<8h", data[end:end+16])
            if all(-10000 < s < 10000 for s in shorts):
                print(f"    As shorts: {list(shorts)}")
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python examine_blocks.py file.bin")
        sys.exit(1)
    examine_blocks(sys.argv[1])

