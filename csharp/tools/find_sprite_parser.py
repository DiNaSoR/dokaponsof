"""Find the sprite section parser in the EXE by scanning for string references
using broader patterns (MOV, LEA with different prefixes)."""
import struct
import pefile
from capstone import *

EXE = r"D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\DOKAPON! Sword of Fury.exe"
pe = pefile.PE(EXE)
data = open(EXE, 'rb').read()
image_base = pe.OPTIONAL_HEADER.ImageBase

def va_to_offset(va):
    rva = va - image_base
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            return rva - s.VirtualAddress + s.PointerToRawData
    return None

def offset_to_va(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            rva = off - s.PointerToRawData + s.VirtualAddress
            return image_base + rva
    return None

# Find all section name strings
targets = {}
for name in ["Sequence", "Sprite\x00", "SpriteGp", "TextureParts", "Parts\x00", "Texture\x00", "Anime\x00", "ConvertInfo", "PartsColor"]:
    clean = name.rstrip('\x00')
    pos = 0
    while True:
        pos = data.find(name.encode('ascii'), pos)
        if pos == -1:
            break
        va = offset_to_va(pos)
        if va:
            targets[f"{clean}@{pos}"] = (va, pos, clean)
        pos += 1

print(f"Found {len(targets)} string targets")

# Get .text section
text_sec = None
for s in pe.sections:
    if b'.text' in s.Name:
        text_sec = s
        break

if not text_sec:
    print("No .text section!")
    exit()

text_data = data[text_sec.PointerToRawData:text_sec.PointerToRawData + text_sec.SizeOfRawData]
text_rva = text_sec.VirtualAddress

# Search for ANY instruction that references these string VAs
# Including: LEA with 48/4C prefix, MOV with various prefixes
print("\nSearching for xrefs in .text section...")

for key, (target_va, target_off, name) in targets.items():
    target_rva = target_va - image_base
    refs = []

    for i in range(len(text_data) - 7):
        # Check LEA patterns: [REX] 8D [modrm] [disp32]
        # REX can be 48, 4C, or none (for 32-bit LEA)
        for prefix_len, check in [
            (2, lambda: text_data[i] in (0x48, 0x4C) and text_data[i+1] == 0x8D and (text_data[i+2] & 0xC7) == 0x05),
            (1, lambda: text_data[i] == 0x8D and (text_data[i+1] & 0xC7) == 0x05),
        ]:
            try:
                if check():
                    disp_off = i + prefix_len + 1
                    disp = struct.unpack_from('<i', text_data, disp_off)[0]
                    instr_end_rva = text_rva + i + prefix_len + 5
                    ref_target_rva = instr_end_rva + disp
                    if ref_target_rva == target_rva:
                        ref_va = image_base + text_rva + i
                        refs.append(ref_va)
            except:
                pass

    if refs:
        print(f"\n  '{name}' (VA=0x{target_va:X}): {len(refs)} xref(s)")
        for ref in refs[:5]:
            print(f"    at 0x{ref:X}")
            # Disassemble context
            off = va_to_offset(ref - 0x10)
            if off:
                code = data[off:off + 0x80]
                md = Cs(CS_ARCH_X86, CS_MODE_64)
                for insn in md.disasm(code, ref - 0x10):
                    marker = " <-- XREF" if insn.address == ref else ""
                    print(f"      0x{insn.address:X}: {insn.mnemonic} {insn.op_str}{marker}")
                    if insn.address > ref + 0x40:
                        break
