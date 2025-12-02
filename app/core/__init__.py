# Core functionality exports
import os
import sys

# Add the parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Now use absolute imports
from app.core.dokapon_extract import decompress_lz77, process_file, extract_tex, extract_spranm, extract_fnt
from app.core.text_extract_repack import extract_texts, import_texts
from app.core.voice_pck_extractor import extract_voices
from app.core.pck_handler import PCKFile, Sound, extract_pck, create_pck
from app.core.hex_editor import (
    HexPatch, PatchConflict, parse_hex_file, parse_hex_files, 
    detect_conflicts, apply_patches, find_hex_files
)
from app.core.video_converter import VideoConverter, VideoInfo, ConversionSettings, find_game_videos
from app.core.tool_manager import ToolManager, get_ffmpeg_path, get_ffprobe_path, get_opusenc_path

# Export all the functions
__all__ = [
    # Original exports
    'decompress_lz77',
    'process_file',
    'extract_tex',
    'extract_spranm',
    'extract_fnt',
    'extract_texts',
    'import_texts',
    'extract_voices',
    # PCK handling
    'PCKFile',
    'Sound',
    'extract_pck',
    'create_pck',
    # Hex editing
    'HexPatch',
    'PatchConflict',
    'parse_hex_file',
    'parse_hex_files',
    'detect_conflicts',
    'apply_patches',
    'find_hex_files',
    # Video conversion
    'VideoConverter',
    'VideoInfo',
    'ConversionSettings',
    'find_game_videos',
    # Tool management
    'ToolManager',
    'get_ffmpeg_path',
    'get_ffprobe_path',
    'get_opusenc_path',
] 