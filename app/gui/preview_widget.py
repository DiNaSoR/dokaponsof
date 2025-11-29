"""
Preview widget for displaying file previews and information.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QSizePolicy, QScrollArea, QStackedWidget
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from app.core.dokapon_extract import decompress_lz77
from app.core.mdl_handler import LZ77Decompressor
from app.core.mdl_parser import MDLParser, MDLGeometry
from app.gui.widgets.viewer_3d import Viewer3DWidget, is_3d_viewer_available
import os


class PreviewWidget(QWidget):
    """Widget for previewing game asset files with image and info display."""
    
    def __init__(self):
        super().__init__()
        self._current_pixmap = None  # Store original pixmap for resizing
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # Stacked widget to switch between 2D and 3D views
        self.preview_stack = QStackedWidget()
        
        # Page 0: 2D Preview (images/textures)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { border: none; background-color: transparent; }")
        
        # Preview label (inside scroll area)
        self.preview_label = QLabel("No preview available")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(200, 200)
        self.preview_label.setStyleSheet("QLabel { background-color: #2d2d30; border-radius: 4px; padding: 8px; }")
        self.scroll_area.setWidget(self.preview_label)
        
        self.preview_stack.addWidget(self.scroll_area)  # Index 0
        
        # Page 1: 3D Viewer (for MDL files)
        self.viewer_3d = Viewer3DWidget()
        self.preview_stack.addWidget(self.viewer_3d)  # Index 1
        
        # Add stacked widget with stretch factor
        layout.addWidget(self.preview_stack, stretch=3)
        
        # Info text area
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(150)
        self.info_text.setMinimumHeight(100)
        self.info_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.info_text, stretch=0)
        
        # Set overall widget size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumWidth(250)
    
    def _show_2d_view(self):
        """Switch to 2D preview mode."""
        self.preview_stack.setCurrentIndex(0)
    
    def _show_3d_view(self):
        """Switch to 3D viewer mode."""
        self.preview_stack.setCurrentIndex(1)

    def show_preview(self, file_path):
        """Show preview for a file."""
        if not os.path.exists(file_path):
            self.clear_preview()
            return
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Build file information
        file_info = f"File: {os.path.basename(file_path)}\n"
        try:
            file_info += f"Size: {os.path.getsize(file_path):,} bytes\n"
        except OSError:
            file_info += "Size: Unknown\n"
        file_info += f"Type: {file_ext}\n"
        
        try:
            # Read file data
            with open(file_path, 'rb') as f:
                data = f.read()

            mdl_compression = None

            # Handle LZ77 compression - but for SPRANM, work with raw data
            # as many SPRANM files have hybrid format with Sequ header at fixed offset
            if data.startswith(b'LZ77'):
                if file_ext == '.mdl':
                    try:
                        decompressor = LZ77Decompressor()
                        header = decompressor.read_header(data)
                        decompressed = decompressor.decompress_data(data)
                        if decompressed:
                            # Combine decompressed payload and any trailing raw bytes
                            trailing = decompressor.trailing_data or b""
                            data = decompressed + trailing
                            mdl_compression = {
                                "header": header,
                                "consumed": decompressor.bytes_consumed,
                                "trailing": len(trailing),
                            }
                            file_info += "LZ77 compression: Yes (MDL token stream)\n"
                            if header:
                                file_info += f"Declared size: {header.decompressed_size:,} bytes\n"
                                file_info += f"Flag1: 0x{header.flag1:08X}, Flag2: 0x{header.flag2:08X}\n"
                            file_info += f"Stream bytes consumed: {decompressor.bytes_consumed:,}\n"
                            file_info += f"Trailing raw bytes: {len(decompressor.trailing_data):,}\n"
                    except Exception as e:
                        file_info += f"LZ77 compression: Yes (Decompression error: {str(e)})\n"
                elif file_ext != '.spranm':
                    decompressed = decompress_lz77(data)
                    if decompressed:
                        data = decompressed
                        file_info += "LZ77 compression: Yes\n"
                    else:
                        raise ValueError("Failed to decompress LZ77 data")
                else:
                    file_info += "LZ77 format: Yes (hybrid)\n"

            # Handle different file types
            if file_ext == '.tex':
                self._preview_tex(data, file_info)
            elif file_ext == '.mpd':
                self._preview_mpd(data, file_info)
            elif file_ext == '.spranm':
                self._preview_spranm(data, file_info)
            elif file_ext == '.mdl':
                self._preview_mdl(data, file_info, mdl_compression)
            else:
                self._current_pixmap = None
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText(f"No preview available for {file_ext} files")
                self.info_text.setText(file_info)
                
        except Exception as e:
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Error loading preview")
            self.info_text.setText(f"{file_info}\nError: {str(e)}")

    def _preview_tex(self, data, file_info):
        """Preview TEX file."""
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            # Find IEND to get proper PNG bounds
            iend_pos = data.find(b'IEND', png_start)
            if iend_pos > 0:
                png_data = data[png_start:iend_pos + 8]
            else:
                png_data = data[png_start:]
            
            pixmap = QPixmap()
            if pixmap.loadFromData(png_data) and not pixmap.isNull():
                file_info += f"\nDimensions: {pixmap.width()}x{pixmap.height()}\n"
                file_info += "Texture preview loaded successfully"
                self._show_pixmap(pixmap)
            else:
                self._current_pixmap = None
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("Failed to load texture preview")
        else:
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No PNG data found in TEX file")
        self.info_text.setText(file_info)

    def _preview_mpd(self, data, file_info):
        """Preview MPD file."""
        if not data.startswith(b'Cell'):
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Not a valid MPD file")
            self.info_text.setText(file_info)
            return

        # Parse MPD header
        try:
            width = int.from_bytes(data[0x18:0x1C], 'little')
            height = int.from_bytes(data[0x1C:0x20], 'little')
            cell_width = int.from_bytes(data[0x20:0x24], 'little')
            cell_height = int.from_bytes(data[0x24:0x28], 'little')
            file_info += f"\nDimensions: {width}x{height}\n"
            file_info += f"Cell size: {cell_width}x{cell_height}\n"
        except Exception:
            pass

        # Find and display embedded PNG
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            # Find IEND to get proper PNG bounds
            iend_pos = data.find(b'IEND', png_start)
            if iend_pos > 0:
                png_data = data[png_start:iend_pos + 8]
            else:
                png_data = data[png_start:]
            
            pixmap = QPixmap()
            if pixmap.loadFromData(png_data) and not pixmap.isNull():
                file_info += f"Dimensions: {pixmap.width()}x{pixmap.height()}\n"
                file_info += "MPD preview loaded successfully"
                self._show_pixmap(pixmap)
            else:
                self._current_pixmap = None
                self.preview_label.setPixmap(QPixmap())
                self.preview_label.setText("Failed to load MPD preview")
        else:
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No PNG data found in MPD file")
        
        self.info_text.setText(file_info)

    def _preview_spranm(self, data, file_info):
        """Preview SPRANM file."""
        # Handle both uncompressed (Sequ) and compressed (LZ77) formats
        
        # Check if file starts with Sequence header
        if data.startswith(b'Sequ'):
            self._preview_sequence_data(data, file_info)
            return
        
        # Check if this is a compressed file - look for Sequ header anywhere
        sequ_pos = data.find(b'Sequ')
        if sequ_pos > 0:
            # File has embedded Sequence data
            file_info += f"Sequence header at offset: {sequ_pos}\n"
            
            # Try to find PNG in the Sequence portion
            png_start = data.find(b'\x89PNG\r\n\x1a\n', sequ_pos)
            if png_start >= 0:
                self._preview_png_data(data, png_start, file_info)
                return
            
            # Also check for PNG before the Sequence header
            png_start = data.find(b'\x89PNG\r\n\x1a\n')
            if png_start >= 0 and png_start < sequ_pos:
                self._preview_png_data(data, png_start, file_info)
                return
            
            # No PNG found - this is an Animation Control file
            # Parse Sequence metadata for more info
            try:
                sequ_data = data[sequ_pos:]
                frame_count = sequ_data[0x14] if len(sequ_data) > 0x14 else 0
                file_info += f"Frame count: {frame_count}\n"
                file_info += "\nType: Animation Control File\n"
                file_info += "Contains: Transform data, sprite indices, animation flags\n"
                file_info += "Note: This file controls animations but doesn't contain sprites.\n"
                file_info += "Look for H_*.spranm files for the actual sprite sheets."
            except Exception:
                file_info += "\nType: Animation Control File (compressed)\n"
            
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Animation Control File\n\nNo sprite data - references\nexternal sprite resources")
            self.info_text.setText(file_info)
            return
        
        # Unknown format
        self._current_pixmap = None
        self.preview_label.setPixmap(QPixmap())
        header_preview = data[:16].hex() if len(data) >= 16 else data.hex()
        self.preview_label.setText(f"Unknown SPRANM format\nHeader: {header_preview}")
        self.info_text.setText(file_info)
    
    def _preview_sequence_data(self, data, file_info):
        """Preview a file that starts with Sequence header."""
        try:
            frame_count = data[0x14]
            file_info += f"\nFrame count: {frame_count}\n"
        except Exception:
            pass
        
        # Find PNG data
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            self._preview_png_data(data, png_start, file_info)
        else:
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("No PNG data found in SPRANM file")
            self.info_text.setText(file_info)
    
    def _preview_png_data(self, data, png_start, file_info):
        """Extract and display PNG data."""
        # Find IEND to get proper PNG bounds
        iend_pos = data.find(b'IEND', png_start)
        if iend_pos > 0:
            png_data = data[png_start:iend_pos + 8]
        else:
            png_data = data[png_start:]
        
        file_info += f"PNG offset: {png_start}, size: {len(png_data)} bytes\n"
        
        pixmap = QPixmap()
        if pixmap.loadFromData(png_data) and not pixmap.isNull():
            file_info += f"Dimensions: {pixmap.width()}x{pixmap.height()}\n"
            file_info += "Animation preview loaded successfully"
            self._show_pixmap(pixmap)
        else:
            self._current_pixmap = None
            self.preview_label.setPixmap(QPixmap())
            self.preview_label.setText("Failed to load PNG preview")
        
        self.info_text.setText(file_info)

    def _preview_mdl(self, data, file_info, compression_info=None):
        """Preview MDL (3D model) file."""
        file_info += "\nFormat: 3D Model (MDL)\n"

        if compression_info:
            header = compression_info.get("header")
            if header:
                file_info += f"Declared size: {header.decompressed_size:,} bytes\n"
                file_info += f"Flag1: 0x{header.flag1:08X}, Flag2: 0x{header.flag2:08X}\n"
            file_info += f"Stream bytes consumed: {compression_info.get('consumed', 0):,}\n"
            file_info += f"Trailing raw bytes: {compression_info.get('trailing', 0):,}\n"

        geometry = None
        try:
            parser = MDLParser()
            geometry = parser.parse(data)
        except Exception as exc:
            file_info += f"\nMDL parse error: {exc}"

        if geometry and geometry.vertex_count > 0:
            file_info += "\nGeometry:\n"
            file_info += f"Vertices: {geometry.vertex_count}\n"
            file_info += f"Faces: {geometry.face_count}\n"
            if geometry.normals is not None:
                file_info += f"Normals: {len(geometry.normals)}\n"
            bounds_min, bounds_max = geometry.bounds
            file_info += f"Bounds min: {bounds_min}\n"
            file_info += f"Bounds max: {bounds_max}\n"

            faces = geometry.indices
            if is_3d_viewer_available():
                shown = False
                if faces is not None and len(faces) > 0:
                    shown = self.viewer_3d.display_mesh(geometry.vertices, faces, geometry.normals)
                if not shown:
                    # Fallback to point cloud for models without indices
                    shown = self.viewer_3d.display_point_cloud(geometry.vertices)
                if shown:
                    self._show_3d_view()
                    self.info_text.setText(file_info)
                    return
                file_info += "\n3D viewer available but failed to render mesh."
            else:
                file_info += "\nPyVista not installed; showing summary only."
        else:
            file_info += "\nCould not parse MDL geometry."

        # Fallback summary when 3D view is not available
        self._show_2d_view()
        self._current_pixmap = None
        self.preview_label.setPixmap(QPixmap())
        fallback_text = "🎮 3D Enemy Model\n\n"
        if geometry:
            fallback_text += f"Vertices detected: {geometry.vertex_count}\n"
            fallback_text += f"Faces detected: {geometry.face_count}\n"
        else:
            fallback_text += "MDL geometry could not be parsed\n"
        if not is_3d_viewer_available():
            fallback_text += "\nInstall pyvista + pyvistaqt to enable 3D preview"
        self.preview_label.setText(fallback_text)
        self.info_text.setText(file_info)

    def _show_pixmap(self, pixmap):
        """Display a pixmap, scaled to fit the preview area."""
        if pixmap.isNull():
            return
        
        # Store original for resize events
        self._current_pixmap = pixmap
        
        # Get available size from scroll area viewport
        available_size = self.scroll_area.viewport().size()
        available_size.setWidth(available_size.width() - 20)  # Account for padding
        available_size.setHeight(available_size.height() - 20)
        
        # Scale if image is larger than available space
        if pixmap.width() > available_size.width() or pixmap.height() > available_size.height():
            scaled = pixmap.scaled(
                available_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled)
        else:
            # Show at original size if it fits
            self.preview_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        """Handle resize to re-scale the preview image."""
        super().resizeEvent(event)
        # Re-scale current pixmap if we have one
        if self._current_pixmap and not self._current_pixmap.isNull():
            self._show_pixmap(self._current_pixmap)

    def clear_preview(self):
        """Clear the preview display."""
        self._current_pixmap = None
        self.preview_label.setText("No preview available")
        self.preview_label.setPixmap(QPixmap())
        self.info_text.clear()
        self.viewer_3d.clear()
        self._show_2d_view()
