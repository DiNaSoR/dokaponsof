# PNG Font File Extractor and Repacker
# Author: q8fft2
# Purpose: Extract and repack PNG files from .fnt and .spranm formats
# Game: DOKAPON! Sword of Fury (PC Version)
# License: MIT - Free to use and modify
#
# IMPORTANT NOTES:
# - This tool is for game modding purposes
# - Please purchase DOKAPON! Sword of Fury on Steam
# - Support the developers by buying the game legally
#
# Community:
# - Discord: discord.gg/wXhAEvhTuR
# - Reddit: reddit.com/r/dokaponofficial/
#
# Usage: Place this script in the directory containing your .fnt/.spranm files

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_IEND = b'IEND\xaeB`\x82'

def ensure_directory_exists(dir_path):
    """
    Create the directory if it doesn't already exist.
    """
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

def get_output_directory_for_extension(ext):
    """
    Decide which subdirectory to use based on the file extension.
    You can adjust these names as needed.
    """
    if ext == ".fnt":
        return "extracted_fnt"
    elif ext == ".spranm":
        return "extracted_spranm"
    else:
        return "extracted_other"

def extract_png(file_path, output_png_path):
    """
    Extract PNG data from a file (e.g., .fnt or .spranm).
    Also creates a JSON file that stores the offset and length
    of the embedded PNG for later reinsertion.
    """
    # Initialize LZ77 decompressor for SPRANM files
    decompressor = None
    if file_path.lower().endswith('.spranm'):
        import os
        import sys
        # Add the root directory to the Python path
        tools_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.dirname(tools_dir)  # Go up one level to root
        if root_dir not in sys.path:
            sys.path.append(root_dir)
        from lz77_decompressor import LZ77Decompressor
        decompressor = LZ77Decompressor(debug=False)

    with open(file_path, 'rb') as f:
        # For SPRANM files, decompress first
        if decompressor:
            try:
                data = decompressor.decompress_file(file_path)
            except Exception as e:
                print(f"[{file_path}] Failed to decompress SPRANM: {str(e)}")
                return
        else:
            data = f.read()

    start_index = data.find(PNG_SIGNATURE)
    if start_index == -1:
        print(f"[{file_path}] PNG signature not found.")
        return

    end_index = data.find(PNG_IEND, start_index)
    if end_index == -1:
        print(f"[{file_path}] PNG end marker not found.")
        return
    end_index += len(PNG_IEND)

    png_data = data[start_index:end_index]

    # Save the extracted PNG
    with open(output_png_path, 'wb') as png_file:
        png_file.write(png_data)

    print(f"[{file_path}] PNG extracted and saved to: {output_png_path}")

    # Create a JSON file to store offset and length info
    meta_info = {
        "original_file": os.path.abspath(file_path),
        "offset": start_index,
        "length": end_index - start_index
    }

    json_path = output_png_path + ".json"
    with open(json_path, 'w', encoding='utf-8') as json_file:
        json.dump(meta_info, json_file, ensure_ascii=False, indent=4)
    print(f"JSON metadata file created: {json_path}")


def import_png(json_path, modified_png_path, output_file_path):
    """
    Reinsert modified PNG data at the original offset in the file,
    based on JSON metadata (offset and length).
    """
    # Read offset and length from the JSON file
    try:
        with open(json_path, 'r', encoding='utf-8') as meta_file:
            meta_info = json.load(meta_file)
    except FileNotFoundError:
        print(f"JSON file not found: {json_path}")
        return
    except json.JSONDecodeError:
        print(f"Failed to decode JSON from: {json_path}")
        return

    original_file = meta_info.get("original_file")
    offset = meta_info.get("offset")
    length = meta_info.get("length")

    if not original_file or offset is None or length is None:
        print(f"Incomplete metadata in {json_path}.")
        return

    # Read the original file bytes
    try:
        with open(original_file, 'rb') as f:
            original_data = f.read()
    except FileNotFoundError:
        print(f"Original file not found: {original_file}")
        return

    # Read the new (modified) PNG data
    try:
        with open(modified_png_path, 'rb') as png_file:
            new_png_data = png_file.read()
    except FileNotFoundError:
        print(f"Modified PNG file not found: {modified_png_path}")
        return

    # Match the original allocated length
    if len(new_png_data) < length:
        # If smaller, pad with zeros
        padding_size = length - len(new_png_data)
        new_png_data += b'\x00' * padding_size
    elif len(new_png_data) > length:
        # If larger, truncate
        print("Warning: New PNG data is larger than the original space. It will be truncated.")
        new_png_data = new_png_data[:length]

    # Merge the new data into the original file bytes
    new_data = original_data[:offset] + new_png_data + original_data[offset + length:]

    # Save the resulting file
    with open(output_file_path, 'wb') as out_file:
        out_file.write(new_data)

    print(f"Modified PNG inserted into: {output_file_path}")


def prompt_for_files(extensions):
    """
    Prompt the user for a list of files (space-separated).
    If the user presses Enter without typing anything,
    automatically gather all matching files in the current directory.
    """
    print(f"Enter the file names (space-separated), or press Enter to scan for all {extensions} files in the current directory:")
    user_input = input(" > ").strip()

    if user_input:
        # If the user typed file names manually
        files = user_input.split()
        # Remove quotes if any
        files = [f.strip('"') for f in files]
    else:
        # Automatically find matching files in the current directory
        files = []
        for f in os.listdir('.'):
            if os.path.isfile(f):
                _, ext = os.path.splitext(f)
                if ext.lower() in extensions:
                    files.append(f)
    return files


def main_menu():
    while True:
        print("\n============================")
        print("          Main Menu         ")
        print("============================")
        print("1) Extract PNG from .fnt files only")
        print("2) Extract PNG from .spranm files only")
        print("3) Extract PNG from both .fnt and .spranm")
        print("4) Reinsert (import) PNG using a JSON metadata file")
        print("5) Exit the program")
        print("============================")

        choice = input("Please enter your choice: ").strip()

        if choice == "1":
            print("\n=== Extract PNG from .fnt files ===")
            files = prompt_for_files({".fnt"})
            for file_path in files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                _, ext = os.path.splitext(file_path)
                out_dir = get_output_directory_for_extension(ext.lower())  # "extracted_fnt"
                ensure_directory_exists(out_dir)
                out_png = os.path.join(out_dir, base_name + ".png")
                extract_png(file_path, out_png)

        elif choice == "2":
            print("\n=== Extract PNG from .spranm files ===")
            files = prompt_for_files({".spranm"})
            for file_path in files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                _, ext = os.path.splitext(file_path)
                out_dir = get_output_directory_for_extension(ext.lower())  # "extracted_spranm"
                ensure_directory_exists(out_dir)
                out_png = os.path.join(out_dir, base_name + ".png")
                extract_png(file_path, out_png)

        elif choice == "3":
            print("\n=== Extract PNG from both .fnt and .spranm files ===")
            files = prompt_for_files({".fnt", ".spranm"})
            for file_path in files:
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                _, ext = os.path.splitext(file_path)
                out_dir = get_output_directory_for_extension(ext.lower())
                ensure_directory_exists(out_dir)
                out_png = os.path.join(out_dir, base_name + ".png")
                extract_png(file_path, out_png)

        elif choice == "4":
            print("\n=== Reinsert (import) PNG using JSON metadata ===")
            json_path = input("Enter the path to the JSON file: ").strip('"')
            png_path = input("Enter the path to the modified PNG file: ").strip('"')

            # Attempt to derive a default output file name
            try:
                with open(json_path, 'r', encoding='utf-8') as jf:
                    meta_info = json.load(jf)
                original_file_name = os.path.basename(meta_info["original_file"])
                base_without_ext, orig_ext = os.path.splitext(original_file_name)
                default_output = base_without_ext + "_imported" + orig_ext
            except:
                default_output = "output_imported.fnt"

            user_out = input(f"Enter the output file path (or leave blank to use '{default_output}'): ").strip('"')
            if not user_out:
                user_out = default_output

            import_png(json_path, png_path, user_out)

        elif choice == "5":
            print("Exiting the program.")
            break
        else:
            print("Invalid choice, please try again.")


if __name__ == "__main__":
    main_menu()
