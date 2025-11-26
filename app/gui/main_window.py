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
from PyQt6.QtCore import Qt, QTimer
from .widgets.sidebar import ModernSidebar
from .tabs.asset_tab import AssetExtractorTab
from .tabs.text_tab import TextTab
from .tabs.voice_tab import VoiceExtractorTab
from .tabs.about_tab import AboutTab
from .styles import COLORS
from datetime import datetime
import os


class DokaponToolsGUI(QMainWindow):
    """Main application window with modern sidebar navigation."""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
    
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
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)
        
        # Create stacked widget for views
        self.stacked_widget = QStackedWidget()
        
        # Create and add tabs/views
        self.asset_tab = AssetExtractorTab()
        self.text_tab = TextTab()
        self.voice_tab = VoiceExtractorTab()
        self.about_tab = AboutTab()
        
        self.stacked_widget.addWidget(self.asset_tab)
        self.stacked_widget.addWidget(self.text_tab)
        self.stacked_widget.addWidget(self.voice_tab)
        self.stacked_widget.addWidget(self.about_tab)
        
        content_layout.addWidget(self.stacked_widget, stretch=1)
        
        # Connect status signals from all tabs
        self.asset_tab.status_updated.connect(self._update_status)
        self.text_tab.status_updated.connect(self._update_status)
        self.voice_tab.status_updated.connect(self._update_status)
        
        # Create status panel
        status_panel = self._create_status_panel()
        content_layout.addWidget(status_panel)
        
        main_layout.addWidget(content_widget, stretch=1)
    
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
        
        # Clear log button
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedWidth(70)
        clear_btn.clicked.connect(self._clear_status_log)
        header_layout.addWidget(clear_btn)
        
        # Save log button
        save_btn = QPushButton("Save Log")
        save_btn.setFixedWidth(80)
        save_btn.clicked.connect(self._save_status_log)
        header_layout.addWidget(save_btn)
        
        layout.addLayout(header_layout)
        
        # Status text area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMinimumHeight(120)
        self.status_text.setPlaceholderText("Activity log will appear here...")
        layout.addWidget(self.status_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        return panel
    
    def _on_navigation_changed(self, index: int):
        """Handle sidebar navigation changes."""
        self.stacked_widget.setCurrentIndex(index)
        
        # Handle about tab music
        if index == 3:  # About tab
            if hasattr(self.about_tab, 'media_player'):
                self.about_tab.media_player.play()
        else:
            if hasattr(self.about_tab, 'media_player'):
                self.about_tab.media_player.pause()
    
    def _update_status(self, message: str):
        """
        Update status text area with a new timestamped message.
        Auto-scrolls to show the latest entry.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Determine message type and color
        color = COLORS["text_primary"]
        if "error" in message.lower() or "failed" in message.lower():
            color = COLORS["accent_error"]
        elif "success" in message.lower() or "complete" in message.lower():
            color = COLORS["accent_success"]
        elif "warning" in message.lower():
            color = COLORS["accent_warning"]
        
        # Format and append message
        formatted = f'<span style="color: {COLORS["text_secondary"]}">[{timestamp}]</span> '
        formatted += f'<span style="color: {color}">{message}</span>'
        
        self.status_text.append(formatted)
        
        # Auto-scroll to bottom
        cursor = self.status_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.status_text.setTextCursor(cursor)
    
    def _clear_status_log(self):
        """Clear the status log."""
        self.status_text.clear()
    
    def _save_status_log(self):
        """Save status log to a text file."""
        # Get current view name for filename
        view_names = ["asset_extractor", "text_tools", "voice_tools", "about"]
        current_view = view_names[self.stacked_widget.currentIndex()]
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{current_view}_log_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Status Log",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    # Convert HTML to plain text
                    f.write(self.status_text.toPlainText())
                self._update_status(f"Log saved to: {file_path}")
            except Exception as e:
                self._update_status(f"Error saving log: {str(e)}")
    
    def set_progress(self, value: int):
        """Set progress bar value (0-100)."""
        self.progress_bar.setValue(value)
    
    def reset_progress(self):
        """Reset progress bar to 0."""
        self.progress_bar.setValue(0)
    
    def closeEvent(self, event):
        """Clean up resources when closing the window."""
        # Stop about tab music
        if hasattr(self.about_tab, 'media_player'):
            self.about_tab.media_player.stop()
        
        # Clean up workers in each tab
        for tab in [self.asset_tab, self.text_tab, self.voice_tab]:
            if hasattr(tab, 'workers'):
                for worker in tab.workers:
                    if worker.isRunning():
                        worker.quit()
                        worker.wait(1000)  # Wait up to 1 second
        
        event.accept()
