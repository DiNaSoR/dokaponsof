"""
Modern sidebar navigation component for Dokapon SoF Tools.
Provides VS Code-like vertical navigation with styled buttons.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QButtonGroup, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QFont
from ..styles import get_sidebar_stylesheet, COLORS


class SidebarButton(QPushButton):
    """Custom styled button for sidebar navigation with a properly-sized icon."""

    def __init__(self, text: str, icon_char: str = "", parent=None):
        super().__init__(parent)
        self._label_text = text
        self._icon_char = icon_char
        self.setObjectName("sidebarButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumHeight(44)

        # Use a layout so icon and label can have independent sizing
        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 0, 12, 0)
        layout.setSpacing(10)

        if icon_char:
            self.icon_label = QLabel(icon_char)
            icon_font = QFont("Segoe UI Emoji", 15)
            icon_font.setStyleHint(QFont.StyleHint.System)
            self.icon_label.setFont(icon_font)
            self.icon_label.setFixedWidth(22)
            self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            layout.addWidget(self.icon_label)

        self.text_label = QLabel(text)
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(self.text_label, stretch=1)

    def _sync_colors(self, text_color: str):
        """Update child label colors to match button state."""
        if hasattr(self, 'icon_label'):
            self.icon_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none; padding: 0;")
        self.text_label.setStyleSheet(f"color: {text_color}; background: transparent; border: none; padding: 0;")

    def enterEvent(self, event):
        super().enterEvent(event)
        if not self.isChecked():
            self._sync_colors(COLORS['text_primary'])

    def leaveEvent(self, event):
        super().leaveEvent(event)
        if not self.isChecked():
            self._sync_colors(COLORS['text_secondary'])

    def setChecked(self, checked: bool):
        super().setChecked(checked)
        self._sync_colors(COLORS['text_bright'] if checked else COLORS['text_secondary'])

    def nextCheckState(self):
        super().nextCheckState()
        self._sync_colors(COLORS['text_bright'] if self.isChecked() else COLORS['text_secondary'])


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
        ("Text Tools",      "📝"),
        ("Voice Tools",     "🎙"),
        ("Hex Editor",      "🔧"),
        ("Video Tools",     "🎬"),
        ("Map Explorer",    "🗺"),
        ("About",           "ℹ"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(210)
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
        version_label = QLabel("v0.4.0 • By DiNaSoR")
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

