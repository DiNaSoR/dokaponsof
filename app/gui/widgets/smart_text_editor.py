"""
Smart Text Editor Widget for DOKAPON! Sword of Fury
Provides syntax highlighting and protection for control codes.
"""

from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
                            QLabel, QPushButton, QFrame, QSplitter)
from PyQt6.QtGui import (QSyntaxHighlighter, QTextCharFormat, QColor, QFont,
                         QTextCursor, QPainter, QFontMetrics)
from PyQt6.QtCore import Qt, pyqtSignal, QRegularExpression
import re


class DokaponSyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Dokapon text control codes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_formats()
        self._setup_rules()
    
    def _setup_formats(self):
        """Setup text formats for different code types"""
        # Control codes (\p, \k, \r, \h, \n, \z, \m)
        self.control_format = QTextCharFormat()
        self.control_format.setForeground(QColor("#c586c0"))  # Purple
        self.control_format.setFontWeight(QFont.Weight.Bold)
        
        # Color codes (%0c, %1c, etc.)
        self.color_code_format = QTextCharFormat()
        self.color_code_format.setForeground(QColor("#4ec9b0"))  # Teal
        self.color_code_format.setFontWeight(QFont.Weight.Bold)
        
        # Position codes (%0x, %0y, etc.)
        self.position_format = QTextCharFormat()
        self.position_format.setForeground(QColor("#569cd6"))  # Blue
        self.position_format.setFontWeight(QFont.Weight.Bold)
        
        # Variables (%s, %d, etc.)
        self.variable_format = QTextCharFormat()
        self.variable_format.setForeground(QColor("#dcdcaa"))  # Yellow
        self.variable_format.setFontWeight(QFont.Weight.Bold)
        
        # Button codes (%517M, etc.)
        self.button_format = QTextCharFormat()
        self.button_format.setForeground(QColor("#ce9178"))  # Orange
        self.button_format.setFontWeight(QFont.Weight.Bold)
        
        # Newlines in text
        self.newline_format = QTextCharFormat()
        self.newline_format.setForeground(QColor("#6a9955"))  # Green
        self.newline_format.setBackground(QColor("#2d2d2d"))
    
    def _setup_rules(self):
        """Setup highlighting rules"""
        self.rules = [
            # Control codes: \p, \k, \r, \h, \z, \m
            (QRegularExpression(r'\\[pkrhzm]'), self.control_format),
            # Newline in text
            (QRegularExpression(r'\\n'), self.newline_format),
            # Color codes: %0c, %1c, %10c, etc.
            (QRegularExpression(r'%\d+c'), self.color_code_format),
            # Position codes: %0x, %0y, %16x, etc.
            (QRegularExpression(r'%\d+[xy]'), self.position_format),
            # Button codes: %517M, %518M, etc.
            (QRegularExpression(r'%\d+M'), self.button_format),
            # Variables: %s, %d, %3d, %8s, etc.
            (QRegularExpression(r'%\d*[sd]'), self.variable_format),
            # Comma formatting: \,
            (QRegularExpression(r'\\,'), self.control_format),
        ]
    
    def highlightBlock(self, text):
        """Apply highlighting to a block of text"""
        for pattern, fmt in self.rules:
            iterator = pattern.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


class SmartTextEdit(QTextEdit):
    """Text editor with control code protection"""
    
    textModified = pyqtSignal(str)  # Emits the full text when modified
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.highlighter = DokaponSyntaxHighlighter(self.document())
        self._original_text = ""
        self._control_code_pattern = re.compile(
            r'(\\[pkrhzmnm]|\\,|%\d+[cxyMsd]|%\d*[sd])'
        )
        
        # Setup font
        font = QFont("Consolas", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        
        # Connect text change
        self.textChanged.connect(self._on_text_changed)
    
    def setTextWithProtection(self, text: str):
        """Set text and remember original for protection"""
        self._original_text = text
        self.blockSignals(True)
        self.setPlainText(text)
        self.blockSignals(False)
    
    def _on_text_changed(self):
        """Handle text changes - emit modified signal"""
        self.textModified.emit(self.toPlainText())
    
    def getEditableText(self) -> str:
        """Get only the editable (non-control-code) parts"""
        text = self.toPlainText()
        return self._control_code_pattern.sub('', text)
    
    def getControlCodes(self) -> list:
        """Extract all control codes from text"""
        text = self.toPlainText()
        return self._control_code_pattern.findall(text)


class TextPreviewWidget(QFrame):
    """Widget to show clean preview of text without control codes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            TextPreviewWidget {
                background-color: #1e1e1e;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Title
        title = QLabel("Preview")
        title.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        layout.addWidget(title)
        
        # Preview text
        self.preview_label = QLabel()
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("""
            color: #e0e0e0;
            font-size: 14px;
            line-height: 1.5;
            padding: 8px;
            background-color: #252526;
            border-radius: 4px;
        """)
        self.preview_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.preview_label)
    
    def updatePreview(self, text: str):
        """Update preview with cleaned text"""
        # Remove control codes but format nicely
        clean = text
        
        # Remove start/end markers
        clean = re.sub(r'\\[pkz]', '', clean)
        
        # Convert newlines to HTML
        clean = clean.replace('\\n', '<br>')
        
        # Remove other codes but keep variables as placeholders
        clean = re.sub(r'%\d+c', '', clean)  # Color codes
        clean = re.sub(r'%\d+[xy]', '', clean)  # Position codes
        clean = re.sub(r'%\d+M', '🎮', clean)  # Button codes -> gamepad emoji
        clean = re.sub(r'\\[rhm,]', '', clean)  # Other control codes
        
        # Style variables
        clean = re.sub(r'%(\d*)[sd]', r'<span style="color:#dcdcaa">[VAR]</span>', clean)
        
        self.preview_label.setText(clean.strip())


class CodeLegendWidget(QFrame):
    """Widget showing legend for control codes"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFrameStyle(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            CodeLegendWidget {
                background-color: #252526;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)
        
        title = QLabel("Code Reference")
        title.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        layout.addWidget(title)
        
        codes = [
            ("\\p", "#c586c0", "Text start"),
            ("\\k", "#c586c0", "Wait/pause"),
            ("\\n", "#6a9955", "New line"),
            ("%Nc", "#4ec9b0", "Color code"),
            ("%Nx/y", "#569cd6", "Position"),
            ("%s/%d", "#dcdcaa", "Variable"),
        ]
        
        for code, color, desc in codes:
            row = QHBoxLayout()
            code_label = QLabel(code)
            code_label.setStyleSheet(f"color: {color}; font-family: Consolas; font-weight: bold;")
            code_label.setFixedWidth(50)
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #888; font-size: 10px;")
            row.addWidget(code_label)
            row.addWidget(desc_label)
            row.addStretch()
            layout.addLayout(row)


class SmartTextEditorWidget(QWidget):
    """Complete smart text editor with preview and legend"""
    
    textChanged = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        # Main editor area
        editor_layout = QVBoxLayout()
        
        # Editor label
        editor_title = QLabel("Editor")
        editor_title.setStyleSheet("color: #888; font-size: 11px; font-weight: bold;")
        editor_layout.addWidget(editor_title)
        
        # The editor itself
        self.editor = SmartTextEdit()
        self.editor.setStyleSheet("""
            SmartTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.editor.setMinimumHeight(150)
        self.editor.textModified.connect(self._on_text_modified)
        editor_layout.addWidget(self.editor)
        
        layout.addLayout(editor_layout, stretch=2)
        
        # Right panel (preview + legend)
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        
        # Preview
        self.preview = TextPreviewWidget()
        right_panel.addWidget(self.preview)
        
        # Legend
        self.legend = CodeLegendWidget()
        right_panel.addWidget(self.legend)
        
        right_panel.addStretch()
        
        layout.addLayout(right_panel, stretch=1)
    
    def _on_text_modified(self, text: str):
        """Handle text modification"""
        self.preview.updatePreview(text)
        self.textChanged.emit(text)
    
    def setText(self, text: str):
        """Set the editor text"""
        self.editor.setTextWithProtection(text)
        self.preview.updatePreview(text)
    
    def text(self) -> str:
        """Get the editor text"""
        return self.editor.toPlainText()
    
    def clear(self):
        """Clear the editor"""
        self.editor.clear()
        self.preview.updatePreview("")

