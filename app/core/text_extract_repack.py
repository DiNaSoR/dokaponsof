"""
Text Extractor and Repacker for DOKAPON! Sword of Fury
Extracts and repacks text strings from the game executable.

Author: DiNaSoR (improved from q8fft2's original)
License: Free to use and modify

Text Format:
- Text blocks start with \p (5C 70)
- Control codes: \k (wait), \r (modifier), \h (header), \n (newline in text)
- Color codes: %0c-%10c
- Position codes: %0x, %0y etc.
- Text blocks end with \k, multiple nulls, or next \p

Usage:
    Extract: python script.py extract --exe game.exe --texts output.txt --offsets offsets.txt
    Import:  python script.py import --exe game.exe --texts modified.txt --offsets offsets.txt --output_exe new_game.exe
"""

import re
import os
import argparse
from typing import List, Tuple, Optional


def find_text_end(content: bytes, start: int) -> int:
    """
    Find the end of a text block starting at 'start'.
    
    Text blocks end at:
    1. \k (5C 6B) - wait for key
    2. \z (5C 7A) - unknown terminator
    3. Two or more consecutive null bytes
    4. Next \p (5C 70) - start of new text block
    """
    pos = start + 2  # Skip initial \p
    
    while pos < len(content):
        byte = content[pos]
        
        # Check for \k or \z
        if byte == 0x5C and pos + 1 < len(content):
            next_byte = content[pos + 1]
            if next_byte == 0x6B:  # \k
                return pos + 2  # Include \k in the text
            elif next_byte == 0x7A:  # \z
                return pos + 2  # Include \z in the text
            elif next_byte == 0x70:  # Next \p - don't include
                return pos
        
        # Check for null bytes (end of text entry)
        if byte == 0x00:
            # Count consecutive nulls
            null_count = 0
            temp_pos = pos
            while temp_pos < len(content) and content[temp_pos] == 0x00:
                null_count += 1
                temp_pos += 1
            
            if null_count >= 1:
                return pos  # End at first null
        
        pos += 1
    
    return len(content)


def extract_texts(exe_file_path: str, output_file_path: str, offsets_file_path: str) -> int:
    """
    Extract all text strings from the executable.
    
    Args:
        exe_file_path: Path to the game executable
        output_file_path: Path for extracted texts
        offsets_file_path: Path for text offsets and lengths
        
    Returns:
        Number of texts extracted
    """
    with open(exe_file_path, "rb") as f:
        content = f.read()
    
    # Find all \p markers
    pattern = rb'\\p'
    
    extracted_texts = []
    offsets_data = []  # (offset, length) pairs
    
    for match in re.finditer(pattern, content):
        start = match.start()
        end = find_text_end(content, start)
        
        # Extract the raw bytes
        text_bytes = content[start:end]
        
        # Try to decode as UTF-8
        try:
            text = text_bytes.decode('utf-8')
            
            # Skip very short entries (likely not real text)
            if len(text) < 3:
                continue
            
            # Skip entries that are mostly non-printable
            printable_ratio = sum(1 for c in text if c.isprintable() or c in '\n\r\t') / len(text)
            if printable_ratio < 0.5:
                continue
            
            extracted_texts.append(text)
            offsets_data.append((start, len(text_bytes)))
            
        except UnicodeDecodeError:
            # Skip non-UTF-8 entries
            continue
    
    # Save texts (one per line, preserving embedded \n as literal)
    os.makedirs(os.path.dirname(output_file_path) or '.', exist_ok=True)
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for text in extracted_texts:
            # Replace actual newlines with a placeholder for single-line storage
            # The text already contains \n as literal backslash-n, so no issue
            f.write(text + '\n')
    
    # Save offsets with lengths (offset:length format)
    with open(offsets_file_path, 'w', encoding='utf-8') as f:
        for offset, length in offsets_data:
            f.write(f"{offset}:{length}\n")
    
    print(f"Extracted {len(extracted_texts)} text entries")
    print(f"Texts saved to: {output_file_path}")
    print(f"Offsets saved to: {offsets_file_path}")
    
    return len(extracted_texts)


def import_texts(original_exe_path: str, modified_texts_path: str, 
                 offsets_file_path: str, output_exe_path: str) -> Tuple[int, int]:
    """
    Import modified texts back into the executable.
    
    Args:
        original_exe_path: Path to original executable
        modified_texts_path: Path to modified texts file
        offsets_file_path: Path to offsets file
        output_exe_path: Path for output executable
        
    Returns:
        Tuple of (texts_replaced, texts_skipped)
    """
    # Read original executable
    with open(original_exe_path, 'rb') as f:
        content = bytearray(f.read())
    
    # Read modified texts
    with open(modified_texts_path, 'r', encoding='utf-8') as f:
        modified_texts = f.readlines()
    
    # Read offsets and lengths
    with open(offsets_file_path, 'r', encoding='utf-8') as f:
        offsets_data = []
        for line in f:
            line = line.strip()
            if ':' in line:
                offset, length = line.split(':', 1)
                offsets_data.append((int(offset), int(length)))
            else:
                # Legacy format: just offset (need to detect length)
                offsets_data.append((int(line), None))
    
    replaced = 0
    skipped = 0
    
    for i, (offset_data, new_text) in enumerate(zip(offsets_data, modified_texts)):
        offset, original_length = offset_data
        new_text = new_text.rstrip('\n')  # Remove trailing newline from file
        
        # If we don't have original length, calculate it
        if original_length is None:
            # Find original text end
            original_length = find_text_end(content, offset) - offset
        
        # Encode new text
        new_bytes = new_text.encode('utf-8')
        
        # Check if new text fits
        if len(new_bytes) > original_length:
            print(f"Warning: Text at offset {offset} is too long ({len(new_bytes)} > {original_length}). Truncating...")
            new_bytes = new_bytes[:original_length]
            skipped += 1
        
        # Pad with nulls if shorter
        if len(new_bytes) < original_length:
            new_bytes = new_bytes + b'\x00' * (original_length - len(new_bytes))
        
        # Replace in content
        content[offset:offset + original_length] = new_bytes
        replaced += 1
    
    # Write output
    os.makedirs(os.path.dirname(output_exe_path) or '.', exist_ok=True)
    with open(output_exe_path, 'wb') as f:
        f.write(content)
    
    print(f"Replaced {replaced} texts ({skipped} truncated)")
    print(f"Modified executable saved to: {output_exe_path}")
    
    return replaced, skipped


def extract_with_context(exe_file_path: str, output_file_path: str, 
                        context_bytes: int = 50) -> int:
    """
    Extract texts with surrounding context for analysis.
    Useful for understanding text structure.
    """
    with open(exe_file_path, 'rb') as f:
        content = f.read()
    
    pattern = rb'\\p'
    
    with open(output_file_path, 'w', encoding='utf-8') as out:
        count = 0
        for match in re.finditer(pattern, content):
            start = max(0, match.start() - context_bytes)
            end_pos = find_text_end(content, match.start())
            end = min(len(content), end_pos + context_bytes)
            
            try:
                before = content[start:match.start()].decode('utf-8', errors='replace')
                text = content[match.start():end_pos].decode('utf-8', errors='replace')
                after = content[end_pos:end].decode('utf-8', errors='replace')
                
                out.write(f"=== Offset: 0x{match.start():08X} ===\n")
                out.write(f"Before: {repr(before)}\n")
                out.write(f"Text: {repr(text)}\n")
                out.write(f"After: {repr(after)}\n")
                out.write(f"Length: {end_pos - match.start()}\n\n")
                count += 1
            except:
                continue
    
    print(f"Extracted {count} texts with context to: {output_file_path}")
    return count


def analyze_text_patterns(exe_file_path: str) -> dict:
    """
    Analyze text patterns in the executable.
    Returns statistics about control codes used.
    """
    with open(exe_file_path, 'rb') as f:
        content = f.read()
    
    stats = {
        'total_texts': 0,
        'with_k': 0,  # \k endings
        'with_r': 0,  # \r modifier
        'with_h': 0,  # \h modifier  
        'with_colors': 0,  # %Nc codes
        'with_positions': 0,  # %Nx/%Ny codes
        'with_variables': 0,  # %s, %d
        'avg_length': 0,
        'min_length': float('inf'),
        'max_length': 0,
    }
    
    pattern = rb'\\p'
    lengths = []
    
    for match in re.finditer(pattern, content):
        start = match.start()
        end = find_text_end(content, start)
        text_bytes = content[start:end]
        
        try:
            text = text_bytes.decode('utf-8')
            if len(text) < 3:
                continue
            
            stats['total_texts'] += 1
            lengths.append(len(text))
            
            if '\\k' in text:
                stats['with_k'] += 1
            if '\\r' in text:
                stats['with_r'] += 1
            if '\\h' in text:
                stats['with_h'] += 1
            if re.search(r'%\d+c', text):
                stats['with_colors'] += 1
            if re.search(r'%\d+[xy]', text):
                stats['with_positions'] += 1
            if '%s' in text or '%d' in text:
                stats['with_variables'] += 1
                
        except:
            continue
    
    if lengths:
        stats['avg_length'] = sum(lengths) / len(lengths)
        stats['min_length'] = min(lengths)
        stats['max_length'] = max(lengths)
    
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract or import texts in DOKAPON! Sword of Fury executable.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Extract texts:
    python text_extract_repack.py extract --exe "DOKAPON! Sword of Fury.exe" --texts texts.txt --offsets offsets.txt
  
  Import modified texts:
    python text_extract_repack.py import --exe "DOKAPON! Sword of Fury.exe" --texts modified.txt --offsets offsets.txt --output_exe modded.exe
  
  Analyze text patterns:
    python text_extract_repack.py analyze --exe "DOKAPON! Sword of Fury.exe"
"""
    )
    
    parser.add_argument("mode", choices=["extract", "import", "analyze", "context"],
                       help="Operation mode")
    parser.add_argument("--exe", required=True, 
                       help="Path to the executable file")
    parser.add_argument("--texts", 
                       help="Path to texts file (output for extract, input for import)")
    parser.add_argument("--offsets", 
                       help="Path to offsets file")
    parser.add_argument("--output_exe", 
                       help="Path for modified executable (import mode)")
    
    args = parser.parse_args()
    
    if args.mode == "extract":
        if not args.texts or not args.offsets:
            parser.error("extract mode requires --texts and --offsets")
        extract_texts(args.exe, args.texts, args.offsets)
        
    elif args.mode == "import":
        if not args.texts or not args.offsets or not args.output_exe:
            parser.error("import mode requires --texts, --offsets, and --output_exe")
        import_texts(args.exe, args.texts, args.offsets, args.output_exe)
        
    elif args.mode == "analyze":
        stats = analyze_text_patterns(args.exe)
        print("\n=== Text Pattern Analysis ===")
        print(f"Total text entries: {stats['total_texts']}")
        print(f"With \\k (wait): {stats['with_k']}")
        print(f"With \\r modifier: {stats['with_r']}")
        print(f"With \\h modifier: {stats['with_h']}")
        print(f"With color codes: {stats['with_colors']}")
        print(f"With position codes: {stats['with_positions']}")
        print(f"With variables (%s/%d): {stats['with_variables']}")
        print(f"Length: min={stats['min_length']}, avg={stats['avg_length']:.1f}, max={stats['max_length']}")
        
    elif args.mode == "context":
        if not args.texts:
            parser.error("context mode requires --texts for output")
        extract_with_context(args.exe, args.texts)
