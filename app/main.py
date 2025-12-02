"""
Dokapon SoF Tools - Main Application Entry Point

A modern GUI application for extracting and managing game assets
from DOKAPON! Sword of Fury.

Author: DiNaSoR
Repository: https://github.com/DiNaSoR/dokaponsof
"""

import sys
import os

# Add the parent directory to Python path so it can find the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QFont
from PyQt6.QtCore import Qt
from app.gui import DokaponToolsGUI
from app.gui.styles import get_stylesheet


def main():
    """Initialize and run the application."""
    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    app = QApplication(sys.argv)
    
    # Set application metadata
    app.setApplicationName("Dokapon SoF Tools")
    app.setApplicationVersion("0.3.0")
    app.setOrganizationName("DiNaSoR")
    app.setDesktopFileName("dokapon-sof-tools")
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    
    # Set default font
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)
    
    # Apply modern dark theme
    app.setStyleSheet(get_stylesheet())
    
    # Create and show main window
    window = DokaponToolsGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
