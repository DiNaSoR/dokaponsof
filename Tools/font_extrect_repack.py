# This script extracts and repacks PNG font files from .fnt format
# Author: q8fft2
# Purpose: Font file extractor and repacker for DOKAPON! Sword of Fury (PC Version)
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
# Usage: Place this script in the same directory as your .fnt files

import argparse

PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'
PNG_IEND = b'IEND\xaeB`\x82'

def extract_png_from_fnt(fnt_path, output_png_path):
    with open(fnt_path, 'rb') as fnt_file:
        fnt_data = fnt_file.read()

    start_index = fnt_data.find(PNG_SIGNATURE)
    end_index = fnt_data.find(PNG_IEND, start_index) + len(PNG_IEND)

    if start_index != -1 and end_index != -1:
        png_data = fnt_data[start_index:end_index]
        with open(output_png_path, 'wb') as png_file:
            png_file.write(png_data)
        print(f"Successfully extracted PNG and saved as '{output_png_path}'.")
    else:
        print("No embedded PNG data found in the .fnt file.")

def import_png_to_fnt(original_fnt_path, modified_png_path, output_fnt_path):
    with open(original_fnt_path, 'rb') as fnt_file:
        fnt_data = fnt_file.read()

    start_index = fnt_data.find(PNG_SIGNATURE)
    end_index = fnt_data.find(PNG_IEND, start_index) + len(PNG_IEND)

    if start_index != -1 and end_index != -1:
        with open(modified_png_path, 'rb') as png_file:
            new_png_data = png_file.read()

        # Adjust size to match the original PNG size
        original_size = end_index - start_index
        new_size = len(new_png_data)

        if new_size < original_size:
            # Add padding to match the original size
            padding_size = original_size - new_size
            new_png_data += b'\x00' * padding_size
        elif new_size > original_size:
            # Warn if the new data is larger
            print("Warning: The new PNG data is larger than the original. Truncating to match the original size.")
            new_png_data = new_png_data[:original_size]

        # Replace the old PNG data with the new one
        new_fnt_data = fnt_data[:start_index] + new_png_data + fnt_data[end_index:]

        with open(output_fnt_path, 'wb') as output_file:
            output_file.write(new_fnt_data)

        print(f"Successfully imported modified PNG into '{output_fnt_path}'.")
    else:
        print("No embedded PNG data found in the original .fnt file.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract or import PNG from/to a .fnt file.")
    parser.add_argument("operation", choices=["extract", "import"], help="Operation to perform: 'extract' or 'import'.")
    parser.add_argument("fnt_file", help="Path to the .fnt file.")
    parser.add_argument("image_file", help="Path to the PNG file (for extraction or import).")
    parser.add_argument("--output_fnt", help="Path for the output .fnt file (required for 'import' operation).")

    args = parser.parse_args()

    if args.operation == "extract":
        extract_png_from_fnt(args.fnt_file, args.image_file)
    elif args.operation == "import":
        if not args.output_fnt:
            print("Please specify the output .fnt file path using '--output_fnt' when performing 'import'.")
        else:
            import_png_to_fnt(args.fnt_file, args.image_file, args.output_fnt)
