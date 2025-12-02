"""
Video Tools Tab for Dokapon SoF Tools.
Provides video conversion and replacement for game cutscenes.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QComboBox, QProgressBar, QMessageBox,
    QAbstractItemView, QSplitter, QSpinBox, QCheckBox
)
from PyQt6.QtCore import pyqtSignal, Qt, QThread
from PyQt6.QtGui import QColor, QDragEnterEvent, QDropEvent
from ..widgets.worker import WorkerThread
from app.core.video_converter import (
    VideoConverter, VideoInfo, ConversionSettings,
    find_game_videos, backup_video, get_supported_input_formats
)
from app.core.tool_manager import ToolManager
from ..styles import COLORS
import os


class VideoConversionWorker(QThread):
    """Worker thread for video conversion."""
    progress = pyqtSignal(float)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, converter, input_path, output_path, settings):
        super().__init__()
        self.converter = converter
        self.input_path = input_path
        self.output_path = output_path
        self.settings = settings
    
    def run(self):
        try:
            success, message = self.converter.convert_to_game_format(
                self.input_path,
                self.output_path,
                self.settings,
                progress_callback=self.progress.emit
            )
            self.finished.emit(success, message)
        except Exception as e:
            self.finished.emit(False, str(e))


class VideoTab(QWidget):
    """Video Tools tab for cutscene replacement."""
    
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers = []
        self.game_videos = []       # List of found game OGV files
        self.replacement_queue = {} # {ogv_path: mp4_path}
        self.converter = None
        self._init_ui()
        self._check_ffmpeg()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        
        # FFmpeg status
        self.ffmpeg_status = QLabel()
        self.ffmpeg_status.setStyleSheet(f"padding: 8px; border-radius: 4px;")
        layout.addWidget(self.ffmpeg_status)
        
        # Game directory selection
        dir_group = QGroupBox("Game Directory")
        dir_layout = QVBoxLayout(dir_group)
        
        dir_row = QHBoxLayout()
        dir_row.addWidget(QLabel("Game Folder:"))
        self.game_dir_label = QLabel("No folder selected")
        self.game_dir_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        dir_row.addWidget(self.game_dir_label, 1)
        
        select_dir_btn = QPushButton("Select Folder")
        select_dir_btn.clicked.connect(self._select_game_dir)
        dir_row.addWidget(select_dir_btn)
        dir_layout.addLayout(dir_row)
        
        layout.addWidget(dir_group)
        
        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Game videos
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        left_layout.addWidget(QLabel("Game Videos (OGV)"))
        
        self.game_video_table = QTableWidget()
        self.game_video_table.setColumnCount(4)
        self.game_video_table.setHorizontalHeaderLabels(["Name", "Resolution", "Duration", "Size"])
        self.game_video_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.game_video_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.game_video_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.game_video_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.game_video_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.game_video_table.setAcceptDrops(True)
        self.game_video_table.dragEnterEvent = self._drag_enter_event
        self.game_video_table.dropEvent = self._drop_event
        left_layout.addWidget(self.game_video_table)
        
        splitter.addWidget(left_panel)
        
        # Right panel: Replacement queue
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_header = QHBoxLayout()
        right_header.addWidget(QLabel("Replacement Queue"))
        right_header.addStretch()
        
        add_btn = QPushButton("Add Replacement")
        add_btn.clicked.connect(self._add_replacement)
        right_header.addWidget(add_btn)
        right_layout.addLayout(right_header)
        
        self.queue_table = QTableWidget()
        self.queue_table.setColumnCount(4)
        self.queue_table.setHorizontalHeaderLabels(["Target", "Source", "Status", "Progress"])
        self.queue_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.queue_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.queue_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.queue_table.setColumnWidth(3, 100)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        right_layout.addWidget(self.queue_table)
        
        # Queue buttons
        queue_btn_layout = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)
        queue_btn_layout.addWidget(remove_btn)
        
        clear_btn = QPushButton("Clear Queue")
        clear_btn.clicked.connect(self._clear_queue)
        queue_btn_layout.addWidget(clear_btn)
        queue_btn_layout.addStretch()
        right_layout.addLayout(queue_btn_layout)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter, 1)
        
        # Conversion settings
        settings_group = QGroupBox("Conversion Settings")
        settings_layout = QHBoxLayout(settings_group)
        
        settings_layout.addWidget(QLabel("Quality:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["Default (Balanced)", "High Quality", "Fast (Lower Quality)"])
        settings_layout.addWidget(self.quality_combo)
        
        settings_layout.addWidget(QLabel("Resolution:"))
        self.width_spin = QSpinBox()
        self.width_spin.setRange(320, 1920)
        self.width_spin.setValue(1280)
        settings_layout.addWidget(self.width_spin)
        
        settings_layout.addWidget(QLabel("x"))
        self.height_spin = QSpinBox()
        self.height_spin.setRange(240, 1080)
        self.height_spin.setValue(720)
        settings_layout.addWidget(self.height_spin)
        
        self.backup_checkbox = QCheckBox("Backup originals")
        self.backup_checkbox.setChecked(True)
        settings_layout.addWidget(self.backup_checkbox)
        
        settings_layout.addStretch()
        layout.addWidget(settings_group)
        
        # Progress and action buttons
        bottom_layout = QHBoxLayout()
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        bottom_layout.addWidget(self.status_label)
        
        bottom_layout.addStretch()
        
        self.convert_btn = QPushButton("Convert && Replace")
        self.convert_btn.setProperty("class", "primary")
        self.convert_btn.setEnabled(False)
        self.convert_btn.clicked.connect(self._start_conversion)
        bottom_layout.addWidget(self.convert_btn)
        
        layout.addLayout(bottom_layout)
        
        # Overall progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

    def _check_ffmpeg(self):
        """Check if FFmpeg is available."""
        tool_manager = ToolManager.get_instance()
        available, message = tool_manager.verify_tool("ffmpeg")
        
        if available:
            self.ffmpeg_status.setText(f"FFmpeg: {message}")
            self.ffmpeg_status.setStyleSheet(
                f"background-color: {COLORS['bg_tertiary']}; "
                f"color: {COLORS['accent_success']}; "
                f"padding: 8px; border-radius: 4px;"
            )
            self.converter = VideoConverter(
                tool_manager.get_ffmpeg_path(),
                tool_manager.get_ffprobe_path()
            )
        else:
            self.ffmpeg_status.setText(f"FFmpeg not found: {message}")
            self.ffmpeg_status.setStyleSheet(
                f"background-color: {COLORS['bg_tertiary']}; "
                f"color: {COLORS['accent_error']}; "
                f"padding: 8px; border-radius: 4px;"
            )
            self.convert_btn.setEnabled(False)

    def _select_game_dir(self):
        """Select game directory to find video files."""
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if path:
            self._load_game_dir(path)

    def _load_game_dir(self, path: str):
        """Load game directory and find video files."""
        self.game_dir_label.setText(path)
        self.game_videos = find_game_videos(path)
        self._populate_game_videos()
        self._log_status(f"Found {len(self.game_videos)} video file(s)")

    def _populate_game_videos(self):
        """Populate the game videos table."""
        self.game_video_table.setRowCount(0)
        
        for i, video_path in enumerate(self.game_videos):
            self.game_video_table.insertRow(i)
            
            # Name
            name_item = QTableWidgetItem(os.path.basename(video_path))
            name_item.setData(Qt.ItemDataRole.UserRole, video_path)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.game_video_table.setItem(i, 0, name_item)
            
            # Get video info if converter available
            if self.converter:
                info = self.converter.get_video_info(video_path)
                
                # Resolution
                res_item = QTableWidgetItem(info.resolution if info.width else "Unknown")
                res_item.setFlags(res_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.game_video_table.setItem(i, 1, res_item)
                
                # Duration
                dur_item = QTableWidgetItem(info.duration_str if info.duration else "Unknown")
                dur_item.setFlags(dur_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.game_video_table.setItem(i, 2, dur_item)
                
                # Size
                size_item = QTableWidgetItem(info.file_size_str)
                size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.game_video_table.setItem(i, 3, size_item)
            else:
                for col in range(1, 4):
                    item = QTableWidgetItem("N/A")
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    self.game_video_table.setItem(i, col, item)

    def _add_replacement(self):
        """Add a replacement video for selected game video."""
        selected_rows = list(set(item.row() for item in self.game_video_table.selectedItems()))
        
        if not selected_rows:
            self._log_status("Error: Select a game video to replace first")
            return
        
        # Get supported formats
        formats = get_supported_input_formats()
        filter_str = "Video Files (" + " ".join(f"*{ext}" for ext in formats) + ")"
        
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Replacement Video",
            "",
            f"{filter_str};;All Files (*)"
        )
        
        if not path:
            return
        
        for row in selected_rows:
            target_path = self.game_video_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.replacement_queue[target_path] = path
        
        self._update_queue_table()
        self._update_convert_button()
        self._log_status(f"Queued {len(selected_rows)} replacement(s)")

    def _update_queue_table(self):
        """Update the replacement queue table."""
        self.queue_table.setRowCount(0)
        
        for i, (target, source) in enumerate(self.replacement_queue.items()):
            self.queue_table.insertRow(i)
            
            # Target
            target_item = QTableWidgetItem(os.path.basename(target))
            target_item.setData(Qt.ItemDataRole.UserRole, target)
            target_item.setFlags(target_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 0, target_item)
            
            # Source
            source_item = QTableWidgetItem(os.path.basename(source))
            source_item.setData(Qt.ItemDataRole.UserRole, source)
            source_item.setFlags(source_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 1, source_item)
            
            # Status
            status_item = QTableWidgetItem("Pending")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setForeground(QColor(COLORS['accent_warning']))
            self.queue_table.setItem(i, 2, status_item)
            
            # Progress bar placeholder
            progress_item = QTableWidgetItem("")
            progress_item.setFlags(progress_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.queue_table.setItem(i, 3, progress_item)

    def _remove_selected(self):
        """Remove selected items from queue."""
        selected_rows = sorted(set(item.row() for item in self.queue_table.selectedItems()), reverse=True)
        
        for row in selected_rows:
            target = self.queue_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if target in self.replacement_queue:
                del self.replacement_queue[target]
        
        self._update_queue_table()
        self._update_convert_button()

    def _clear_queue(self):
        """Clear the replacement queue."""
        self.replacement_queue.clear()
        self._update_queue_table()
        self._update_convert_button()
        self._log_status("Cleared replacement queue")

    def _update_convert_button(self):
        """Update convert button state."""
        has_queue = len(self.replacement_queue) > 0
        has_ffmpeg = self.converter is not None
        self.convert_btn.setEnabled(has_queue and has_ffmpeg)

    def _get_settings(self) -> ConversionSettings:
        """Get conversion settings from UI."""
        quality_map = {
            0: ConversionSettings.default,
            1: ConversionSettings.high_quality,
            2: ConversionSettings.fast,
        }
        
        settings = quality_map.get(self.quality_combo.currentIndex(), ConversionSettings.default)()
        settings.width = self.width_spin.value()
        settings.height = self.height_spin.value()
        
        return settings

    def _start_conversion(self):
        """Start the conversion process."""
        if not self.converter:
            QMessageBox.critical(self, "Error", "FFmpeg is not available")
            return
        
        if not self.replacement_queue:
            return
        
        settings = self._get_settings()
        total = len(self.replacement_queue)
        
        self._log_status(f"Starting conversion of {total} video(s)...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.convert_btn.setEnabled(False)
        
        # Process queue
        self.current_conversion_index = 0
        self.conversion_queue = list(self.replacement_queue.items())
        self._process_next_video()

    def _process_next_video(self):
        """Process the next video in queue."""
        if self.current_conversion_index >= len(self.conversion_queue):
            self._on_all_conversions_complete()
            return
        
        target, source = self.conversion_queue[self.current_conversion_index]
        settings = self._get_settings()
        
        # Update status
        self._update_row_status(self.current_conversion_index, "Converting...", COLORS['accent_primary'])
        self._log_status(f"Converting: {os.path.basename(source)} -> {os.path.basename(target)}")
        
        # Backup if enabled
        if self.backup_checkbox.isChecked():
            backup_video(target)
        
        # Start worker
        worker = VideoConversionWorker(self.converter, source, target, settings)
        worker.progress.connect(lambda p: self._on_progress(p, self.current_conversion_index))
        worker.finished.connect(self._on_video_complete)
        
        self.workers.append(worker)
        worker.start()

    def _on_progress(self, progress: float, row: int):
        """Handle conversion progress update."""
        # Update overall progress
        total_progress = (self.current_conversion_index + progress) / len(self.conversion_queue) * 100
        self.progress_bar.setValue(int(total_progress))

    def _on_video_complete(self, success: bool, message: str):
        """Handle single video conversion completion."""
        if success:
            self._update_row_status(self.current_conversion_index, "Done", COLORS['accent_success'])
            self._log_status(f"  Success: {message}")
        else:
            self._update_row_status(self.current_conversion_index, "Failed", COLORS['accent_error'])
            self._log_status(f"  Error: {message}")
        
        # Process next
        self.current_conversion_index += 1
        self._process_next_video()

    def _on_all_conversions_complete(self):
        """Handle completion of all conversions."""
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.convert_btn.setEnabled(True)
        
        self._log_status("All conversions complete!")
        
        QMessageBox.information(
            self,
            "Complete",
            f"Processed {len(self.conversion_queue)} video(s)."
        )

    def _update_row_status(self, row: int, status: str, color: str):
        """Update status of a row in the queue table."""
        if row < self.queue_table.rowCount():
            status_item = self.queue_table.item(row, 2)
            if status_item:
                status_item.setText(status)
                status_item.setForeground(QColor(color))

    def _drag_enter_event(self, event: QDragEnterEvent):
        """Handle drag enter for file drops."""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def _drop_event(self, event: QDropEvent):
        """Handle file drop for replacement."""
        urls = event.mimeData().urls()
        if not urls:
            return
        
        file_path = urls[0].toLocalFile()
        
        # Check if valid video format
        supported = get_supported_input_formats()
        if not any(file_path.lower().endswith(ext) for ext in supported):
            self._log_status(f"Unsupported format. Supported: {', '.join(supported)}")
            return
        
        # Get row under cursor
        pos = event.position().toPoint()
        row = self.game_video_table.rowAt(pos.y())
        
        if row >= 0:
            target_path = self.game_video_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            self.replacement_queue[target_path] = file_path
            self._update_queue_table()
            self._update_convert_button()
            self._log_status(f"Queued replacement for: {os.path.basename(target_path)}")

    def _log_status(self, message: str):
        """Emit status update."""
        self.status_updated.emit(message)
        self.status_label.setText(message)

    def closeEvent(self, event):
        """Clean up worker threads when closing."""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept()

