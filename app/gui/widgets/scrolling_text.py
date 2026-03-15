"""Scrolling text widget used in the About tab credits display."""

from PyQt6.QtWidgets import QWidget, QPushButton
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QColor, QPainter, QDesktopServices, QFontMetrics
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import random


class ScrollingTextWidget(QWidget):
    def __init__(self, text, parent=None):
        super().__init__(parent)
        self.text = text
        self.offset = self.height()
        self.setMinimumHeight(400)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # Speed up the scroll animation a bit
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(50)  # Changed from 100ms to 50ms

        # Slow down color transitions for less flashing
        self.hue = 0
        self.color_timer = QTimer(self)
        self.color_timer.timeout.connect(self.update_colors)
        self.color_timer.start(300)  # Slower color changes

        # Double buffer to reduce flickering
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)

        self.colors = []
        self.update_colors()

        # Respect counter settings
        self.respects_paid = 0
        self.respect_flash = 0
        self.respect_timer = QTimer(self)
        self.respect_timer.timeout.connect(self.update_respect_flash)
        self.respect_timer.setInterval(50)

        # Reduce star animation frequency
        self.star_timer = QTimer(self)
        self.star_timer.timeout.connect(self.update_stars)
        self.star_timer.start(500)  # Update stars every 500ms
        self.stars = self._generate_stars()

        # Add mute button in top-left
        self.mute_button = QPushButton("♪", self)
        self.mute_button.setFixedSize(30, 30)
        self.mute_button.move(10, 10)
        self.mute_button.clicked.connect(self.toggle_mute)
        self.mute_button.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004400;
            }
        """)

        # Add PayPal button next to mute button
        self.donate_button = QPushButton("🎁", self)
        self.donate_button.setFixedSize(30, 30)
        self.donate_button.move(50, 10)  # Position it next to mute button
        self.donate_button.clicked.connect(self._open_paypal)
        self.donate_button.setStyleSheet("""
            QPushButton {
                background-color: #003300;
                color: #00ff00;
                border: 1px solid #00ff00;
                border-radius: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #004400;
                border-color: #00ff00;
            }
            QPushButton:tooltip {
                background-color: #003300;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 5px;
            }
        """)
        self.donate_button.setToolTip("Support via PayPal")

        # Calculate total text height
        self.font = QFont("Courier", 12, QFont.Weight.Bold)
        self.font_metrics = QFontMetrics(self.font)
        self.line_spacing = 25
        self.text_lines = text.split('\n')
        self.total_height = len(self.text_lines) * self.line_spacing

        # Add extra space between end and beginning for smooth loop
        self.loop_spacing = 100

    def _generate_stars(self):
        """Generate a fixed set of stars"""
        stars = []
        for _ in range(50):
            stars.append({
                'x': random.randint(0, self.width()),
                'y': random.randint(0, self.height()),
                'size': random.randint(1, 3),
                'brightness': random.randint(50, 150)
            })
        return stars

    def update_stars(self):
        """Update star positions occasionally"""
        for star in self.stars:
            if random.random() < 0.1:  # Only move some stars
                star['x'] = random.randint(0, self.width())
                star['y'] = random.randint(0, self.height())
                star['brightness'] = random.randint(50, 150)
        self.update()

    def update_colors(self):
        """Update gradient colors with less variation"""
        self.hue = (self.hue + 1) % 360  # Slower color cycling

        # Create green color variations
        self.colors = []
        base_green = QColor(0, 255, 0)  # Bright green
        dark_green = QColor(0, 200, 0)  # Less dark for reduced contrast

        # Create a gradient between bright and dark green
        for i in range(10):
            blend = i / 9.0
            r = int(base_green.red() * (1 - blend) + dark_green.red() * blend)
            g = int(base_green.green() * (1 - blend) + dark_green.green() * blend)
            b = int(base_green.blue() * (1 - blend) + dark_green.blue() * blend)
            self.colors.append(QColor(r, g, b))

        self.update()

    def animate(self):
        """Scroll text upward with looping"""
        self.offset -= 1.0

        # When text scrolls up enough, add a copy below
        if self.offset < -self.total_height:
            self.offset = 0  # Reset to start position

        self.update()

    def keyPressEvent(self, event):
        """Handle keyboard events"""
        if event.key() == Qt.Key.Key_F:
            self.respects_paid += 1
            # Start flashing effect
            self.respect_flash = 10
            self.respect_timer.start()
            self.update()

    def update_respect_flash(self):
        """Update the flashing effect when paying respects"""
        if self.respect_flash > 0:
            self.respect_flash -= 1
            self.update()
        else:
            self.respect_timer.stop()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # Fill background
        painter.fillRect(self.rect(), QColor(0, 20, 0))

        # Draw pre-generated stars
        for star in self.stars:
            color = QColor(0, star['brightness'], 0)
            painter.fillRect(
                int(star['x']), int(star['y']),
                star['size'], star['size'],
                color
            )

        # Draw text with smoother rendering
        painter.setFont(self.font)

        # Draw two copies of the text for smooth looping
        for offset_adjust in [0, self.total_height + self.loop_spacing]:
            y = int(self.offset + offset_adjust)

            for i, line in enumerate(self.text_lines):
                if not line.strip():
                    y += 20
                    continue

                # Center text within the available space
                text_width = painter.fontMetrics().horizontalAdvance(line)
                left_margin = int(self.width() * 0.2)
                available_width = self.width() - left_margin * 2
                x = int(left_margin + (available_width - text_width) // 2)

                # Use green color variations for text
                base_color = self.colors[i % len(self.colors)]

                # Draw each character
                for char_idx, char in enumerate(line):
                    color = QColor(
                        base_color.red(),
                        base_color.green() + random.randint(-10, 10),
                        base_color.blue()
                    )
                    painter.setPen(color)
                    char_width = painter.fontMetrics().horizontalAdvance(char)

                    # Only draw if within visible area
                    if 0 <= y <= self.height():
                        painter.drawText(x, y, char)
                    x += char_width

                y += self.line_spacing

        # Draw respects counter with flash effect if active
        if self.respects_paid > 0:
            respect_text = f"Respects Paid: {self.respects_paid}"
            painter.setFont(QFont("Courier", 10, QFont.Weight.Bold))

            # Flash effect when F is pressed
            if self.respect_flash > 0:
                flash_color = QColor(0, 255, 0)  # Bright green
            else:
                flash_color = QColor(0, 180, 0)  # Normal green

            painter.setPen(flash_color)
            x = int(self.width() - painter.fontMetrics().horizontalAdvance(respect_text) - 20)
            y = int(self.height() - 20)
            painter.drawText(x, y, respect_text)

    def toggle_mute(self):
        if hasattr(self.parent(), 'toggle_music'):
            self.parent().toggle_music()
            # Update button text
            if self.parent().audio_output.isMuted():
                self.mute_button.setText("🔇")
            else:
                self.mute_button.setText("♪")

    def _open_paypal(self):
        """Open PayPal donation link"""
        paypal_url = "https://www.paypal.com/donate/?hosted_button_id=6V7XB84HZFSY2"
        QDesktopServices.openUrl(QUrl(paypal_url))
