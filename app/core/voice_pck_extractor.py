# This script extracts voice files from .pck format
# Author: DiNaSoR [Kunio Discord]
# Purpose: Voice file extractor for DOKAPON! Sword of Fury (PC Version)
# License: Free to use and modify
#
# IMPORTANT:
# - This script is intended to help with game modding
# - Please support the developers by purchasing DOKAPON! Sword of Fury on Steam
# - Do not pirate the game - buy it to support the creators!
#
# Community Links:
# - Discord: discord.gg/wXhAEvhTuR
# - Reddit: reddit.com/r/dokaponofficial/
#
# Usage: Place this script in the same directory as 'Voice-en.pck'

import os

def find_opus_header(data):
    """Find the start of an Opus stream by looking for 'OggS' marker"""
    return data.find(b'OggS')

def extract_voices(pck_path, output_dir=None):
    """
    Extract voice files from a PCK file.
    
    Args:
        pck_path: Path to the PCK file to extract
        output_dir: Optional output directory. If not provided, extracts to 
                    'extracted_voices' folder in the same directory as the PCK file.
    """
    if not os.path.exists(pck_path):
        raise FileNotFoundError(f"Could not find file at {pck_path}")

    # Use provided output_dir or default to extracted_voices in pck directory
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(pck_path), "extracted_voices")
    os.makedirs(output_dir, exist_ok=True)

    with open(pck_path, 'rb') as file:
        # Verify "Filename" header
        header = file.read(16)
        if not header.startswith(b'Filename'):
            raise ValueError("Invalid file format - missing 'Filename' header")
        
        # Read filenames
        filenames = []
        current_name = ''
        while True:
            char = file.read(1).decode('ascii', errors='ignore')
            if char == 'P':  # Check for "Pack" end marker
                next_chars = file.read(3).decode('ascii', errors='ignore')
                if next_chars == 'ack':
                    break
                file.seek(file.tell() - 3)
            
            if char == '\0':
                if current_name.endswith('.voice'):
                    filenames.append(current_name)
                current_name = ''
            else:
                current_name += char
        
        print(f"Found {len(filenames)} voice files")
        
        # Extract each voice file
        file.seek(0x5B0)  # Start of voice data
        for i, filename in enumerate(filenames):
            try:
                # Read a chunk of data
                voice_data = file.read(32768)  # 32KB chunk
                opus_start = find_opus_header(voice_data)
                
                if opus_start >= 0:
                    # Found Opus data, seek back to start of Opus stream
                    file.seek(file.tell() - len(voice_data) + opus_start)
                    
                    # Read until next file's Opus header or end of file
                    opus_data = bytearray()
                    while True:
                        chunk = file.read(4096)
                        if not chunk:
                            break
                        
                        next_opus = find_opus_header(chunk)
                        if next_opus > 0 and len(opus_data) > 0:
                            # Found next Opus stream, keep only up to this point
                            opus_data.extend(chunk[:next_opus])
                            file.seek(file.tell() - len(chunk) + next_opus)
                            break
                        
                        opus_data.extend(chunk)
                    
                    # Save as .opus file
                    opus_name = filename.replace('.voice', '.opus')
                    opus_path = os.path.join(output_dir, opus_name)
                    with open(opus_path, 'wb') as out_file:
                        out_file.write(opus_data)
                    
                    print(f"Extracted {opus_name}")
                else:
                    print(f"Warning: No Opus data found in {filename}")
                
            except Exception as e:
                print(f"Error extracting {filename}: {str(e)}")
