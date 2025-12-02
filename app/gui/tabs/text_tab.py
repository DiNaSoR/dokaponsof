"""
Text Tools Tab - Redesigned UI for DOKAPON! Sword of Fury
Features smart text editing with control code protection.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog, QLineEdit, QFrame, QScrollArea,
                            QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
                            QStackedWidget, QComboBox, QCheckBox, QProgressBar,
                            QSpinBox, QGroupBox, QSizePolicy)
from PyQt6.QtCore import pyqtSignal, Qt, QSize
from PyQt6.QtGui import QColor, QFont, QIcon
from ..widgets.worker import WorkerThread
from ..widgets.smart_text_editor import SmartTextEditorWidget, DokaponSyntaxHighlighter
from app.core.text_extract_repack import extract_texts, import_texts, analyze_text_patterns
import os
import re


class StatCard(QFrame):
    """A card displaying a statistic"""
    
    def __init__(self, title: str, value: str = "0", icon: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setStyleSheet("""
            #StatCard {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
                padding: 12px;
            }
            #StatCard:hover {
                border-color: #007acc;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(4)
        
        # Icon and title row
        header = QHBoxLayout()
        if icon:
            icon_label = QLabel(icon)
            icon_label.setStyleSheet("font-size: 16px;")
            header.addWidget(icon_label)
        
        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888; font-size: 11px; font-weight: 500;")
        header.addWidget(title_label)
        header.addStretch()
        layout.addLayout(header)
        
        # Value
        self.value_label = QLabel(value)
        self.value_label.setStyleSheet("color: #e0e0e0; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.value_label)
    
    def setValue(self, value: str):
        self.value_label.setText(value)


class ActionButton(QPushButton):
    """Styled action button"""
    
    def __init__(self, text: str, icon: str = "", primary: bool = False, parent=None):
        super().__init__(parent)
        self.setText(f"{icon}  {text}" if icon else text)
        self.setMinimumHeight(40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        if primary:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #0e639c;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 20px;
                    font-weight: 600;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #1177bb;
                }
                QPushButton:pressed {
                    background-color: #0d5a8c;
                }
                QPushButton:disabled {
                    background-color: #3c3c3c;
                    color: #666;
                }
            """)
        else:
            self.setStyleSheet("""
                QPushButton {
                    background-color: #3c3c3c;
                    color: #e0e0e0;
                    border: 1px solid #4c4c4c;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-size: 13px;
                }
                QPushButton:hover {
                    background-color: #4c4c4c;
                    border-color: #5c5c5c;
                }
                QPushButton:pressed {
                    background-color: #2c2c2c;
                }
                QPushButton:disabled {
                    background-color: #2c2c2c;
                    color: #555;
                    border-color: #3c3c3c;
                }
            """)


class FileSelector(QFrame):
    """Modern file selector widget"""
    
    fileSelected = pyqtSignal(str)
    
    def __init__(self, label: str, filter_text: str = "All Files (*)", 
                 is_directory: bool = False, parent=None):
        super().__init__(parent)
        self.filter_text = filter_text
        self.is_directory = is_directory
        self._path = ""
        
        self.setStyleSheet("""
            FileSelector {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 8, 8)
        layout.setSpacing(12)
        
        # Label
        self.label = QLabel(label)
        self.label.setStyleSheet("color: #888; font-size: 11px; min-width: 80px;")
        layout.addWidget(self.label)
        
        # Path display
        self.path_label = QLabel("No file selected")
        self.path_label.setStyleSheet("""
            color: #e0e0e0; 
            background-color: #1e1e1e; 
            padding: 6px 12px;
            border-radius: 4px;
            font-family: Consolas;
            font-size: 12px;
        """)
        self.path_label.setWordWrap(False)
        layout.addWidget(self.path_label, stretch=1)
        
        # Browse button
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #0e639c;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #1177bb; }
        """)
        self.browse_btn.clicked.connect(self._browse)
        layout.addWidget(self.browse_btn)
    
    def _browse(self):
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(self, f"Select {self.label.text()}")
        else:
            path, _ = QFileDialog.getOpenFileName(self, f"Select {self.label.text()}", 
                                                   "", self.filter_text)
        if path:
            self.setPath(path)
    
    def setPath(self, path: str):
        self._path = path
        # Show shortened path
        display = path if len(path) < 60 else "..." + path[-57:]
        self.path_label.setText(display)
        self.path_label.setToolTip(path)
        self.fileSelected.emit(path)
    
    def path(self) -> str:
        return self._path


def get_text_preview(text: str, max_len: int = 80) -> str:
    """Get truncated preview without control codes"""
    preview = text
    preview = re.sub(r'\\[pkrhzm,]', '', preview)
    preview = preview.replace('\\n', ' ')
    preview = re.sub(r'%\d+[cxyMsd]', '', preview)
    preview = re.sub(r'%\d*[sd]', '[?]', preview)
    if len(preview) > max_len:
        preview = preview[:max_len] + "..."
    return preview.strip()


class TextTab(QWidget):
    """Redesigned Text Tools tab with smart editor"""
    
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers = []
        self.entries = []  # List of (offset, length, text) tuples
        self.current_index = -1
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create scroll area for the whole content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(20)
        
        # Header
        header = self._create_header()
        content_layout.addWidget(header)
        
        # File selector section
        file_section = self._create_file_section()
        content_layout.addWidget(file_section)
        
        # Stats cards
        stats_section = self._create_stats_section()
        content_layout.addWidget(stats_section)
        
        # Main splitter for list and editor
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #3c3c3c;
                width: 2px;
            }
        """)
        
        # Left panel - Text list
        list_panel = self._create_list_panel()
        splitter.addWidget(list_panel)
        
        # Right panel - Editor
        editor_panel = self._create_editor_panel()
        splitter.addWidget(editor_panel)
        
        splitter.setSizes([400, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        content_layout.addWidget(splitter, stretch=1)
        
        scroll.setWidget(content)
        main_layout.addWidget(scroll)
    
    def _create_header(self) -> QWidget:
        """Create the page header"""
        header = QWidget()
        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title and description
        title_section = QVBoxLayout()
        title = QLabel("Text Tools")
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #e0e0e0;")
        title_section.addWidget(title)
        
        subtitle = QLabel("Extract, edit, and reimport game text with smart control code protection")
        subtitle.setStyleSheet("font-size: 13px; color: #888;")
        title_section.addWidget(subtitle)
        
        layout.addLayout(title_section)
        layout.addStretch()
        
        # Quick actions
        self.analyze_btn = ActionButton("Analyze", "📊")
        self.analyze_btn.clicked.connect(self._analyze_text)
        layout.addWidget(self.analyze_btn)
        
        return header
    
    def _create_file_section(self) -> QFrame:
        """Create the file selection section"""
        section = QFrame()
        section.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(section)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # EXE selector
        self.exe_selector = FileSelector("Game EXE", "Executable (*.exe);;All Files (*)")
        self.exe_selector.fileSelected.connect(self._on_exe_selected)
        layout.addWidget(self.exe_selector)
        
        # Output directory
        self.output_selector = FileSelector("Output Dir", is_directory=True)
        self.output_selector.setPath("./output")
        layout.addWidget(self.output_selector)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        
        self.load_btn = ActionButton("Load & Preview", "📖", primary=True)
        self.load_btn.clicked.connect(self._load_preview)
        self.load_btn.setEnabled(False)
        btn_layout.addWidget(self.load_btn)
        
        self.extract_btn = ActionButton("Extract to Files", "📤")
        self.extract_btn.clicked.connect(self._extract_to_files)
        self.extract_btn.setEnabled(False)
        btn_layout.addWidget(self.extract_btn)
        
        self.save_btn = ActionButton("Save Changes", "💾", primary=True)
        self.save_btn.clicked.connect(self._save_changes)
        self.save_btn.setEnabled(False)
        btn_layout.addWidget(self.save_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return section
    
    def _create_stats_section(self) -> QWidget:
        """Create statistics cards"""
        section = QWidget()
        layout = QHBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        self.total_card = StatCard("Total Entries", "0", "📝")
        layout.addWidget(self.total_card)
        
        self.modified_card = StatCard("Modified", "0", "✏️")
        layout.addWidget(self.modified_card)
        
        self.overlength_card = StatCard("Over Length", "0", "⚠️")
        layout.addWidget(self.overlength_card)
        
        self.with_vars_card = StatCard("With Variables", "0", "🔤")
        layout.addWidget(self.with_vars_card)
        
        return section
    
    def _create_list_panel(self) -> QFrame:
        """Create the text entries list panel using QTableWidget for performance"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with search
        header = QWidget()
        header.setStyleSheet("background-color: #252526; border-bottom: 1px solid #3c3c3c;")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(12, 12, 12, 12)
        header_layout.setSpacing(8)
        
        # Title
        title = QLabel("Text Entries")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0;")
        header_layout.addWidget(title)
        
        # Search box
        search_layout = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 Search text...")
        self.search_box.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 4px;
                padding: 8px 12px;
                color: #e0e0e0;
                font-size: 12px;
            }
            QLineEdit:focus {
                border-color: #007acc;
            }
        """)
        self.search_box.textChanged.connect(self._filter_entries)
        search_layout.addWidget(self.search_box)
        
        # Filter dropdown
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["All", "Modified", "Over Length", "With Variables", "With Colors"])
        self.filter_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #4c4c4c;
                border-radius: 4px;
                padding: 6px 12px;
                color: #e0e0e0;
                min-width: 120px;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
            QComboBox QAbstractItemView {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                selection-background-color: #094771;
            }
        """)
        self.filter_combo.currentTextChanged.connect(self._filter_entries)
        search_layout.addWidget(self.filter_combo)
        
        header_layout.addLayout(search_layout)
        layout.addWidget(header)
        
        # Use QTableWidget for efficient handling of large datasets
        self.entries_table = QTableWidget()
        self.entries_table.setColumnCount(4)
        self.entries_table.setHorizontalHeaderLabels(["#", "Offset", "Text Preview", "Size"])
        self.entries_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.entries_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.entries_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.setShowGrid(False)
        self.entries_table.setAlternatingRowColors(True)
        
        # Column sizing
        header_view = self.entries_table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.entries_table.setColumnWidth(0, 60)
        self.entries_table.setColumnWidth(1, 90)
        self.entries_table.setColumnWidth(3, 80)
        
        # Style
        self.entries_table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                color: #d4d4d4;
                border: none;
                gridline-color: transparent;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #2d2d2d;
            }
            QTableWidget::item:selected {
                background-color: #094771;
                color: #ffffff;
            }
            QTableWidget::item:hover {
                background-color: #2a2d2e;
            }
            QHeaderView::section {
                background-color: #252526;
                color: #888;
                padding: 8px;
                border: none;
                border-bottom: 1px solid #3c3c3c;
                font-weight: bold;
                font-size: 11px;
            }
            QScrollBar:vertical {
                background-color: #1e1e1e;
                width: 10px;
            }
            QScrollBar::handle:vertical {
                background-color: #3c3c3c;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #4c4c4c;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Connect selection change
        self.entries_table.itemSelectionChanged.connect(self._on_table_selection_changed)
        
        layout.addWidget(self.entries_table, stretch=1)
        
        return panel
    
    def _create_editor_panel(self) -> QFrame:
        """Create the smart text editor panel"""
        panel = QFrame()
        panel.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Header
        header = QHBoxLayout()
        title = QLabel("Text Editor")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #e0e0e0;")
        header.addWidget(title)
        
        self.entry_info = QLabel("Select an entry to edit")
        self.entry_info.setStyleSheet("color: #888; font-size: 12px;")
        header.addWidget(self.entry_info)
        header.addStretch()
        
        # Navigation buttons
        self.prev_btn = ActionButton("◀ Prev")
        self.prev_btn.setFixedWidth(80)
        self.prev_btn.clicked.connect(self._go_prev)
        self.prev_btn.setEnabled(False)
        header.addWidget(self.prev_btn)
        
        self.next_btn = ActionButton("Next ▶")
        self.next_btn.setFixedWidth(80)
        self.next_btn.clicked.connect(self._go_next)
        self.next_btn.setEnabled(False)
        header.addWidget(self.next_btn)
        
        layout.addLayout(header)
        
        # Smart editor widget
        self.smart_editor = SmartTextEditorWidget()
        self.smart_editor.textChanged.connect(self._on_editor_text_changed)
        layout.addWidget(self.smart_editor, stretch=1)
        
        # Bottom info bar
        info_bar = QHBoxLayout()
        
        self.byte_count_label = QLabel("Bytes: 0/0")
        self.byte_count_label.setStyleSheet("color: #888; font-family: Consolas; font-size: 11px;")
        info_bar.addWidget(self.byte_count_label)
        
        info_bar.addStretch()
        
        self.apply_btn = ActionButton("Apply Changes", "✓", primary=True)
        self.apply_btn.clicked.connect(self._apply_current_edit)
        self.apply_btn.setEnabled(False)
        info_bar.addWidget(self.apply_btn)
        
        layout.addLayout(info_bar)
        
        return panel
    
    def _log_status(self, message: str):
        """Emit status update"""
        self.status_updated.emit(message)

    def _on_exe_selected(self, path: str):
        """Handle EXE file selection"""
        has_file = bool(path)
        self.load_btn.setEnabled(has_file)
        self.extract_btn.setEnabled(has_file)
        self.analyze_btn.setEnabled(has_file)
        if has_file:
            self._log_status(f"Selected: {os.path.basename(path)}")
    
    def _load_preview(self):
        """Load and preview text from EXE"""
        exe_path = self.exe_selector.path()
        if not exe_path:
            self._log_status("Error: No EXE file selected")
            return

        self._log_status(f"Loading text from {os.path.basename(exe_path)}...")
        self.load_btn.setEnabled(False)
        
        # Create temp files for extraction
        temp_dir = os.path.join(os.path.dirname(exe_path), ".temp_extract")
        os.makedirs(temp_dir, exist_ok=True)
        
        text_file = os.path.join(temp_dir, "texts.txt")
        offset_file = os.path.join(temp_dir, "offsets.txt")
        
        def do_extract():
            return extract_texts(exe_path, text_file, offset_file)
        
        worker = WorkerThread(do_extract)
        worker.finished.connect(lambda: self._on_load_complete(text_file, offset_file, temp_dir))
        worker.error.connect(lambda e: self._on_load_error(e))
        self.workers.append(worker)
        worker.start()
    
    def _on_load_complete(self, text_file: str, offset_file: str, temp_dir: str):
        """Handle successful load"""
        try:
            # Read data
            with open(text_file, 'r', encoding='utf-8') as f:
                texts = f.readlines()
            with open(offset_file, 'r', encoding='utf-8') as f:
                offsets = f.readlines()
            
            # Parse entries
            self.entries = []
            for text_line, offset_line in zip(texts, offsets):
                text = text_line.rstrip('\n')
                offset_line = offset_line.strip()
                
                if ':' in offset_line:
                    offset, length = offset_line.split(':', 1)
                    length = int(length)
                else:
                    offset = offset_line
                    length = len(text.encode('utf-8'))
                
                self.entries.append({
                    'offset': offset,
                    'length': length,
                    'original_text': text,
                    'current_text': text,
                    'modified': False
                })
            
            # Update UI
            self._populate_list()
            self._update_stats()
            self.save_btn.setEnabled(True)
            self._log_status(f"Loaded {len(self.entries)} text entries")
            
            # Cleanup temp files
            os.remove(text_file)
            os.remove(offset_file)
            os.rmdir(temp_dir)
            
        except Exception as e:
            self._log_status(f"Error loading: {str(e)}")
        finally:
            self.load_btn.setEnabled(True)
    
    def _on_load_error(self, error: str):
        """Handle load error"""
        self._log_status(f"Error: {error}")
        self.load_btn.setEnabled(True)
    
    def _populate_list(self):
        """Populate the text entries table efficiently"""
        self.entries_table.setUpdatesEnabled(False)  # Disable updates for speed
        self.entries_table.setRowCount(0)  # Clear
        self.entries_table.setRowCount(len(self.entries))
        
        for i, entry in enumerate(self.entries):
            # Index column
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            idx_item.setForeground(QColor("#569cd6"))
            self.entries_table.setItem(i, 0, idx_item)
            
            # Offset column
            offset_item = QTableWidgetItem(entry['offset'])
            offset_item.setForeground(QColor("#666"))
            self.entries_table.setItem(i, 1, offset_item)
            
            # Text preview column
            preview = get_text_preview(entry['current_text'])
            text_item = QTableWidgetItem(preview)
            self.entries_table.setItem(i, 2, text_item)
            
            # Size column with color coding
            current_bytes = len(entry['current_text'].encode('utf-8'))
            size_item = QTableWidgetItem(f"{current_bytes}/{entry['length']}")
            size_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            
            if current_bytes > entry['length']:
                size_item.setForeground(QColor("#f14c4c"))  # Red
            elif current_bytes < entry['length']:
                size_item.setForeground(QColor("#dcdcaa"))  # Yellow
            else:
                size_item.setForeground(QColor("#4ec9b0"))  # Green
            
            self.entries_table.setItem(i, 3, size_item)
        
        self.entries_table.setUpdatesEnabled(True)  # Re-enable updates
    
    def _on_table_selection_changed(self):
        """Handle table row selection - load into editor"""
        selected = self.entries_table.selectedItems()
        if not selected:
            return
        
        index = selected[0].row()
        if 0 <= index < len(self.entries):
            self.current_index = index
            entry = self.entries[index]
            
            self.smart_editor.setText(entry['current_text'])
            self.entry_info.setText(f"Entry #{index + 1} | Offset: {entry['offset']}")
            
            current_bytes = len(entry['current_text'].encode('utf-8'))
            self.byte_count_label.setText(f"Bytes: {current_bytes}/{entry['length']}")
            self._update_byte_count_style(current_bytes, entry['length'])
            
            self.apply_btn.setEnabled(True)
            self.prev_btn.setEnabled(index > 0)
            self.next_btn.setEnabled(index < len(self.entries) - 1)
    
    def _on_editor_text_changed(self, text: str):
        """Handle editor text changes"""
        if self.current_index < 0:
            return
        
        entry = self.entries[self.current_index]
        current_bytes = len(text.encode('utf-8'))
        self.byte_count_label.setText(f"Bytes: {current_bytes}/{entry['length']}")
        self._update_byte_count_style(current_bytes, entry['length'])
    
    def _update_byte_count_style(self, current: int, max_bytes: int):
        """Update byte count label color based on length"""
        if current > max_bytes:
            self.byte_count_label.setStyleSheet("color: #f14c4c; font-family: Consolas; font-size: 11px;")
        elif current < max_bytes:
            self.byte_count_label.setStyleSheet("color: #dcdcaa; font-family: Consolas; font-size: 11px;")
        else:
            self.byte_count_label.setStyleSheet("color: #4ec9b0; font-family: Consolas; font-size: 11px;")
    
    def _apply_current_edit(self):
        """Apply changes from editor to current entry"""
        if self.current_index < 0:
            return
        
        new_text = self.smart_editor.text()
        entry = self.entries[self.current_index]
        
        # Check if modified
        entry['current_text'] = new_text
        entry['modified'] = (new_text != entry['original_text'])
        
        # Update the table row
        i = self.current_index
        
        # Update text preview
        preview = get_text_preview(new_text)
        text_item = self.entries_table.item(i, 2)
        if text_item:
            text_item.setText(preview)
        
        # Update size with color coding
        current_bytes = len(new_text.encode('utf-8'))
        size_item = self.entries_table.item(i, 3)
        if size_item:
            size_item.setText(f"{current_bytes}/{entry['length']}")
            if current_bytes > entry['length']:
                size_item.setForeground(QColor("#f14c4c"))
            elif current_bytes < entry['length']:
                size_item.setForeground(QColor("#dcdcaa"))
            else:
                size_item.setForeground(QColor("#4ec9b0"))
        
        self._update_stats()
        self._log_status(f"Applied changes to entry #{self.current_index + 1}")
    
    def _go_prev(self):
        """Go to previous entry"""
        if self.current_index > 0:
            self.entries_table.selectRow(self.current_index - 1)
    
    def _go_next(self):
        """Go to next entry"""
        if self.current_index < len(self.entries) - 1:
            self.entries_table.selectRow(self.current_index + 1)
    
    def _filter_entries(self):
        """Filter entries based on search and filter"""
        search = self.search_box.text().lower()
        filter_type = self.filter_combo.currentText()
        
        for i, entry in enumerate(self.entries):
            text = entry['current_text'].lower()
            
            # Search filter
            matches_search = not search or search in text
            
            # Type filter
            matches_type = True
            if filter_type == "Modified":
                matches_type = entry['modified']
            elif filter_type == "Over Length":
                current_bytes = len(entry['current_text'].encode('utf-8'))
                matches_type = current_bytes > entry['length']
            elif filter_type == "With Variables":
                matches_type = bool(re.search(r'%\d*[sd]', entry['current_text']))
            elif filter_type == "With Colors":
                matches_type = bool(re.search(r'%\d+c', entry['current_text']))
            
            self.entries_table.setRowHidden(i, not (matches_search and matches_type))
    
    def _update_stats(self):
        """Update statistics cards"""
        total = len(self.entries)
        modified = sum(1 for e in self.entries if e['modified'])
        overlength = sum(1 for e in self.entries 
                        if len(e['current_text'].encode('utf-8')) > e['length'])
        with_vars = sum(1 for e in self.entries 
                       if re.search(r'%\d*[sd]', e['current_text']))
        
        self.total_card.setValue(str(total))
        self.modified_card.setValue(str(modified))
        self.overlength_card.setValue(str(overlength))
        self.with_vars_card.setValue(str(with_vars))
        
        if overlength > 0:
            self.overlength_card.value_label.setStyleSheet(
                "color: #f14c4c; font-size: 24px; font-weight: bold;")
        else:
            self.overlength_card.value_label.setStyleSheet(
                "color: #4ec9b0; font-size: 24px; font-weight: bold;")
    
    def _extract_to_files(self):
        """Extract text to files"""
        exe_path = self.exe_selector.path()
        output_dir = self.output_selector.path()
        
        if not exe_path:
            self._log_status("Error: No EXE file selected")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        text_file = os.path.join(output_dir, "extracted_texts.txt")
        offset_file = os.path.join(output_dir, "text_offsets.txt")
        
        self._log_status(f"Extracting to {output_dir}...")
        
        worker = WorkerThread(extract_texts, [exe_path, text_file, offset_file])
        worker.finished.connect(lambda: self._log_status(f"Extracted to {output_dir}"))
        worker.error.connect(lambda e: self._log_status(f"Error: {e}"))
        self.workers.append(worker)
        worker.start()
    
    def _save_changes(self):
        """Save all changes back to EXE"""
        if not self.entries:
            self._log_status("Error: No text loaded")
            return

        exe_path = self.exe_selector.path()
        if not exe_path:
            self._log_status("Error: No EXE file selected")
            return

        # Create temp files for import
        temp_dir = os.path.join(os.path.dirname(exe_path), ".temp_import")
        os.makedirs(temp_dir, exist_ok=True)
            
        text_file = os.path.join(temp_dir, "texts.txt")
        offset_file = os.path.join(temp_dir, "offsets.txt")
        
        # Write current state
        with open(text_file, 'w', encoding='utf-8') as tf, \
             open(offset_file, 'w', encoding='utf-8') as of:
            for entry in self.entries:
                tf.write(entry['current_text'] + '\n')
                of.write(f"{entry['offset']}:{entry['length']}\n")
        
            output_exe = exe_path.replace(".exe", "_modified.exe")
        self._log_status(f"Saving to {os.path.basename(output_exe)}...")
        
        def do_import():
            return import_texts(exe_path, text_file, offset_file, output_exe)
        
        def cleanup():
            os.remove(text_file)
            os.remove(offset_file)
            os.rmdir(temp_dir)
            self._log_status(f"Saved to {os.path.basename(output_exe)}")
        
        worker = WorkerThread(do_import)
        worker.finished.connect(cleanup)
        worker.error.connect(lambda e: self._log_status(f"Error: {e}"))
        self.workers.append(worker)
        worker.start()
    
    def _analyze_text(self):
        """Analyze text patterns"""
        exe_path = self.exe_selector.path()
        if not exe_path:
            self._log_status("Error: No EXE file selected")
            return
            
        self._log_status("Analyzing text patterns...")
        
        worker = WorkerThread(analyze_text_patterns, [exe_path])
        worker.result.connect(self._show_analysis)
        worker.error.connect(lambda e: self._log_status(f"Error: {e}"))
        self.workers.append(worker)
        worker.start()
    
    def _show_analysis(self, stats: dict):
        """Display analysis results"""
        if not stats:
            return
        
        self._log_status("=" * 50)
        self._log_status("TEXT ANALYSIS RESULTS")
        self._log_status("=" * 50)
        self._log_status(f"Total entries: {stats['total_texts']}")
        self._log_status(f"With \\k (pause): {stats['with_k']}")
        self._log_status(f"With \\r modifier: {stats['with_r']}")
        self._log_status(f"With \\h header: {stats['with_h']}")
        self._log_status(f"With color codes: {stats['with_colors']}")
        self._log_status(f"With positions: {stats['with_positions']}")
        self._log_status(f"With variables: {stats['with_variables']}")
        self._log_status(f"Length range: {stats['min_length']}-{stats['max_length']} chars")
        self._log_status(f"Average length: {stats['avg_length']:.1f} chars")
        self._log_status("=" * 50)

    def closeEvent(self, event):
        """Clean up workers"""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept() 
