"""
Hex Editor Core for DOKAPON! Sword of Fury
Parses .hex patch files and applies binary patches to executables.

Based on the hex format from NewDoc:
- 8 bytes: offset (big-endian int64)
- 8 bytes: data size (big-endian int64)
- N bytes: patch data

Author: DiNaSoR
License: Free to use and modify
"""

import os
import struct
import shutil
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from pathlib import Path


@dataclass
class HexPatch:
    """Represents a single binary patch from a .hex file."""
    offset: int          # Target offset in EXE
    size: int            # Size of patch data
    data: bytes          # Patch data to write
    source_file: str     # Path to source .hex file
    
    def __str__(self) -> str:
        """Format patch info for display."""
        hex_offset = f"0x{self.offset:08X}"
        hex_size = f"0x{self.size:04X}"
        preview = self.data[:16].hex(' ').upper()
        if len(self.data) > 16:
            preview += " ..."
        return f"{os.path.basename(self.source_file)}: {hex_offset} ({hex_size} bytes)"
    
    def get_hex_preview(self, max_bytes: int = 32) -> str:
        """Get a hex dump preview of the patch data."""
        preview = self.data[:max_bytes].hex(' ').upper()
        if len(self.data) > max_bytes:
            preview += f" ... ({len(self.data) - max_bytes} more bytes)"
        return preview
    
    @property
    def end_offset(self) -> int:
        """Calculate the end offset of this patch."""
        return self.offset + self.size


@dataclass 
class PatchConflict:
    """Represents a conflict between two patches."""
    patch1: HexPatch
    patch2: HexPatch
    conflict_type: str  # "overlap" or "same_offset"
    
    def __str__(self) -> str:
        return (f"Conflict ({self.conflict_type}): "
                f"{os.path.basename(self.patch1.source_file)} vs "
                f"{os.path.basename(self.patch2.source_file)} "
                f"at 0x{self.patch1.offset:08X}")


def parse_hex_file(file_path: str) -> List[HexPatch]:
    """
    Parse a .hex patch file into a list of HexPatch objects.
    
    File format (big-endian):
    - 8 bytes: offset in target file
    - 8 bytes: size of data
    - N bytes: patch data
    (repeats for multiple patches in one file)
    
    Args:
        file_path: Path to the .hex file
        
    Returns:
        List of HexPatch objects parsed from the file
        
    Raises:
        FileNotFoundError: If the file doesn't exist
        ValueError: If the file format is invalid
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Hex file not found: {file_path}")
    
    patches = []
    
    with open(file_path, 'rb') as f:
        data = f.read()
    
    pos = 0
    file_size = len(data)
    
    while pos < file_size:
        # Need at least 16 bytes for header (8 + 8)
        if file_size - pos < 16:
            if pos == 0:
                raise ValueError(f"Invalid hex file format: {file_path} (too small)")
            break
        
        # Read offset (8 bytes, big-endian)
        offset_bytes = data[pos:pos + 8]
        offset = int.from_bytes(offset_bytes, byteorder='big')
        pos += 8
        
        # Read size (8 bytes, big-endian)
        size_bytes = data[pos:pos + 8]
        size = int.from_bytes(size_bytes, byteorder='big')
        pos += 8
        
        # Validate size
        if size <= 0:
            raise ValueError(f"Invalid patch size at offset {pos - 8} in {file_path}")
        
        if pos + size > file_size:
            raise ValueError(f"Patch data exceeds file size at offset {pos - 16} in {file_path}")
        
        # Read patch data
        patch_data = data[pos:pos + size]
        pos += size
        
        patches.append(HexPatch(
            offset=offset,
            size=size,
            data=patch_data,
            source_file=file_path
        ))
    
    return patches


def parse_hex_files(file_paths: List[str]) -> List[HexPatch]:
    """
    Parse multiple .hex files into a combined list of patches.
    
    Args:
        file_paths: List of paths to .hex files
        
    Returns:
        Combined list of all patches from all files
    """
    all_patches = []
    for path in file_paths:
        try:
            patches = parse_hex_file(path)
            all_patches.extend(patches)
        except Exception as e:
            print(f"Warning: Failed to parse {path}: {e}")
    return all_patches


def detect_conflicts(patches: List[HexPatch]) -> List[PatchConflict]:
    """
    Detect conflicts between patches (overlapping regions).
    
    Args:
        patches: List of patches to check
        
    Returns:
        List of PatchConflict objects describing any conflicts found
    """
    conflicts = []
    
    # Sort patches by offset for efficient comparison
    sorted_patches = sorted(patches, key=lambda p: p.offset)
    
    for i, patch1 in enumerate(sorted_patches):
        for patch2 in sorted_patches[i + 1:]:
            # Skip patches from the same file
            if patch1.source_file == patch2.source_file:
                continue
            
            # Check for same offset
            if patch1.offset == patch2.offset:
                conflicts.append(PatchConflict(
                    patch1=patch1,
                    patch2=patch2,
                    conflict_type="same_offset"
                ))
            # Check for overlap
            elif patch1.offset < patch2.offset < patch1.end_offset:
                conflicts.append(PatchConflict(
                    patch1=patch1,
                    patch2=patch2,
                    conflict_type="overlap"
                ))
            # Early exit if patch2 is beyond patch1's range
            elif patch2.offset >= patch1.end_offset:
                break
    
    return conflicts


def validate_patches(patches: List[HexPatch], exe_size: int) -> List[str]:
    """
    Validate patches against target file size.
    
    Args:
        patches: List of patches to validate
        exe_size: Size of target executable in bytes
        
    Returns:
        List of error messages (empty if all valid)
    """
    errors = []
    
    for patch in patches:
        if patch.offset < 0:
            errors.append(f"{patch.source_file}: Negative offset 0x{patch.offset:X}")
        elif patch.offset >= exe_size:
            errors.append(f"{patch.source_file}: Offset 0x{patch.offset:X} exceeds file size")
        elif patch.end_offset > exe_size:
            errors.append(f"{patch.source_file}: Patch at 0x{patch.offset:X} extends beyond file end")
    
    return errors


def apply_patches(exe_path: str, patches: List[HexPatch], 
                  output_path: str = None, 
                  backup: bool = True) -> Tuple[int, List[str]]:
    """
    Apply a list of patches to an executable file.
    
    Args:
        exe_path: Path to the source executable
        patches: List of HexPatch objects to apply
        output_path: Output path (defaults to overwriting original if None,
                    or creates *_patched.exe if backup=True)
        backup: Whether to create a backup of the original
        
    Returns:
        Tuple of (patches_applied_count, list_of_error_messages)
    """
    if not os.path.exists(exe_path):
        return 0, [f"Executable not found: {exe_path}"]
    
    if not patches:
        return 0, ["No patches to apply"]
    
    errors = []
    
    # Read original file
    with open(exe_path, 'rb') as f:
        exe_data = bytearray(f.read())
    
    exe_size = len(exe_data)
    
    # Validate patches
    validation_errors = validate_patches(patches, exe_size)
    if validation_errors:
        return 0, validation_errors
    
    # Detect conflicts (warning only, still apply)
    conflicts = detect_conflicts(patches)
    for conflict in conflicts:
        errors.append(f"Warning: {conflict}")
    
    # Sort patches by offset for consistent application order
    sorted_patches = sorted(patches, key=lambda p: p.offset)
    
    # Apply patches
    applied = 0
    for patch in sorted_patches:
        try:
            exe_data[patch.offset:patch.offset + patch.size] = patch.data
            applied += 1
        except Exception as e:
            errors.append(f"Failed to apply patch from {patch.source_file}: {e}")
    
    # Determine output path
    if output_path is None:
        if backup:
            # Create backup
            backup_path = exe_path + ".backup"
            if not os.path.exists(backup_path):
                shutil.copy2(exe_path, backup_path)
            output_path = exe_path
        else:
            base, ext = os.path.splitext(exe_path)
            output_path = f"{base}_patched{ext}"
    
    # Write output
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(exe_data)
    
    return applied, errors


def create_hex_patch(offset: int, data: bytes, output_path: str) -> None:
    """
    Create a .hex patch file from raw data.
    
    Args:
        offset: Target offset in executable
        data: Patch data bytes
        output_path: Path to write the .hex file
    """
    with open(output_path, 'wb') as f:
        # Write offset (big-endian int64)
        f.write(offset.to_bytes(8, byteorder='big'))
        # Write size (big-endian int64)
        f.write(len(data).to_bytes(8, byteorder='big'))
        # Write data
        f.write(data)


def find_hex_files(directory: str, recursive: bool = True) -> List[str]:
    """
    Find all .hex files in a directory.
    
    Args:
        directory: Directory to search
        recursive: Whether to search subdirectories
        
    Returns:
        List of paths to .hex files found
    """
    hex_files = []
    
    if recursive:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.lower().endswith('.hex'):
                    hex_files.append(os.path.join(root, file))
    else:
        for file in os.listdir(directory):
            if file.lower().endswith('.hex'):
                hex_files.append(os.path.join(directory, file))
    
    return sorted(hex_files)


def get_patch_summary(patches: List[HexPatch]) -> Dict[str, any]:
    """
    Generate a summary of patch statistics.
    
    Args:
        patches: List of patches to summarize
        
    Returns:
        Dictionary with summary statistics
    """
    if not patches:
        return {
            "total_patches": 0,
            "total_bytes": 0,
            "source_files": 0,
            "offset_range": (0, 0),
        }
    
    source_files = set(p.source_file for p in patches)
    offsets = [p.offset for p in patches]
    total_bytes = sum(p.size for p in patches)
    
    return {
        "total_patches": len(patches),
        "total_bytes": total_bytes,
        "source_files": len(source_files),
        "offset_range": (min(offsets), max(offsets)),
        "files": list(source_files),
    }

