"""
PCK File Handler for DOKAPON! Sword of Fury
Supports reading and writing PCK sound archive files.

Based on the PCK format documentation from NewDoc:
- Filename Section: 0x14 header + section_size + offset_array + name_strings + padding
- Pack Section: 0x14 header + section_size + file_count + (offset, size)[] + audio_data

Author: DiNaSoR
License: Free to use and modify
"""

import os
import struct
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class Sound:
    """Represents a single sound file within a PCK archive."""
    name: str
    data: bytes
    loop_start: int = 0  # Opus LoopStart metadata (sample position)
    loop_end: int = 0    # Opus LoopEnd metadata (sample position)
    
    @classmethod
    def from_file(cls, file_path: str, loop_start: int = 0, loop_end: int = 0) -> 'Sound':
        """Create a Sound from an external file."""
        name = os.path.basename(file_path)
        with open(file_path, 'rb') as f:
            data = f.read()
        return cls(name=name, data=data, loop_start=loop_start, loop_end=loop_end)
    
    def write(self, output_dir: str) -> str:
        """Write the sound data to a file."""
        output_path = os.path.join(output_dir, self.name)
        os.makedirs(output_dir, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(self.data)
        return output_path
    
    @property
    def size(self) -> int:
        """Return the size of the sound data in bytes."""
        return len(self.data)
    
    def is_opus(self) -> bool:
        """Check if this sound is in Opus/OGG format."""
        return self.data.startswith(b'OggS')


class PCKFile:
    """
    Handler for PCK sound archive files.
    
    PCK File Structure:
    - Filename Section:
        - 0x14 bytes: "Filename" padded with spaces
        - 4 bytes: section size (little-endian int32)
        - N * 4 bytes: offset array pointing to filenames
        - Variable: null-terminated filename strings
        - Padding: align to 8 bytes
    - Pack Section:
        - 0x14 bytes: "Pack" padded with spaces  
        - 4 bytes: section size (little-endian int32)
        - 4 bytes: file count (little-endian int32)
        - N * 8 bytes: (offset, size) pairs for each sound
        - 4 bytes: padding
        - Variable: sound data (each aligned to 16 bytes)
    """
    
    HEADER_SIZE = 0x14  # 20 bytes
    FILENAME_HEADER = b'Filename            '  # Padded to 20 bytes
    PACK_HEADER = b'Pack                '      # Padded to 20 bytes
    
    def __init__(self, file_path: str = None):
        """
        Initialize a PCK file handler.
        
        Args:
            file_path: Optional path to an existing PCK file to parse.
                      If None, creates an empty PCK for building.
        """
        self.sounds: List[Sound] = []
        self.source_path: Optional[str] = file_path
        
        if file_path:
            self._parse(file_path)
    
    def _parse(self, file_path: str) -> None:
        """Parse an existing PCK file."""
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Verify Filename header
        if not data[:8].startswith(b'Filename'):
            raise ValueError(f"Invalid PCK file: missing 'Filename' header")
        
        # Read Filename section size
        filename_section_size = struct.unpack('<I', data[self.HEADER_SIZE:self.HEADER_SIZE + 4])[0]
        
        # Calculate sound count from first offset
        # First offset tells us how many offsets there are (offset / 4 = count)
        first_offset = struct.unpack('<I', data[self.HEADER_SIZE + 4:self.HEADER_SIZE + 8])[0]
        sound_count = first_offset // 4
        
        # Read all filename offsets
        filename_offsets = []
        offset_base = self.HEADER_SIZE + 4  # After header and size
        for i in range(sound_count):
            offset = struct.unpack('<I', data[offset_base + i * 4:offset_base + i * 4 + 4])[0]
            filename_offsets.append(offset)
        
        # Read filenames
        sound_names = []
        for offset in filename_offsets:
            name_start = offset_base + offset
            name_end = data.find(b'\x00', name_start)
            name = data[name_start:name_end].decode('ascii', errors='replace')
            sound_names.append(name)
        
        # Find Pack section (aligned to 8 bytes after Filename section)
        pack_offset = filename_section_size
        if pack_offset % 8 != 0:
            pack_offset += 8 - (pack_offset % 8)
        
        # Verify Pack header
        if not data[pack_offset:pack_offset + 4].startswith(b'Pack'):
            raise ValueError(f"Invalid PCK file: missing 'Pack' header at offset {pack_offset}")
        
        # Read Pack section info
        pack_section_size = struct.unpack('<I', data[pack_offset + self.HEADER_SIZE:pack_offset + self.HEADER_SIZE + 4])[0]
        pack_file_count = struct.unpack('<I', data[pack_offset + self.HEADER_SIZE + 4:pack_offset + self.HEADER_SIZE + 8])[0]
        
        # Read sound data info (offset, size pairs)
        info_base = pack_offset + self.HEADER_SIZE + 8
        for i in range(sound_count):
            sound_offset = struct.unpack('<I', data[info_base + i * 8:info_base + i * 8 + 4])[0]
            sound_size = struct.unpack('<I', data[info_base + i * 8 + 4:info_base + i * 8 + 8])[0]
            
            # Extract sound data
            sound_data = data[sound_offset:sound_offset + sound_size]
            
            # Create Sound object
            self.sounds.append(Sound(
                name=sound_names[i],
                data=sound_data
            ))
    
    def _format_header(self, name: str) -> bytes:
        """Format a section header (padded to 20 bytes with spaces)."""
        if len(name) > self.HEADER_SIZE:
            raise ValueError(f"Header name too long: {name}")
        return name.encode('ascii').ljust(self.HEADER_SIZE, b' ')
    
    def _align(self, size: int, alignment: int) -> int:
        """Calculate padding needed for alignment."""
        if size % alignment == 0:
            return 0
        return alignment - (size % alignment)
    
    def add_sound(self, sound: Sound) -> None:
        """Add a sound to the PCK file."""
        self.sounds.append(sound)
    
    def remove_sound(self, name: str) -> bool:
        """Remove a sound by name. Returns True if found and removed."""
        for i, sound in enumerate(self.sounds):
            if sound.name == name or os.path.splitext(sound.name)[0] == os.path.splitext(name)[0]:
                del self.sounds[i]
                return True
        return False
    
    def find_sound(self, name: str) -> Optional[Sound]:
        """Find a sound by name (with or without extension)."""
        name_base = os.path.splitext(name)[0]
        for sound in self.sounds:
            if sound.name == name or os.path.splitext(sound.name)[0] == name_base:
                return sound
        return None
    
    def replace_sound(self, name: str, new_sound: Sound) -> bool:
        """
        Replace a sound by name.
        
        Args:
            name: Name of sound to replace (with or without extension)
            new_sound: New Sound object to use as replacement
        
        Returns:
            True if sound was found and replaced, False otherwise
        """
        name_base = os.path.splitext(name)[0]
        for i, sound in enumerate(self.sounds):
            sound_base = os.path.splitext(sound.name)[0]
            if sound.name == name or sound_base == name_base:
                # Keep original name extension if new sound has different extension
                if os.path.splitext(new_sound.name)[1] != os.path.splitext(sound.name)[1]:
                    new_sound.name = name_base + os.path.splitext(sound.name)[1]
                self.sounds[i] = new_sound
                return True
        return False
    
    def write(self, output_path: str) -> None:
        """
        Write the PCK file to disk.
        
        Args:
            output_path: Path where the PCK file should be written
        """
        if not self.sounds:
            raise ValueError("Cannot write empty PCK file")
        
        # Build Filename section
        filename_section = bytearray()
        
        # Header
        filename_section.extend(self._format_header("Filename"))
        
        # Placeholder for section size (will fill later)
        size_offset = len(filename_section)
        filename_section.extend(b'\x00\x00\x00\x00')
        
        # Build name offset array and name data
        name_offsets = []
        name_data = bytearray()
        
        for sound in self.sounds:
            # Offset is relative to start of offset array
            name_offsets.append(len(name_data) + len(self.sounds) * 4)
            name_data.extend(sound.name.encode('ascii'))
            name_data.extend(b'\x00')  # Null terminator
        
        # Write offsets
        for offset in name_offsets:
            filename_section.extend(struct.pack('<I', offset))
        
        # Write name data
        filename_section.extend(name_data)
        
        # Update section size
        section_size = len(filename_section)
        struct.pack_into('<I', filename_section, size_offset, section_size)
        
        # Add padding for 8-byte alignment
        padding = self._align(len(filename_section), 8)
        filename_section.extend(b'\x00' * padding)
        
        # Build Pack section
        pack_section = bytearray()
        
        # Header
        pack_section.extend(self._format_header("Pack"))
        
        # Section size (will be: header + size + count + info_array + padding = 0x1C + count*8)
        pack_section_length = 0x1C + len(self.sounds) * 8
        pack_section.extend(struct.pack('<I', pack_section_length))
        
        # File count
        pack_section.extend(struct.pack('<I', len(self.sounds)))
        
        # Build sound data with 16-byte alignment
        sound_data = bytearray()
        sound_info = []  # (offset, size) pairs
        
        # Calculate base offset for sound data
        # It's: filename_section_length + pack_header(0x14) + size(4) + count(4) + info_array + padding(4)
        data_base_offset = len(filename_section) + pack_section_length + 4
        
        for sound in self.sounds:
            # Record offset and size
            sound_info.append((data_base_offset + len(sound_data), len(sound.data)))
            
            # Add sound data
            sound_data.extend(sound.data)
            
            # Add padding for 16-byte alignment
            padding = self._align(len(sound.data), 16)
            sound_data.extend(b'\x00' * padding)
        
        # Write sound info (offset, size pairs)
        for offset, size in sound_info:
            pack_section.extend(struct.pack('<I', offset))
            pack_section.extend(struct.pack('<I', size))
        
        # Add padding before data
        pack_section.extend(b'\x00\x00\x00\x00')
        
        # Add sound data
        pack_section.extend(sound_data)
        
        # Combine sections
        output_data = bytes(filename_section) + bytes(pack_section)
        
        # Final padding to 16-byte alignment
        padding = self._align(len(output_data), 16)
        output_data += b'\x00' * padding
        
        # Write to file
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(output_data)
    
    def extract_all(self, output_dir: str) -> List[str]:
        """
        Extract all sounds to a directory.
        
        Args:
            output_dir: Directory to extract sounds to
            
        Returns:
            List of paths to extracted files
        """
        extracted = []
        os.makedirs(output_dir, exist_ok=True)
        
        for sound in self.sounds:
            path = sound.write(output_dir)
            extracted.append(path)
        
        return extracted
    
    def get_sound_list(self) -> List[Tuple[str, int]]:
        """Get list of (name, size) tuples for all sounds."""
        return [(s.name, s.size) for s in self.sounds]
    
    def __len__(self) -> int:
        return len(self.sounds)
    
    def __iter__(self):
        return iter(self.sounds)
    
    def __getitem__(self, index: int) -> Sound:
        return self.sounds[index]


def extract_pck(pck_path: str, output_dir: str = None) -> List[str]:
    """
    Convenience function to extract all sounds from a PCK file.
    
    Args:
        pck_path: Path to the PCK file
        output_dir: Output directory (defaults to 'extracted_<pck_name>')
        
    Returns:
        List of paths to extracted files
    """
    if output_dir is None:
        base_name = os.path.splitext(os.path.basename(pck_path))[0]
        output_dir = os.path.join(os.path.dirname(pck_path), f"extracted_{base_name}")
    
    pck = PCKFile(pck_path)
    return pck.extract_all(output_dir)


def create_pck(sound_files: List[str], output_path: str) -> None:
    """
    Convenience function to create a new PCK file from sound files.
    
    Args:
        sound_files: List of paths to sound files
        output_path: Path for the output PCK file
    """
    pck = PCKFile()
    for file_path in sound_files:
        pck.add_sound(Sound.from_file(file_path))
    pck.write(output_path)

