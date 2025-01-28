"""
LZ77 Decompressor
A specialized tool for decompressing LZ77-compressed data with advanced block handling and window management.

Created by: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
License: GNU General Public License v3.0 (GPL-3.0)

Features:
- Advanced LZ77 decompression with block-aware processing
- Intelligent window size management for different data types
- Support for multiple block types (vertex, normal, transform, etc.)
- Chain and sequence tracking for optimized decompression
- Detailed logging and debugging capabilities
- Robust error handling and validation

Usage: python lz77_decompressor.py [-h] [-i INPUT] [-o OUTPUT] [--debug] [--info]

Arguments:
  -h, --help     Show this help message and exit
  -i, --input    Input compressed file
  -o, --output   Output decompressed file
  --debug        Enable debug logging
  --info         Show file information without decompressing

Examples:
  # Basic decompression
  python lz77_decompressor.py input.bin output.bin

  # Decompression with debug logging
  python lz77_decompressor.py input.bin output.bin --debug

  # Show file information
  python lz77_decompressor.py input.bin --info

Block Type Support:
- Vertex data (32KB window)
- Normal vectors (12KB window) 
- Index data (4KB window)
- Transform matrices (16KB window)
- Float arrays (8KB window)
- Raw data (64KB window)

Note: This implementation includes specialized handling for geometry,
animation, and transform data with dynamic window size adjustment
and sequence-aware processing.
"""

import struct
from dataclasses import dataclass
from typing import BinaryIO, Optional, List, Tuple, Dict
import logging
from pathlib import Path

@dataclass
class LZ77Header:
    """LZ77 header structure"""
    def __init__(self, magic: bytes, size: int, flag1: int, flag2: int):
        self.magic = magic
        self.size = size
        self.flag1 = flag1
        self.flag2 = flag2
        
    def __str__(self) -> str:
        return f"LZ77Header(magic={self.magic}, size={self.size}, flag1=0x{self.flag1:08x}, flag2=0x{self.flag2:08x})"
        
    def __repr__(self) -> str:
        return self.__str__()

@dataclass
class MarkerInfo:
    type: str
    offset: int
    next_marker: Optional['MarkerInfo'] = None
    prev_marker: Optional['MarkerInfo'] = None
    related_marker: Optional['MarkerInfo'] = None
    window_size: int = 0
    data_start: int = 0
    data_end: int = 0
    circular_refs: List['MarkerInfo'] = None  # Track circular references
    ref_chain: List['MarkerInfo'] = None      # Track reference chain

    def __post_init__(self):
        self.circular_refs = []
        self.ref_chain = []

class LZ77Block:
    def __init__(self, offset: int, size: int, flags: int):
        self.offset = offset
        self.size = size
        self.flags = flags
        self.data = bytearray()

class LZ77Decompressor:
    def __init__(self, debug: bool = False):
        self.logger = logging.getLogger("LZ77Decompressor")
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
        # Add window_size initialization
        self.window_size = 65536  # Default window size
        
        # Window size constants from executable analysis
        self.WINDOW_SIZES = {
            # Core block types
            'vertex': 32768,      # 0x8000 - Geometry vertex data
            'normal': 12288,      # 0x3000 - Normal vectors
            'index': 4096,        # 0x1000 - Index data
            'frame': 8192,        # 0x2000 - Animation frames
            'float': 8192,        # 0x2000 - Float values (increased from 4096)
            'data': 65536,        # 0x10000 - Raw data
            'align': 65536,       # 0x10000 - Alignment blocks
            'structure': 65536,   # 0x10000 - Structure blocks
            
            # Additional geometry types
            'transform': 16384,   # 0x4000 - Transform matrices
            'tangent': 12288,     # 0x3000 - Tangent vectors
            'weight': 4096,       # 0x1000 - Weight values
            'scale': 8192,        # 0x2000 - Scale values
            'rotation': 12288,    # 0x3000 - Rotation data
            'position': 16384,    # 0x4000 - Position data
            
            # Control blocks
            'end': 4096,         # 0x1000 - End markers
            'header': 4096,      # 0x1000 - Header blocks
            'footer': 4096,      # 0x1000 - Footer blocks
            
            # Metadata blocks
            'metadata_start': 8192,   # 0x2000
            'metadata_block': 8192,   # 0x2000
            'metadata_end': 8192,     # 0x2000
            
            # Array types
            'float_array': 16384,     # 0x4000
            'vertex_array': 32768,    # 0x8000
            'normal_array': 12288,    # 0x3000
            
            # Extended types
            'header_ext': 4096,       # 0x1000
            'metadata_ext': 8192,     # 0x2000
            'block_start': 65536,     # 0x10000
            'block_end': 65536,       # 0x10000
            'chain_start': 16384,     # 0x4000
            'chain_end': 16384        # 0x4000
        }
        
        # Block alignment requirements
        self.BLOCK_ALIGNMENTS = {
            'vertex': 12,    # 3 floats per vertex
            'normal': 12,    # 3 floats per normal
            'index': 2,      # 2 bytes per index
            'frame': 52,     # Animation frame alignment (updated from debug analysis)
            'float': 4,      # Single float
            'data': 1,       # Raw data
            'transform': 16, # 4x4 matrix
            'tangent': 12,  # 3 floats
            'weight': 4,    # Single float
            'scale': 4,     # Single float (updated)
            'rotation': 16, # Quaternion
            'position': 12  # 3 floats
        }
        
        # Window size progression for dynamic sizing
        self.WINDOW_PROGRESSION = {
            'vertex': [4096, 8192, 16384, 32768],  # Progressive growth for vertex data
            'normal': [4096, 8192, 12288],         # Limited growth for normals
            'index': [2048, 4096],                 # Small window for indices
            'frame': [4096, 8192],                 # Animation frames
            'float': [2048, 4096],                 # Float values
            'data': [8192, 16384, 32768, 65536],   # Full range for raw data
            
            # Geometry progression
            'transform': [4096, 8192, 16384],
            'tangent': [4096, 8192, 12288],
            'weight': [2048, 4096],
            'scale': [4096, 8192],
            'rotation': [4096, 8192, 12288],
            'position': [4096, 8192, 16384],
            
            # Metadata progression
            'metadata_start': [4096, 8192],
            'metadata_block': [4096, 8192],
            'metadata_end': [4096, 8192],
            
            # Array progression
            'float_array': [8192, 16384],
            'vertex_array': [16384, 32768],
            'normal_array': [8192, 12288]
        }
        
        # Block type detection
        self.BLOCK_TYPE_MARKERS = {
            # Core block types
            b'\x00\x00\xc0\x00': 'vertex',
            b'\x00\x00\x40\xc1': 'normal',
            b'\x00\x00\x40\x00': 'index',
            b'\x00\x00\x80\xb9': 'frame',
            b'\x00\x00\x80\x3f': 'float',
            b'\xFF\xFF\xFF\xFF': 'data',
            b'\xAA\xAA\xAA\xAA': 'align',
            b'\x55\x55\x55\x55': 'structure',
            
            # Additional geometry markers
            b'\x00\x00\x80\xba': 'transform',
            b'\x00\x00\x40\xc2': 'tangent',
            b'\x00\x00\x00\x3f': 'weight',
            b'\x00\x00\x80\x3e': 'scale',
            b'\x00\x00\x40\x3f': 'rotation',
            b'\x00\x00\xc0\x3f': 'position',
            
            # Control markers
            b'\x00\x00\x00\x00': 'end',
            b'\xff\xff\xdf\xff': 'header',
            b'\xff\xff\xef\xff': 'footer',
            
            # Metadata markers with precise values
            b'\xff\xff\x00\x00': 'metadata_start',
            b'\xff\xff\x80\x00': 'metadata_block',
            b'\xff\xff\xc0\x00': 'metadata_end',
            
            # Additional data markers from E000/E002 analysis
            b'\x00\x00\x39\x01': 'float_array',
            b'\x00\x00\xa4\x00': 'vertex_array',
            b'\x00\x00\xb2\xbc': 'normal_array',
            b'\xff\xff\xe3\xff': 'header_ext',
            b'\xff\xff\x8f\xff': 'metadata_ext',
            b'\xff\xff\xfb\xfe': 'block_start',
            b'\xff\xff\xfd\xff': 'block_end',
            b'\xff\xff\xf7\xff': 'chain_start',
            b'\xff\xff\x7f\x8f': 'chain_end'
        }
        
        # Block chains and relationships
        self.BLOCK_CHAINS = {
            'model': ['structure', 'geometry', 'normal', 'index'],
            'animation': ['animation', 'float', 'data'],
            'transform': ['float', 'normal', 'geometry'],
            # Additional chains
            'skeleton': ['position', 'rotation', 'scale'],
            'mesh': ['vertex', 'normal', 'tangent', 'weight'],
            'material': ['texture', 'float', 'data'],
            'physics': ['vertex', 'index', 'transform'],
            # Metadata chains
            'header': ['header', 'metadata_start', 'metadata_block', 'metadata_end'],
            'metadata': ['metadata_start', 'metadata_block', 'metadata_end']
        }
        
        # Block sequences and patterns
        self.BLOCK_SEQUENCES = {
            'geometry': [
                # Core geometry sequences
                ('vertex', 'normal', 'index'),
                ('vertex', 'index', 'normal'),
                ('normal', 'vertex', 'index'),
                ('vertex', 'normal', 'tangent', 'index'),
                ('vertex', 'tangent', 'normal', 'index'),
                ('normal', 'tangent', 'vertex', 'index'),
                
                # Extended geometry sequences
                ('vertex_array', 'normal_array', 'index'),
                ('vertex', 'weight', 'normal', 'index'),
                ('vertex', 'normal', 'weight', 'index'),
                ('vertex', 'tangent', 'weight', 'index'),
                
                # Float-based geometry sequences
                ('float', 'normal', 'vertex'),
                ('float', 'vertex', 'normal'),
                ('float', 'tangent', 'normal')
            ],
            'animation': [
                # Core animation sequences
                ('frame', 'float', 'data'),
                ('float', 'frame', 'data'),
                ('position', 'rotation', 'scale', 'frame'),
                ('rotation', 'position', 'scale', 'frame'),
                ('frame', 'position', 'rotation', 'scale'),
                
                # Extended animation sequences
                ('frame', 'float_array', 'data'),
                ('position', 'rotation', 'scale', 'float_array'),
                ('frame', 'transform', 'data'),
                
                # Float-based animation sequences
                ('float', 'position', 'rotation'),
                ('float', 'rotation', 'scale'),
                ('float', 'transform', 'frame')
            ],
            'transform': [
                # Core transform sequences
                ('transform', 'position', 'rotation'),
                ('position', 'rotation', 'transform'),
                ('rotation', 'position', 'transform'),
                
                # Extended transform sequences
                ('transform', 'scale', 'position'),
                ('position', 'scale', 'rotation'),
                ('transform', 'position', 'scale'),
                
                # Float-based transform sequences
                ('float', 'transform', 'position'),
                ('float', 'position', 'rotation'),
                ('float', 'rotation', 'scale')
            ]
        }
        
        # Block relationships for window preservation
        self.BLOCK_RELATIONSHIPS = {
            # Core relationships
            'vertex': ['normal', 'tangent', 'weight', 'index', 'float'],
            'normal': ['vertex', 'tangent', 'weight', 'float'],
            'index': ['vertex', 'normal', 'float'],
            'frame': ['float', 'position', 'rotation', 'scale'],
            'float': ['frame', 'data', 'normal', 'vertex', 'position', 'rotation', 'scale', 'transform'],
            
            # Geometry relationships
            'vertex_array': ['normal_array', 'index', 'float'],
            'normal_array': ['vertex_array', 'index', 'float'],
            'tangent': ['normal', 'vertex', 'float'],
            'weight': ['vertex', 'normal', 'float'],
            
            # Transform relationships
            'transform': ['position', 'rotation', 'scale', 'float'],
            'position': ['rotation', 'scale', 'transform', 'float'],
            'rotation': ['position', 'scale', 'transform', 'float'],
            'scale': ['position', 'rotation', 'transform', 'float']
        }
        
        # Chain state tracking
        self.chain_states = {
            'current_chain': None,
            'chain_position': 0,
            'chain_windows': {},
            'block_count': {}
        }
        
        # Initialize state
        self.window_buffer = bytearray(65536)  # Max window size
        self.window_pos = 0
        self.last_byte = 0
        self.total_output = 0
        self.current_block_type = None
        self.current_window_size = 65536
        self.current_alignment = 1
        
        # Initialize flags
        self.flags = 0
        self.flag2 = 0
        
        # Add block sequence tracking
        self.block_sequence = []
        self.current_sequence = []
        
        # Add block state tracking
        self.block_states = {}
        
        # Add chain tracking
        self.chain_history = []
        
        # Chain dependencies
        self.CHAIN_DEPENDENCIES = {
            'vertex': ['normal', 'index'],
            'normal': ['vertex', 'float'],
            'index': ['vertex'],
            'frame': ['float'],
            'float': ['normal', 'frame']
        }
        
        # Initialize sequence tracking
        self.current_sequence = []
        self.sequence_history = []
        self.block_dependencies = {}
    
    def get_block_type(self, marker: bytes) -> str:
        """Get block type from marker"""
        if marker in self.BLOCK_TYPE_MARKERS:
            return self.BLOCK_TYPE_MARKERS[marker]
        return 'data'  # Default to raw data
    
    def get_chain_for_block(self, block_type: str) -> tuple[str, list[str]]:
        """Find which chain a block belongs to"""
        for chain_name, chain in self.BLOCK_CHAINS.items():
            if block_type in chain:
                return chain_name, chain
        return None, []
    
    def setup_window(self, block_type: str) -> int:
        """Setup window size based on block type and flags with improved handling"""
        # Get base window size
        base_size = self.WINDOW_SIZES.get(block_type, 65536)
        
        # Get block count for this type
        count = self.chain_states['block_count'].get(block_type, 0)
        
        # Special handling for float sequences
        if block_type == 'float':
            if self.chain_states['current_chain'] == 'animation':
                base_size = 8192  # Larger window for animation floats
            elif count > 0 and count % 3 == 0:
                base_size = 12288  # Increase window for vector components
            elif count > 0 and count % 4 == 0:
                base_size = 16384  # Increase window for matrix components
        
        # Handle special flag combinations
        if self.flags & 0x8000:  # High bit set - use special window handling
            if block_type in ('vertex', 'vertex_array'):
                if count == 0:
                    base_size = 8192
                elif count == 1:
                    base_size = 16384
                else:
                    base_size = 32768
            elif block_type in ('normal', 'normal_array', 'tangent'):
                base_size = 12288
            elif block_type == 'index':
                base_size = 4096
            elif block_type == 'float':
                if count > 0 and count % 3 == 0:
                    base_size = max(base_size, 12288)  # Ensure sufficient space for vector data
        
        # Handle chain-specific adjustments
        chain_name = self.chain_states['current_chain']
        if chain_name:
            position = self.chain_states['chain_position']
            if position > 0:
                if chain_name == 'geometry':
                    # Use more granular window sizes for geometry chains
                    if block_type == 'vertex':
                        base_size = min(base_size, 16384)  # Cap vertex windows
                    elif block_type in ('normal', 'tangent'):
                        base_size = min(base_size, 12288)  # Cap normal/tangent windows
                    elif block_type == 'index':
                        base_size = min(base_size, 8192)   # Cap index windows
                elif chain_name == 'animation':
                    # Handle animation chain windows
                    if block_type == 'frame':
                        base_size = min(base_size, 8192)   # Cap frame windows
                    elif block_type in ('position', 'rotation', 'scale'):
                        base_size = min(base_size, 4096)   # Small windows for transform data
                elif chain_name == 'metadata':
                    # Use consistent sizes for metadata chains
                    base_size = 8192
        
        # Handle block relationships
        if block_type in self.block_dependencies:
            dep_type = self.block_dependencies[block_type]
            if dep_type in self.block_states:
                dep_state = self.block_states[dep_type]
                # Use at least the same size as dependent block
                base_size = max(base_size, dep_state['size'])
        
        # Handle sequence-specific adjustments
        for seq in self.sequence_history[-3:]:  # Look at recent sequences
            seq_type, pattern = seq
            if block_type in pattern:
                if seq_type == 'geometry':
                    # Ensure geometry sequences have sufficient windows
                    base_size = max(base_size, 16384)
                elif seq_type == 'animation':
                    # Keep animation data in smaller windows
                    base_size = min(base_size, 8192)
                elif seq_type == 'transform':
                    # Use consistent size for transform data
                    base_size = 16384
        
        return min(base_size, 65536)  # Cap at max window size
    
    def adjust_offset(self, offset: int, block_type: str) -> int:
        """Adjust offset based on block type and alignment with improved handling"""
        # Get alignment requirement
        alignment = self.BLOCK_ALIGNMENTS.get(block_type, 1)
        
        # Special handling for float sequences
        if block_type == 'float':
            chain_name = self.chain_states['current_chain']
            if chain_name == 'animation':
                # Use animation-specific alignment
                alignment = 52  # Match frame alignment
            elif self.current_sequence and len(self.current_sequence) >= 2:
                prev_type = self.current_sequence[-2]
                if prev_type in ('position', 'normal', 'tangent'):
                    alignment = 12  # Vector alignment
                elif prev_type in ('transform', 'rotation'):
                    alignment = 16  # Matrix/quaternion alignment
        
        if alignment > 1:
            # Align offset to data type
            offset = (offset // alignment) * alignment
        
        # Handle window boundaries with improved logic
        if offset > self.current_window_size:
            if block_type in ('vertex', 'vertex_array'):
                # Use progressive window reduction for vertex data
                if offset > 5000:  # Large vertex block
                    offset = offset % (self.current_window_size // 4)  # Quarter window
                else:
                    offset = offset % (self.current_window_size // 2)  # Half window
            elif block_type in ('normal', 'normal_array', 'tangent'):
                # Use half window for normal/tangent data
                offset = offset % (self.current_window_size // 2)
            elif block_type == 'index':
                # Keep indices in smaller window
                offset = offset % min(4096, self.current_window_size)
            elif block_type in ('position', 'rotation', 'scale'):
                # Use quarter window for transform data
                offset = offset % (self.current_window_size // 4)
            elif block_type.startswith('metadata'):
                # Use consistent window for metadata
                offset = offset % 8192
            else:
                offset = offset % self.current_window_size
        
        # Handle geometry block size ranges
        if block_type in ('vertex', 'normal', 'index', 'vertex_array', 'normal_array'):
            # Check if we're in a geometry sequence
            if self.chain_states['current_chain'] == 'geometry':
                chain_pos = self.chain_states['chain_position']
                if chain_pos > 0:
                    # Adjust window based on sequence position
                    if 65 <= offset <= 7500:  # Within observed geometry block range
                        # Use more precise window for geometry data
                        if offset <= 1000:
                            window_div = 8  # Small blocks
                        elif offset <= 3000:
                            window_div = 4  # Medium blocks
                        else:
                            window_div = 2  # Large blocks
                        offset = offset % (self.current_window_size // window_div)
        
        return offset
    
    def update_chain_state(self, block_type: str):
        """Update chain state with improved sequence handling"""
        # Find chain for block
        chain_name, chain = self.get_chain_for_block(block_type)
        
        # Track sequence with improved float handling
        self.current_sequence.append(block_type)
        if len(self.current_sequence) >= 3:
            # Check if sequence matches a pattern
            for seq_type, patterns in self.BLOCK_SEQUENCES.items():
                if tuple(self.current_sequence[-3:]) in patterns:
                    self.sequence_history.append((seq_type, self.current_sequence[-3:]))
                    # Special handling for float sequences
                    if 'float' in self.current_sequence[-3:]:
                        float_pos = self.current_sequence[-3:].index('float')
                        if float_pos > 0:
                            # Preserve previous block's window for float data
                            prev_type = self.current_sequence[-3:][float_pos - 1]
                            if prev_type in self.block_states:
                                state = self.block_states[prev_type]
                                self.chain_states['chain_windows']['float'] = (
                                    bytes(state['buffer'][:state['pos']]),
                                    state['pos']
                                )
                    # Preserve windows for sequence
                    for b_type in self.current_sequence[-3:]:
                        if b_type not in self.block_states:
                            continue
                        state = self.block_states[b_type]
                        self.chain_states['chain_windows'][b_type] = (
                            bytes(state['buffer'][:state['pos']]),
                            state['pos']
                        )
            self.current_sequence = self.current_sequence[-3:]
        
        # Handle chain transition
        if chain_name != self.chain_states['current_chain']:
            # Save current window state if in a chain
            if self.chain_states['current_chain']:
                self.chain_states['chain_windows'][self.chain_states['current_chain']] = (
                    bytes(self.window_buffer[:self.window_pos]),
                    self.window_pos
                )
            
            # Load new chain state or initialize
            if chain_name and chain_name in self.chain_states['chain_windows']:
                buffer, pos = self.chain_states['chain_windows'][chain_name]
                self.window_buffer[:pos] = buffer
                self.window_pos = pos
            else:
                # Reset state but preserve flags and dependencies
                flags = self.flags
                flag2 = self.flag2
                deps = self.block_dependencies.copy()
                self.reset_state()
                self.flags = flags
                self.flag2 = flag2
                self.block_dependencies = deps
            
            self.chain_states['current_chain'] = chain_name
            self.chain_states['chain_position'] = chain.index(block_type) if chain else 0
        
        # Update block count
        self.chain_states['block_count'][block_type] = (
            self.chain_states['block_count'].get(block_type, 0) + 1
        )
        
        # Track dependencies
        if block_type in self.CHAIN_DEPENDENCIES:
            for dep_type in self.CHAIN_DEPENDENCIES[block_type]:
                if dep_type in self.block_states:
                    self.block_dependencies[block_type] = dep_type
        
        # Update window size with sequence awareness
        count = self.chain_states['block_count'][block_type]
        progression = self.WINDOW_PROGRESSION.get(block_type, [65536])
        if count < len(progression):
            self.current_window_size = progression[count]
        else:
            self.current_window_size = progression[-1]
        
        # Adjust for dependencies
        if block_type in self.block_dependencies:
            dep_type = self.block_dependencies[block_type]
            if dep_type in self.block_states:
                dep_state = self.block_states[dep_type]
                self.current_window_size = max(self.current_window_size, dep_state['size'])
        
        self.current_alignment = self.BLOCK_ALIGNMENTS.get(block_type, 1)
    
    def handle_block_sequence(self, block_type: str, data: bytes = None) -> None:
        """Handle block sequences and transitions"""
        # Core sequences
        GEOMETRY_SEQUENCES = [
            ('normal', 'vertex', 'index'),
            ('normal', 'tangent', 'vertex', 'index'),
            ('float', 'normal', 'vertex'),
            ('float', 'vertex', 'normal'),
            ('float', 'tangent', 'normal')
        ]
        
        ANIMATION_SEQUENCES = [
            ('float', 'frame', 'data'),
            ('float', 'position', 'rotation'),
            ('float', 'rotation', 'scale'),
            ('float', 'transform', 'frame')
        ]
        
        TRANSFORM_SEQUENCES = [
            ('float', 'transform', 'position'),
            ('float', 'position', 'rotation'),
            ('float', 'rotation', 'scale'),
            ('transform', 'position', 'rotation'),
            ('transform', 'scale', 'position'),
            ('transform', 'position', 'scale')
        ]
        
        # Check for sequence start
        for sequence in GEOMETRY_SEQUENCES:
            if block_type == sequence[0]:
                self.logger.debug(f"Starting sequence geometry: {sequence}")
                self.current_sequence = sequence
                self.sequence_position = 0
                return
                
        for sequence in ANIMATION_SEQUENCES:
            if block_type == sequence[0]:
                self.logger.debug(f"Starting sequence animation: {sequence}")
                self.current_sequence = sequence
                self.sequence_position = 0
                return
                
        for sequence in TRANSFORM_SEQUENCES:
            if block_type == sequence[0]:
                self.logger.debug(f"Starting sequence transform: {sequence}")
                self.current_sequence = sequence
                self.sequence_position = 0
                return
                
        # Check for sequence continuation
        if self.current_sequence:
            next_position = self.sequence_position + 1
            if next_position < len(self.current_sequence):
                expected_type = self.current_sequence[next_position]
                if block_type == expected_type:
                    self.logger.debug(f"Continuing sequence {self.current_sequence} at position {next_position}")
                    self.sequence_position = next_position
                    return
                    
        # Handle sequence restart
        if self.current_sequence:
            if block_type == self.current_sequence[0]:
                self.logger.debug(f"Restarting sequence {self.current_sequence}")
                self.sequence_position = 0
                return
                
        # No valid sequence found
        self.current_sequence = None
        self.sequence_position = 0
    
    def handle_block_marker(self, marker: bytes, pos: int, data: bytes = None) -> int:
        """Handle block marker and update state"""
        block_type = None
        
        # Convert marker to bytes if needed
        if isinstance(marker, str):
            marker = marker.encode('utf-8')
            
        # Check for block type markers
        for type_name, markers in self.BLOCK_TYPE_MARKERS.items():
            # Convert each marker to bytes for comparison
            byte_markers = [m.encode('utf-8') if isinstance(m, str) else m for m in markers]
            if marker in byte_markers:
                block_type = type_name
                break
                
        if block_type:
            self.logger.debug(f"Found block type: {block_type} at {hex(pos)}")
            
            # Handle metadata block sizes
            if data and block_type in ('header', 'metadata_start', 'metadata_block', 'metadata_end'):
                # Look ahead for block size
                if pos + 8 <= len(data):
                    size_marker = data[pos+4:pos+8]
                    block_size = struct.unpack('<I', size_marker)[0]
                    
                    # Validate against known ranges
                    if block_type == 'header':
                        if 1 <= block_size <= 3000:  # Cover both E000 and E002 ranges
                            self.window_size = min(4096, block_size * 2)
                    elif block_type.startswith('metadata'):
                        if 17 <= block_size <= 3400:  # Cover both E000 and E002 ranges
                            self.window_size = min(8192, block_size * 2)
                    
                    self.logger.debug(f"Metadata block size: {block_size}")
            
            # Update sequence tracking
            self.handle_block_sequence(block_type, data)
            
            # Set up window parameters
            self.setup_window(block_type)
            
            # Handle alignment blocks
            if block_type in ('align', 'structure'):
                current_pos = pos + 4
                padding = (16 - (current_pos % 16)) % 16
                return padding
            
            # Update block marker info
            self.logger.debug(f"Block marker: {block_type} at {hex(pos)}")
            
            return len(marker)
            
        return 0
    
    def get_window_byte(self, offset: int) -> int:
        """Get byte from window with improved state handling"""
        # Handle alignment
        if self.current_alignment > 1:
            offset = (offset // self.current_alignment) * self.current_alignment
        
        # Handle special flag combinations
        if self.flags & 0x8000:  # High bit set - use special window handling
            if self.current_block_type in ('vertex', 'normal', 'tangent'):
                # Use half window size for vertex data
                offset = offset % (self.current_window_size // 2)
            elif self.current_block_type in ('position', 'rotation', 'scale'):
                # Use quarter window size for transform data
                offset = offset % (self.current_window_size // 4)
        
        # Handle flag2 special cases
        if self.flag2 & 0x4000:  # Bit 14 set - use chain windows
            chain_name = self.chain_states['current_chain']
            if chain_name and chain_name in self.chain_states['chain_windows']:
                buffer, pos = self.chain_states['chain_windows'][chain_name]
                if offset <= pos:
                    window_pos = pos - offset
                    if window_pos >= 0 and window_pos < len(buffer):
                        return buffer[window_pos]
        
        # Try block state with improved handling
        if self.current_block_type in self.block_states:
            state = self.block_states[self.current_block_type]
            if offset <= state['size']:
                window_pos = state['pos'] - offset
                if window_pos >= 0 and window_pos < len(state['buffer']):
                    # Handle block-specific transformations
                    byte = state['buffer'][window_pos]
                    if self.current_block_type == 'float':
                        # Handle float data specially
                        if self.flags & 0x4000:  # Bit 14 set - negate float
                            byte ^= 0x80  # Flip sign bit
                    elif self.current_block_type in ('normal', 'tangent'):
                        # Handle normalized vectors
                        if self.flags & 0x2000:  # Bit 13 set - normalize
                            byte = (byte + 128) & 0xFF  # Center around zero
                    return byte
        
        # Try current window with improved boundary handling
        if offset <= self.window_pos:
            window_pos = self.window_pos - offset
            if window_pos >= 0 and window_pos < len(self.window_buffer):
                byte = self.window_buffer[window_pos]
                # Apply any final transformations
                if self.flags & 0x1000:  # Bit 12 set - byte transformation
                    byte = ((byte << 1) | (byte >> 7)) & 0xFF  # Rotate left
                return byte
        
        return self.last_byte
    
    def update_window(self, byte: int):
        """Update window buffer with improved state handling"""
        # Handle alignment with block-specific rules
        if self.current_block_type in ('vertex', 'normal', 'tangent', 'position', 'rotation', 'scale'):
            # Ensure proper alignment for vector/matrix data
            aligned_pos = (self.window_pos // self.current_alignment) * self.current_alignment
            for i in range(self.current_alignment):
                pos = (aligned_pos + i) % self.current_window_size
                if i == self.window_pos % self.current_alignment:
                    self.window_buffer[pos] = byte
                else:
                    # Preserve existing aligned data
                    self.window_buffer[pos] = self.window_buffer[pos]
            self.window_pos = (aligned_pos + self.current_alignment) % self.current_window_size
        else:
            # Standard update for other types
            self.window_buffer[self.window_pos % self.current_window_size] = byte
            self.window_pos = (self.window_pos + 1) % self.current_window_size
        
        self.last_byte = byte
        
        # Update block state with improved handling
        if self.current_block_type:
            if self.current_block_type not in self.block_states:
                self.block_states[self.current_block_type] = {
                    'buffer': bytearray(self.current_window_size),
                    'pos': 0,
                    'size': self.current_window_size,
                    'alignment': self.current_alignment,
                    'chain': self.chain_states['current_chain']
                }
            state = self.block_states[self.current_block_type]
            
            # Update with alignment
            aligned_pos = (state['pos'] // state['alignment']) * state['alignment']
            state['buffer'][aligned_pos % state['size']] = byte
            state['pos'] = (aligned_pos + 1) % state['size']
            
            # Handle chain relationships
            if state['chain'] and state['chain'] in self.chain_states['chain_windows']:
                chain_buffer, chain_pos = self.chain_states['chain_windows'][state['chain']]
                if chain_pos < len(chain_buffer):
                    chain_buffer[chain_pos] = byte
                    self.chain_states['chain_windows'][state['chain']] = (chain_buffer, chain_pos + 1)

    def handle_data_block(self, data: bytes = None) -> None:
        """Handle data block type"""
        self.window_size = 4096  # Use self.window_size instead of local window_size
        self.alignment = 4
        
        # Check if we're in a sequence that requires larger window
        if self.current_sequence:
            if any(t in self.current_sequence for t in ('transform', 'normal', 'vertex')):
                self.window_size = 8192
                self.alignment = 16
            elif any(t in self.current_sequence for t in ('float', 'rotation')):
                self.window_size = 4096
                self.alignment = 4
                
        # Check data content for size adjustment
        if data and len(data) >= 16:
            # Check for matrix data
            try:
                values = struct.unpack('<ffff', data[:16])
                if any(abs(v) > 100.0 for v in values):
                    self.window_size = 8192
                    self.alignment = 16
            except struct.error:
                pass
                
        # Adjust for sequence position
        if self.sequence_position > 0:
            self.window_size *= 2
            
        # Check for data block patterns
        if hasattr(self, 'last_data_pos') and isinstance(self.last_data_pos, int):
            current_pos = data.tell() if hasattr(data, 'tell') else 0
            diff = current_pos - self.last_data_pos
            if 0x300 <= diff <= 0x400:  # Common pattern in debug output
                self.window_size = max(self.window_size, 8192)
            elif 0x2000 <= diff <= 0x3000:  # Another common pattern
                self.window_size = max(self.window_size, 16384)
            self.last_data_pos = current_pos
            
        self.logger.debug(f"Data block window size: {self.window_size}")
        self.logger.debug(f"Data block alignment: {self.alignment}")

    def process_data_with_markers(self, data: bytes, output: bytearray, flags: int, header_size: int) -> int:
        """Process data with block markers"""
        pos = 0
        self.last_data_pos = 0
        window_buffer = bytearray(self.window_size)  # Initialize with proper size
        
        self.logger.debug(f"Starting decompression with flags: 0x{flags:04x}")
        
        try:
            while pos < len(data):
                # Look for block markers
                marker = self.find_block_marker(data[pos:])
                if marker:
                    padding = self.handle_block_marker(marker, pos, data)
                    self.logger.debug(f"Found marker at 0x{pos:x}, padding: {padding}")
                    pos += len(marker) + padding
                    continue
                    
                # Handle compression flags
                is_compressed = bool(flags & 0x8000)
                
                if is_compressed and len(output) < header_size - 2:  # Changed condition
                    # Read compression token
                    if pos >= len(data):
                        self.logger.warning(f"Unexpected end of data at 0x{pos:x}")
                        break
                        
                    token = data[pos]
                    pos += 1
                    
                    if token & 0x80:  # Compressed block
                        if pos >= len(data):
                            self.logger.warning(f"Unexpected end of data at 0x{pos:x}")
                            break
                            
                        length = ((token & 0x7F) >> 2) + 3
                        offset = ((token & 0x03) << 8) | data[pos]
                        pos += 1
                        
                        self.logger.debug(f"Compressed block at 0x{pos:x}: length={length}, offset={offset}")
                        
                        # Adjust window size based on offset patterns
                        old_size = self.window_size
                        if offset > self.window_size // 2:
                            self.window_size *= 2
                            
                        # Ensure window size is power of 2
                        self.window_size = 1 << (self.window_size - 1).bit_length()
                        
                        if old_size != self.window_size:
                            self.logger.debug(f"Adjusted window size: {old_size} -> {self.window_size}")
                        
                        # Copy from window with improved handling
                        for i in range(length):
                            if len(window_buffer) > 0:
                                window_idx = (len(window_buffer) - offset) & (self.window_size - 1)
                                if window_idx < len(window_buffer):
                                    byte = window_buffer[window_idx]
                                else:
                                    # Handle window underflow
                                    byte = 0
                                    self.logger.debug(f"Window underflow at 0x{pos:x}: idx={window_idx}, len={len(window_buffer)}")
                            else:
                                byte = 0
                                self.logger.debug(f"Empty window at 0x{pos:x}")
                                
                            if len(output) < header_size:
                                output.append(byte)
                                window_buffer.append(byte)
                            else:
                                self.logger.warning(f"Output buffer full at 0x{pos:x}")
                                break
                            
                            # Keep window buffer size under control
                            if len(window_buffer) > self.window_size * 2:
                                window_buffer = window_buffer[-self.window_size:]
                                self.logger.debug(f"Trimmed window buffer to {len(window_buffer)} bytes")
                    else:  # Uncompressed block
                        self.logger.debug(f"Uncompressed byte at 0x{pos:x}: 0x{token:02x}")
                        if len(output) < header_size:
                            output.append(token)
                            window_buffer.append(token)
                        else:
                            self.logger.warning(f"Output buffer full at 0x{pos:x}")
                            break
                        
                        # Keep window buffer size under control
                        if len(window_buffer) > self.window_size * 2:
                            window_buffer = window_buffer[-self.window_size:]
                            self.logger.debug(f"Trimmed window buffer to {len(window_buffer)} bytes")
                else:
                    # Direct copy
                    if pos >= len(data):
                        break
                        
                    byte = data[pos]
                    if len(output) < header_size:  # Changed condition
                        output.append(byte)
                        window_buffer[len(output) % self.window_size] = byte  # Circular buffer
                    else:
                        break
                    pos += 1
                    
                    # Keep window buffer size under control
                    if len(window_buffer) > self.window_size * 2:
                        window_buffer = window_buffer[-self.window_size:]
                        self.logger.debug(f"Trimmed window buffer to {len(window_buffer)} bytes")
                    
            self.logger.debug(f"Decompression complete: {len(output)} bytes")
            return len(output)
            
        except Exception as e:
            self.logger.error(f"Error during data processing: {str(e)}")
            raise
    
    def read_header(self, f: BinaryIO) -> Optional[LZ77Header]:
        """Read and validate LZ77 header"""
        try:
            magic = f.read(4)
            if magic != b'LZ77':
                self.logger.error(f"Invalid magic: {magic}")
                return None
                
            size = struct.unpack('<I', f.read(4))[0]
            flag1 = struct.unpack('<I', f.read(4))[0]
            flag2 = struct.unpack('<I', f.read(4))[0]
            
            return LZ77Header(magic, size, flag1, flag2)
            
        except struct.error as e:
            self.logger.error(f"Error reading header: {str(e)}")
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error reading header: {str(e)}")
            return None
            
    def decompress_file(self, filename: str) -> bytes:
        """Decompress an LZ77 compressed file"""
        try:
            with open(filename, 'rb') as f:
                # Read and validate header
                header = self.read_header(f)
                if not header:
                    raise ValueError("Invalid header")
                    
                self.logger.debug(f"Header: {header}")
                
                # Validate reasonable size
                if header.size > 100_000_000:  # 100MB sanity check
                    raise ValueError(f"Suspicious decompressed size: {header.size} bytes")
                
                # Read compressed data
                data = f.read()
                if not data:
                    raise ValueError("No data to decompress")
                    
                self.logger.debug(f"Read {len(data)} bytes of compressed data")
                
                # Initialize output buffer with reasonable size
                output = bytearray()
                
                # Process data with markers
                try:
                    final_size = self.process_data_with_markers(data, output, header.flag1, header.size)
                    self.logger.debug(f"Processed {final_size} bytes")
                    
                    if final_size != header.size:
                        self.logger.warning(f"Size mismatch: got {final_size}, expected {header.size}")
                        
                    return bytes(output)
                except Exception as e:
                    self.logger.error(f"Error during decompression: {str(e)}")
                    raise
                    
        except IOError as e:
            self.logger.error(f"IO error: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            raise
    
    def reset_state(self):
        """Reset decompressor state"""
        self.window_buffer = bytearray(65536)
        self.window_pos = 0
        self.window_size = 65536  # Add window_size reset
        self.last_byte = 0
        self.total_output = 0
        self.current_block_type = None
        self.current_window_size = 65536
        self.current_alignment = 1
        self.block_sequence = []
        self.current_sequence = []
        self.block_states = {}
        self.chain_history = []
        self.chain_states = {
            'current_chain': None,
            'chain_position': 0,
            'chain_windows': {},
            'block_count': {}
        }
        self.sequence_history = []
        self.block_dependencies = {}
    
    def get_block_window_size(self, block_type: str) -> int:
        """Get appropriate window size for block type"""
        if block_type not in self.WINDOW_SIZES:
            return 65536  # Default
            
        config = self.WINDOW_SIZES[block_type]
        count = self.chain_states['block_count'].get(block_type, 0)
        
        size = config['start'] + (config['increment'] * count)
        return min(size, config['max'])
    
    def handle_block_sequence(self, marker: bytes, pos: int) -> None:
        """Handle block sequence markers"""
        if marker not in self.BLOCK_SEQUENCES:
            return
            
        info = self.BLOCK_SEQUENCES[marker]
        block_type = info['type']
        window_action = info['window']
        
        # Update block count
        self.chain_states['block_count'][block_type] = self.chain_states['block_count'].get(block_type, 0) + 1
        
        # Handle window action
        if window_action == 'reset':
            self.reset_window()
        elif window_action == 'new':
            self.current_window_size = self.get_block_window_size(block_type)
            self.reset_window()
        elif window_action == 'expand':
            self.current_window_size = self.get_block_window_size(block_type)
        elif window_action == 'preserve':
            # Save current window state if needed
            if block_type not in self.window_states:
                self.window_states[block_type] = (
                    self.window_buffer[:self.window_pos],
                    self.window_pos
                )

    def handle_float_block(self, data: bytes = None) -> None:
        """Handle float block type"""
        self.window_size = 4096  # Use self.window_size instead of local window_size
        self.alignment = 4
        
        # Check if we're in a transform sequence
        if self.current_sequence and 'transform' in self.current_sequence:
            self.window_size = 8192
            self.alignment = 16
            
        # Check if we're in a normal sequence
        elif self.current_sequence and 'normal' in self.current_sequence:
            self.window_size = 8192
            self.alignment = 12
            
        # Adjust window for vector components
        if data and len(data) >= 12:
            if struct.unpack('<fff', data[:12])[0] > 100.0:
                self.window_size = 8192
                self.alignment = 16
                
        self.logger.debug(f"Window size: {self.window_size}")
        self.logger.debug(f"Alignment: {self.alignment}")

    def handle_transform_block(self, data: bytes = None) -> None:
        """Handle transform block type"""
        self.window_size = 8192
        self.alignment = 16
        
        # Check if we're in a float sequence
        if self.current_sequence and 'float' in self.current_sequence:
            self.window_size = 4096
            self.alignment = 4
            
        # Adjust for matrix data
        if data and len(data) >= 16:
            if any(abs(x) > 100.0 for x in struct.unpack('<ffff', data[:16])):
                self.window_size = 8192
                self.alignment = 16
                
        self.logger.debug(f"Window size: {self.window_size}")
        self.logger.debug(f"Alignment: {self.alignment}")

    def setup_window(self, block_type: str) -> None:
        """Set up window parameters based on block type"""
        if block_type == 'float':
            self.handle_float_block()
        elif block_type == 'transform':
            self.handle_transform_block()
        elif block_type == 'normal':
            self.window_size = 8192
            self.alignment = 12
        elif block_type == 'vertex':
            self.window_size = 4096
            self.alignment = 12
        elif block_type == 'index':
            self.window_size = 2048
            self.alignment = 2
        elif block_type == 'data':
            self.handle_data_block()
        else:
            # Default values
            self.window_size = 4096
            self.alignment = 4
            
        self.logger.debug(f"Window size: {self.window_size}")
        self.logger.debug(f"Alignment: {self.alignment}")

    def find_block_marker(self, data: bytes) -> Optional[bytes]:
        """Find a block marker in the data"""
        if len(data) < 4:
            return None
            
        # Check for known markers
        marker = data[:4]
        for type_name, markers in self.BLOCK_TYPE_MARKERS.items():
            # Convert markers to bytes for comparison
            byte_markers = [m.encode('utf-8') if isinstance(m, str) else m for m in markers]
            if marker in byte_markers:
                return marker
                
        return None

def show_file_info(filename: str):
    """Show detailed information about the MDL file"""
    with open(filename, 'rb') as f:
        # Get file size
        f.seek(0, 2)
        file_size = f.tell()
        f.seek(0)
        
        print(f"\nFile: {filename}")
        print(f"Total size: {file_size:,} bytes")
        
        # Show first 64 bytes (header)
        header = f.read(64)
        print("\nFirst 64 bytes (header):")
        for i in range(0, len(header), 16):
            chunk = header[i:i+16]
            hex_str = " ".join(f"{b:02x}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            print(f"{i:04x}: {hex_str:48} {ascii_str}")
            
        # Show last 64 bytes
        f.seek(-64, 2)
        tail = f.read()
        print("\nLast 64 bytes:")
        for i in range(0, len(tail), 16):
            chunk = tail[i:i+16]
            hex_str = " ".join(f"{b:02x}" for b in chunk)
            ascii_str = "".join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
            print(f"{file_size - 64 + i:04x}: {hex_str:48} {ascii_str}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='MDL LZ77 Decompressor')
    parser.add_argument('input', help='Input compressed MDL file')
    parser.add_argument('output', help='Output decompressed file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('--info', action='store_true', help='Show file information without decompressing')
    args = parser.parse_args()
    
    if args.info:
        show_file_info(args.input)
        return
        
    decompressor = LZ77Decompressor(debug=args.debug)
    decompressed = decompressor.decompress_file(args.input)
    
    with open(args.output, 'wb') as f:
        f.write(decompressed)
    
    print(f"Successfully decompressed {len(decompressed):,} bytes")

if __name__ == '__main__':
    main() 