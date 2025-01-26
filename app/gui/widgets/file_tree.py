from PyQt6.QtWidgets import QTreeView, QHeaderView, QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox
from PyQt6.QtGui import QStandardItemModel, QStandardItem, QIcon
from PyQt6.QtCore import Qt, pyqtSignal, QRect, QSize
import os

class FileTreeWidget(QTreeView):
    file_selected = pyqtSignal(str)  # Signal when file is selected
    extract_file = pyqtSignal(str)   # New signal for file extraction
    
    VALID_EXTENSIONS = {".tex", ".spranm", ".fnt"}  # Cache valid extensions
    
    def __init__(self, file_type_combo=None):
        super().__init__()
        self.file_type_combo = file_type_combo  # Store reference to combo box
        
        # Setup model
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(['Name', 'Type', 'Size'])
        self.setModel(self.model)
        
        # Configure view settings
        self._setup_view_settings()
        self._setup_header_and_columns()
        
        # Connect signals
        self.clicked.connect(self._handle_click)
        self.model.itemChanged.connect(self._handle_item_changed)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def _setup_view_settings(self):
        """Configure basic view settings"""
        self.setEditTriggers(QTreeView.EditTrigger.NoEditTriggers)
        self.setExpandsOnDoubleClick(False)
        self.setAllColumnsShowFocus(True)
        self.setRootIsDecorated(True)
        self.setItemsExpandable(True)
        self.setUniformRowHeights(True)
        self.setIndentation(25)  # Increased for better spacing
        self.setAlternatingRowColors(True)
        self.setIconSize(QSize(16, 16))  # Set consistent icon size
        
        # Disable tri-state checkboxes
        self.model.setItemPrototype(QStandardItem())
        for column in range(self.model.columnCount()):
            item = self.model.horizontalHeaderItem(column)
            if item:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsAutoTristate)

    def _setup_header_and_columns(self):
        """Configure header and column settings"""
        header = self.header()
        header.setStretchLastSection(True)  # Make last column stretch
        header.setSectionsMovable(False)
        
        # Set resize modes
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        
        # Initial setup of column widths
        self._update_column_widths()

    def _update_column_widths(self):
        """Update column widths to maintain proportions"""
        # Get the viewport width (visible area)
        viewport_width = self.viewport().width()
        
        # Calculate proportional widths
        name_width = int(viewport_width * 0.60)  # 70%
        type_width = int(viewport_width * 0.20)  # 20%
        # Use remaining width for size column to ensure exactly 100%
        size_width = viewport_width - name_width - type_width
        
        # Apply the widths
        self.setColumnWidth(0, name_width)
        self.setColumnWidth(1, type_width)
        self.setColumnWidth(2, size_width)

    def resizeEvent(self, event):
        """Handle resize events"""
        super().resizeEvent(event)
        self._update_column_widths()

    def showEvent(self, event):
        """Handle initial show event"""
        super().showEvent(event)
        self._update_column_widths()

    def _format_size(self, size_in_bytes):
        """Format file size to human readable format (MB and above)"""
        # Convert to MB first (1 MB = 1024 * 1024 bytes)
        size_in_mb = size_in_bytes / (1024 * 1024)
        
        # For files smaller than 1 MB, still show in MB with 3 decimals
        if size_in_mb < 1:
            return f"{size_in_mb:.3f} MB"
        # For files between 1 MB and 1024 MB
        elif size_in_mb < 1024:
            return f"{size_in_mb:.2f} MB"
        
        # Convert to GB if larger than 1024 MB
        size_in_gb = size_in_mb / 1024
        if size_in_gb < 1024:
            return f"{size_in_gb:.2f} GB"
        
        # Convert to TB if larger than 1024 GB
        size_in_tb = size_in_gb / 1024
        return f"{size_in_tb:.2f} TB"

    def _handle_click(self, index):
        """Handle item clicks"""
        if not index.isValid() or index.column() != 0:
            return
            
        item = self.model.itemFromIndex(index)
        if not item:
            return
            
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if file_path and os.path.isfile(file_path):
            self.file_selected.emit(file_path)

    def _add_file_to_tree(self, parent_item, file_path, selected_type=None):
        """Add a file to the tree"""
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        
        if selected_type and selected_type != "all files" and not file_ext in self.VALID_EXTENSIONS:
            return
        
        file_item = QStandardItem(QIcon("file.png"), file_name)
        file_item.setData(file_path, Qt.ItemDataRole.UserRole)
        file_item.setCheckable(True)
        # Disable tri-state for file items
        file_item.setFlags(file_item.flags() & ~Qt.ItemFlag.ItemIsAutoTristate)
        
        type_item = QStandardItem(file_ext)
        size_item = QStandardItem(self._format_size(os.path.getsize(file_path)))
        
        parent_item.appendRow([file_item, type_item, size_item])

    def _add_directory_to_tree(self, parent_item, dir_path, selected_type=None):
        """Add a directory and its contents to the tree"""
        dir_name = os.path.basename(dir_path) or dir_path
        dir_item = QStandardItem(QIcon("folder.png"), dir_name)
        dir_item.setData(dir_path, Qt.ItemDataRole.UserRole)
        dir_item.setCheckable(True)
        # Disable tri-state for directory items
        dir_item.setFlags(dir_item.flags() & ~Qt.ItemFlag.ItemIsAutoTristate)
        
        type_item = QStandardItem("Directory")
        size_item = QStandardItem("")  # Directories don't show size
        
        parent_item.appendRow([dir_item, type_item, size_item])
        
        # Add all files and subdirectories
        for entry in os.scandir(dir_path):
            if entry.is_file():
                self._add_file_to_tree(dir_item, entry.path, selected_type)
            else:
                self._add_directory_to_tree(dir_item, entry.path, selected_type)

    def populate_tree(self, path):
        """Populate tree with files from path"""
        self.model.clear()
        self.model.setHorizontalHeaderLabels(['Name', 'Type', 'Size'])
        
        if not os.path.exists(path):
            return
            
        selected_type = self.file_type_combo.currentText().lower() if self.file_type_combo else "all files"
        
        # Create root item
        root_item = self.model.invisibleRootItem()
        
        if os.path.isfile(path):
            self._add_file_to_tree(root_item, path, selected_type)
        else:
            # Add the input folder as the first item
            input_item = QStandardItem(QIcon("folder.png"), os.path.basename(path) or path)
            input_item.setData(path, Qt.ItemDataRole.UserRole)
            input_item.setCheckable(True)
            input_item.setFlags(input_item.flags() & ~Qt.ItemFlag.ItemIsAutoTristate)
            
            type_item = QStandardItem("Directory")
            size_item = QStandardItem("")
            
            root_item.appendRow([input_item, type_item, size_item])
            
            # Add contents to the input folder
            for entry in os.scandir(path):
                if entry.is_file():
                    self._add_file_to_tree(input_item, entry.path, selected_type)
                else:
                    self._add_directory_to_tree(input_item, entry.path, selected_type)

    def _handle_item_changed(self, item):
        """Handle checkbox state changes"""
        if not item.isCheckable():
            return
            
        state = item.checkState()
        
        # Block signals to prevent recursion
        self.model.blockSignals(True)
        
        try:
            # If this is the root item (first folder), handle specially
            if item.parent() is None or item.parent() == self.model.invisibleRootItem():
                # Update all children first
                self._update_children_state(item, state)
                # Force a visual refresh
                self.viewport().update()
            else:
                # Update all children (including the folder items)
                self._update_children_state(item, state)
                # Update parent states
                self._update_parent_state(item.parent())
        finally:
            # Re-enable signals
            self.model.blockSignals(False)

    def _update_children_state(self, parent_item, state):
        """Recursively update all children states"""
        if not parent_item:
            return
            
        for row in range(parent_item.rowCount()):
            child = parent_item.child(row)
            if child and child.isCheckable():
                child.setCheckState(state)
                # Force visual update for each child
                index = self.model.indexFromItem(child)
                if index.isValid():
                    self.update(index)
                if child.hasChildren():
                    self._update_children_state(child, state)

    def _update_parent_state(self, parent):
        """Update parent checkbox state based on children"""
        while parent and parent.isCheckable():
            children_states = []
            for row in range(parent.rowCount()):
                child = parent.child(row)
                if child and child.isCheckable():
                    children_states.append(child.checkState())
            
            if children_states:
                if all(state == Qt.CheckState.Checked for state in children_states):
                    parent.setCheckState(Qt.CheckState.Checked)
                else:
                    parent.setCheckState(Qt.CheckState.Unchecked)
            
            parent = parent.parent()

    def get_checked_files(self):
        """Get list of checked file paths"""
        checked_files = []
        self._collect_checked_files(self.model.invisibleRootItem(), checked_files)
        return checked_files

    def _collect_checked_files(self, parent_item, checked_files):
        """Recursively collect checked file paths"""
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if not item:
                continue
                
            if item.checkState() == Qt.CheckState.Checked:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                if os.path.isfile(file_path):
                    checked_files.append(file_path)
                    
            if item.hasChildren():
                self._collect_checked_files(item, checked_files)

    def get_checked_files_with_paths(self):
        """Get list of checked files with their relative paths"""
        checked_files = []
        root_path = os.path.dirname(self.model.invisibleRootItem().child(0).data(Qt.ItemDataRole.UserRole))
        self._collect_checked_files_with_paths(self.model.invisibleRootItem(), checked_files, root_path)
        return checked_files

    def _collect_checked_files_with_paths(self, parent_item, checked_files, root_path):
        """Recursively collect checked files with relative paths"""
        for row in range(parent_item.rowCount()):
            item = parent_item.child(row)
            if not item:
                continue
                
            if item.checkState() == Qt.CheckState.Checked:
                file_path = item.data(Qt.ItemDataRole.UserRole)
                if os.path.isfile(file_path):
                    # Get relative path from root
                    rel_path = os.path.relpath(file_path, root_path)
                    checked_files.append((file_path, rel_path))
                    
            if item.hasChildren():
                self._collect_checked_files_with_paths(item, checked_files, root_path)

    def _show_context_menu(self, position):
        """Show context menu on right click"""
        # Get the index at the clicked position
        index = self.indexAt(position)
        if not index.isValid():
            return

        # Get the item from the model
        item = self.model.itemFromIndex(index)
        if not item:
            return

        # Get the file path from the item's data
        file_path = item.data(Qt.ItemDataRole.UserRole)
        if not file_path or not os.path.isfile(file_path):
            return

        # Create context menu
        context_menu = QMenu(self)
        
        # Add extract action
        extract_action = context_menu.addAction("Extract File")
        extract_action.triggered.connect(lambda: self._extract_file(file_path))
        
        # Show menu at cursor position
        context_menu.exec(self.mapToGlobal(position))

    def _extract_file(self, file_path):
        """Emit signal to extract the file"""
        try:
            self.extract_file.emit(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to extract file: {str(e)}")
