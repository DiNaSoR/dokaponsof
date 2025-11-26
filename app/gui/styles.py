"""
Modern VS Code-like theme system for Dokapon SoF Tools.
Defines color palette and Qt Style Sheets for the application.
"""

# Color Palette - VS Code Dark Theme inspired
COLORS = {
    # Backgrounds
    "bg_primary": "#1e1e1e",      # Main background
    "bg_secondary": "#252526",     # Sidebar, panels
    "bg_tertiary": "#2d2d30",      # Input fields, cards
    "bg_hover": "#3e3e42",         # Hover states
    "bg_active": "#094771",        # Active/selected items
    
    # Accent colors
    "accent_primary": "#007acc",   # Primary accent (blue)
    "accent_hover": "#1c97ea",     # Accent hover
    "accent_success": "#4ec9b0",   # Success green
    "accent_warning": "#dcdcaa",   # Warning yellow
    "accent_error": "#f14c4c",     # Error red
    
    # Text colors
    "text_primary": "#cccccc",     # Primary text
    "text_secondary": "#858585",   # Secondary/muted text
    "text_bright": "#ffffff",      # Bright/highlighted text
    "text_disabled": "#5a5a5a",    # Disabled text
    
    # Borders
    "border_primary": "#3e3e42",   # Primary borders
    "border_focus": "#007acc",     # Focus borders
    
    # Scrollbar
    "scrollbar_bg": "#1e1e1e",
    "scrollbar_handle": "#424242",
    "scrollbar_hover": "#4f4f4f",
}


def get_stylesheet() -> str:
    """Generate the complete application stylesheet."""
    c = COLORS
    
    return f"""
        /* ===== Global Styles ===== */
        QMainWindow, QWidget {{
            background-color: {c["bg_primary"]};
            color: {c["text_primary"]};
            font-family: "Segoe UI", "SF Pro Display", system-ui, sans-serif;
            font-size: 13px;
        }}
        
        /* ===== Labels ===== */
        QLabel {{
            color: {c["text_primary"]};
            padding: 2px;
        }}
        
        QLabel[class="heading"] {{
            font-size: 16px;
            font-weight: 600;
            color: {c["text_bright"]};
        }}
        
        QLabel[class="muted"] {{
            color: {c["text_secondary"]};
        }}
        
        /* ===== Buttons ===== */
        QPushButton {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 8px 16px;
            font-weight: 500;
            min-height: 20px;
        }}
        
        QPushButton:hover {{
            background-color: {c["bg_hover"]};
            border-color: {c["accent_primary"]};
        }}
        
        QPushButton:pressed {{
            background-color: {c["bg_active"]};
        }}
        
        QPushButton:disabled {{
            background-color: {c["bg_secondary"]};
            color: {c["text_disabled"]};
            border-color: {c["border_primary"]};
        }}
        
        QPushButton[class="primary"] {{
            background-color: {c["accent_primary"]};
            color: {c["text_bright"]};
            border: none;
        }}
        
        QPushButton[class="primary"]:hover {{
            background-color: {c["accent_hover"]};
        }}
        
        QPushButton[class="danger"] {{
            background-color: {c["accent_error"]};
            color: {c["text_bright"]};
            border: none;
        }}
        
        /* ===== Input Fields ===== */
        QLineEdit, QTextEdit, QPlainTextEdit {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 6px 10px;
            selection-background-color: {c["accent_primary"]};
        }}
        
        QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
            border-color: {c["accent_primary"]};
        }}
        
        QLineEdit:disabled, QTextEdit:disabled {{
            background-color: {c["bg_secondary"]};
            color: {c["text_disabled"]};
        }}
        
        /* ===== ComboBox ===== */
        QComboBox {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 6px 10px;
            min-height: 20px;
        }}
        
        QComboBox:hover {{
            border-color: {c["accent_primary"]};
        }}
        
        QComboBox::drop-down {{
            border: none;
            width: 24px;
        }}
        
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c["text_primary"]};
            margin-right: 8px;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            selection-background-color: {c["bg_active"]};
        }}
        
        /* ===== Progress Bar ===== */
        QProgressBar {{
            background-color: {c["bg_tertiary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            text-align: center;
            color: {c["text_primary"]};
            min-height: 20px;
        }}
        
        QProgressBar::chunk {{
            background: qlineargradient(
                x1:0, y1:0, x2:1, y2:0,
                stop:0 {c["accent_primary"]},
                stop:1 {c["accent_hover"]}
            );
            border-radius: 3px;
        }}
        
        /* ===== Tree View ===== */
        QTreeView {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            alternate-background-color: {c["bg_secondary"]};
            outline: none;
        }}
        
        QTreeView::item {{
            padding: 4px;
            border-radius: 2px;
        }}
        
        QTreeView::item:hover {{
            background-color: {c["bg_hover"]};
        }}
        
        QTreeView::item:selected {{
            background-color: {c["bg_active"]};
        }}
        
        QTreeView::branch {{
            background-color: transparent;
        }}
        
        QTreeView::branch:has-children:!has-siblings:closed,
        QTreeView::branch:closed:has-children:has-siblings {{
            border-image: none;
            image: url(none);
        }}
        
        QTreeView::branch:has-children:!has-siblings:closed::marker,
        QTreeView::branch:closed:has-children:has-siblings::marker {{
            image: none;
        }}
        
        QTreeView::branch:open:has-children:!has-siblings,
        QTreeView::branch:open:has-children:has-siblings {{
            border-image: none;
            image: url(none);
        }}
        
        QTreeView::indicator {{
            width: 16px;
            height: 16px;
        }}
        
        QTreeView::indicator:unchecked {{
            border: 2px solid {c["border_primary"]};
            border-radius: 3px;
            background-color: {c["bg_tertiary"]};
        }}
        
        QTreeView::indicator:checked {{
            border: 2px solid {c["accent_primary"]};
            border-radius: 3px;
            background-color: {c["accent_primary"]};
        }}
        
        QHeaderView::section {{
            background-color: {c["bg_secondary"]};
            color: {c["text_primary"]};
            padding: 8px;
            border: none;
            border-right: 1px solid {c["border_primary"]};
            border-bottom: 1px solid {c["border_primary"]};
            font-weight: 600;
        }}
        
        /* ===== Table Widget ===== */
        QTableWidget, QTableView {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            gridline-color: {c["border_primary"]};
            alternate-background-color: {c["bg_secondary"]};
        }}
        
        QTableWidget::item, QTableView::item {{
            padding: 4px;
        }}
        
        QTableWidget::item:selected, QTableView::item:selected {{
            background-color: {c["bg_active"]};
        }}
        
        /* ===== Scrollbars ===== */
        QScrollBar:vertical {{
            background-color: {c["scrollbar_bg"]};
            width: 12px;
            margin: 0;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {c["scrollbar_handle"]};
            min-height: 30px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {c["scrollbar_hover"]};
        }}
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        
        QScrollBar:horizontal {{
            background-color: {c["scrollbar_bg"]};
            height: 12px;
            margin: 0;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:horizontal {{
            background-color: {c["scrollbar_handle"]};
            min-width: 30px;
            border-radius: 6px;
            margin: 2px;
        }}
        
        QScrollBar::handle:horizontal:hover {{
            background-color: {c["scrollbar_hover"]};
        }}
        
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        
        /* ===== Splitter ===== */
        QSplitter::handle {{
            background-color: {c["border_primary"]};
        }}
        
        QSplitter::handle:horizontal {{
            width: 2px;
        }}
        
        QSplitter::handle:vertical {{
            height: 2px;
        }}
        
        /* ===== Radio Buttons ===== */
        QRadioButton {{
            color: {c["text_primary"]};
            spacing: 8px;
        }}
        
        QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 8px;
            border: 2px solid {c["border_primary"]};
            background-color: {c["bg_tertiary"]};
        }}
        
        QRadioButton::indicator:hover {{
            border-color: {c["accent_primary"]};
        }}
        
        QRadioButton::indicator:checked {{
            background-color: {c["accent_primary"]};
            border-color: {c["accent_primary"]};
        }}
        
        /* ===== Checkboxes ===== */
        QCheckBox {{
            color: {c["text_primary"]};
            spacing: 8px;
        }}
        
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
            border-radius: 3px;
            border: 2px solid {c["border_primary"]};
            background-color: {c["bg_tertiary"]};
        }}
        
        QCheckBox::indicator:hover {{
            border-color: {c["accent_primary"]};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {c["accent_primary"]};
            border-color: {c["accent_primary"]};
        }}
        
        /* ===== Tool Tips ===== */
        QToolTip {{
            background-color: {c["bg_secondary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        
        /* ===== Menu ===== */
        QMenu {{
            background-color: {c["bg_secondary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 4px;
        }}
        
        QMenu::item {{
            padding: 6px 24px;
            border-radius: 2px;
        }}
        
        QMenu::item:selected {{
            background-color: {c["bg_active"]};
        }}
        
        /* ===== Group Box ===== */
        QGroupBox {{
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            margin-top: 12px;
            padding-top: 8px;
            font-weight: 600;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
        }}
        
        /* ===== List View (Grid/Thumbnail mode) ===== */
        QListView {{
            background-color: {c["bg_tertiary"]};
            color: {c["text_primary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            outline: none;
        }}
        
        QListView::item {{
            background-color: {c["bg_secondary"]};
            border: 1px solid {c["border_primary"]};
            border-radius: 4px;
            padding: 8px;
            margin: 4px;
        }}
        
        QListView::item:hover {{
            background-color: {c["bg_hover"]};
            border-color: {c["accent_primary"]};
        }}
        
        QListView::item:selected {{
            background-color: {c["bg_active"]};
            border-color: {c["accent_primary"]};
        }}
        
        /* ===== Stacked Widget ===== */
        QStackedWidget {{
            background-color: transparent;
        }}
    """


def get_sidebar_stylesheet() -> str:
    """Generate stylesheet specifically for the sidebar."""
    c = COLORS
    
    return f"""
        QWidget#sidebar {{
            background-color: {c["bg_secondary"]};
            border-right: 1px solid {c["border_primary"]};
        }}
        
        QPushButton#sidebarButton {{
            background-color: transparent;
            color: {c["text_secondary"]};
            border: none;
            border-radius: 0;
            padding: 14px 20px;
            text-align: left;
            font-size: 13px;
            font-weight: 500;
        }}
        
        QPushButton#sidebarButton:hover {{
            background-color: {c["bg_hover"]};
            color: {c["text_primary"]};
        }}
        
        QPushButton#sidebarButton:checked {{
            background-color: {c["bg_primary"]};
            color: {c["text_bright"]};
            border-left: 3px solid {c["accent_primary"]};
        }}
        
        QLabel#sidebarTitle {{
            color: {c["text_secondary"]};
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 1px;
            padding: 16px 20px 8px 20px;
        }}
        
        QLabel#sidebarVersion {{
            color: {c["text_disabled"]};
            font-size: 11px;
            padding: 8px 20px;
        }}
    """


def get_status_colors() -> dict:
    """Get colors for status message types."""
    return {
        "info": COLORS["text_primary"],
        "success": COLORS["accent_success"],
        "warning": COLORS["accent_warning"],
        "error": COLORS["accent_error"],
    }

