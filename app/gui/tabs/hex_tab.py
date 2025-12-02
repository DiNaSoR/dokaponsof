"""
Hex Editor Tab for Dokapon SoF Tools.
Provides binary patch management for game executable modifications.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QCheckBox, QMessageBox, QAbstractItemView,
    QSplitter, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent
from ..widgets.worker import WorkerThread
from app.core.hex_editor import (
    HexPatch, PatchConflict, parse_hex_file, parse_hex_files,
    detect_conflicts, apply_patches, find_hex_files, get_patch_summary
)
from ..styles import COLORS
import os


class HexEditorTab(QWidget):
    """Hex Editor tab for applying binary patches to executables."""
    
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers = []
        self.hex_files = []  # List of loaded hex file paths
        self.patches = []    # List of parsed HexPatch objects
        self.conflicts = []  # List of detected conflicts
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # EXE file selection
        exe_group = QGroupBox("Target Executable")
        exe_layout = QVBoxLayout(exe_group)
        
        exe_row = QHBoxLayout()
        exe_row.addWidget(QLabel("EXE File:"))
        self.exe_path_label = QLabel("No file selected")
        self.exe_path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        exe_row.addWidget(self.exe_path_label, 1)
        
        select_exe_btn = QPushButton("Select EXE")
        select_exe_btn.clicked.connect(self._select_exe)
        exe_row.addWidget(select_exe_btn)
        exe_layout.addLayout(exe_row)
        
        # Output path
        output_row = QHBoxLayout()
        output_row.addWidget(QLabel("Output:"))
        self.output_path_label = QLabel("(will create *_patched.exe)")
        self.output_path_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        output_row.addWidget(self.output_path_label, 1)
        
        self.backup_checkbox = QCheckBox("Create backup")
        self.backup_checkbox.setChecked(True)
        output_row.addWidget(self.backup_checkbox)
        exe_layout.addLayout(output_row)
        
        layout.addWidget(exe_group)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Hex file list
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_header = QHBoxLayout()
        left_header.addWidget(QLabel("Hex Patch Files"))
        left_header.addStretch()
        
        add_file_btn = QPushButton("Add Files")
        add_file_btn.clicked.connect(self._add_hex_files)
        left_header.addWidget(add_file_btn)
        
        add_folder_btn = QPushButton("Add Folder")
        add_folder_btn.clicked.connect(self._add_hex_folder)
        left_header.addWidget(add_folder_btn)
        
        left_layout.addLayout(left_header)
        
        self.file_list = QListWidget()
        self.file_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.file_list.setAcceptDrops(True)
        self.file_list.dragEnterEvent = self._drag_enter_event
        self.file_list.dropEvent = self._drop_event
        self.file_list.itemSelectionChanged.connect(self._on_file_selection_changed)
        left_layout.addWidget(self.file_list)
        
        # File list buttons
        file_btn_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected_files)
        file_btn_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self._clear_all_files)
        file_btn_layout.addWidget(clear_btn)
        file_btn_layout.addStretch()
        left_layout.addLayout(file_btn_layout)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Patch details table
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addWidget(QLabel("Patch Details"))
        
        self.patch_table = QTableWidget()
        self.patch_table.setColumnCount(4)
        self.patch_table.setHorizontalHeaderLabels(["File", "Offset", "Size", "Preview"])
        self.patch_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.patch_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.patch_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.patch_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.patch_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.patch_table)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 500])
        
        layout.addWidget(splitter, 1)
        
        # Conflicts panel
        self.conflicts_group = QGroupBox("Conflicts Detected")
        self.conflicts_group.setStyleSheet(f"QGroupBox {{ color: {COLORS['accent_error']}; }}")
        conflicts_layout = QVBoxLayout(self.conflicts_group)
        
        self.conflicts_list = QListWidget()
        self.conflicts_list.setMaximumHeight(100)
        conflicts_layout.addWidget(self.conflicts_list)
        
        self.conflicts_group.setVisible(False)
        layout.addWidget(self.conflicts_group)
        
        # Summary and action buttons
        bottom_layout = QHBoxLayout()
        
        self.summary_label = QLabel("No patches loaded")
        self.summary_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bottom_layout.addWidget(self.summary_label)
        
        bottom_layout.addStretch()
        
        self.apply_btn = QPushButton("Apply Patches")
        self.apply_btn.setProperty("class", "primary")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self._apply_patches)
        bottom_layout.addWidget(self.apply_btn)
        
        layout.addLayout(bottom_layout)

    def _select_exe(self):
        """Select target executable file."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable File",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if path:
            self.exe_path_label.setText(path)
            base, ext = os.path.splitext(path)
            self.output_path_label.setText(f"{base}_patched{ext}")
            self._update_apply_button()
            self._log_status(f"Selected EXE: {os.path.basename(path)}")

    def _add_hex_files(self):
        """Add hex files via file dialog."""
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Hex Patch Files",
            "",
            "Hex Files (*.hex);;All Files (*)"
        )
        if paths:
            self._load_hex_files(paths)

    def _add_hex_folder(self):
        """Add all hex files from a folder."""
        path = QFileDialog.getExistingDirectory(self, "Select Folder with Hex Files")
        if path:
            hex_files = find_hex_files(path)
            if hex_files:
                self._load_hex_files(hex_files)
            else:
                self._log_status(f"No .hex files found in {path}")

    def _load_hex_files(self, paths: list):
        """Load hex files and parse patches."""
        added = 0
        for path in paths:
            if path not in self.hex_files:
                self.hex_files.append(path)
                
                # Add to list widget
                item = QListWidgetItem(os.path.basename(path))
                item.setData(Qt.ItemDataRole.UserRole, path)
                item.setCheckState(Qt.CheckState.Checked)
                self.file_list.addItem(item)
                added += 1
        
        if added > 0:
            self._refresh_patches()
            self._log_status(f"Added {added} hex file(s)")

    def _remove_selected_files(self):
        """Remove selected files from the list."""
        selected_items = self.file_list.selectedItems()
        for item in selected_items:
            path = item.data(Qt.ItemDataRole.UserRole)
            if path in self.hex_files:
                self.hex_files.remove(path)
            self.file_list.takeItem(self.file_list.row(item))
        
        self._refresh_patches()

    def _clear_all_files(self):
        """Clear all loaded hex files."""
        self.hex_files.clear()
        self.file_list.clear()
        self._refresh_patches()
        self._log_status("Cleared all hex files")

    def _refresh_patches(self):
        """Refresh the patches list from loaded files."""
        # Get only checked files
        active_files = []
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                active_files.append(item.data(Qt.ItemDataRole.UserRole))
        
        # Parse patches
        self.patches = parse_hex_files(active_files)
        
        # Detect conflicts
        self.conflicts = detect_conflicts(self.patches)
        
        # Update UI
        self._update_patch_table()
        self._update_conflicts_panel()
        self._update_summary()
        self._update_apply_button()

    def _update_patch_table(self):
        """Update the patch details table."""
        self.patch_table.setRowCount(0)
        
        for i, patch in enumerate(self.patches):
            self.patch_table.insertRow(i)
            
            # File name
            file_item = QTableWidgetItem(os.path.basename(patch.source_file))
            file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.patch_table.setItem(i, 0, file_item)
            
            # Offset (hex)
            offset_item = QTableWidgetItem(f"0x{patch.offset:08X}")
            offset_item.setFlags(offset_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.patch_table.setItem(i, 1, offset_item)
            
            # Size
            size_item = QTableWidgetItem(f"{patch.size} bytes")
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.patch_table.setItem(i, 2, size_item)
            
            # Preview (hex dump)
            preview = patch.get_hex_preview(16)
            preview_item = QTableWidgetItem(preview)
            preview_item.setFlags(preview_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            preview_item.setStyleSheet(f"font-family: 'Consolas', monospace;")
            self.patch_table.setItem(i, 3, preview_item)
            
            # Highlight if in conflict
            is_conflict = any(
                patch.source_file == c.patch1.source_file or patch.source_file == c.patch2.source_file
                for c in self.conflicts
            )
            if is_conflict:
                for col in range(4):
                    self.patch_table.item(i, col).setBackground(QColor("#5a1d1d"))

    def _update_conflicts_panel(self):
        """Update the conflicts display panel."""
        self.conflicts_list.clear()
        
        if self.conflicts:
            self.conflicts_group.setVisible(True)
            for conflict in self.conflicts:
                item = QListWidgetItem(str(conflict))
                item.setForeground(QColor(COLORS['accent_error']))
                self.conflicts_list.addItem(item)
        else:
            self.conflicts_group.setVisible(False)

    def _update_summary(self):
        """Update the summary label."""
        if not self.patches:
            self.summary_label.setText("No patches loaded")
            return
        
        summary = get_patch_summary(self.patches)
        text = (f"{summary['total_patches']} patches from {summary['source_files']} file(s), "
                f"{summary['total_bytes']} bytes total")
        
        if self.conflicts:
            text += f" | {len(self.conflicts)} conflict(s) detected"
            self.summary_label.setStyleSheet(f"color: {COLORS['accent_warning']};")
        else:
            self.summary_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        
        self.summary_label.setText(text)

    def _update_apply_button(self):
        """Update the apply button state."""
        has_exe = self.exe_path_label.text() != "No file selected"
        has_patches = len(self.patches) > 0
        self.apply_btn.setEnabled(has_exe and has_patches)

    def _on_file_selection_changed(self):
        """Handle file list selection changes."""
        # Could highlight patches from selected file
        pass

    def _apply_patches(self):
        """Apply all patches to the executable."""
        exe_path = self.exe_path_label.text()
        output_path = self.output_path_label.text()
        
        if not os.path.exists(exe_path):
            QMessageBox.critical(self, "Error", f"Executable not found:\n{exe_path}")
            return
        
        if self.conflicts:
            result = QMessageBox.warning(
                self,
                "Conflicts Detected",
                f"There are {len(self.conflicts)} conflict(s) between patches.\n"
                "Applying may cause unexpected behavior.\n\n"
                "Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if result != QMessageBox.StandardButton.Yes:
                return
        
        try:
            self._log_status(f"Applying {len(self.patches)} patches...")
            
            backup = self.backup_checkbox.isChecked()
            applied, errors = apply_patches(exe_path, self.patches, output_path, backup)
            
            for error in errors:
                self._log_status(f"  {error}")
            
            if applied > 0:
                self._log_status(f"Successfully applied {applied} patches to: {output_path}")
                
                if backup:
                    self._log_status(f"Backup saved as: {exe_path}.backup")
                
                QMessageBox.information(
                    self,
                    "Success",
                    f"Applied {applied} patches successfully!\n\nOutput: {output_path}"
                )
            else:
                self._log_status("No patches were applied")
                QMessageBox.warning(self, "Warning", "No patches were applied.")
                
        except Exception as e:
            self._log_status(f"Error applying patches: {e}")
            QMessageBox.critical(self, "Error", f"Failed to apply patches:\n{e}")

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent):
        """Handle file drop."""
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            path = url.toLocalFile()
            if path.lower().endswith('.hex'):
                paths.append(path)
            elif os.path.isdir(path):
                paths.extend(find_hex_files(path))
        
        if paths:
            self._load_hex_files(paths)

    def _log_status(self, message: str):
        """Emit status update."""
        self.status_updated.emit(message)

    def closeEvent(self, event):
        """Clean up worker threads when closing."""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept()

