from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox, QFileDialog, QButtonGroup, QRadioButton, 
                            QLineEdit, QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy)
from ..widgets.worker import WorkerThread
from app.core.text_extract_repack import extract_texts, import_texts
import os
from PyQt6.QtCore import pyqtSignal, Qt

class TextTab(QWidget):
    status_updated = pyqtSignal(str)  # Signal for status updates

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.workers = []

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Mode selection (Extract/Import)
        mode_layout = QHBoxLayout()
        self.mode_group = QButtonGroup()
        self.extract_radio = QRadioButton("Extract")
        self.import_radio = QRadioButton("Import")
        self.extract_radio.setChecked(True)  # Default to extract mode
        self.mode_group.addButton(self.extract_radio)
        self.mode_group.addButton(self.import_radio)
        mode_layout.addWidget(self.extract_radio)
        mode_layout.addWidget(self.import_radio)
        layout.addLayout(mode_layout)
        
        # Common EXE selection
        exe_layout = QHBoxLayout()
        self.exe_label = QLabel("EXE file:")
        self.exe_path = QLabel("No file selected")
        self.select_exe_btn = QPushButton("Select EXE")
        self.select_exe_btn.clicked.connect(self._select_exe)
        exe_layout.addWidget(self.exe_label)
        exe_layout.addWidget(self.exe_path)
        exe_layout.addWidget(self.select_exe_btn)
        layout.addLayout(exe_layout)
        
        # Create mode-specific controls
        self.extract_widgets = self._create_extract_controls()
        self.import_widgets = self._create_import_controls()
        
        # Add mode-specific widgets to main layout
        layout.addWidget(self.extract_widgets)
        layout.addWidget(self.import_widgets)
        
        # Add search box above preview table
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Enter text to search...")
        self.search_box.textChanged.connect(self._filter_preview)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_box)
        layout.addLayout(search_layout)
        
        # Add preview table with three columns
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["Offset", "Text", "Length"])
        self.preview_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.preview_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.preview_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.preview_table.setMinimumHeight(400)
        
        # Connect itemChanged signal
        self.preview_table.itemChanged.connect(self._on_text_edited)
        layout.addWidget(self.preview_table, stretch=1)
        
        # Add statistics bar
        stats_layout = QHBoxLayout()
        self.total_lines_label = QLabel("Total Lines: 0")
        self.visible_lines_label = QLabel("Visible: 0")
        self.modified_lines_label = QLabel("Modified: 0")
        
        stats_layout.addWidget(self.total_lines_label)
        stats_layout.addWidget(QLabel("|"))  # Separator
        stats_layout.addWidget(self.visible_lines_label)
        stats_layout.addWidget(QLabel("|"))  # Separator
        stats_layout.addWidget(self.modified_lines_label)
        stats_layout.addStretch()  # Push stats to the left
        
        layout.addLayout(stats_layout)
        
        # Connect mode change signal
        self.extract_radio.toggled.connect(self._update_ui_visibility)
        
        # Initial UI update
        self._update_ui_visibility()

    def _create_extract_controls(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Output selection
        output_layout = QHBoxLayout()
        self.output_label = QLabel("Output directory:")
        self.output_path = QLabel("./output")
        self.select_output_btn = QPushButton("Select Output Directory")
        self.select_output_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(self.select_output_btn)
        layout.addLayout(output_layout)
        
        # Buttons
        buttons_layout = QHBoxLayout()
        self.extract_btn = QPushButton("Extract Text")
        self.preview_btn = QPushButton("Preview Text")
        self.extract_btn.clicked.connect(self._start_extraction)
        self.preview_btn.clicked.connect(self._preview_text)
        buttons_layout.addWidget(self.extract_btn)
        buttons_layout.addWidget(self.preview_btn)
        layout.addLayout(buttons_layout)
        
        return widget

    def _create_import_controls(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Text file selection
        text_layout = QHBoxLayout()
        self.text_label = QLabel("Text file:")
        self.text_path = QLabel("No file selected")
        self.select_text_btn = QPushButton("Select Text File")
        self.select_text_btn.clicked.connect(self._select_text_file)
        text_layout.addWidget(self.text_label)
        text_layout.addWidget(self.text_path)
        text_layout.addWidget(self.select_text_btn)
        layout.addLayout(text_layout)
        
        # Offset file selection
        offset_layout = QHBoxLayout()
        self.offset_label = QLabel("Offset file:")
        self.offset_path = QLabel("No file selected")
        self.select_offset_btn = QPushButton("Select Offset File")
        self.select_offset_btn.clicked.connect(self._select_offset_file)
        offset_layout.addWidget(self.offset_label)
        offset_layout.addWidget(self.offset_path)
        offset_layout.addWidget(self.select_offset_btn)
        layout.addLayout(offset_layout)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import from Files")
        self.import_preview_btn = QPushButton("Import from Preview")
        self.import_btn.clicked.connect(self._start_import)
        self.import_preview_btn.clicked.connect(self._import_from_preview)
        buttons_layout.addWidget(self.import_btn)
        buttons_layout.addWidget(self.import_preview_btn)
        layout.addLayout(buttons_layout)
        
        return widget

    def _update_ui_visibility(self):
        """Update UI based on selected mode"""
        is_extract = self.extract_radio.isChecked()
        self.extract_widgets.setVisible(is_extract)
        self.import_widgets.setVisible(not is_extract)

    def _select_exe(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable File",
            "",
            "Executable Files (*.exe);;All Files (*)"
        )
        if path:
            self.exe_path.setText(path)

    def _select_text_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Text File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.text_path.setText(path)
            # Auto-detect offset file
            offset_path = path.replace(".txt", "_offsets.txt")
            if os.path.exists(offset_path):
                self.offset_path.setText(offset_path)

    def _select_offset_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Offset File",
            "",
            "Text Files (*.txt);;All Files (*)"
        )
        if path:
            self.offset_path.setText(path)

    def _select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_path.setText(path)

    def _log_status(self, message):
        """Helper to emit status updates"""
        self.status_updated.emit(message)

    def _start_extraction(self):
        """Extract text to files without preview"""
        exe_path = self.exe_path.text()
        if exe_path == "No file selected":
            self._log_status("Error: No EXE file selected")
            return

        try:
            output_dir = self.output_path.text()
            output_text = os.path.join(output_dir, "extracted_text.txt")
            output_offsets = os.path.join(output_dir, "text_offsets.txt")
            
            self._log_status(f"Starting text extraction from {os.path.basename(exe_path)}...")
            
            worker = WorkerThread(
                extract_texts,
                [exe_path, output_text, output_offsets]
            )
            worker.finished.connect(lambda: self._log_status("Text extraction completed successfully"))
            worker.error.connect(self._on_extraction_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error starting extraction: {str(e)}")

    def _preview_text(self):
        """Extract and preview text without saving to files"""
        exe_path = self.exe_path.text()
        if exe_path == "No file selected":
            self._log_status("Error: No EXE file selected")
            return

        try:
            # Create temporary directory for preview
            temp_dir = os.path.join(os.path.dirname(exe_path), "temp_preview")
            os.makedirs(temp_dir, exist_ok=True)
            
            output_text = os.path.join(temp_dir, "preview_text.txt")
            output_offsets = os.path.join(temp_dir, "preview_offsets.txt")
            
            self._log_status(f"Loading text preview from {os.path.basename(exe_path)}...")
            
            worker = WorkerThread(
                extract_texts,
                [exe_path, output_text, output_offsets]
            )
            worker.finished.connect(lambda: self._update_preview(output_text, output_offsets))
            worker.error.connect(self._on_extraction_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error loading preview: {str(e)}")

    def _update_preview(self, text_path, offset_path):
        try:
            if os.path.exists(text_path) and os.path.exists(offset_path):
                # Block signals during update
                self.preview_table.blockSignals(True)
                
                with open(text_path, 'r', encoding='utf-8') as tf, \
                     open(offset_path, 'r', encoding='utf-8') as of:
                    texts = tf.readlines()
                    offsets = of.readlines()
                    
                    # Clear and populate table
                    self.preview_table.setRowCount(0)
                    for i, (offset, text) in enumerate(zip(offsets, texts)):
                        text = text.strip()
                        self.preview_table.insertRow(i)
                        
                        # Store original length in offset item's data
                        offset_item = QTableWidgetItem(offset.strip())
                        offset_item.setData(Qt.ItemDataRole.UserRole, len(text))
                        self.preview_table.setItem(i, 0, offset_item)
                        
                        text_item = QTableWidgetItem(text)
                        self.preview_table.setItem(i, 1, text_item)
                        
                        # Add length column with validation
                        length_item = QTableWidgetItem(f"{len(text)}/{len(text)}")
                        length_item.setFlags(length_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                        self.preview_table.setItem(i, 2, length_item)
                
                # Re-enable signals after update
                self.preview_table.blockSignals(False)
                self._log_status("Preview loaded successfully")
                self._update_stats()  # Update stats after loading
                
                # Clean up temporary files
                os.remove(text_path)
                os.remove(offset_path)
                os.rmdir(os.path.dirname(text_path))
                
        except Exception as e:
            self._log_status(f"Error updating preview: {str(e)}")

    def _on_text_edited(self, item):
        """Handle text edits in the preview table"""
        if item.column() == 1:  # Text column
            row = item.row()
            text = item.text()
            curr_len = len(text)
            
            # Get original length from offset item's data
            offset_item = self.preview_table.item(row, 0)
            original_len = offset_item.data(Qt.ItemDataRole.UserRole)
            
            # Create or update length column
            length_item = self.preview_table.item(row, 2)
            if length_item is None:
                length_item = QTableWidgetItem()
                length_item.setFlags(length_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.preview_table.setItem(row, 2, length_item)
            
            # Update length display
            length_item.setText(f"{curr_len}/{original_len}")
            
            # Highlight only the length column if length doesn't match original
            if curr_len != original_len:
                length_item.setForeground(Qt.GlobalColor.darkYellow)
                length_item.setBackground(Qt.GlobalColor.darkRed)
            else:
                length_item.setForeground(Qt.GlobalColor.black)
                length_item.setBackground(Qt.GlobalColor.transparent)

            # Update stats after text edit
            self._update_stats()

    def _on_extraction_error(self, error_msg):
        self._log_status(f"Error during extraction: {error_msg}")

    def _start_import(self):
        exe_path = self.exe_path.text()
        text_path = self.text_path.text()
        offset_path = self.offset_path.text()
        
        if exe_path == "No file selected":
            self._log_status("Error: No EXE file selected")
            return
            
        if text_path == "No file selected":
            self._log_status("Error: No text file selected")
            return
            
        if offset_path == "No file selected":
            self._log_status("Error: No offset file selected")
            return

        try:
            output_exe = exe_path.replace(".exe", "_modified.exe")
            self._log_status(f"Starting text import to {os.path.basename(output_exe)}...")
            
            worker = WorkerThread(
                import_texts,
                [exe_path, text_path, offset_path, output_exe]
            )
            worker.finished.connect(self._on_import_complete)
            worker.error.connect(self._on_import_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error starting import: {str(e)}")

    def _on_import_complete(self):
        self._log_status("Text import completed successfully")
        self._log_status("Modified EXE has been saved with '_modified' suffix")

    def _on_import_error(self, error_msg):
        self._log_status(f"Error during import: {error_msg}")

    def _import_from_preview(self):
        """Import text directly from preview table"""
        if self.preview_table.rowCount() == 0:
            self._log_status("Error: No text to import")
            return

        exe_path = self.exe_path.text()
        if exe_path == "No file selected":
            self._log_status("Error: No EXE file selected")
            return

        try:
            # Create temporary files for import
            temp_dir = os.path.join(os.path.dirname(exe_path), "temp_import")
            os.makedirs(temp_dir, exist_ok=True)
            
            text_path = os.path.join(temp_dir, "import_text.txt")
            offset_path = os.path.join(temp_dir, "import_offsets.txt")
            
            # Save table contents to files
            with open(text_path, 'w', encoding='utf-8') as tf, \
                 open(offset_path, 'w', encoding='utf-8') as of:
                for row in range(self.preview_table.rowCount()):
                    offset = self.preview_table.item(row, 0).text()
                    text = self.preview_table.item(row, 1).text()
                    of.write(f"{offset}\n")
                    tf.write(f"{text}\n")
            
            # Start import
            output_exe = exe_path.replace(".exe", "_modified.exe")
            self._log_status(f"Starting text import from preview to {os.path.basename(output_exe)}...")
            
            worker = WorkerThread(
                import_texts,
                [exe_path, text_path, offset_path, output_exe]
            )
            worker.finished.connect(lambda: self._cleanup_import(temp_dir))
            worker.error.connect(self._on_import_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error starting import: {str(e)}")

    def _cleanup_import(self, temp_dir):
        """Clean up temporary files after import"""
        try:
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
            self._log_status("Text import completed successfully")
            self._log_status("Modified EXE has been saved with '_modified' suffix")
        except Exception as e:
            self._log_status(f"Error cleaning up: {str(e)}")

    def _filter_preview(self, search_text):
        """Filter preview table based on search text"""
        search_text = search_text.lower()
        
        # Show all rows if search is empty
        if not search_text:
            for row in range(self.preview_table.rowCount()):
                self.preview_table.setRowHidden(row, False)
            return
            
        # Hide rows that don't match search
        for row in range(self.preview_table.rowCount()):
            text_item = self.preview_table.item(row, 1)  # Text column
            offset_item = self.preview_table.item(row, 0)  # Offset column
            
            if text_item and offset_item:
                text = text_item.text().lower()
                offset = offset_item.text().lower()
                
                # Show row if search text is in either text or offset
                matches = search_text in text or search_text in offset
                self.preview_table.setRowHidden(row, not matches)

        # Update stats after filtering
        self._update_stats()

    def _update_stats(self):
        """Update statistics display"""
        total_lines = self.preview_table.rowCount()
        visible_lines = sum(1 for row in range(total_lines) 
                          if not self.preview_table.isRowHidden(row))
        
        # Count modified lines (where length doesn't match original)
        modified_lines = 0
        for row in range(total_lines):
            if not self.preview_table.isRowHidden(row):
                text_item = self.preview_table.item(row, 1)
                offset_item = self.preview_table.item(row, 0)
                if text_item and offset_item:
                    curr_len = len(text_item.text())
                    original_len = offset_item.data(Qt.ItemDataRole.UserRole)
                    if curr_len != original_len:
                        modified_lines += 1
        
        self.total_lines_label.setText(f"Total Lines: {total_lines}")
        self.visible_lines_label.setText(f"Visible: {visible_lines}")
        self.modified_lines_label.setText(f"Modified: {modified_lines}") 