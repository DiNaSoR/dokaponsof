"""
Voice Tools Tab for Dokapon SoF Tools.
Provides PCK sound file extraction and replacement functionality.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QRadioButton, QButtonGroup, QTableWidget, 
    QTableWidgetItem, QHeaderView, QProgressBar, QSpinBox,
    QGroupBox, QSplitter, QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import pyqtSignal, Qt, QMimeData
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent
from ..widgets.worker import WorkerThread
from app.core.pck_handler import PCKFile, Sound, extract_pck
from app.core.tool_manager import ToolManager
from ..styles import COLORS
import os
import subprocess
import tempfile


class VoiceExtractorTab(QWidget):
    """Enhanced Voice Tools tab with Extract and Replace modes."""
    
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers = []
        self.current_pck: PCKFile = None
        self.replacement_queue = {}  # {original_name: (new_path, loop_start, loop_end)}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # Mode selection
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup()
        self.extract_radio = QRadioButton("Extract Mode")
        self.replace_radio = QRadioButton("Replace Mode")
        self.extract_radio.setChecked(True)
        self.mode_group.addButton(self.extract_radio)
        self.mode_group.addButton(self.replace_radio)
        mode_layout.addWidget(self.extract_radio)
        mode_layout.addWidget(self.replace_radio)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        
        # PCK file selection (common to both modes)
        pck_layout = QHBoxLayout()
        pck_layout.addWidget(QLabel("PCK File:"))
        self.pck_path_label = QLabel("No file selected")
        self.pck_path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        pck_layout.addWidget(self.pck_path_label, 1)
        self.select_pck_btn = QPushButton("Select PCK")
        self.select_pck_btn.clicked.connect(self._select_pck)
        pck_layout.addWidget(self.select_pck_btn)
        layout.addLayout(pck_layout)
        
        # Sound list table
        self.sound_table = QTableWidget()
        self.sound_table.setColumnCount(5)
        self.sound_table.setHorizontalHeaderLabels(["Name", "Size", "Format", "Replacement", "Status"])
        self.sound_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sound_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sound_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sound_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.sound_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.sound_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sound_table.setAcceptDrops(True)
        self.sound_table.dragEnterEvent = self._drag_enter_event
        self.sound_table.dropEvent = self._drop_event
        layout.addWidget(self.sound_table, 1)
        
        # Extract mode controls
        self.extract_controls = self._create_extract_controls()
        layout.addWidget(self.extract_controls)
        
        # Replace mode controls
        self.replace_controls = self._create_replace_controls()
        layout.addWidget(self.replace_controls)
        
        # Connect mode change
        self.extract_radio.toggled.connect(self._update_mode_visibility)
        self._update_mode_visibility()

    def _create_extract_controls(self) -> QWidget:
        """Create extract mode control panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_path_label = QLabel("./extracted_voices")
        self.output_path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        output_layout.addWidget(self.output_path_label, 1)
        select_output_btn = QPushButton("Select Output")
        select_output_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(select_output_btn)
        layout.addLayout(output_layout)
        
        # Extract button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.extract_btn = QPushButton("Extract All Sounds")
        self.extract_btn.setProperty("class", "primary")
        self.extract_btn.clicked.connect(self._start_extraction)
        btn_layout.addWidget(self.extract_btn)
        
        self.extract_selected_btn = QPushButton("Extract Selected")
        self.extract_selected_btn.clicked.connect(self._extract_selected)
        btn_layout.addWidget(self.extract_selected_btn)
        layout.addLayout(btn_layout)
        
        return widget

    def _create_replace_controls(self) -> QWidget:
        """Create replace mode control panel."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 8, 0, 0)
        
        # Loop point settings
        loop_group = QGroupBox("Loop Settings (for music files)")
        loop_layout = QHBoxLayout(loop_group)
        
        loop_layout.addWidget(QLabel("Loop Start (samples):"))
        self.loop_start_spin = QSpinBox()
        self.loop_start_spin.setRange(0, 999999999)
        self.loop_start_spin.setSpecialValueText("Auto")
        loop_layout.addWidget(self.loop_start_spin)
        
        loop_layout.addWidget(QLabel("Loop End (samples):"))
        self.loop_end_spin = QSpinBox()
        self.loop_end_spin.setRange(0, 999999999)
        self.loop_end_spin.setSpecialValueText("Auto")
        loop_layout.addWidget(self.loop_end_spin)
        
        loop_layout.addStretch()
        layout.addWidget(loop_group)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        
        self.add_replacement_btn = QPushButton("Add Replacement")
        self.add_replacement_btn.clicked.connect(self._add_replacement)
        btn_layout.addWidget(self.add_replacement_btn)
        
        self.clear_replacements_btn = QPushButton("Clear All")
        self.clear_replacements_btn.clicked.connect(self._clear_replacements)
        btn_layout.addWidget(self.clear_replacements_btn)
        
        btn_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply Replacements")
        self.apply_btn.setProperty("class", "primary")
        self.apply_btn.clicked.connect(self._apply_replacements)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)
        
        # Output PCK path
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output PCK:"))
        self.output_pck_label = QLabel("(will create modified copy)")
        self.output_pck_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        output_layout.addWidget(self.output_pck_label, 1)
        layout.addLayout(output_layout)
        
        return widget

    def _update_mode_visibility(self):
        """Update UI based on selected mode."""
        is_extract = self.extract_radio.isChecked()
        self.extract_controls.setVisible(is_extract)
        self.replace_controls.setVisible(not is_extract)
        
        # Update table columns visibility
        self.sound_table.setColumnHidden(3, is_extract)  # Replacement column
        self.sound_table.setColumnHidden(4, is_extract)  # Status column

    def _select_pck(self):
        """Select a PCK file to work with."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PCK File",
            "",
            "PCK Files (*.pck);;All Files (*)"
        )
        if path:
            self._load_pck(path)

    def _load_pck(self, path: str):
        """Load and display a PCK file."""
        try:
            self.pck_path_label.setText(path)
            self.current_pck = PCKFile(path)
            self._populate_sound_table()
            self._log_status(f"Loaded PCK: {os.path.basename(path)} ({len(self.current_pck)} sounds)")
            
            # Update output PCK label
            base, ext = os.path.splitext(path)
            self.output_pck_label.setText(f"{base}_modified{ext}")
            
        except Exception as e:
            self._log_status(f"Error loading PCK: {e}")
            QMessageBox.critical(self, "Error", f"Failed to load PCK file:\n{e}")

    def _populate_sound_table(self):
        """Populate the sound table with current PCK contents."""
        self.sound_table.setRowCount(0)
        
        if not self.current_pck:
            return
        
        for i, sound in enumerate(self.current_pck.sounds):
            self.sound_table.insertRow(i)
            
            # Name
            name_item = QTableWidgetItem(sound.name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sound_table.setItem(i, 0, name_item)
            
            # Size
            size_str = self._format_size(sound.size)
            size_item = QTableWidgetItem(size_str)
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sound_table.setItem(i, 1, size_item)
            
            # Format
            format_str = "Opus/OGG" if sound.is_opus() else "Unknown"
            format_item = QTableWidgetItem(format_str)
            format_item.setFlags(format_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sound_table.setItem(i, 2, format_item)
            
            # Replacement (for replace mode)
            replacement = self.replacement_queue.get(sound.name, None)
            replace_item = QTableWidgetItem(os.path.basename(replacement[0]) if replacement else "")
            replace_item.setFlags(replace_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.sound_table.setItem(i, 3, replace_item)
            
            # Status
            status_item = QTableWidgetItem("Pending" if replacement else "")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if replacement:
                status_item.setForeground(QColor(COLORS['accent_warning']))
            self.sound_table.setItem(i, 4, status_item)

    def _format_size(self, size: int) -> str:
        """Format file size for display."""
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

    def _select_output_dir(self):
        """Select output directory for extraction."""
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_path_label.setText(path)

    def _log_status(self, message: str):
        """Emit status update."""
        self.status_updated.emit(message)

    def _start_extraction(self):
        """Extract all sounds from current PCK."""
        if not self.current_pck:
            self._log_status("Error: No PCK file loaded")
            return
        
        output_dir = self.output_path_label.text()
        pck_path = self.pck_path_label.text()
        
        try:
            self._log_status(f"Extracting {len(self.current_pck)} sounds...")
            
            worker = WorkerThread(
                self._do_extraction,
                [output_dir]
            )
            worker.finished.connect(self._on_extraction_complete)
            worker.error.connect(self._on_extraction_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error: {e}")

    def _do_extraction(self, output_dir: str):
        """Worker function for extraction."""
        os.makedirs(output_dir, exist_ok=True)
        extracted = self.current_pck.extract_all(output_dir)
        return extracted

    def _extract_selected(self):
        """Extract only selected sounds."""
        if not self.current_pck:
            self._log_status("Error: No PCK file loaded")
            return
        
        selected_rows = set(item.row() for item in self.sound_table.selectedItems())
        if not selected_rows:
            self._log_status("Error: No sounds selected")
            return
        
        output_dir = self.output_path_label.text()
        os.makedirs(output_dir, exist_ok=True)
        
        count = 0
        for row in selected_rows:
            sound = self.current_pck.sounds[row]
            sound.write(output_dir)
            count += 1
        
        self._log_status(f"Extracted {count} sounds to {output_dir}")

    def _on_extraction_complete(self):
        """Handle extraction completion."""
        self._log_status(f"Extraction complete! Files saved to: {self.output_path_label.text()}")

    def _on_extraction_error(self, error_msg: str):
        """Handle extraction error."""
        self._log_status(f"Extraction error: {error_msg}")

    def _add_replacement(self):
        """Add a replacement file for selected sound."""
        selected_rows = list(set(item.row() for item in self.sound_table.selectedItems()))
        
        if not selected_rows:
            self._log_status("Error: Select a sound to replace first")
            return
        
        if not self.current_pck:
            self._log_status("Error: No PCK file loaded")
            return
        
        # Select replacement file
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Replacement Audio",
            "",
            "Audio Files (*.opus *.ogg *.wav *.mp3 *.flac);;All Files (*)"
        )
        
        if not path:
            return
        
        # Add to replacement queue for each selected sound
        for row in selected_rows:
            original_name = self.current_pck.sounds[row].name
            loop_start = self.loop_start_spin.value()
            loop_end = self.loop_end_spin.value()
            
            self.replacement_queue[original_name] = (path, loop_start, loop_end)
            
            # Update table
            replace_item = self.sound_table.item(row, 3)
            replace_item.setText(os.path.basename(path))
            
            status_item = self.sound_table.item(row, 4)
            status_item.setText("Pending")
            status_item.setForeground(QColor(COLORS['accent_warning']))
        
        self._log_status(f"Queued {len(selected_rows)} replacement(s)")

    def _clear_replacements(self):
        """Clear all queued replacements."""
        self.replacement_queue.clear()
        self._populate_sound_table()
        self._log_status("Cleared all replacements")

    def _apply_replacements(self):
        """Apply all queued replacements and save new PCK."""
        if not self.current_pck:
            self._log_status("Error: No PCK file loaded")
            return
        
        if not self.replacement_queue:
            self._log_status("Error: No replacements queued")
            return
        
        # Check if opusenc is available
        tool_manager = ToolManager.get_instance()
        opusenc_path = tool_manager.get_opusenc_path()
        
        try:
            self._log_status(f"Processing {len(self.replacement_queue)} replacements...")
            
            for original_name, (replacement_path, loop_start, loop_end) in self.replacement_queue.items():
                # Convert to Opus if needed
                if not replacement_path.lower().endswith(('.opus', '.ogg')):
                    self._log_status(f"Converting {os.path.basename(replacement_path)} to Opus...")
                    
                    # Create temp file for conversion
                    temp_opus = tempfile.mktemp(suffix='.opus')
                    
                    # Build opusenc command
                    cmd = [opusenc_path]
                    if loop_start > 0:
                        cmd.extend(["--comment", f"LoopStart={loop_start}"])
                    if loop_end > 0:
                        cmd.extend(["--comment", f"LoopEnd={loop_end}"])
                    cmd.extend([replacement_path, temp_opus])
                    
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                        if result.returncode != 0:
                            self._log_status(f"Warning: opusenc failed for {original_name}, using raw file")
                            with open(replacement_path, 'rb') as f:
                                new_data = f.read()
                        else:
                            with open(temp_opus, 'rb') as f:
                                new_data = f.read()
                            os.remove(temp_opus)
                    except FileNotFoundError:
                        self._log_status("Warning: opusenc not found, using raw file")
                        with open(replacement_path, 'rb') as f:
                            new_data = f.read()
                else:
                    with open(replacement_path, 'rb') as f:
                        new_data = f.read()
                
                # Create new Sound and replace
                new_sound = Sound(
                    name=original_name,
                    data=new_data,
                    loop_start=loop_start,
                    loop_end=loop_end
                )
                
                if self.current_pck.replace_sound(original_name, new_sound):
                    self._log_status(f"Replaced: {original_name}")
                    
                    # Update status in table
                    for row in range(self.sound_table.rowCount()):
                        if self.sound_table.item(row, 0).text() == original_name:
                            status_item = self.sound_table.item(row, 4)
                            status_item.setText("Done")
                            status_item.setForeground(QColor(COLORS['accent_success']))
                            break
                else:
                    self._log_status(f"Warning: Could not find {original_name} in PCK")
            
            # Save modified PCK
            output_path = self.output_pck_label.text()
            self.current_pck.write(output_path)
            
            self._log_status(f"Saved modified PCK to: {output_path}")
            self.replacement_queue.clear()
            
        except Exception as e:
            self._log_status(f"Error applying replacements: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply replacements:\n{e}")

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent):
        """Handle file drop for replacement."""
        if not self.replace_radio.isChecked():
            return
        
        urls = event.mimeData().urls()
        if urls:
            file_path = urls[0].toLocalFile()
            
            # Get row under cursor
            pos = event.position().toPoint()
            row = self.sound_table.rowAt(pos.y())
            
            if row >= 0 and self.current_pck:
                original_name = self.current_pck.sounds[row].name
                loop_start = self.loop_start_spin.value()
                loop_end = self.loop_end_spin.value()
                
                self.replacement_queue[original_name] = (file_path, loop_start, loop_end)
                
                # Update table
                replace_item = self.sound_table.item(row, 3)
                replace_item.setText(os.path.basename(file_path))
                
                status_item = self.sound_table.item(row, 4)
                status_item.setText("Pending")
                status_item.setForeground(QColor(COLORS['accent_warning']))
                
                self._log_status(f"Queued replacement for: {original_name}")

    def closeEvent(self, event):
        """Clean up worker threads when closing."""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept()
