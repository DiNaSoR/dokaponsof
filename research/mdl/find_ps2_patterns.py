#!/usr/bin/env python3
"""Find PS2-style VIF/GIF patterns in decompressed MDL"""
import struct
import sys

def find_ps2_patterns(filename):
    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    
    # Common PS2 VIF codes (little-endian)
    VIF_CODES = {
        0x6C: "UNPACK V3-32",     # 3 floats
        0x6D: "UNPACK V4-32",     # 4 floats  
        0x68: "UNPACK V2-32",     # 2 floats
        0x6E: "UNPACK V2-16",     # 2 shorts
        0x6F: "UNPACK V3-16",     # 3 shorts
        0x61: "UNPACK V4-8",      # 4 bytes
        0x72: "UNPACK V4-16",     # 4 shorts
        0x00: "NOP",
        0x01: "STCYCL",
        0x02: "OFFSET",
        0x03: "BASE",
        0x04: "ITOP",
        0x05: "STMOD",
        0x06: "MSKPATH3",
        0x10: "FLUSHE",
        0x11: "FLUSH",
        0x13: "FLUSHA",
        0x14: "MSCAL",
        0x15: "MSCALF",
        0x17: "MSCNT",
        0x20: "STMASK",
        0x30: "STROW",
        0x31: "STCOL",
    }
    
    print("\n=== SEARCHING FOR VIF CODES ===")
    
    vif_hits = {}
    for i in range(0, len(data) - 4, 4):
        # VIF codes are in the upper byte of a 32-bit word
        word = struct.unpack("<I", data[i:i+4])[0]
        cmd = (word >> 24) & 0x7F  # Upper 7 bits of highest byte
        
        if cmd in VIF_CODES:
            if cmd not in vif_hits:
                vif_hits[cmd] = []
            vif_hits[cmd].append(i)
    
    for cmd, positions in sorted(vif_hits.items()):
        if len(positions) >= 3:  # At least 3 occurrences
            print(f"  VIF 0x{cmd:02X} ({VIF_CODES.get(cmd, 'unknown')}): {len(positions)} hits")
            for p in positions[:5]:
                word = struct.unpack("<I", data[p:p+4])[0]
                print(f"    0x{p:06x}: 0x{word:08X}")
    
    # Look for GIF tags (64-bit with specific patterns)
    print("\n=== SEARCHING FOR GIF TAGS ===")
    
    gif_candidates = []
    for i in range(0, len(data) - 16, 8):
        try:
            # GIF tag format: NLOOP (15 bits) | EOP (1) | ? | PRE | PRIM | FLG | NREG | REGS
            lo, hi = struct.unpack("<2I", data[i:i+8])
            
            nloop = lo & 0x7FFF
            eop = (lo >> 15) & 1
            flag = (hi >> 26) & 0x3
            nreg = (hi >> 28) & 0xF
            
            # Reasonable GIF tag
            if 1 <= nloop <= 1000 and nreg <= 16 and flag <= 2:
                # Check if REGS field makes sense
                regs = data[i+8:i+8+nreg] if i+8+nreg <= len(data) else b''
                gif_candidates.append((i, nloop, eop, flag, nreg))
        except:
            pass
    
    print(f"Found {len(gif_candidates)} potential GIF tags")
    for off, nloop, eop, flag, nreg in gif_candidates[:10]:
        print(f"  0x{off:06x}: NLOOP={nloop}, EOP={eop}, FLAG={flag}, NREG={nreg}")
        print(f"    Data: {data[off:off+16].hex()}")
    
    # Look for vertex data in DirectX/OpenGL format (interleaved)
    print("\n=== SEARCHING FOR INTERLEAVED VERTEX DATA ===")
    
    # Pattern: pos (3f), normal (3f), uv (2f) = 32 bytes per vertex
    # Or: pos (3f), uv (2f) = 20 bytes per vertex
    
    for stride in [12, 20, 24, 32, 36, 40, 44, 48]:
        # Try to find sequences with this stride
        for start in range(0, min(len(data), 0x80000), 4):
            valid_verts = 0
            for j in range(20):  # Check 20 potential vertices
                off = start + j * stride
                if off + 12 > len(data):
                    break
                
                try:
                    x, y, z = struct.unpack("<3f", data[off:off+12])
                    if all(-500 < v < 500 for v in (x, y, z)) and any(v != 0 for v in (x, y, z)):
                        valid_verts += 1
                except:
                    break
            
            if valid_verts >= 15:
                print(f"  Stride {stride} at 0x{start:06x}: {valid_verts} valid vertices")
                # Show first few
                for j in range(3):
                    off = start + j * stride
                    x, y, z = struct.unpack("<3f", data[off:off+12])
                    print(f"    [{j}]: ({x:.3f}, {y:.3f}, {z:.3f})")
                break  # Found one, move to next stride

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python find_ps2_patterns.py file.bin")
        sys.exit(1)
    find_ps2_patterns(sys.argv[1])

