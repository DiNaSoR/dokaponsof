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
import wave

# Get the directory where the script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the full path to the .pck file
pck_file_path = os.path.join(script_dir, 'Voice-en.pck')

def raw_to_wav(raw_data, wav_path, sample_rate=22050, channels=1, sample_width=2):
    """Convert raw PCM data to WAV format"""
    with wave.open(wav_path, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_data)

def analyze_voice_data(pck_path):
    with open(pck_path, 'rb') as file:
        # Skip header
        header = file.read(16)
        if not header.startswith(b'Filename'):
            raise ValueError("Invalid file format - missing 'Filename' header")
        
        # Skip to voice data start
        file.seek(0x5B0)
        
        # Read first voice file header/data
        voice_data = file.read(64)  # Read first 64 bytes to analyze format
        
        print("First 64 bytes of voice data:")
        print("Hex:", ' '.join(f'{b:02X}' for b in voice_data))
        print("\nPossible format indicators:")
        print("First 4 bytes:", ' '.join(f'{b:02X}' for b in voice_data[:4]))
        print("Magic number/ID:", ''.join(chr(b) if 32 <= b <= 126 else '.' for b in voice_data[:4]))
        
        # Try to detect potential audio format markers
        if voice_data.startswith(b'RIFF'):
            print("Appears to be WAV format")
        elif voice_data.startswith(b'OggS'):
            print("Appears to be OGG format")
        else:
            print("Custom or proprietary format")

def extract_voices(pck_path):
    with open(pck_path, 'rb') as file:
        # Verify "Filename" header
        header = file.read(16)
        if not header.startswith(b'Filename'):
            raise ValueError("Invalid file format - missing 'Filename' header")
        
        # Create output directory
        output_dir = os.path.join(script_dir, 'extracted_voices')
        os.makedirs(output_dir, exist_ok=True)
        
        # Read until we find the first .voice filename
        while True:
            if file.read(1).decode('ascii', errors='ignore') == 'V':
                file.seek(file.tell() - 1)
                break
        
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
                voice_data = file.read(32768)  # Read a reasonable chunk
                
                # Save as WAV
                wav_name = filename.replace('.voice', '.wav')
                wav_path = os.path.join(output_dir, wav_name)
                raw_to_wav(voice_data, wav_path)
                
                print(f"Extracted {filename} as WAV")
                
            except Exception as e:
                print(f"Error extracting {filename}: {str(e)}")

try:
    analyze_voice_data(pck_file_path)
    extract_voices(pck_file_path)
    print("\nExtraction complete!")
    print("\nNote: If the WAV files don't sound correct, try modifying these settings in raw_to_wav():")
    print("- Current sample_rate: 22050 Hz (try 11025 or 44100)")
    print("- Current sample_width: 2 (16-bit) (try 1 for 8-bit)")
    print("- Current channels: 1 (mono)")
except FileNotFoundError:
    print(f"Error: Could not find file at {pck_file_path}")
except Exception as e:
    print(f"Error: {str(e)}")
