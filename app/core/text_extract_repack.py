# This script extracts and repacks text from executable files
# Author: q8fft2
# Purpose: Text extractor and repacker for game executable files
# License: Free to use and modify
#
# IMPORTANT:
# - This script helps extract and repack text from executable files
# - Useful for game translation and modding
# - Please respect intellectual property rights
#
# Features:
# - Extracts text strings starting with \p
# - Preserves original text offsets
# - Supports UTF-8 encoding
# - Handles both extraction and repacking
#
# Usage: 
# Extract mode: python script.py extract --exe game.exe --texts output.txt --offsets offsets.txt
# Import mode: python script.py import --exe game.exe --texts modified.txt --offsets offsets.txt --output_exe new_game.exe

import re
import argparse

def extract_texts(exe_file_path, output_file_path, offsets_file_path):
    """
    Extracts texts and their offsets from an executable file.

    Parameters:
    exe_file_path (str): Path to the executable file.
    output_file_path (str): Path to save the extracted texts.
    offsets_file_path (str): Path to save the offsets of the texts.
    """
    with open(exe_file_path, "rb") as exe_file:
        content = exe_file.read()

    # Extract texts starting with \p and their surrounding context
    pattern = rb"\\p.*?(?=\\k|\\z|\x00|\n)"
    matches = re.finditer(pattern, content)

    extracted_texts = []
    offsets = []

    for match in matches:
        try:
            text = match.group(0).decode("utf-8").strip()
            extracted_texts.append(text)
            offsets.append(match.start())
        except UnicodeDecodeError:
            continue

    # Save extracted texts and offsets
    with open(output_file_path, "w", encoding="utf-8") as output_file:
        for text in extracted_texts:
            output_file.write(text + "\n")

    with open(offsets_file_path, "w") as offsets_file:
        offsets_file.write("\n".join(map(str, offsets)))

    print(f"Extracted texts saved to {output_file_path}")
    print(f"Offsets saved to {offsets_file_path}")


def import_texts(original_exe_path, modified_texts_path, offsets_file_path, output_exe_path):
    """
    Imports modified texts back into the executable file.

    Parameters:
    original_exe_path (str): Path to the original executable file.
    modified_texts_path (str): Path to the modified texts file.
    offsets_file_path (str): Path to the offsets file.
    output_exe_path (str): Path to save the modified executable file.
    """
    with open(original_exe_path, "rb") as exe_file:
        content = bytearray(exe_file.read())

    with open(modified_texts_path, "r", encoding="utf-8") as texts_file:
        modified_texts = texts_file.readlines()

    with open(offsets_file_path, "r") as offsets_file:
        offsets = list(map(int, offsets_file.readlines()))

    for offset, new_text in zip(offsets, modified_texts):
        new_text = new_text.strip().encode("utf-8")

        # Ensure new text fits in the allocated space
        original_length = len(content[offset:offset + len(new_text)])
        if len(new_text) > original_length:
            print(f"New text too long for offset {offset}. Skipping...")
            continue

        # Replace text at the specified offset
        content[offset:offset + original_length] = new_text.ljust(original_length, b'\x00')

    with open(output_exe_path, "wb") as output_file:
        output_file.write(content)

    print(f"Modified executable saved to {output_exe_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract or import texts in an executable file.")
    parser.add_argument("mode", choices=["extract", "import"], help="Mode of operation: extract or import.")
    parser.add_argument("--exe", required=True, help="Path to the executable file.")
    parser.add_argument("--texts", required=True, help="Path to the texts file (output for extract, input for import).")
    parser.add_argument("--offsets", required=True, help="Path to the offsets file (output for extract, input for import).")
    parser.add_argument("--output_exe", help="Path to save the modified executable file (for import mode only).")

    args = parser.parse_args()

    if args.mode == "extract":
        extract_texts(args.exe, args.texts, args.offsets)
    elif args.mode == "import":
        if not args.output_exe:
            print("Error: --output_exe is required for import mode.")
        else:
            import_texts(args.exe, args.texts, args.offsets, args.output_exe)
