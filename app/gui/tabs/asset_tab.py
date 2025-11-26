from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QComboBox, QSplitter, QFileDialog, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSignal
from ..widgets.file_browser import FileBrowserWidget
from ..preview_widget import PreviewWidget
from ..widgets.worker import WorkerThread
from app.core.dokapon_extract import process_file
import os

class AssetExtractorTab(QWidget):
    status_updated = pyqtSignal(str)  # Add status signal

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.workers = []
        self.results = {'success': [], 'failed': [], 'raw_bin': []}
        
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Add file selection UI
        layout.addLayout(self._create_file_selection())
        
        # Add file browser and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.file_browser = FileBrowserWidget(self.file_type)
        self.preview = PreviewWidget()
        self.file_browser.file_selected.connect(self.preview.show_preview)
        self.file_browser.extract_file.connect(self._extract_single_file)
        splitter.addWidget(self.file_browser)
        splitter.addWidget(self.preview)
        splitter.setSizes([400, 400])  # Equal split
        layout.addWidget(splitter)
        
        # Add extract button
        extract_btn = QPushButton("Extract Selected")
        extract_btn.setProperty("class", "primary")
        extract_btn.clicked.connect(self._start_extraction)
        layout.addWidget(extract_btn)

    def _create_file_selection(self):
        # Input selection
        input_layout = QVBoxLayout()
        file_layout = QHBoxLayout()
        
        self.input_label = QLabel("Input file/folder:")
        self.input_path = QLabel("No file selected")
        select_btn = QPushButton("Select File")
        select_dir_btn = QPushButton("Select Directory")
        select_btn.clicked.connect(lambda: self._select_input(False))
        select_dir_btn.clicked.connect(lambda: self._select_input(True))
        
        file_layout.addWidget(self.input_label)
        file_layout.addWidget(self.input_path)
        file_layout.addWidget(select_btn)
        file_layout.addWidget(select_dir_btn)
        input_layout.addLayout(file_layout)
        
        # Output selection
        output_layout = QHBoxLayout()
        self.output_path = QLabel("./output")
        select_output_btn = QPushButton("Select Output Directory")
        select_output_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(QLabel("Output directory:"))
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(select_output_btn)
        input_layout.addLayout(output_layout)
        
        # File type selection
        type_layout = QHBoxLayout()
        self.file_type = QComboBox()
        self.file_type.addItems([
            "All Files",
            "Texture Files (.tex)",
            "Sprite Files (.spranm)",
            "Font Files (.fnt)"
        ])
        type_layout.addWidget(QLabel("File type:"))
        type_layout.addWidget(self.file_type)
        input_layout.addLayout(type_layout)
        
        return input_layout

    def _select_input(self, is_directory=False):
        if is_directory:
            path = QFileDialog.getExistingDirectory(self, "Select Input Directory")
        else:
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Input File",
                "",
                "All Files (*);;Texture Files (*.tex);;Sprite Files (*.spranm);;Font Files (*.fnt)"
            )
        if path:
            self.input_path.setText(path)
            self.file_browser.populate_tree(path)

    def _select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_path.setText(path)

    def _log_status(self, message):
        """Helper to emit status updates"""
        self.status_updated.emit(message)

    def _start_extraction(self):
        output_base = self.output_path.text()
        if output_base == "No file selected":
            self._log_status("Error: Please select an output directory")
            return
            
        files_to_extract = self.file_browser.get_checked_files_with_paths()
        if not files_to_extract:
            self._log_status("Error: No files selected for extraction")
            return
            
        type_map = {
            "All Files": "all",
            "Texture Files (.tex)": "tex",
            "Sprite Files (.spranm)": "spranm",
            "Font Files (.fnt)": "fnt"
        }
        selected_type = type_map.get(self.file_type.currentText(), "all")
        
        # Reset results for new extraction
        self.results = {
            'success': [],
            'failed': [],
            'raw_bin': []  # Track .bin files
        }
        total_files = len(files_to_extract)
        self._log_status(f"\nStarting extraction of {total_files} files...")
        
        try:
            self.workers = []  # Clear previous workers
            
            for input_path, rel_path in files_to_extract:
                # Create output directory maintaining structure
                output_dir = os.path.join(output_base, os.path.dirname(rel_path))
                os.makedirs(output_dir, exist_ok=True)
                
                worker = WorkerThread(
                    process_file,
                    [input_path, output_dir, selected_type]
                )
                
                # Store file info with worker
                worker.file_path = input_path
                worker.rel_path = rel_path
                
                worker.finished.connect(self._on_worker_finished)
                worker.error.connect(self._on_worker_error)
                
                self.workers.append(worker)
                worker.start()
                
        except Exception as e:
            self._log_status(f"Error starting extraction: {str(e)}")

    def _on_worker_finished(self):
        worker = self.sender()
        if worker and hasattr(worker, 'file_path'):
            file_name = os.path.basename(worker.file_path)
            # Check if a .bin file was created
            bin_path = os.path.join(worker.args[1], file_name + ".bin")
            if os.path.exists(bin_path):
                self.results['raw_bin'].append(worker.file_path)
                self._log_status(f"Saved raw data: {file_name}.bin (Not yet decompressed)")
            else:
                self.results['success'].append(worker.file_path)
                self._log_status(f"Successfully extracted: {file_name}")
            self._check_extraction_complete()

    def _on_worker_error(self, error_msg):
        worker = self.sender()
        if worker and hasattr(worker, 'file_path'):
            self.results['failed'].append((worker.file_path, error_msg))
            self._log_status(f"Failed to extract {os.path.basename(worker.file_path)}: {error_msg}")
            self._check_extraction_complete()

    def _check_extraction_complete(self):
        """Check if all extractions are complete and show report"""
        total_processed = len(self.results['success']) + len(self.results['failed']) + len(self.results['raw_bin'])
        total_files = len(self.workers)
        
        if total_processed == total_files:
            self._show_extraction_report()

    def _show_extraction_report(self):
        """Show detailed extraction report in status"""
        total = len(self.results['success']) + len(self.results['failed']) + len(self.results['raw_bin'])
        
        report = f"\n{'='*50}\n"
        report += "EXTRACTION COMPLETE\n"
        report += f"{'='*50}\n\n"
        
        # Summary section
        report += "SUMMARY:\n"
        report += f"{'─'*30}\n"
        report += f"Total files processed: {total}\n"
        report += f"Successfully extracted: {len(self.results['success'])}\n"
        report += f"Saved as raw data: {len(self.results['raw_bin'])}\n"
        report += f"Failed: {len(self.results['failed'])}\n\n"
        
        # Raw bin files section
        if self.results['raw_bin']:
            report += "RAW DATA FILES (Not yet decompressed):\n"
            report += f"{'─'*30}\n"
            for path in sorted(self.results['raw_bin']):
                report += f"• {os.path.basename(path)}\n"
            report += "\n"
        
        # Failed files section
        if self.results['failed']:
            report += "FAILED EXTRACTIONS:\n"
            report += f"{'─'*30}\n"
            for path, error in sorted(self.results['failed']):
                report += f"• {os.path.basename(path)}: {error}\n"
            report += "\n"
        
        # Successful files section
        if self.results['success']:
            report += "SUCCESSFULLY EXTRACTED:\n"
            report += f"{'─'*30}\n"
            # Group by file type
            by_type = {}
            for path in sorted(self.results['success']):
                ext = os.path.splitext(path)[1].lower()
                if ext not in by_type:
                    by_type[ext] = []
                by_type[ext].append(path)
            
            for ext in sorted(by_type.keys()):
                report += f"\n{ext.upper()[1:]} Files:\n"
                for path in by_type[ext]:
                    report += f"• {os.path.basename(path)}\n"
        
        report += f"\n{'='*50}\n"
        self._log_status(report)
        self.workers.clear()

    def closeEvent(self, event):
        """Clean up worker threads when closing"""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept()

    def _extract_single_file(self, file_path):
        """Extract a single file from the archive"""
        if not self.input_path.text() or self.input_path.text() == "No file selected":
            self._log_status("Error: No input file selected")
            return
            
        try:
            # Let user choose where to save the extracted file
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory for Extraction",
                self.output_path.text()
            )
            
            if not output_dir:  # User cancelled
                return
            
            # Reset results for single file extraction
            self.results = {
                'success': [],
                'failed': [],
                'raw_bin': []
            }
            
            file_name = os.path.basename(file_path)
            self._log_status(f"\nStarting extraction of {file_name}...")
            
            type_map = {
                "All Files": "all",
                "Texture Files (.tex)": "tex",
                "Sprite Files (.spranm)": "spranm",
                "Font Files (.fnt)": "fnt"
            }
            selected_type = type_map.get(self.file_type.currentText(), "all")
            
            # Create worker for single file extraction
            worker = WorkerThread(
                process_file,
                [file_path, output_dir, selected_type]
            )
            
            # Store file info with worker
            worker.file_path = file_path
            worker.rel_path = os.path.basename(file_path)  # Just the filename for single extraction
            
            worker.finished.connect(self._on_worker_finished)  # Use the same handler as bulk extraction
            worker.error.connect(self._on_worker_error)
            
            self.workers = [worker]  # Clear and set single worker
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error extracting file: {str(e)}") 