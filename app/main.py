import sys
import os

# Add the parent directory to Python path so it can find the app package
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon, QPalette, QColor
from PyQt6.QtCore import Qt
from app.gui import DokaponToolsGUI

def set_dark_theme(app):
    """Set dark theme for the entire application"""
    dark_palette = QPalette()
    
    # Base colors
    dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    
    # Disabled colors
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(127, 127, 127))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, QColor(80, 80, 80))
    dark_palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.HighlightedText, QColor(127, 127, 127))
    
    # Apply the palette
    app.setPalette(dark_palette)
    
    # Set stylesheet for more consistent dark theme
    app.setStyleSheet("""
        QToolTip { 
            color: #ffffff; 
            background-color: #2a2a2a; 
            border: 1px solid #767676; 
            border-radius: 4px; 
            padding: 4px;
        }
        QTableView {
            gridline-color: #505050;
            background-color: #2a2a2a;
            alternate-background-color: #353535;
        }
        QHeaderView::section {
            background-color: #383838;
            color: white;
            padding: 4px;
            border: 1px solid #505050;
        }
        QTabWidget::pane {
            border: 1px solid #505050;
        }
        QTabBar::tab {
            background-color: #353535;
            color: white;
            padding: 8px 16px;
            border: 1px solid #505050;
            border-bottom: none;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #505050;
        }
        QScrollBar:vertical {
            border: none;
            background-color: #2a2a2a;
            width: 14px;
            margin: 0px;
        }
        QScrollBar::handle:vertical {
            background-color: #505050;
            min-height: 30px;
            border-radius: 7px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #606060;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QTextEdit, QLineEdit {
            background-color: #2a2a2a;
            color: white;
            border: 1px solid #505050;
            border-radius: 4px;
            padding: 2px;
        }
        QPushButton {
            background-color: #424242;
            color: white;
            border: 1px solid #505050;
            border-radius: 4px;
            padding: 6px 12px;
        }
        QPushButton:hover {
            background-color: #505050;
        }
        QPushButton:pressed {
            background-color: #383838;
        }
        QComboBox {
            background-color: #424242;
            color: white;
            border: 1px solid #505050;
            border-radius: 4px;
            padding: 4px;
        }
        QComboBox::drop-down {
            border: none;
        }
        QComboBox::down-arrow {
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid white;
            margin-right: 5px;
        }
        QProgressBar {
            border: 1px solid #505050;
            border-radius: 4px;
            text-align: center;
            background-color: #2a2a2a;
        }
        QProgressBar::chunk {
            background-color: #2a82da;
            width: 1px;
        }
    """)

def main():
    app = QApplication(sys.argv)
    
    # Set application icon
    icon_path = os.path.join(os.path.dirname(__file__), "resources", "icon.ico")
    if os.path.exists(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
        # Set the taskbar icon name
        app.setApplicationName("Dokapon SoF Tools")
        app.setDesktopFileName("dokapon-sof-tools")
    
    # Apply dark theme
    set_dark_theme(app)
    
    window = DokaponToolsGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 