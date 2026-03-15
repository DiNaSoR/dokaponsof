#!/usr/bin/env python3
"""
Clean Control Codes from DOKAPON! Sword of Fury Text Files
Removes all control codes and formatting, leaving only readable text.

Usage:
    python clean_text.py                           # Uses default input/output
    python clean_text.py input.txt output.txt      # Custom files
    python clean_text.py --preview                 # Show preview only
"""

import re
import sys
import argparse


def clean_text(text: str) -> str:
    """
    Remove all Dokapon control codes from text.
    
    Control codes removed:
    - \p, \k, \r, \h, \z, \m (control markers)
    - \n (converted to actual newline or space)
    - \, (comma formatting)
    - %0c - %10c (color codes)
    - %0x - %99x, %0y - %99y (position codes)
    - %s, %d, %3d, %8s (variable placeholders)
    - %517M, %518M (button codes)
    """
    cleaned = text
    
    # Remove start/end markers: \p, \k, \z
    cleaned = re.sub(r'\\[pkz]', '', cleaned)
    
    # Remove modifiers: \r, \h, \m
    cleaned = re.sub(r'\\[rhm]', '', cleaned)
    
    # Convert \n to space (or newline if you prefer)
    cleaned = cleaned.replace('\\n', ' ')
    
    # Remove comma formatting: \,
    cleaned = cleaned.replace('\\,', ',')
    
    # Remove color codes: %0c, %1c, %10c, etc.
    cleaned = re.sub(r'%\d+c', '', cleaned)
    
    # Remove position codes: %0x, %16x, %0y, %2y, etc.
    cleaned = re.sub(r'%\d+[xy]', '', cleaned)
    
    # Remove button codes: %517M, %518M, etc.
    cleaned = re.sub(r'%\d+M', '[BTN]', cleaned)
    
    # Replace variable placeholders with readable markers
    cleaned = re.sub(r'%(\d*)s', '[TEXT]', cleaned)
    cleaned = re.sub(r'%(\d*)d', '[NUM]', cleaned)
    
    # Clean up multiple spaces
    cleaned = re.sub(r'  +', ' ', cleaned)
    
    # Strip whitespace
    cleaned = cleaned.strip()
    
    return cleaned


def clean_text_minimal(text: str) -> str:
    """
    Minimal cleaning - only removes codes, preserves structure.
    Keeps \n as actual newlines.
    """
    cleaned = text
    
    # Remove markers but keep structure
    cleaned = re.sub(r'\\[pkzrhm]', '', cleaned)
    
    # Convert \n to actual newline
    cleaned = cleaned.replace('\\n', '\n')
    
    # Remove \,
    cleaned = cleaned.replace('\\,', ',')
    
    # Remove formatting codes
    cleaned = re.sub(r'%\d+[cxy]', '', cleaned)
    cleaned = re.sub(r'%\d+M', '🎮', cleaned)
    cleaned = re.sub(r'%\d*[sd]', '___', cleaned)
    
    return cleaned.strip()


def process_file(input_path: str, output_path: str, minimal: bool = False):
    """Process a text file and clean all entries."""
    
    print(f"Reading: {input_path}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Processing {len(lines)} entries...")
    
    clean_func = clean_text_minimal if minimal else clean_text
    cleaned_lines = []
    
    for line in lines:
        cleaned = clean_func(line.rstrip('\n'))
        cleaned_lines.append(cleaned)
    
    # Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        for line in cleaned_lines:
            f.write(line + '\n')
    
    print(f"Saved to: {output_path}")
    print(f"Total entries: {len(cleaned_lines)}")
    
    # Stats
    non_empty = sum(1 for line in cleaned_lines if line)
    print(f"Non-empty entries: {non_empty}")


def preview(input_path: str, count: int = 20, minimal: bool = False):
    """Preview cleaned text without saving."""
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    clean_func = clean_text_minimal if minimal else clean_text
    
    print("=" * 60)
    print("PREVIEW (showing first {} entries)".format(count))
    print("=" * 60)
    
    for i, line in enumerate(lines[:count]):
        original = line.rstrip('\n')
        cleaned = clean_func(original)
        
        print(f"\n--- Entry {i+1} ---")
        print(f"Original: {original[:100]}{'...' if len(original) > 100 else ''}")
        print(f"Cleaned:  {cleaned[:100]}{'...' if len(cleaned) > 100 else ''}")
    
    print("\n" + "=" * 60)


def create_translation_csv(input_path: str, output_path: str):
    """
    Create a CSV file for translation with original and cleaned text.
    Format: index,offset,original,cleaned,translation
    """
    import csv
    
    # Try to load offsets if available
    offset_path = input_path.replace('extracted_texts', 'text_offsets')
    offsets = []
    try:
        with open(offset_path, 'r', encoding='utf-8') as f:
            offsets = [line.strip().split(':')[0] for line in f.readlines()]
    except:
        pass
    
    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    print(f"Creating translation CSV: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Index', 'Offset', 'Original', 'Cleaned', 'Translation'])
        
        for i, line in enumerate(lines):
            original = line.rstrip('\n')
            cleaned = clean_text(original)
            offset = offsets[i] if i < len(offsets) else ''
            
            # Skip empty entries
            if not cleaned:
                continue
            
            writer.writerow([i + 1, offset, original, cleaned, ''])
    
    print(f"Created CSV with {len(lines)} entries")


def main():
    parser = argparse.ArgumentParser(
        description='Clean control codes from Dokapon text files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clean_text.py                              # Default: extracted_texts.txt -> cleaned_texts.txt
  python clean_text.py input.txt output.txt         # Custom input/output
  python clean_text.py --preview                    # Preview first 20 entries
  python clean_text.py --preview -n 50              # Preview first 50 entries
  python clean_text.py --minimal                    # Preserve newlines as actual newlines
  python clean_text.py --csv                        # Create translation CSV
"""
    )
    
    parser.add_argument('input', nargs='?', default='extracted_texts.txt',
                       help='Input text file (default: extracted_texts.txt)')
    parser.add_argument('output', nargs='?', default=None,
                       help='Output text file (default: cleaned_<input>)')
    parser.add_argument('--preview', '-p', action='store_true',
                       help='Preview mode - show cleaned text without saving')
    parser.add_argument('-n', type=int, default=20,
                       help='Number of entries to preview (default: 20)')
    parser.add_argument('--minimal', '-m', action='store_true',
                       help='Minimal cleaning - preserve newlines')
    parser.add_argument('--csv', action='store_true',
                       help='Create translation CSV file')
    
    args = parser.parse_args()
    
    # Set default output
    if args.output is None:
        if args.csv:
            args.output = args.input.replace('.txt', '_translation.csv')
        else:
            args.output = 'cleaned_' + args.input
    
    if args.preview:
        preview(args.input, args.n, args.minimal)
    elif args.csv:
        create_translation_csv(args.input, args.output)
    else:
        process_file(args.input, args.output, args.minimal)


if __name__ == '__main__':
    main()

