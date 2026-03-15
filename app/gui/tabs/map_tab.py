"""
Map Explorer tab for Dokapon SoF Tools.
Provides visual exploration of Cell/Map files with atlas view, map rendering,
records and parts tables, and full scan report generation.
"""

from io import BytesIO
from pathlib import Path

from PIL import Image
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QPoint, pyqtSignal
from PyQt6.QtGui import QPixmap, QWheelEvent, QMouseEvent

from .base_tab import BaseTab
from ..styles import COLORS
from ..widgets.worker import WorkerThread
from ...core.map_renderer import (
    LoadedCellDocument,
    build_atlas_for_document,
    list_cell_files,
    load_cell_document,
    render_map_image,
    scan_workspace,
)
from ...core.game_scanner import scan_map_groups
from ...core.report_generator import write_markdown_report


def pil_to_qpixmap(image: Image.Image) -> QPixmap:
    """Convert a PIL Image to a QPixmap."""
    buf = BytesIO()
    image.save(buf, format="PNG")
    pixmap = QPixmap()
    pixmap.loadFromData(buf.getvalue())
    return pixmap


class ZoomPanLabel(QLabel):
    """A QLabel that supports mouse-wheel zoom and click-drag panning inside a QScrollArea."""

    zoom_changed = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pixmap_original: QPixmap | None = None
        self._zoom: float = 1.0
        self._min_zoom: float = 0.05
        self._max_zoom: float = 20.0
        self._drag_start: QPoint | None = None
        self._scroll_start_h: int = 0
        self._scroll_start_v: int = 0
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    # -- public API --

    def setSourcePixmap(self, pixmap: QPixmap):
        """Set the full-resolution source pixmap and display at current zoom."""
        self._pixmap_original = pixmap
        self._apply_zoom()

    def resetZoom(self):
        """Reset zoom to 1:1."""
        self._zoom = 1.0
        self._apply_zoom()

    def fitToView(self):
        """Fit the image to the viewport of the parent QScrollArea."""
        scroll = self._scroll_area()
        if scroll is None or self._pixmap_original is None or self._pixmap_original.isNull():
            return
        vp = scroll.viewport().size()
        pw, ph = self._pixmap_original.width(), self._pixmap_original.height()
        if pw == 0 or ph == 0:
            return
        self._zoom = min(vp.width() / pw, vp.height() / ph)
        self._apply_zoom()

    @property
    def zoom(self) -> float:
        return self._zoom

    # -- internal --

    def _apply_zoom(self):
        if self._pixmap_original is None or self._pixmap_original.isNull():
            return
        w = max(1, int(self._pixmap_original.width() * self._zoom))
        h = max(1, int(self._pixmap_original.height() * self._zoom))
        scaled = self._pixmap_original.scaled(
            w, h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.setPixmap(scaled)
        self.adjustSize()
        self.zoom_changed.emit(self._zoom)

    def _scroll_area(self) -> QScrollArea | None:
        parent = self.parent()
        while parent is not None:
            if isinstance(parent, QScrollArea):
                return parent
            parent = parent.parent()
        return None

    # -- events --

    def wheelEvent(self, event: QWheelEvent):
        if self._pixmap_original is None:
            return super().wheelEvent(event)

        scroll = self._scroll_area()
        # Remember cursor position relative to the image so we can keep it stable
        old_zoom = self._zoom
        delta = event.angleDelta().y()
        factor = 1.15 if delta > 0 else 1.0 / 1.15
        new_zoom = max(self._min_zoom, min(self._max_zoom, self._zoom * factor))
        if new_zoom == old_zoom:
            return

        # Position of cursor in the viewport
        if scroll:
            vp_pos = event.position()
            # Corresponding position in the *image* coordinate space
            h_bar = scroll.horizontalScrollBar()
            v_bar = scroll.verticalScrollBar()
            img_x = (h_bar.value() + vp_pos.x()) / old_zoom
            img_y = (v_bar.value() + vp_pos.y()) / old_zoom

        self._zoom = new_zoom
        self._apply_zoom()

        # Adjust scrollbars so the image point under the cursor stays put
        if scroll:
            h_bar.setValue(int(img_x * new_zoom - vp_pos.x()))
            v_bar.setValue(int(img_y * new_zoom - vp_pos.y()))

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint()
            scroll = self._scroll_area()
            if scroll:
                self._scroll_start_h = scroll.horizontalScrollBar().value()
                self._scroll_start_v = scroll.verticalScrollBar().value()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self._drag_start is not None:
            delta = event.globalPosition().toPoint() - self._drag_start
            scroll = self._scroll_area()
            if scroll:
                scroll.horizontalScrollBar().setValue(self._scroll_start_h - delta.x())
                scroll.verticalScrollBar().setValue(self._scroll_start_v - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        else:
            super().mouseReleaseEvent(event)


class MapExplorerTab(BaseTab):
    """Map Explorer tab with atlas/map views, record/part tables, and report."""

    def __init__(self):
        super().__init__()
        self._current_document: LoadedCellDocument | None = None
        self._game_dir: Path | None = None
        self._init_ui()

    def _init_ui(self):
        """Initialize the Map Explorer UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Left Panel: directory selection + file list ---
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 4, 8)
        left_layout.setSpacing(8)

        heading = QLabel("Map Explorer")
        heading.setStyleSheet(
            f"color: {COLORS['text_bright']}; font-size: 16px; font-weight: 600;"
        )
        left_layout.addWidget(heading)

        # Directory selection
        dir_layout = QHBoxLayout()
        self.dir_btn = QPushButton("Select Game Directory")
        self.dir_btn.setStyleSheet(
            f"background-color: {COLORS['accent_primary']}; color: {COLORS['text_bright']}; border: none;"
        )
        self.dir_btn.clicked.connect(self._select_directory)
        dir_layout.addWidget(self.dir_btn)
        left_layout.addLayout(dir_layout)

        self.dir_label = QLabel("No directory selected")
        self.dir_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        self.dir_label.setWordWrap(True)
        left_layout.addWidget(self.dir_label)

        # File list
        file_list_label = QLabel("Cell Files")
        file_list_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-weight: 600; font-size: 12px;"
        )
        left_layout.addWidget(file_list_label)

        self.file_list = QListWidget()
        self.file_list.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_primary']}; "
            f"border-radius: 4px;"
        )
        self.file_list.currentRowChanged.connect(self._on_file_selected)
        left_layout.addWidget(self.file_list, stretch=1)

        # Scan button
        self.scan_btn = QPushButton("Full Scan")
        self.scan_btn.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_primary']};"
        )
        self.scan_btn.setEnabled(False)
        self.scan_btn.clicked.connect(self._run_full_scan)
        left_layout.addWidget(self.scan_btn)

        splitter.addWidget(left_panel)

        # --- Right Panel: tabbed views ---
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 8, 8, 8)
        right_layout.setSpacing(0)

        self.detail_tabs = QTabWidget()
        self.detail_tabs.setStyleSheet(
            f"QTabWidget::pane {{ "
            f"  border: 1px solid {COLORS['border_primary']}; "
            f"  background-color: {COLORS['bg_primary']}; "
            f"}} "
            f"QTabBar::tab {{ "
            f"  background-color: {COLORS['bg_secondary']}; "
            f"  color: {COLORS['text_secondary']}; "
            f"  padding: 8px 16px; "
            f"  border: 1px solid {COLORS['border_primary']}; "
            f"  border-bottom: none; "
            f"}} "
            f"QTabBar::tab:selected {{ "
            f"  background-color: {COLORS['bg_primary']}; "
            f"  color: {COLORS['text_bright']}; "
            f"  border-bottom: 2px solid {COLORS['accent_primary']}; "
            f"}} "
            f"QTabBar::tab:hover {{ "
            f"  color: {COLORS['text_primary']}; "
            f"}}"
        )

        # Atlas View tab
        self._init_atlas_tab()
        # Map View tab
        self._init_map_tab()
        # Records Table tab
        self._init_records_tab()
        # Parts Table tab
        self._init_parts_tab()
        # Report tab
        self._init_report_tab()

        right_layout.addWidget(self.detail_tabs)
        splitter.addWidget(right_panel)

        # Set splitter proportions
        splitter.setSizes([250, 750])

        main_layout.addWidget(splitter)

    # ------------------------------------------------------------------ #
    #  Sub-tab initialisation
    # ------------------------------------------------------------------ #

    def _init_atlas_tab(self):
        """Create the Atlas View sub-tab."""
        atlas_widget = QWidget()
        atlas_layout = QVBoxLayout(atlas_widget)
        atlas_layout.setContentsMargins(8, 8, 8, 8)
        atlas_layout.setSpacing(8)

        # Palette selector
        palette_bar = QHBoxLayout()
        palette_label = QLabel("Palette:")
        palette_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        palette_bar.addWidget(palette_label)

        self.atlas_palette_combo = QComboBox()
        self.atlas_palette_combo.setMinimumWidth(120)
        self.atlas_palette_combo.currentIndexChanged.connect(self._refresh_atlas)
        palette_bar.addWidget(self.atlas_palette_combo)
        palette_bar.addStretch()
        atlas_layout.addLayout(palette_bar)

        # Atlas image
        self.atlas_scroll = QScrollArea()
        self.atlas_scroll.setWidgetResizable(True)
        self.atlas_scroll.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; border: 1px solid {COLORS['border_primary']};"
        )
        self.atlas_label = QLabel("No atlas loaded")
        self.atlas_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.atlas_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.atlas_scroll.setWidget(self.atlas_label)
        atlas_layout.addWidget(self.atlas_scroll, stretch=1)

        self.detail_tabs.addTab(atlas_widget, "Atlas View")

    def _init_map_tab(self):
        """Create the Map View sub-tab with zoom/pan support."""
        map_widget = QWidget()
        map_layout = QVBoxLayout(map_widget)
        map_layout.setContentsMargins(8, 8, 8, 8)
        map_layout.setSpacing(8)

        # Controls bar
        controls_bar = QHBoxLayout()

        palette_label = QLabel("Palette:")
        palette_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        controls_bar.addWidget(palette_label)

        self.map_palette_combo = QComboBox()
        self.map_palette_combo.setMinimumWidth(120)
        self.map_palette_combo.currentIndexChanged.connect(self._refresh_map)
        controls_bar.addWidget(self.map_palette_combo)

        render_label = QLabel("Render Size:")
        render_label.setStyleSheet(f"color: {COLORS['text_primary']};")
        controls_bar.addWidget(render_label)

        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(64, 8192)
        self.zoom_spin.setValue(2048)
        self.zoom_spin.setSingleStep(256)
        self.zoom_spin.setSuffix(" px")
        self.zoom_spin.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_primary']}; "
            f"border-radius: 4px; padding: 4px;"
        )
        self.zoom_spin.valueChanged.connect(self._refresh_map)
        controls_bar.addWidget(self.zoom_spin)

        # Zoom controls
        controls_bar.addSpacing(16)

        fit_btn = QPushButton("Fit")
        fit_btn.setToolTip("Fit image to viewport")
        fit_btn.setFixedWidth(50)
        fit_btn.clicked.connect(lambda: self.map_label.fitToView())
        controls_bar.addWidget(fit_btn)

        reset_btn = QPushButton("1:1")
        reset_btn.setToolTip("Reset to 100% zoom")
        reset_btn.setFixedWidth(40)
        reset_btn.clicked.connect(lambda: self.map_label.resetZoom())
        controls_bar.addWidget(reset_btn)

        self.zoom_pct_label = QLabel("100%")
        self.zoom_pct_label.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; min-width: 48px;"
        )
        controls_bar.addWidget(self.zoom_pct_label)

        controls_bar.addStretch()

        hint_label = QLabel("Scroll to zoom \u2022 Drag to pan")
        hint_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 10px;")
        controls_bar.addWidget(hint_label)

        map_layout.addLayout(controls_bar)

        # Map image with zoom/pan
        self.map_scroll = QScrollArea()
        self.map_scroll.setWidgetResizable(False)
        self.map_scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_scroll.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; border: 1px solid {COLORS['border_primary']};"
        )
        self.map_label = ZoomPanLabel()
        self.map_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.map_label.setText("No map loaded")
        self.map_label.zoom_changed.connect(lambda _: self._update_zoom_label())
        self.map_scroll.setWidget(self.map_label)
        map_layout.addWidget(self.map_scroll, stretch=1)

        self.detail_tabs.addTab(map_widget, "Map View")

    def _init_records_tab(self):
        """Create the Records Table sub-tab."""
        records_widget = QWidget()
        records_layout = QVBoxLayout(records_widget)
        records_layout.setContentsMargins(8, 8, 8, 8)
        records_layout.setSpacing(8)

        self.records_table = QTableWidget()
        self.records_table.setColumnCount(7)
        self.records_table.setHorizontalHeaderLabels(
            ["Index", "value_a", "low16", "high16", "value_b", "value_c", "ref_count"]
        )
        self.records_table.setAlternatingRowColors(True)
        self.records_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.records_table.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; "
            f"gridline-color: {COLORS['border_primary']}; "
            f"alternate-background-color: {COLORS['bg_secondary']};"
        )
        records_layout.addWidget(self.records_table)

        self.detail_tabs.addTab(records_widget, "Records Table")

    def _init_parts_tab(self):
        """Create the Parts Table sub-tab."""
        parts_widget = QWidget()
        parts_layout = QVBoxLayout(parts_widget)
        parts_layout.setContentsMargins(8, 8, 8, 8)
        parts_layout.setSpacing(8)

        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(9)
        self.parts_table.setHorizontalHeaderLabels(
            ["Index", "offset_x", "offset_y", "width", "height", "u0", "v0", "u1", "v1"]
        )
        self.parts_table.setAlternatingRowColors(True)
        self.parts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.parts_table.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; "
            f"gridline-color: {COLORS['border_primary']}; "
            f"alternate-background-color: {COLORS['bg_secondary']};"
        )
        parts_layout.addWidget(self.parts_table)

        self.detail_tabs.addTab(parts_widget, "Parts Table")

    def _init_report_tab(self):
        """Create the Report sub-tab."""
        report_widget = QWidget()
        report_layout = QVBoxLayout(report_widget)
        report_layout.setContentsMargins(8, 8, 8, 8)
        report_layout.setSpacing(8)

        self.report_text = QTextEdit()
        self.report_text.setReadOnly(True)
        self.report_text.setStyleSheet(
            f"background-color: {COLORS['bg_tertiary']}; "
            f"color: {COLORS['text_primary']}; "
            f"border: 1px solid {COLORS['border_primary']}; "
            f"border-radius: 4px; "
            f"font-family: 'Consolas', 'Courier New', monospace; "
            f"font-size: 12px;"
        )
        self.report_text.setPlaceholderText(
            "Run a full scan to generate a report, or select a file to view its details."
        )
        report_layout.addWidget(self.report_text)

        self.detail_tabs.addTab(report_widget, "Report")

    # ------------------------------------------------------------------ #
    #  Directory selection
    # ------------------------------------------------------------------ #

    def _select_directory(self):
        """Open a directory dialog and populate the file list."""
        directory = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if not directory:
            return
        self._game_dir = Path(directory)
        self.dir_label.setText(str(self._game_dir))
        self._log_status(f"Game directory set to: {self._game_dir}")
        self.scan_btn.setEnabled(True)
        self._populate_file_list()

    def _populate_file_list(self):
        """Populate file list using list_cell_files via WorkerThread."""
        if self._game_dir is None:
            return

        self.file_list.clear()
        self._log_status("Scanning for cell files...")

        worker = WorkerThread(list_cell_files, [self._game_dir])
        worker.result.connect(self._on_files_listed)
        worker.error.connect(lambda e: self._log_status(f"Error listing files: {e}"))
        worker.finished.connect(lambda: self._log_status("File scan complete."))
        self.workers.append(worker)
        worker.start()

    def _on_files_listed(self, files):
        """Handle the result of list_cell_files."""
        self._cell_files: list[Path] = files
        self.file_list.clear()
        for path in files:
            # Show relative path from game dir for readability
            try:
                display = str(path.relative_to(self._game_dir))
            except ValueError:
                display = str(path)
            self.file_list.addItem(display)
        self._log_status(f"Found {len(files)} cell file(s).")

    # ------------------------------------------------------------------ #
    #  File selection -> load document
    # ------------------------------------------------------------------ #

    def _on_file_selected(self, row: int):
        """Load the selected cell file via WorkerThread."""
        if row < 0 or not hasattr(self, "_cell_files") or row >= len(self._cell_files):
            return
        path = self._cell_files[row]
        self._log_status(f"Loading: {path.name}...")

        worker = WorkerThread(load_cell_document, [path])
        worker.result.connect(self._on_document_loaded)
        worker.error.connect(lambda e: self._log_status(f"Error loading file: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_document_loaded(self, document: LoadedCellDocument):
        """Handle the loaded document and populate all views."""
        self._current_document = document
        self._log_status(
            f"Loaded: {document.source_path.name} "
            f"({len(document.records)} records, "
            f"{len(document.decoded_records)} decoded)"
        )
        self._populate_palette_combos()
        self._refresh_atlas()
        self._refresh_map()
        self._populate_records_table()
        self._populate_parts_table()
        self._populate_single_file_report()

    # ------------------------------------------------------------------ #
    #  Palette combos
    # ------------------------------------------------------------------ #

    def _populate_palette_combos(self):
        """Update palette combo boxes based on current document."""
        doc = self._current_document
        if doc is None:
            return

        count = len(doc.palettes) if doc.palettes else 0
        for combo in (self.atlas_palette_combo, self.map_palette_combo):
            combo.blockSignals(True)
            combo.clear()
            if count == 0:
                combo.addItem("(no palettes)")
            else:
                for i in range(count):
                    combo.addItem(f"Palette {i}")
            combo.setCurrentIndex(0)
            combo.blockSignals(False)

    # ------------------------------------------------------------------ #
    #  Atlas View
    # ------------------------------------------------------------------ #

    def _refresh_atlas(self):
        """Render the atlas image with the selected palette via WorkerThread."""
        doc = self._current_document
        if doc is None:
            return

        palette_index = max(0, self.atlas_palette_combo.currentIndex())

        worker = WorkerThread(build_atlas_for_document, [doc, palette_index])
        worker.result.connect(self._on_atlas_rendered)
        worker.error.connect(lambda e: self._log_status(f"Atlas render error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_atlas_rendered(self, image):
        """Display the atlas image."""
        if image is None:
            self.atlas_label.setText("No atlas available for this file.")
            return
        pixmap = pil_to_qpixmap(image)
        self.atlas_label.setPixmap(pixmap)
        self.atlas_label.adjustSize()

    # ------------------------------------------------------------------ #
    #  Map View
    # ------------------------------------------------------------------ #

    def _refresh_map(self):
        """Render the map image with the selected palette and zoom via WorkerThread."""
        doc = self._current_document
        if doc is None:
            return

        palette_index = max(0, self.map_palette_combo.currentIndex())
        max_edge = self.zoom_spin.value()

        worker = WorkerThread(render_map_image, [doc, palette_index, max_edge])
        worker.result.connect(self._on_map_rendered)
        worker.error.connect(lambda e: self._log_status(f"Map render error: {e}"))
        self.workers.append(worker)
        worker.start()

    def _on_map_rendered(self, image):
        """Display the map image."""
        if image is None:
            self.map_label.setText("No map available for this file.")
            return
        pixmap = pil_to_qpixmap(image)
        self.map_label.setSourcePixmap(pixmap)
        self._update_zoom_label()

    def _update_zoom_label(self):
        """Update the zoom percentage indicator."""
        self.zoom_pct_label.setText(f"{self.map_label.zoom * 100:.0f}%")

    # ------------------------------------------------------------------ #
    #  Records Table
    # ------------------------------------------------------------------ #

    def _populate_records_table(self):
        """Fill the records table from decoded_records."""
        doc = self._current_document
        if doc is None:
            self.records_table.setRowCount(0)
            return

        # Build a ref_count map from the cell_map
        ref_counts: dict[int, int] = {}
        if doc.cell_map is not None:
            for value in doc.cell_map.values:
                idx = value & 0xFFFF
                ref_counts[idx] = ref_counts.get(idx, 0) + 1

        decoded = doc.decoded_records
        self.records_table.setRowCount(len(decoded))
        for row, rec in enumerate(decoded):
            self.records_table.setItem(row, 0, QTableWidgetItem(str(rec.index)))
            self.records_table.setItem(row, 1, QTableWidgetItem(f"0x{rec.value_a:08X}"))
            self.records_table.setItem(row, 2, QTableWidgetItem(str(rec.value_a_low16)))
            self.records_table.setItem(row, 3, QTableWidgetItem(str(rec.value_a_high16)))
            self.records_table.setItem(row, 4, QTableWidgetItem(f"0x{rec.value_b:08X}"))
            self.records_table.setItem(row, 5, QTableWidgetItem(f"0x{rec.value_c:08X}"))
            self.records_table.setItem(
                row, 6, QTableWidgetItem(str(ref_counts.get(rec.index, 0)))
            )

        self.records_table.resizeColumnsToContents()

    # ------------------------------------------------------------------ #
    #  Parts Table
    # ------------------------------------------------------------------ #

    def _populate_parts_table(self):
        """Fill the parts table from texture.parts."""
        doc = self._current_document
        if doc is None or doc.texture is None:
            self.parts_table.setRowCount(0)
            return

        parts = doc.texture.parts
        self.parts_table.setRowCount(len(parts))
        for row, part in enumerate(parts):
            self.parts_table.setItem(row, 0, QTableWidgetItem(str(part.index)))
            self.parts_table.setItem(row, 1, QTableWidgetItem(f"{part.offset_x:.2f}"))
            self.parts_table.setItem(row, 2, QTableWidgetItem(f"{part.offset_y:.2f}"))
            self.parts_table.setItem(row, 3, QTableWidgetItem(f"{part.width:.2f}"))
            self.parts_table.setItem(row, 4, QTableWidgetItem(f"{part.height:.2f}"))
            self.parts_table.setItem(row, 5, QTableWidgetItem(f"{part.u0:.6f}"))
            self.parts_table.setItem(row, 6, QTableWidgetItem(f"{part.v0:.6f}"))
            self.parts_table.setItem(row, 7, QTableWidgetItem(f"{part.u1:.6f}"))
            self.parts_table.setItem(row, 8, QTableWidgetItem(f"{part.v1:.6f}"))

        self.parts_table.resizeColumnsToContents()

    # ------------------------------------------------------------------ #
    #  Single-file report
    # ------------------------------------------------------------------ #

    def _populate_single_file_report(self):
        """Show a text summary of the current document in the Report tab."""
        doc = self._current_document
        if doc is None:
            self.report_text.clear()
            return

        lines: list[str] = []
        lines.append(f"# File: {doc.source_path.name}")
        lines.append(f"Source: {doc.source_path}")
        lines.append(f"Raw size: {len(doc.raw_data)} bytes")
        lines.append(f"Decompressed size: {len(doc.decompressed_data)} bytes")
        if doc.lz77 is not None:
            lines.append(f"LZ77 compressed: yes")
        lines.append("")

        lines.append(f"## Header")
        lines.append(f"  Table offset: 0x{doc.header.table_offset:X}")
        lines.append(f"  Entry count: {doc.header.entry_count}")
        lines.append(f"  Grid: {doc.header.grid_width} x {doc.header.grid_height}")
        lines.append("")

        lines.append(f"## Records ({len(doc.records)})")
        for rec in doc.decoded_records[:20]:
            lines.append(
                f"  [{rec.index:4d}] a=0x{rec.value_a:08X} "
                f"(lo={rec.value_a_low16}, hi={rec.value_a_high16}) "
                f"b=0x{rec.value_b:08X} c=0x{rec.value_c:08X}"
            )
        if len(doc.decoded_records) > 20:
            lines.append(f"  ... ({len(doc.decoded_records) - 20} more)")
        lines.append("")

        lines.append(f"## Chunks ({len(doc.chunks)})")
        for chunk in doc.chunks:
            lines.append(
                f"  {chunk.name} @ 0x{chunk.offset:X} "
                f"size=0x{chunk.size_total:X} payload=0x{chunk.payload_size:X}"
            )
        lines.append("")

        if doc.cell_map is not None:
            lines.append(f"## Map")
            lines.append(f"  Dimensions: {doc.cell_map.width} x {doc.cell_map.height}")
            lines.append(f"  Total cells: {len(doc.cell_map.values)}")
            lines.append("")

        if doc.texture is not None:
            lines.append(f"## Texture")
            lines.append(f"  Atlas: {doc.texture.header.width} x {doc.texture.header.height}")
            lines.append(f"  Storage: {doc.texture.storage_kind}")
            lines.append(f"  Parts: {len(doc.texture.parts)}")
            lines.append(f"  Palettes: {len(doc.palettes)}")
            lines.append("")

        self.report_text.setPlainText("\n".join(lines))

    # ------------------------------------------------------------------ #
    #  Full Scan
    # ------------------------------------------------------------------ #

    def _run_full_scan(self):
        """Run a full workspace scan via WorkerThread."""
        if self._game_dir is None:
            self._log_status("No game directory selected.")
            return

        self._log_status("Starting full scan (this may take a while)...")
        self.scan_btn.setEnabled(False)

        worker = WorkerThread(scan_workspace, [self._game_dir])
        worker.result.connect(self._on_scan_complete)
        worker.error.connect(lambda e: self._log_status(f"Scan error: {e}"))
        worker.finished.connect(lambda: self.scan_btn.setEnabled(True))
        self.workers.append(worker)
        worker.start()

    def _on_scan_complete(self, result):
        """Handle full scan results and build a markdown report in the Report tab."""
        debug_insight, map_groups = result
        self._log_status(
            f"Scan complete: {len(map_groups)} map group(s) found."
        )

        # Build report text in-memory (same format as write_markdown_report but
        # we render it directly into the QTextEdit instead of writing to disk).
        try:
            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                report_path = write_markdown_report(Path(tmp), debug_insight, map_groups)
                report_text = report_path.read_text(encoding="utf-8")
            self.report_text.setPlainText(report_text)
            self.detail_tabs.setCurrentIndex(4)  # Switch to Report tab
            self._log_status("Report generated successfully.")
        except Exception as exc:
            self._log_status(f"Error generating report: {exc}")
