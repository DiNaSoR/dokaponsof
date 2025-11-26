"""
Modern sidebar navigation component for Dokapon SoF Tools.
Provides VS Code-like vertical navigation with styled buttons.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QButtonGroup, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QIcon
from ..styles import get_sidebar_stylesheet
import os


class SidebarButton(QPushButton):
    """Custom styled button for sidebar navigation."""
    
    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon_char}  {text}" if icon_char else f"  {text}")
        self.setObjectName("sidebarButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)


class ModernSidebar(QWidget):
    """
    Modern vertical sidebar navigation component.
    
    Signals:
        navigation_changed(int): Emitted when user clicks a navigation button.
            The int parameter is the index of the selected view.
    """
    
    navigation_changed = pyqtSignal(int)
    
    # Navigation items: (display_name, icon_character)
    NAV_ITEMS = [
        ("Asset Extractor", "📦"),
        ("Text Tools", "📝"),
        ("Voice Tools", "🎙"),
        ("About", "ℹ"),
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(200)
        self._init_ui()
        self.setStyleSheet(get_sidebar_stylesheet())
    
    def _init_ui(self):
        """Initialize the sidebar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # App title/branding
        title_label = QLabel("DOKAPON TOOLS")
        title_label.setObjectName("sidebarTitle")
        layout.addWidget(title_label)
        
        # Navigation button group (ensures only one is checked)
        self.button_group = QButtonGroup(self)
        self.button_group.setExclusive(True)
        
        # Create navigation buttons
        self.nav_buttons = []
        for index, (name, icon) in enumerate(self.NAV_ITEMS):
            button = SidebarButton(name, icon)
            button.clicked.connect(lambda checked, idx=index: self._on_button_clicked(idx))
            self.button_group.addButton(button, index)
            self.nav_buttons.append(button)
            layout.addWidget(button)
        
        # Select first button by default
        if self.nav_buttons:
            self.nav_buttons[0].setChecked(True)
        
        # Spacer to push version to bottom
        layout.addSpacerItem(
            QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)
        )
        
        # Version label at bottom
        version_label = QLabel("v0.2.0 • By DiNaSoR")
        version_label.setObjectName("sidebarVersion")
        layout.addWidget(version_label)
        
        # Bottom padding
        layout.addSpacing(16)
    
    def _on_button_clicked(self, index: int):
        """Handle navigation button clicks."""
        self.navigation_changed.emit(index)
    
    def set_active_index(self, index: int):
        """Programmatically set the active navigation item."""
        if 0 <= index < len(self.nav_buttons):
            self.nav_buttons[index].setChecked(True)
    
    def get_active_index(self) -> int:
        """Get the currently active navigation index."""
        return self.button_group.checkedId()

