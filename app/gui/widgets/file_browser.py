"""
File browser widget with dual view modes (Details and Thumbnails).
Supports keyboard navigation and file selection.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget,
    QTreeView, QListView, QHeaderView, QMenu, QMessageBox,
    QPushButton, QButtonGroup, QAbstractItemView, QLabel,
    QApplication
)
from PyQt6.QtGui import (
    QStandardItemModel, QStandardItem, QPixmap, QIcon
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QModelIndex, QTimer
import os

from app.core.dokapon_extract import decompress_lz77


class FileBrowserWidget(QWidget):
    """
    Combined file browser with Details (tree) and Thumbnails (grid) views.
    
    Signals:
        file_selected(str): Emitted when a file is selected (single click or arrow keys)
        extract_file(str): Emitted when user requests to extract a file
    """
    
    file_selected = pyqtSignal(str)
    extract_file = pyqtSignal(str)
    
    # Supported preview extensions
    PREVIEW_EXTENSIONS = {".tex", ".spranm", ".mpd", ".fnt"}
    
    def __init__(self, file_type_combo=None, parent=None):
        super().__init__(parent)
        self.file_type_combo = file_type_combo
        self._root_path = None      # Original root path
        self._current_path = None   # Current path in grid view
        self._thumbnail_cache = {}
        self._all_files = []        # Flat list of all files for tree view
        self._navigation_history = []  # For back navigation
        self._init_ui()
    
    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # View toggle buttons
        toggle_layout = QHBoxLayout()
        toggle_layout.setSpacing(4)
        
        self.view_label = QLabel("View:")
        toggle_layout.addWidget(self.view_label)
        
        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        
        self.details_btn = QPushButton("☰ Details")
        self.details_btn.setCheckable(True)
        self.details_btn.setChecked(True)
        self.details_btn.setFixedWidth(90)
        self.btn_group.addButton(self.details_btn, 0)
        
        self.thumbs_btn = QPushButton("⊞ Thumbs")
        self.thumbs_btn.setCheckable(True)
        self.thumbs_btn.setFixedWidth(90)
        self.btn_group.addButton(self.thumbs_btn, 1)
        
        toggle_layout.addWidget(self.details_btn)
        toggle_layout.addWidget(self.thumbs_btn)
        toggle_layout.addStretch()
        
        # File count label
        self.file_count_label = QLabel("0 files")
        toggle_layout.addWidget(self.file_count_label)
        
        layout.addLayout(toggle_layout)
        
        # Stacked widget for views
        self.stack = QStackedWidget()
        
        # Tree model (hierarchical for details view)
        self.tree_model = QStandardItemModel()
        self.tree_model.setHorizontalHeaderLabels(['Name', 'Type', 'Size'])
        
        # Grid model (for thumbnails view - shows current folder contents)
        self.grid_model = QStandardItemModel()
        
        # Keep reference to main model for compatibility
        self.model = self.tree_model
        
        # Details view (Tree)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.tree_model)
        self._setup_tree_view()
        
        # Thumbnails view container (includes navigation bar)
        thumb_container = QWidget()
        thumb_layout = QVBoxLayout(thumb_container)
        thumb_layout.setContentsMargins(0, 0, 0, 0)
        thumb_layout.setSpacing(4)
        
        # Navigation bar for grid view
        nav_layout = QHBoxLayout()
        nav_layout.setSpacing(4)
        
        self.back_btn = QPushButton("← Back")
        self.back_btn.setFixedWidth(70)
        self.back_btn.clicked.connect(self._navigate_back)
        self.back_btn.setEnabled(False)
        nav_layout.addWidget(self.back_btn)
        
        self.path_label = QLabel("")
        self.path_label.setStyleSheet("color: #858585; padding: 4px;")
        nav_layout.addWidget(self.path_label, stretch=1)
        
        thumb_layout.addLayout(nav_layout)
        
        # Grid view
        self.grid_view = QListView()
        self.grid_view.setModel(self.grid_model)
        self._setup_grid_view()
        thumb_layout.addWidget(self.grid_view)
        
        self.stack.addWidget(self.tree_view)
        self.stack.addWidget(thumb_container)
        
        layout.addWidget(self.stack)
        
        # Connect signals
        self.btn_group.idClicked.connect(self._on_view_changed)
        self.tree_view.clicked.connect(self._on_item_clicked_tree)
        self.tree_view.selectionModel().currentChanged.connect(self._on_selection_changed_tree)
        self.grid_view.clicked.connect(self._on_item_clicked_grid)
        self.grid_view.selectionModel().currentChanged.connect(self._on_selection_changed_grid)
        
        # Context menus
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_context_menu_tree)
        self.grid_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.grid_view.customContextMenuRequested.connect(self._show_context_menu_grid)
    
    def _setup_tree_view(self):
        """Configure the tree/details view."""
        self.tree_view.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.tree_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.setRootIsDecorated(True)
        self.tree_view.setItemsExpandable(True)
        self.tree_view.setUniformRowHeights(True)
        self.tree_view.setIndentation(20)
        
        # Enable keyboard navigation
        self.tree_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Header setup
        header = self.tree_view.header()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.resizeSection(1, 80)
        header.resizeSection(2, 100)
    
    def _setup_grid_view(self):
        """Configure the grid/thumbnails view."""
        self.grid_view.setViewMode(QListView.ViewMode.IconMode)
        self.grid_view.setIconSize(QSize(96, 96))
        self.grid_view.setGridSize(QSize(120, 140))
        self.grid_view.setSpacing(8)
        self.grid_view.setResizeMode(QListView.ResizeMode.Adjust)
        self.grid_view.setWrapping(True)
        self.grid_view.setWordWrap(True)
        self.grid_view.setUniformItemSizes(True)
        self.grid_view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.grid_view.setEditTriggers(QListView.EditTrigger.NoEditTriggers)
        
        # Enable keyboard navigation
        self.grid_view.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Double-click to enter folders
        self.grid_view.doubleClicked.connect(self._on_grid_double_click)
    
    def _on_view_changed(self, view_id: int):
        """Switch between views."""
        self.stack.setCurrentIndex(view_id)
        
        # Sync selection between views
        if view_id == 0:  # Details
            self.tree_view.setFocus()
        else:  # Thumbnails
            # Reset to root when switching to thumbs
            if self._root_path and self._current_path != self._root_path:
                self._navigate_to(self._root_path)
            self.grid_view.setFocus()
    
    def _on_grid_double_click(self, index: QModelIndex):
        """Handle double-click in grid view to navigate into folders."""
        if not index.isValid():
            return
        
        item = self.grid_model.itemFromIndex(index)
        if not item:
            return
        
        path = item.data(Qt.ItemDataRole.UserRole)
        is_folder = item.data(Qt.ItemDataRole.UserRole + 1)  # Custom role for folder flag
        
        if path and is_folder:
            self._navigate_to(path)
        elif path and os.path.isfile(path):
            # Double-click on file emits extract signal
            self.extract_file.emit(path)
    
    def _navigate_to(self, path: str):
        """Navigate to a folder in grid view."""
        if not os.path.isdir(path):
            return
        
        # Save current path to history for back navigation
        if self._current_path and self._current_path != path:
            self._navigation_history.append(self._current_path)
        
        self._current_path = path
        self._populate_grid_folder(path)
        self._update_nav_ui()
    
    def _navigate_back(self):
        """Go back to previous folder in grid view."""
        if self._navigation_history:
            prev_path = self._navigation_history.pop()
            self._current_path = prev_path
            self._populate_grid_folder(prev_path)
            self._update_nav_ui()
    
    def _update_nav_ui(self):
        """Update navigation UI elements."""
        # Enable/disable back button
        can_go_back = len(self._navigation_history) > 0
        self.back_btn.setEnabled(can_go_back)
        
        # Update path label
        if self._current_path and self._root_path:
            try:
                rel_path = os.path.relpath(self._current_path, os.path.dirname(self._root_path))
                self.path_label.setText(f"📁 {rel_path}")
            except ValueError:
                self.path_label.setText(f"📁 {os.path.basename(self._current_path)}")
    
    def _on_item_clicked_tree(self, index: QModelIndex):
        """Handle item click in tree view."""
        if not index.isValid():
            return
        
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        
        item = self.tree_model.itemFromIndex(index)
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isfile(file_path):
                self.file_selected.emit(file_path)
    
    def _on_item_clicked_grid(self, index: QModelIndex):
        """Handle item click in grid view."""
        if not index.isValid():
            return
        
        item = self.grid_model.itemFromIndex(index)
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isfile(file_path):
                self.file_selected.emit(file_path)
    
    def _on_selection_changed_tree(self, current: QModelIndex, previous: QModelIndex):
        """Handle selection change in tree view via keyboard navigation."""
        if not current.isValid():
            return
        
        if current.column() != 0:
            current = current.siblingAtColumn(0)
        
        item = self.tree_model.itemFromIndex(current)
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isfile(file_path):
                self.file_selected.emit(file_path)
    
    def _on_selection_changed_grid(self, current: QModelIndex, previous: QModelIndex):
        """Handle selection change in grid view via keyboard navigation."""
        if not current.isValid():
            return
        
        item = self.grid_model.itemFromIndex(current)
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.isfile(file_path):
                self.file_selected.emit(file_path)
    
    def _show_context_menu_tree(self, position):
        """Show right-click context menu for tree view."""
        index = self.tree_view.indexAt(position)
        if not index.isValid():
            return
        
        if index.column() != 0:
            index = index.siblingAtColumn(0)
        
        item = self.tree_model.itemFromIndex(index)
        if not item:
            return
        
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.isfile(file_path):
            return
        
        menu = QMenu(self)
        extract_action = menu.addAction("Extract File")
        extract_action.triggered.connect(lambda: self.extract_file.emit(file_path))
        menu.exec(self.tree_view.mapToGlobal(position))
    
    def _show_context_menu_grid(self, position):
        """Show right-click context menu for grid view."""
        index = self.grid_view.indexAt(position)
        if not index.isValid():
            return
        
        item = self.grid_model.itemFromIndex(index)
        if not item:
            return
        
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.isfile(file_path):
            return
        
        menu = QMenu(self)
        extract_action = menu.addAction("Extract File")
        extract_action.triggered.connect(lambda: self.extract_file.emit(file_path))
        menu.exec(self.grid_view.mapToGlobal(position))
    
    def populate_tree(self, path: str):
        """Populate the browser with files from the given path."""
        self._root_path = path
        self._current_path = path
        self._thumbnail_cache.clear()
        self._all_files = []  # Reset flat file list
        self._navigation_history = []  # Reset navigation
        
        # Clear both models
        self.tree_model.clear()
        self.tree_model.setHorizontalHeaderLabels(['Name', 'Type', 'Size'])
        self.grid_model.clear()
        
        if not os.path.exists(path):
            self.file_count_label.setText("0 files")
            return
        
        selected_type = "all files"
        if self.file_type_combo:
            selected_type = self.file_type_combo.currentText().lower()
        
        root_item = self.tree_model.invisibleRootItem()
        file_count = 0
        
        if os.path.isfile(path):
            self._add_file_item(root_item, path, selected_type)
            file_count = 1
        else:
            # Add root folder to tree
            folder_item = self._create_folder_item(os.path.basename(path) or path, path)
            root_item.appendRow(folder_item)
            
            # Add contents to tree and collect files for grid
            file_count = self._add_directory_contents(folder_item[0], path, selected_type)
            
            # Auto-expand root in tree view
            root_index = self.tree_model.indexFromItem(folder_item[0])
            if root_index.isValid():
                self.tree_view.expand(root_index)
        
        self.file_count_label.setText(f"{file_count} files")
        
        # Populate grid view with current folder contents
        self._populate_grid_folder(path)
        self._update_nav_ui()
    
    def _create_folder_item(self, name: str, path: str) -> list:
        """Create a folder item row."""
        name_item = QStandardItem(f"📁 {name}")
        name_item.setData(path, Qt.ItemDataRole.UserRole)
        name_item.setCheckable(True)
        
        type_item = QStandardItem("Directory")
        size_item = QStandardItem("")
        
        return [name_item, type_item, size_item]
    
    def _create_file_item(self, name: str, path: str, size: int, ext: str) -> list:
        """Create a file item row with optional thumbnail."""
        # Choose icon based on extension
        icon_map = {
            ".tex": "🖼",
            ".spranm": "🎬",
            ".mpd": "🗺",
            ".fnt": "🔤",
        }
        icon = icon_map.get(ext, "📄")
        
        name_item = QStandardItem(f"{icon} {name}")
        name_item.setData(path, Qt.ItemDataRole.UserRole)
        name_item.setCheckable(True)
        
        # Try to load thumbnail for grid view
        if ext in self.PREVIEW_EXTENSIONS:
            thumbnail = self._get_thumbnail(path)
            if thumbnail:
                name_item.setIcon(QIcon(thumbnail))
        
        type_item = QStandardItem(ext)
        size_item = QStandardItem(self._format_size(size))
        
        return [name_item, type_item, size_item]
    
    def _get_thumbnail(self, file_path: str) -> QPixmap:
        """Get or create a thumbnail for a file."""
        if file_path in self._thumbnail_cache:
            return self._thumbnail_cache[file_path]
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Handle LZ77 compression
            if data.startswith(b'LZ77'):
                data = decompress_lz77(data)
                if not data:
                    return None
            
            # Find PNG data
            png_start = data.find(b'\x89PNG\r\n\x1a\n')
            if png_start >= 0:
                pixmap = QPixmap()
                if pixmap.loadFromData(data[png_start:]):
                    # Scale to thumbnail size
                    thumbnail = pixmap.scaled(
                        96, 96,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    self._thumbnail_cache[file_path] = thumbnail
                    return thumbnail
        except Exception:
            pass
        
        return None
    
    def _add_file_item(self, parent_item: QStandardItem, file_path: str, selected_type: str) -> bool:
        """Add a file item to the tree. Returns True if file was added."""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Filter by type
        if selected_type != "all files":
            type_ext_map = {
                "texture files (.tex)": ".tex",
                "sprite files (.spranm)": ".spranm",
                "font files (.fnt)": ".fnt",
            }
            required_ext = type_ext_map.get(selected_type)
            if required_ext and file_ext != required_ext:
                return False
        
        try:
            size = os.path.getsize(file_path)
        except OSError:
            size = 0
        
        row = self._create_file_item(file_name, file_path, size, file_ext)
        parent_item.appendRow(row)
        
        # Also track file for grid view
        self._all_files.append((file_path, file_name, file_ext, size))
        return True
    
    def _add_directory_contents(self, parent_item: QStandardItem, dir_path: str, selected_type: str) -> int:
        """Add directory contents recursively. Returns file count."""
        file_count = 0
        
        try:
            entries = sorted(os.scandir(dir_path), key=lambda e: (not e.is_dir(), e.name.lower()))
            
            for entry in entries:
                if entry.is_file():
                    if self._add_file_item(parent_item, entry.path, selected_type):
                        file_count += 1
                elif entry.is_dir():
                    folder_row = self._create_folder_item(entry.name, entry.path)
                    parent_item.appendRow(folder_row)
                    file_count += self._add_directory_contents(folder_row[0], entry.path, selected_type)
        except PermissionError:
            pass
        
        return file_count
    
    def _populate_grid_folder(self, folder_path: str):
        """Populate the grid view with contents of a specific folder."""
        self.grid_model.clear()
        
        if not os.path.isdir(folder_path):
            return
        
        selected_type = "all files"
        if self.file_type_combo:
            selected_type = self.file_type_combo.currentText().lower()
        
        try:
            entries = sorted(os.scandir(folder_path), key=lambda e: (not e.is_dir(), e.name.lower()))
            
            for entry in entries:
                if entry.is_dir():
                    # Add folder item
                    item = QStandardItem(entry.name)
                    item.setData(entry.path, Qt.ItemDataRole.UserRole)
                    item.setData(True, Qt.ItemDataRole.UserRole + 1)  # Mark as folder
                    item.setIcon(self._get_folder_icon())
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
                    # Folders are not checkable for extraction
                    item.setCheckable(False)
                    self.grid_model.appendRow(item)
                    
                elif entry.is_file():
                    file_ext = os.path.splitext(entry.name)[1].lower()
                    
                    # Filter by type
                    if selected_type != "all files":
                        type_ext_map = {
                            "texture files (.tex)": ".tex",
                            "sprite files (.spranm)": ".spranm",
                            "font files (.fnt)": ".fnt",
                        }
                        required_ext = type_ext_map.get(selected_type)
                        if required_ext and file_ext != required_ext:
                            continue
                    
                    # Add file item
                    item = QStandardItem(entry.name)
                    item.setData(entry.path, Qt.ItemDataRole.UserRole)
                    item.setData(False, Qt.ItemDataRole.UserRole + 1)  # Mark as file
                    item.setCheckable(True)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
                    
                    # Try to load thumbnail
                    if file_ext in self.PREVIEW_EXTENSIONS:
                        thumbnail = self._get_thumbnail(entry.path)
                        if thumbnail and not thumbnail.isNull():
                            item.setIcon(QIcon(thumbnail))
                        else:
                            item.setIcon(self._get_placeholder_icon(file_ext))
                    else:
                        item.setIcon(self._get_placeholder_icon(file_ext))
                    
                    self.grid_model.appendRow(item)
                    
        except PermissionError:
            pass
    
    def _get_folder_icon(self) -> QIcon:
        """Get a folder icon for the grid view."""
        pixmap = QPixmap(96, 96)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        from PyQt6.QtGui import QPainter, QFont, QColor, QPainterPath
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw folder shape
        folder_color = QColor("#f0c36d")  # Golden folder color
        folder_dark = QColor("#d4a84a")   # Darker shade
        
        # Folder tab (top part)
        painter.setBrush(folder_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(8, 20, 30, 12, 4, 4)
        
        # Folder body
        painter.setBrush(folder_color)
        painter.drawRoundedRect(8, 28, 80, 52, 6, 6)
        
        # Folder front (3D effect)
        painter.setBrush(folder_dark)
        painter.drawRoundedRect(8, 38, 80, 42, 6, 6)
        
        painter.end()
        return QIcon(pixmap)
    
    def _get_placeholder_icon(self, ext: str) -> QIcon:
        """Get a placeholder icon for files without thumbnails."""
        # Create a simple colored pixmap as placeholder
        pixmap = QPixmap(96, 96)
        
        # Choose color based on extension
        color_map = {
            ".tex": "#4a9eff",    # Blue for textures
            ".spranm": "#ff9f4a", # Orange for animations
            ".mpd": "#4aff9f",    # Green for maps
            ".fnt": "#ff4a9f",    # Pink for fonts
            ".mdl": "#9f4aff",    # Purple for models
        }
        color = color_map.get(ext, "#888888")
        pixmap.fill(Qt.GlobalColor.transparent)
        
        from PyQt6.QtGui import QPainter, QFont, QColor
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle background
        painter.setBrush(QColor(color))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(8, 8, 80, 80, 8, 8)
        
        # Draw extension text
        painter.setPen(QColor("#ffffff"))
        font = QFont("Segoe UI", 14, QFont.Weight.Bold)
        painter.setFont(font)
        ext_text = ext[1:].upper() if ext else "FILE"
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, ext_text)
        
        painter.end()
        return QIcon(pixmap)
    
    def _format_size(self, size_bytes: int) -> str:
        """Format file size to human readable string."""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"
    
    def get_checked_files(self) -> list:
        """Get list of checked file paths from both views."""
        checked = set()
        
        # Collect from tree model
        self._collect_checked(self.tree_model.invisibleRootItem(), checked)
        
        # Collect from grid model
        for row in range(self.grid_model.rowCount()):
            item = self.grid_model.item(row)
            if item and item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path and os.path.isfile(path):
                    checked.add(path)
        
        return list(checked)
    
    def get_checked_files_with_paths(self) -> list:
        """Get list of (file_path, relative_path) tuples for checked files."""
        checked = []
        checked_paths = set()
        
        # Get root path from tree model
        root = self.tree_model.invisibleRootItem()
        if root.rowCount() == 0:
            return checked
        
        first_child = root.child(0)
        if not first_child:
            return checked
        
        base_path = first_child.data(Qt.ItemDataRole.UserRole)
        if not base_path:
            return checked
        
        root_path = os.path.dirname(base_path)
        
        # Collect from tree model
        self._collect_checked_with_paths(root, checked, checked_paths, root_path)
        
        # Collect from grid model (for items checked in grid view)
        for row in range(self.grid_model.rowCount()):
            item = self.grid_model.item(row)
            if item and item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path and os.path.isfile(path) and path not in checked_paths:
                    rel_path = os.path.relpath(path, root_path)
                    checked.append((path, rel_path))
                    checked_paths.add(path)
        
        return checked
    
    def _collect_checked(self, parent: QStandardItem, checked: set):
        """Recursively collect checked file paths."""
        for row in range(parent.rowCount()):
            item = parent.child(row, 0)
            if not item:
                continue
            
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path and os.path.isfile(path):
                    checked.add(path)
            
            if item.hasChildren():
                self._collect_checked(item, checked)
    
    def _collect_checked_with_paths(self, parent: QStandardItem, checked: list, checked_paths: set, root_path: str):
        """Recursively collect checked files with relative paths."""
        for row in range(parent.rowCount()):
            item = parent.child(row, 0)
            if not item:
                continue
            
            if item.checkState() == Qt.CheckState.Checked:
                path = item.data(Qt.ItemDataRole.UserRole)
                if path and os.path.isfile(path) and path not in checked_paths:
                    rel_path = os.path.relpath(path, root_path)
                    checked.append((path, rel_path))
                    checked_paths.add(path)
            
            if item.hasChildren():
                self._collect_checked_with_paths(item, checked, checked_paths, root_path)
    
    def keyPressEvent(self, event):
        """Handle key press events for better navigation."""
        # Space toggles checkbox on selected items
        if event.key() == Qt.Key.Key_Space:
            current_view_index = self.stack.currentIndex()
            
            if current_view_index == 0:  # Tree view
                indexes = self.tree_view.selectionModel().selectedIndexes()
                for index in indexes:
                    if index.column() == 0:
                        item = self.tree_model.itemFromIndex(index)
                        if item and item.isCheckable():
                            new_state = (
                                Qt.CheckState.Unchecked 
                                if item.checkState() == Qt.CheckState.Checked 
                                else Qt.CheckState.Checked
                            )
                            item.setCheckState(new_state)
            else:  # Grid view
                indexes = self.grid_view.selectionModel().selectedIndexes()
                for index in indexes:
                    item = self.grid_model.itemFromIndex(index)
                    if item and item.isCheckable():
                        new_state = (
                            Qt.CheckState.Unchecked 
                            if item.checkState() == Qt.CheckState.Checked 
                            else Qt.CheckState.Checked
                        )
                        item.setCheckState(new_state)
            return
        
        super().keyPressEvent(event)

