import struct
import binascii
from pathlib import Path

def extract_decompression_code(exe_path: str, offset: int = 0x522f61, size: int = 1024):
    """Extract potential decompression routine from executable"""
    with open(exe_path, 'rb') as f:
        f.seek(offset)
        code = f.read(size)
        
    print("\nDecompression Code Analysis:")
    print("First 64 bytes:")
    for i in range(0, min(64, len(code)), 16):
        chunk = code[i:i+16]
        hex_str = " ".join(f"{b:02x}" for b in chunk)
        ascii_str = "".join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        print(f"{i:04x}: {hex_str:48} {ascii_str}")
        
    # Look for function boundaries
    function_start = code.find(b"\x55\x48\x89\xe5")  # push rbp; mov rbp, rsp
    function_end = code.find(b"\xc3", function_start)  # ret
    
    if function_start >= 0 and function_end > function_start:
        print(f"\nFound function boundaries: 0x{function_start:x} to 0x{function_end:x}")
        print("Function code:")
        print(binascii.hexlify(code[function_start:function_end]).decode())
        
    # Look for LZ77 related constants
    constants = {
        'window_size': [b'\x00\x10\x00\x00', b'\x00\x20\x00\x00', b'\x00\x40\x00\x00'],
        'magic': b'LZ77',
        'masks': [b'\x0F\x00', b'\x1F\x00', b'\x3F\x00', b'\x7F\x00', b'\xFF\x00']
    }
    
    print("\nInteresting constants found:")
    for const_type, patterns in constants.items():
        if isinstance(patterns, bytes):
            patterns = [patterns]
        for pattern in patterns:
            pos = code.find(pattern)
            if pos >= 0:
                print(f"{const_type}: at offset 0x{pos:x} - {binascii.hexlify(pattern).decode()}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extract decompression code from Dokapon executable')
    parser.add_argument('exe', type=Path, help='Path to the executable')
    parser.add_argument('--offset', type=lambda x: int(x,0), default=0x522f61, 
                      help='Offset to extract from (default: 0x522f61)')
    parser.add_argument('--size', type=int, default=1024,
                      help='Number of bytes to extract (default: 1024)')
    
    args = parser.parse_args()
    
    if not args.exe.exists():
        print(f"Error: File not found: {args.exe}")
        return
        
    extract_decompression_code(args.exe, args.offset, args.size)

if __name__ == '__main__':
    main() 