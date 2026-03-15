"""
Main window for Dokapon SoF Tools GUI.
Features a modern VS Code-like interface with sidebar navigation.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QTextEdit, QProgressBar, QStackedWidget,
    QPushButton, QFileDialog, QSizePolicy
)
from PyQt6.QtGui import QIcon, QTextCursor
from PyQt6.QtCore import Qt, QSettings
from .widgets.sidebar import ModernSidebar
from .tabs.asset_tab import AssetExtractorTab
from .tabs.text_tab import TextTab
from .tabs.voice_tab import VoiceExtractorTab
from .tabs.hex_tab import HexEditorTab
from .tabs.video_tab import VideoTab
from .tabs.map_tab import MapExplorerTab
from .tabs.about_tab import AboutTab
from .styles import COLORS
from datetime import datetime
import os


class DokaponToolsGUI(QMainWindow):
    """Main application window with modern sidebar navigation."""

    TAB_ASSET, TAB_TEXT, TAB_VOICE, TAB_HEX, TAB_VIDEO, TAB_MAP, TAB_ABOUT = range(7)

    def __init__(self):
        super().__init__()
        self._settings = QSettings("DiNaSoR", "DokaponSoFTools")
        self._init_ui()
        # Restore last game path
        saved = self._settings.value("game_path", "")
        if saved and os.path.isdir(saved):
            self._set_game_path(saved)

    def _init_ui(self):
        """Initialize the main window UI."""
        self.setWindowTitle("Dokapon SoF Tools - By DiNaSoR")
        self.setMinimumSize(1000, 700)

        # Set window icon
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "resources", "icon.ico"
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Create central widget with horizontal layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create sidebar
        self.sidebar = ModernSidebar()
        self.sidebar.navigation_changed.connect(self._on_navigation_changed)
        main_layout.addWidget(self.sidebar)

        # Create content area
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 12, 16, 16)
        content_layout.setSpacing(10)

        # --- Game path bar (single source of truth) ---
        game_path_bar = self._create_game_path_bar()
        content_layout.addWidget(game_path_bar)

        # Create stacked widget for views
        self.stacked_widget = QStackedWidget()

        # Create tabs
        self.asset_tab = AssetExtractorTab()
        self.text_tab = TextTab()
        self.voice_tab = VoiceExtractorTab()
        self.hex_tab = HexEditorTab()
        self.video_tab = VideoTab()
        self.map_tab = MapExplorerTab()
        self.about_tab = AboutTab()

        # Ordered list of tool tabs (excludes About)
        self._tool_tabs = [
            self.asset_tab,
            self.text_tab,
            self.voice_tab,
            self.hex_tab,
            self.video_tab,
            self.map_tab,
        ]

        self.stacked_widget.addWidget(self.asset_tab)
        self.stacked_widget.addWidget(self.text_tab)
        self.stacked_widget.addWidget(self.voice_tab)
        self.stacked_widget.addWidget(self.hex_tab)
        self.stacked_widget.addWidget(self.video_tab)
        self.stacked_widget.addWidget(self.map_tab)
        self.stacked_widget.addWidget(self.about_tab)

        content_layout.addWidget(self.stacked_widget, stretch=1)

        # Connect status signals from all tool tabs
        for tab in self._tool_tabs:
            tab.status_updated.connect(self._update_status)

        # Create status panel
        status_panel = self._create_status_panel()
        content_layout.addWidget(status_panel)

        main_layout.addWidget(content_widget, stretch=1)

    # ------------------------------------------------------------------ #
    #  Game path bar
    # ------------------------------------------------------------------ #

    def _create_game_path_bar(self) -> QWidget:
        """Create the global game directory bar."""
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {COLORS['bg_secondary']}; "
            f"border: 1px solid {COLORS['border_primary']}; "
            f"border-radius: 6px;"
        )
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        icon_label = QLabel("🎮")
        icon_label.setStyleSheet("border: none; font-size: 16px;")
        layout.addWidget(icon_label)

        title = QLabel("Game Directory:")
        title.setStyleSheet(
            f"border: none; color: {COLORS['text_secondary']}; "
            f"font-weight: 600; font-size: 12px;"
        )
        layout.addWidget(title)

        self.game_path_label = QLabel("Not set — click Browse to select your game folder")
        self.game_path_label.setStyleSheet(
            f"border: none; color: {COLORS['text_primary']}; "
            f"font-family: Consolas; font-size: 12px;"
        )
        self.game_path_label.setWordWrap(False)
        layout.addWidget(self.game_path_label, stretch=1)

        browse_btn = QPushButton("Browse")
        browse_btn.setProperty("class", "primary")
        browse_btn.setFixedHeight(28)
        browse_btn.setMinimumWidth(80)
        browse_btn.setStyleSheet(
            f"background-color: {COLORS['accent_primary']}; "
            f"color: {COLORS['text_bright']}; border: none; "
            f"border-radius: 4px; padding: 4px 14px; font-weight: 600;"
        )
        browse_btn.clicked.connect(self._browse_game_path)
        layout.addWidget(browse_btn)

        return bar

    def _browse_game_path(self):
        """Open a directory dialog to select the game folder."""
        start = self._settings.value("game_path", "")
        path = QFileDialog.getExistingDirectory(
            self, "Select Dokapon Game Directory", start
        )
        if path:
            self._set_game_path(path)

    def _set_game_path(self, path: str):
        """Set the game path and propagate to all tabs."""
        # Shorten for display
        display = path if len(path) < 80 else "..." + path[-77:]
        self.game_path_label.setText(display)
        self.game_path_label.setToolTip(path)

        # Persist
        self._settings.setValue("game_path", path)

        # Propagate to every tool tab
        for tab in self._tool_tabs:
            tab.set_game_path(path)

        self._update_status(f"Game directory set to: {path}")

    # ------------------------------------------------------------------ #
    #  Status panel
    # ------------------------------------------------------------------ #

    def _create_status_panel(self) -> QWidget:
        """Create the status panel with log, progress bar, and controls."""
        panel = QWidget()
        panel.setMaximumHeight(220)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # Header with title and buttons
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        status_label = QLabel("Status Log")
        status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-weight: 600;")
        header_layout.addWidget(status_label)

        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._clear_status_log)
        header_layout.addWidget(clear_btn)

        save_btn = QPushButton("Save Log")
        save_btn.setMinimumWidth(90)
        save_btn.clicked.connect(self._save_status_log)
        header_layout.addWidget(save_btn)

        layout.addLayout(header_layout)

        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(120)
        self.status_text.setPlaceholderText("Activity log will appear here...")
        layout.addWidget(self.status_text)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)

        return panel

    # ------------------------------------------------------------------ #
    #  Navigation
    # ------------------------------------------------------------------ #

    def _on_navigation_changed(self, index: int):
        """Handle sidebar navigation changes."""
        self.stacked_widget.setCurrentIndex(index)

        if index == self.TAB_ABOUT:
            if hasattr(self.about_tab, 'media_player'):
                self.about_tab.media_player.play()
        else:
            if hasattr(self.about_tab, 'media_player'):
                self.about_tab.media_player.pause()

    # ------------------------------------------------------------------ #
    #  Status helpers
    # ------------------------------------------------------------------ #

    def _update_status(self, message: str):
        """Update status text area with a new timestamped message."""
        timestamp = datetime.now().strftime("%H:%M:%S")

        color = COLORS["text_primary"]
        if "error" in message.lower() or "failed" in message.lower():
            color = COLORS["accent_error"]
        elif "success" in message.lower() or "complete" in message.lower():
            color = COLORS["accent_success"]
        elif "warning" in message.lower():
            color = COLORS["accent_warning"]

        formatted = f'<span style="color: {COLORS["text_secondary"]}">[{timestamp}]</span> '
        formatted += f'<span style="color: {color}">{message}</span>'

        self.status_text.append(formatted)

        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)

    def _clear_status_log(self):
        self.status_text.clear()

    def _save_status_log(self):
        view_names = ["asset_extractor", "text_tools", "voice_tools",
                      "hex_editor", "video_tools", "map_explorer", "about"]
        current_view = view_names[self.stacked_widget.currentIndex()]

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{current_view}_log_{timestamp}.txt"

        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Status Log", default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.status_text.toPlainText())
                self._update_status(f"Log saved to: {file_path}")
            except Exception as e:
                self._update_status(f"Error saving log: {str(e)}")

    def set_progress(self, value: int):
        self.progress_bar.setValue(value)

    def reset_progress(self):
        self.progress_bar.setValue(0)

    def closeEvent(self, event):
        if hasattr(self.about_tab, 'media_player'):
            self.about_tab.media_player.stop()

        for tab in self._tool_tabs:
            for worker in tab.workers:
                if worker.isRunning():
                    worker.quit()
                    worker.wait(1000)

        event.accept()
