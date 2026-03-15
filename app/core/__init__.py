# Core functionality exports
from app.core.dokapon_extract import decompress_lz77, process_file, extract_tex, extract_spranm, extract_fnt
from app.core.text_extract_repack import extract_texts, extract_texts_to_memory, import_texts
from app.core.pck_handler import PCKFile, Sound, extract_pck, create_pck
from app.core.hex_editor import (
    HexPatch, PatchConflict, parse_hex_file, parse_hex_files, 
    detect_conflicts, apply_patches, find_hex_files
)
from app.core.video_converter import VideoConverter, VideoInfo, ConversionSettings, find_game_videos
from app.core.tool_manager import ToolManager, get_ffmpeg_path, get_ffprobe_path, get_opusenc_path

# Cell / texture / map explorer modules
from app.core.cell_parser import (
    CellHeader, CellRecord, CellChunk, CellMap, DecodedCellRecord,
    parse_cell_header, parse_cell_records, parse_cell_chunks, parse_cell_map,
    decode_record, summarize_records, summarize_record_decoding, summarize_map,
    render_map_text,
)
from app.core.texture_parser import (
    TextureHeader, TexturePart, TexturePartsContainer,
    parse_texture_header, parse_texture_parts_payload, parse_texture_parts_chunk,
    parse_palette_chunk, build_indexed_atlas_image, build_png_image,
    summarize_texture_parts,
)
from app.core.game_scanner import (
    FileInsight, MapGroup, DebugOffsetState, DebugInsight,
    detect_signature, count_pngs, analyze_file, scan_map_groups,
    analyze_debug, summarize_map_groups,
)
from app.core.map_renderer import (
    LoadedCellDocument,
    load_cell_document, build_atlas_for_document, render_map_image,
    list_cell_files, scan_workspace,
)
from app.core.report_generator import (
    write_json_report, write_markdown_report, write_logic_report,
)

# Export all the functions
__all__ = [
    # Original exports
    'decompress_lz77',
    'process_file',
    'extract_tex',
    'extract_spranm',
    'extract_fnt',
    'extract_texts',
    'extract_texts_to_memory',
    'import_texts',
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
    # Cell parser
    'CellHeader',
    'CellRecord',
    'CellChunk',
    'CellMap',
    'DecodedCellRecord',
    'parse_cell_header',
    'parse_cell_records',
    'parse_cell_chunks',
    'parse_cell_map',
    'decode_record',
    'summarize_records',
    'summarize_record_decoding',
    'summarize_map',
    'render_map_text',
    # Texture parser
    'TextureHeader',
    'TexturePart',
    'TexturePartsContainer',
    'parse_texture_header',
    'parse_texture_parts_payload',
    'parse_texture_parts_chunk',
    'parse_palette_chunk',
    'build_indexed_atlas_image',
    'build_png_image',
    'summarize_texture_parts',
    # Game scanner
    'FileInsight',
    'MapGroup',
    'DebugOffsetState',
    'DebugInsight',
    'detect_signature',
    'count_pngs',
    'analyze_file',
    'scan_map_groups',
    'analyze_debug',
    'summarize_map_groups',
    # Map renderer
    'LoadedCellDocument',
    'load_cell_document',
    'build_atlas_for_document',
    'render_map_image',
    'list_cell_files',
    'scan_workspace',
    # Report generator
    'write_json_report',
    'write_markdown_report',
    'write_logic_report',
] 