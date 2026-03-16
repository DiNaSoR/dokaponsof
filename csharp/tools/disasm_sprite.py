"""Disassemble code around spranm section parsing to understand struct layout."""
import struct
import pefile
from capstone import *

EXE = r"D:\Program Files (x86)\Steam\steamapps\common\DOKAPON ~Sword of Fury~\DOKAPON! Sword of Fury.exe"
pe = pefile.PE(EXE)
data = open(EXE, 'rb').read()
image_base = pe.OPTIONAL_HEADER.ImageBase

# String VAs from previous analysis
STRING_VAS = {
    "Sequence": 0x1406C8D80,
    "Sprite": None,  # need to find
    "SpriteGp": 0x1406C8D60,
    "TextureParts": 0x1406C8D90,
}

# Find the exact VA for "Sprite\0" (not "SpriteGp")
pos = 0
while True:
    pos = data.find(b"Sprite\x00", pos)
    if pos == -1:
        break
    # Check it's not "SpriteGp"
    if pos + 7 < len(data) and data[pos+6] == 0:  # null terminated at 6
        for sec in pe.sections:
            off = sec.PointerToRawData
            if off <= pos < off + sec.SizeOfRawData:
                rva = pos - off + sec.VirtualAddress
                va = image_base + rva
                STRING_VAS["Sprite"] = va
                print(f"Found 'Sprite\\0' at VA=0x{va:X}")
                break
        break
    pos += 1

def va_to_offset(va):
    rva = va - image_base
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.Misc_VirtualSize:
            return rva - s.VirtualAddress + s.PointerToRawData
    return None

def find_xrefs(target_va, section_name=b'.text'):
    """Find all LEA instructions referencing a target VA."""
    results = []
    for sec in pe.sections:
        if section_name not in sec.Name:
            continue
        sec_data = data[sec.PointerToRawData:sec.PointerToRawData + sec.SizeOfRawData]
        sec_rva = sec.VirtualAddress
        for i in range(len(sec_data) - 7):
            # LEA r64, [rip+disp32]: 48 8D {modrm} {disp32}
            # or 4C 8D for r8-r15
            prefix = sec_data[i]
            if prefix in (0x48, 0x4C) and sec_data[i+1] == 0x8D:
                modrm = sec_data[i+2]
                if (modrm & 0xC7) == 0x05:  # mod=00, rm=101 (RIP-relative)
                    disp = struct.unpack_from('<i', sec_data, i+3)[0]
                    instr_end_rva = sec_rva + i + 7
                    target_rva = instr_end_rva + disp
                    if target_rva == target_va - image_base:
                        ref_va = image_base + sec_rva + i
                        results.append(ref_va)
    return results

# Find xrefs to each string
for name, va in STRING_VAS.items():
    if va is None:
        continue
    refs = find_xrefs(va)
    print(f"\nXrefs to '{name}' (VA=0x{va:X}): {len(refs)} found")
    for ref in refs[:3]:
        print(f"  at 0x{ref:X}")
        # Disassemble surrounding code
        off = va_to_offset(ref - 0x20)
        if off is None:
            continue
        code = data[off:off + 0x120]
        md = Cs(CS_ARCH_X86, CS_MODE_64)
        md.detail = True
        base_va = ref - 0x20
        print(f"  --- Disassembly around 0x{ref:X} ---")
        for insn in md.disasm(code, base_va):
            marker = " <-- STRING REF" if insn.address == ref else ""
            print(f"    0x{insn.address:X}: {insn.mnemonic} {insn.op_str}{marker}")
            if insn.address > ref + 0x80:
                break
