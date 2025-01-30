"""
LZ77 Decompression Finder for Dokapon Sword of Fury
=================================================

This script combines the functionality of exe_scanner.py and lz77_extractor.py
to locate and analyze the LZ77 decompression code used for S_TIT00_00.mpd.

Usage:
    python find_lz77.py

Created by: Assistant
Based on work by: DiNaSoR
"""

import os
import struct
import binascii
from pathlib import Path
from typing import List, Tuple, Optional

class LZ77Finder:
    def __init__(self, exe_path: str):
        self.exe_path = exe_path
        self.exe_data = None
        self.load_exe()
    
    def load_exe(self):
        """Load the executable into memory"""
        with open(self.exe_path, 'rb') as f:
            self.exe_data = f.read()
        print(f"Loaded {len(self.exe_data):,} bytes from {self.exe_path}")
    
    def find_string_refs(self, target: str) -> List[int]:
        """Find all references to a string in the executable"""
        refs = []
        encoded = target.encode('utf-8')
        pos = 0
        while True:
            pos = self.exe_data.find(encoded, pos)
            if pos < 0:
                break
            refs.append(pos)
            pos += 1
        return refs
    
    def scan_for_lz77(self, start_offset: int = 0, range_size: Optional[int] = None) -> List[Tuple[int, bytes]]:
        """Scan for potential LZ77 decompression code"""
        if range_size is None:
            range_size = len(self.exe_data)
        
        # Common patterns in LZ77 decompression
        patterns = [
            (b'LZ77', "LZ77 magic constant"),
            (b'\x48\x8b\x54\x24', "Buffer access"),
            (b'\x48\x83\xc2\x10', "Skip header"),
            (b'\x48\x83\xec', "Stack frame setup"),
            (b'\x48\x8b\x8c', "Memory operations"),
            (b'\x0f\x85', "Loop control"),
            (b'\x48\xc1', "Bit shifts"),
            (b'\x48\x83', "AND/OR operations"),
            (b'\x0f\xb6', "Zero extend (MOVZX)"),
        ]
        
        matches = []
        for pattern, desc in patterns:
            pos = start_offset
            while pos < start_offset + range_size:
                pos = self.exe_data.find(pattern, pos)
                if pos < 0 or pos >= start_offset + range_size:
                    break
                matches.append((pos, pattern, desc))
                pos += 1
        
        return sorted(matches, key=lambda x: x[0])
    
    def analyze_potential_function(self, offset: int, size: int = 0x100) -> None:
        """Analyze a potential decompression function"""
        data = self.exe_data[offset:offset + size]
        
        print(f"\nAnalyzing potential function at 0x{offset:08x}:")
        print("=" * 50)
        
        # Look for compression parameters
        window_sizes = [b'\x00\x10\x00\x00', b'\x00\x20\x00\x00', b'\x00\x40\x00\x00']
        for size in window_sizes:
            pos = data.find(size)
            if pos >= 0:
                print(f"Found window size: 0x{struct.unpack('<I', size)[0]:x} bytes")
        
        # Look for bit masks
        masks = [b'\x0f\x00', b'\x1f\x00', b'\x3f\x00', b'\x7f\x00', b'\xff\x00']
        for mask in masks:
            pos = data.find(mask)
            if pos >= 0:
                print(f"Found bit mask: 0x{mask[0]:02x}")
        
        # Print hex dump with basic analysis
        for i in range(0, len(data), 16):
            chunk = data[i:i+16]
            hex_str = " ".join(f"{b:02x}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            print(f"{offset+i:08x}: {hex_str:48} {ascii_str}")

def main():
    # Find the executable in the workspace root
    exe_name = "DOKAPON! Sword of Fury.exe"
    workspace_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    exe_path = os.path.join(workspace_root, exe_name)
    
    if not os.path.exists(exe_path):
        print(f"Error: Could not find {exe_name} in workspace root")
        return
    
    finder = LZ77Finder(exe_path)
    
    # Look for S_TIT00_00.mpd references
    print("\nSearching for S_TIT00_00.mpd references...")
    mpd_refs = finder.find_string_refs("S_TIT00_00.mpd")
    if not mpd_refs:
        print("Looking for format string S_TIT%02d_00.mpd instead...")
        mpd_refs = finder.find_string_refs("S_TIT%02d_00.mpd")
    
    if mpd_refs:
        print(f"Found {len(mpd_refs)} references:")
        for ref in mpd_refs:
            print(f"  At offset: 0x{ref:08x}")
            # Analyze code around the reference
            finder.analyze_potential_function(max(0, ref - 0x100))
    
    # Scan for LZ77 decompression code
    print("\nScanning for LZ77 decompression code...")
    matches = finder.scan_for_lz77()
    
    if matches:
        print(f"\nFound {len(matches)} potential LZ77-related patterns:")
        
        # Group matches that are close together (likely part of same function)
        groups = []
        current_group = []
        
        for i, (offset, pattern, desc) in enumerate(matches):
            if not current_group or offset - current_group[-1][0] < 0x100:
                current_group.append((offset, pattern, desc))
            else:
                if len(current_group) > 2:  # Only show groups with multiple matches
                    groups.append(current_group)
                current_group = [(offset, pattern, desc)]
        
        if current_group:
            groups.append(current_group)
        
        # Print grouped matches
        for i, group in enumerate(groups, 1):
            if len(group) < 3:  # Skip groups with few matches
                continue
            
            start_offset = group[0][0]
            print(f"\nPotential LZ77 function #{i} at 0x{start_offset:08x}:")
            for offset, pattern, desc in group:
                print(f"  +0x{offset-start_offset:04x}: {desc:20} | {binascii.hexlify(pattern).decode()}")
            
            # Analyze the potential function
            finder.analyze_potential_function(start_offset)
    
    else:
        print("No LZ77 patterns found")

if __name__ == '__main__':
    main() 