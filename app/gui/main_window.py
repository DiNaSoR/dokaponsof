from PyQt6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QTextEdit, QProgressBar, QTabWidget, QHBoxLayout, QPushButton, QFileDialog
from PyQt6.QtGui import QIcon
from .tabs.asset_tab import AssetExtractorTab
from .tabs.text_tab import TextTab
from .tabs.voice_tab import VoiceExtractorTab
from .tabs.about_tab import AboutTab
from datetime import datetime
import os

class DokaponToolsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Dokapon SoF Tools GUI - By DiNaSoR v0.1")
        self.setMinimumSize(800, 600)
        
        # Update icon path to look in resources directory
        icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources", "icon.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Create tab widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Add tabs
        self.asset_tab = AssetExtractorTab()
        self.text_tab = TextTab()
        self.voice_tab = VoiceExtractorTab()
        self.about_tab = AboutTab()
        
        self.tabs.addTab(self.asset_tab, "Asset Extractor")
        self.tabs.addTab(self.text_tab, "Text Tools")
        self.tabs.addTab(self.voice_tab, "Voice Tools")
        self.tabs.addTab(self.about_tab, "About")
        
        # Connect status signals
        self.asset_tab.status_updated.connect(self._update_status)
        self.text_tab.status_updated.connect(self._update_status)
        self.voice_tab.status_updated.connect(self._update_status)
        
        # Connect tab change signal
        self.tabs.currentChanged.connect(self._on_tab_changed)
        
        # Status area
        status_layout = QVBoxLayout()
        status_header = QHBoxLayout()
        
        status_header.addWidget(QLabel("Status:"))
        
        # Add save log button
        save_log_btn = QPushButton("Save Status Log")
        save_log_btn.clicked.connect(self._save_status_log)
        status_header.addWidget(save_log_btn)
        
        status_layout.addLayout(status_header)
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setMaximumHeight(200)  # Made taller for better visibility
        status_layout.addWidget(self.status_text)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        status_layout.addWidget(self.progress_bar)
        
        layout.addLayout(status_layout)

    def _save_status_log(self):
        """Save status log to a text file"""
        current_tab = self.tabs.currentWidget()
        tab_name = self.tabs.tabText(self.tabs.currentIndex()).lower().replace(" ", "_")
        
        # Get current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"{tab_name}_log_{timestamp}.txt"
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Status Log",
            default_filename,
            "Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(self.status_text.toPlainText())
                self._update_status(f"\nStatus log saved to: {file_path}")
            except Exception as e:
                self._update_status(f"\nError saving log: {str(e)}")

    def _update_status(self, message):
        """Update status text area with new message"""
        self.status_text.append(message)

    def _on_tab_changed(self, index):
        """Handle tab changes"""
        # Start music if switching to about tab
        if self.tabs.widget(index) == self.about_tab:
            if hasattr(self.about_tab, 'media_player'):
                self.about_tab.media_player.play() 