from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                            QLabel, QFileDialog)
from ..widgets.worker import WorkerThread
from app.core.voice_pck_extractor import extract_voices
from PyQt6.QtCore import pyqtSignal
import os

class VoiceExtractorTab(QWidget):
    status_updated = pyqtSignal(str)  # Add status signal

    def __init__(self):
        super().__init__()
        self._init_ui()
        self.workers = []

    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Input selection
        input_layout = QHBoxLayout()
        self.input_label = QLabel("PCK file:")
        self.input_path = QLabel("No file selected")
        select_btn = QPushButton("Select PCK")
        select_btn.clicked.connect(self._select_input)
        
        input_layout.addWidget(self.input_label)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(select_btn)
        layout.addLayout(input_layout)
        
        # Output selection
        output_layout = QHBoxLayout()
        self.output_path = QLabel("./output")
        select_output_btn = QPushButton("Select Output Directory")
        select_output_btn.clicked.connect(self._select_output_dir)
        output_layout.addWidget(QLabel("Output directory:"))
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(select_output_btn)
        layout.addLayout(output_layout)
        
        # Extract button
        extract_btn = QPushButton("Extract Voice")
        extract_btn.clicked.connect(self._start_extraction)
        layout.addWidget(extract_btn)

    def _select_input(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select PCK File",
            "",
            "PCK Files (*.pck);;All Files (*)"
        )
        if path:
            self.input_path.setText(path)

    def _select_output_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self.output_path.setText(path)

    def _log_status(self, message):
        """Helper to emit status updates"""
        self.status_updated.emit(message)

    def _start_extraction(self):
        input_path = self.input_path.text()
        output_path = self.output_path.text()
        
        if input_path == "No file selected":
            self._log_status("Error: No PCK file selected")
            return
            
        try:
            self._log_status(f"Starting voice extraction from {os.path.basename(input_path)}...")
            
            worker = WorkerThread(
                extract_voices,
                [input_path, output_path]
            )
            worker.finished.connect(self._on_extraction_complete)
            worker.error.connect(self._on_extraction_error)
            
            self.workers.append(worker)
            worker.start()
            
        except Exception as e:
            self._log_status(f"Error starting extraction: {str(e)}")

    def _on_extraction_complete(self):
        self._log_status("Voice extraction completed successfully")
        self._log_status(f"Files saved to: {self.output_path.text()}")

    def _on_extraction_error(self, error_msg):
        self._log_status(f"Error during extraction: {error_msg}")

    def closeEvent(self, event):
        """Clean up worker threads when closing"""
        for worker in self.workers:
            if worker.isRunning():
                worker.quit()
                worker.wait()
        event.accept() 