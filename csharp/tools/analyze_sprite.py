"""Analyze the game EXE to find how sprite position fields are used in rendering."""
import struct
import pefile
import sys

EXE = r"D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\DOKAPON! Sword of Fury.exe"

pe = pefile.PE(EXE)
data = open(EXE, 'rb').read()
image_base = pe.OPTIONAL_HEADER.ImageBase  # 0x140000000

def rva_to_offset(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            return rva - s.VirtualAddress + s.PointerToRawData
    return None

def find_strings(pattern, encoding='ascii'):
    """Find all occurrences of a string in the binary."""
    results = []
    encoded = pattern.encode(encoding)
    pos = 0
    while True:
        pos = data.find(encoded, pos)
        if pos == -1:
            break
        results.append(pos)
        pos += 1
    return results

# Find the "Sprite" section name strings (padded to 20 bytes)
print("=== Looking for section name strings ===")
for name in ["Sequence", "Sprite", "SpriteGp", "TextureParts", "Parts", "Texture"]:
    padded = name.ljust(20).encode('ascii')
    positions = []
    pos = 0
    while True:
        pos = data.find(padded, pos)
        if pos == -1:
            break
        positions.append(pos)
        pos += 1
    # Also find just the name as a reference string
    refs = find_strings(name + "\x00")
    print(f"  '{name}' padded: {len(positions)} hits, null-term: {len(refs)} hits")
    for p in positions[:3]:
        # Calculate VA
        for s in pe.sections:
            off = s.PointerToRawData
            if off <= p < off + s.SizeOfRawData:
                rva = p - off + s.VirtualAddress
                va = image_base + rva
                print(f"    offset=0x{p:X} VA=0x{va:X}")
                break

# Now find key float patterns that might indicate sprite struct reading
# Look for the pattern of reading 5 uint32s (Sequence entry) or 8 fields (Sprite entry)
# More practically: find references to "Sprite" string to locate the parser

# Search for specific string patterns in .rdata
print("\n=== Searching for sprite-related strings ===")
for s in ["SpriteGp", "TextureParts", "Sequence", "Anime", "ConvertInfo"]:
    positions = find_strings(s + "\x00")
    for p in positions[:2]:
        for sec in pe.sections:
            off = sec.PointerToRawData
            if off <= p < off + sec.SizeOfRawData:
                rva = p - off + sec.VirtualAddress
                va = image_base + rva
                print(f"  '{s}' at VA=0x{va:X}")
                break

# Look for the float 1.0 (3F800000) near sprite struct code
# Look for patterns where multiple ReadUInt32 + ReadFloat happen in sequence
print("\n=== Looking for sprite rendering hints ===")

# Find "Load Anime Model Thread" string
for s in ["Load Anime Model Thread", "Anime Model", "k_cgraphics"]:
    positions = find_strings(s)
    for p in positions[:2]:
        for sec in pe.sections:
            off = sec.PointerToRawData
            if off <= p < off + sec.SizeOfRawData:
                rva = p - off + sec.VirtualAddress
                va = image_base + rva
                print(f"  '{s}' at VA=0x{va:X}")
                break

# Try to find cross-references to the "Sprite" string by scanning for its VA in LEA instructions
print("\n=== Finding code that references 'Sprite' string ===")
sprite_str_positions = find_strings("Sprite\x00")
for sp in sprite_str_positions[:5]:
    for sec in pe.sections:
        off = sec.PointerToRawData
        if off <= sp < off + sec.SizeOfRawData:
            rva = sp - off + sec.VirtualAddress
            va = image_base + rva
            # Search for LEA with RIP-relative addressing that points to this VA
            # In x64, LEA reg, [rip+disp32] is common
            # Look for the RVA in .text section
            text = None
            for s2 in pe.sections:
                if b'.text' in s2.Name:
                    text = s2
                    break
            if text:
                text_data = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]
                text_rva = text.VirtualAddress
                # For each position in .text, check if rip+disp32 = target rva
                # LEA opcode: 48 8D xx (with mod/rm)
                found_refs = 0
                for i in range(len(text_data) - 7):
                    # Check for LEA r64, [rip+disp32]
                    if text_data[i] == 0x48 and text_data[i+1] == 0x8D:
                        modrm = text_data[i+2]
                        if (modrm & 0xC7) == 0x05:  # [rip+disp32] with any register
                            disp = struct.unpack_from('<i', text_data, i+3)[0]
                            target_rva = text_rva + i + 7 + disp
                            if target_rva == rva:
                                ref_va = image_base + text_rva + i
                                print(f"  LEA ref to 'Sprite' at VA=0x{ref_va:X}")
                                found_refs += 1
                                if found_refs >= 5:
                                    break
            break

# Find "Parts" string references too
print("\n=== Finding code that references 'Parts' string ===")
parts_str = find_strings("Parts\x00")
for sp in parts_str[:3]:
    for sec in pe.sections:
        off = sec.PointerToRawData
        if off <= sp < off + sec.SizeOfRawData:
            rva = sp - off + sec.VirtualAddress
            va = image_base + rva
            text = None
            for s2 in pe.sections:
                if b'.text' in s2.Name:
                    text = s2
                    break
            if text:
                text_data = data[text.PointerToRawData:text.PointerToRawData + text.SizeOfRawData]
                text_rva = text.VirtualAddress
                found_refs = 0
                for i in range(len(text_data) - 7):
                    if text_data[i] == 0x48 and text_data[i+1] == 0x8D:
                        modrm = text_data[i+2]
                        if (modrm & 0xC7) == 0x05:
                            disp = struct.unpack_from('<i', text_data, i+3)[0]
                            target_rva = text_rva + i + 7 + disp
                            if target_rva == rva:
                                ref_va = image_base + text_rva + i
                                print(f"  LEA ref to 'Parts' at VA=0x{ref_va:X}")
                                found_refs += 1
                                if found_refs >= 5:
                                    break
            break
