from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from app.core.dokapon_extract import decompress_lz77
import os

class PreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        
        # Main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        # Preview label
        self.preview_label = QLabel("No preview available")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_label.setMinimumHeight(300)  # Set minimum height
        layout.addWidget(self.preview_label)
        
        # Info text
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.info_text)
        
        # Set widget size policy to expand
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def show_preview(self, file_path):
        if not os.path.exists(file_path):
            self.clear_preview()
            return
            
        file_ext = os.path.splitext(file_path)[1].lower()
        
        # Show file information
        file_info = f"File: {os.path.basename(file_path)}\n"
        file_info += f"Size: {os.path.getsize(file_path):,} bytes\n"
        file_info += f"Type: {file_ext}\n"
        
        try:
            # Read file data
            with open(file_path, 'rb') as f:
                data = f.read()

            # Handle LZ77 compression
            if data.startswith(b'LZ77'):
                data = decompress_lz77(data)
                if not data:
                    raise ValueError("Failed to decompress LZ77 data")
                file_info += "LZ77 compression: Yes\n"

            # Handle different file types
            if file_ext == '.tex':
                self._preview_tex(data, file_info)
            elif file_ext == '.mpd':
                self._preview_mpd(data, file_info)
            elif file_ext == '.spranm':
                self._preview_spranm(data, file_info)
            else:
                self.preview_label.setText(f"No preview available for {file_ext} files")
                self.info_text.setText(file_info)
                
        except Exception as e:
            self.preview_label.setText("Error loading preview")
            self.info_text.setText(f"Error: {str(e)}")

    def _preview_tex(self, data, file_info):
        """Preview TEX file"""
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            # Create QPixmap from PNG data
            pixmap = QPixmap()
            pixmap.loadFromData(data[png_start:])
            if not pixmap.isNull():
                self.show_pixmap(pixmap)
                file_info += "\nTexture preview loaded successfully"
            else:
                self.preview_label.setText("Failed to load texture preview")
        else:
            self.preview_label.setText("No PNG data found in TEX file")
        self.info_text.setText(file_info)

    def _preview_mpd(self, data, file_info):
        """Preview MPD file"""
        if not data.startswith(b'Cell'):
            self.preview_label.setText("Not a valid MPD file")
            self.info_text.setText(file_info)
            return

        # Parse MPD header
        width = int.from_bytes(data[0x18:0x1C], 'little')
        height = int.from_bytes(data[0x1C:0x20], 'little')
        cell_width = int.from_bytes(data[0x20:0x24], 'little')
        cell_height = int.from_bytes(data[0x24:0x28], 'little')

        file_info += f"\nDimensions: {width}x{height}\n"
        file_info += f"Cell size: {cell_width}x{cell_height}\n"

        # Find and display embedded PNG
        png_start = data.find(b'\x89PNG\r\n\x1a\n')
        if png_start >= 0:
            pixmap = QPixmap()
            pixmap.loadFromData(data[png_start:])
            if not pixmap.isNull():
                self.show_pixmap(pixmap)
                file_info += "MPD preview loaded successfully"
            else:
                self.preview_label.setText("Failed to load MPD preview")
        else:
            self.preview_label.setText("No PNG data found in MPD file")
        
        self.info_text.setText(file_info)

    def _preview_spranm(self, data, file_info):
        """Preview SPRANM file"""
        if data.startswith(b'Sequ'):
            # Parse sequence header
            frame_count = data[0x14]
            file_info += f"\nFrame count: {frame_count}\n"

            # Find and display embedded PNG
            png_start = data.find(b'\x89PNG\r\n\x1a\n')
            if png_start >= 0:
                pixmap = QPixmap()
                pixmap.loadFromData(data[png_start:])
                if not pixmap.isNull():
                    self.show_pixmap(pixmap)
                    file_info += "Animation preview loaded successfully"
                else:
                    self.preview_label.setText("Failed to load animation preview")
            else:
                self.preview_label.setText("No PNG data found in SPRANM file")
        else:
            self.preview_label.setText("Not a valid SPRANM file")
        
        self.info_text.setText(file_info)

    def show_pixmap(self, pixmap):
        """Show a scaled pixmap in the preview label"""
        if pixmap.isNull():
            return
            
        # Scale pixmap to fit the label while maintaining aspect ratio
        scaled = pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.preview_label.setPixmap(scaled)

    def clear_preview(self):
        self.preview_label.setText("No preview available")
        self.preview_label.setPixmap(QPixmap())
        self.info_text.clear()

    # ... (rest of the PreviewWidget methods) 