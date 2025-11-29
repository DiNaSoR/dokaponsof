#!/usr/bin/env python3
"""Analyze VIF command structure in detail"""
import struct
import sys

def analyze_vif_commands(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("=== VIF 0x6C COMMAND ANALYSIS ===")
    
    # Find VIF 0x6C commands
    positions = []
    for i in range(0, len(data) - 4, 4):
        word = struct.unpack("<I", data[i:i+4])[0]
        cmd = (word >> 24) & 0x7F
        if cmd == 0x6C:
            positions.append(i)
    
    print(f"Found {len(positions)} VIF 0x6C commands")
    
    # Examine first few in detail
    for pos in positions[:10]:
        word = struct.unpack("<I", data[pos:pos+4])[0]
        print(f"\nAt 0x{pos:06x}: 0x{word:08X}")
        
        # Parse VIF fields
        num = (word >> 16) & 0xFF
        addr = word & 0x3FF
        print(f"  NUM={num}, ADDR={addr}")
        
        # Show hex dump of surrounding data
        before = data[pos-16:pos] if pos >= 16 else b''
        print(f"  Before: {before.hex()}")
        print(f"  Command: {data[pos:pos+4].hex()}")
        print(f"  After: {data[pos+4:pos+68].hex()}")
        
        # Try to interpret as floats at different offsets
        print(f"  As floats (offset +4):")
        for j in range(min(4, num)):
            off = pos + 4 + j * 12
            if off + 12 <= len(data):
                x, y, z = struct.unpack("<3f", data[off:off+12])
                print(f"    [{j}]: ({x:.4f}, {y:.4f}, {z:.4f})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_vif_cmd.py file.bin")
        sys.exit(1)
    analyze_vif_commands(sys.argv[1])

