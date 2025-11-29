#!/usr/bin/env python3
"""Simple LZ77 decompressor for MDL files"""
import struct
import sys

def decompress_lz77(filename):
    with open(filename, "rb") as f:
        magic = f.read(4)
        if magic != b"LZ77":
            print(f"Invalid magic: {magic}")
            return None
        size = struct.unpack("<I", f.read(4))[0]
        f.read(8)  # Skip flags
        data = f.read()
    
    output = bytearray()
    pos = 0
    
    while len(output) < size and pos < len(data):
        token = data[pos]
        pos += 1
        
        if token & 0x80:  # Back reference
            if pos >= len(data):
                break
            length = ((token & 0x7C) >> 2) + 3
            offset = (((token & 0x03) << 8) | data[pos]) + 1
            pos += 1
            
            for _ in range(length):
                if len(output) >= offset:
                    output.append(output[-offset])
                else:
                    output.append(0)
                if len(output) >= size:
                    break
        else:  # Literal
            output.append(token)
    
    return bytes(output)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python decomp_simple.py input.mdl output.bin")
        sys.exit(1)
    
    result = decompress_lz77(sys.argv[1])
    if result:
        with open(sys.argv[2], "wb") as f:
            f.write(result)
        print(f"Decompressed {len(result)} bytes to {sys.argv[2]}")

