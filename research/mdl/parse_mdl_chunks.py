#!/usr/bin/env python3
"""Parse MDL chunk structure based on EXE analysis"""
import struct
import sys

# Block type names based on table mappings
BLOCK_TYPES = {
    0: "Position",
    1: "Normal",
    2: "Index",
    3: "UV",
    4: "Color",
    5: "Weight",
    6: "Bone",
    7: "Unknown7",
    8: "Transform",
    9: "Animation",
    10: "Material",
    11: "Texture",
}

def parse_chunk_header(data, offset):
    """Parse 0x18 byte chunk header"""
    if offset + 0x18 > len(data):
        return None
    
    chunk = data[offset:offset+0x18]
    
    primary_type = chunk[0]
    sub_type = chunk[1]
    byte2 = chunk[2]
    obj_class = chunk[3]
    size = struct.unpack("<I", chunk[4:8])[0]
    field8 = struct.unpack("<I", chunk[8:12])[0]
    count = struct.unpack("<I", chunk[12:16])[0]
    data_ptr = struct.unpack("<Q", chunk[16:24])[0]
    
    return {
        'offset': offset,
        'primary_type': primary_type,
        'sub_type': sub_type,
        'byte2': byte2,
        'obj_class': obj_class,
        'size': size,
        'field8': field8,
        'count': count,
        'data_ptr': data_ptr,
        'type_name': BLOCK_TYPES.get(primary_type, f"Type{primary_type}")
    }

def find_chunks(data):
    """Find chunk structures in decompressed MDL data"""
    chunks = []
    
    # Look for chunk-like patterns
    for i in range(0, len(data) - 0x18, 4):
        chunk = parse_chunk_header(data, i)
        if chunk is None:
            continue
        
        # Validate chunk looks reasonable
        if chunk['primary_type'] <= 15:  # Valid type range
            if 0 < chunk['size'] < len(data):  # Valid size
                if 0 < chunk['count'] < 100000:  # Valid count
                    if chunk['data_ptr'] == 0 or chunk['data_ptr'] < len(data):
                        chunks.append(chunk)
    
    return chunks

def analyze_decompressed_mdl(filename):
    """Analyze decompressed MDL file"""
    with open(filename, 'rb') as f:
        data = f.read()
    
    print(f"File size: {len(data)} bytes")
    print("\n=== SCANNING FOR CHUNK HEADERS ===")
    
    chunks = find_chunks(data)
    
    # Group by type
    type_groups = {}
    for chunk in chunks:
        t = chunk['primary_type']
        if t not in type_groups:
            type_groups[t] = []
        type_groups[t].append(chunk)
    
    print(f"\nFound {len(chunks)} potential chunks")
    
    for type_id in sorted(type_groups.keys()):
        group = type_groups[type_id]
        type_name = BLOCK_TYPES.get(type_id, f"Type{type_id}")
        print(f"\n{type_name} (type {type_id}): {len(group)} chunks")
        
        for chunk in group[:5]:  # Show first 5
            print(f"  Offset 0x{chunk['offset']:06x}: size={chunk['size']}, count={chunk['count']}, ptr=0x{chunk['data_ptr']:x}")
    
    # Look for specific patterns that indicate geometry data
    print("\n\n=== LOOKING FOR GEOMETRY PATTERNS ===")
    
    # Find float arrays that look like vertex data
    for i in range(0, len(data) - 48, 4):
        # Check for sequence of reasonable floats
        try:
            floats = struct.unpack("<12f", data[i:i+48])
            # Check for varied, reasonable values
            varied = len(set(floats)) > 6
            reasonable = all(-1000 < f < 1000 for f in floats)
            non_zero = sum(1 for f in floats if abs(f) > 0.01) > 6
            
            if varied and reasonable and non_zero:
                # Check if continues
                count = 4
                for j in range(12, 100):
                    off = i + j*4
                    if off + 4 > len(data):
                        break
                    f = struct.unpack("<f", data[off:off+4])[0]
                    if -1000 < f < 1000:
                        count += 1
                    else:
                        break
                
                if count >= 20:
                    print(f"\nFloat array at 0x{i:06x} ({count} floats):")
                    for k in range(min(4, count//3)):
                        x, y, z = struct.unpack("<3f", data[i+k*12:i+k*12+12])
                        print(f"  [{k}]: ({x:10.4f}, {y:10.4f}, {z:10.4f})")
                    i += count * 4  # Skip ahead
                    continue
        except:
            pass

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_mdl_chunks.py decompressed.bin")
        sys.exit(1)
    
    analyze_decompressed_mdl(sys.argv[1])

