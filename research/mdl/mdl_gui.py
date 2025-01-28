import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                            QProgressBar, QTextEdit, QFileDialog, QMessageBox,
                            QTabWidget, QGroupBox, QCheckBox, QComboBox, QSpinBox,
                            QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem)
import os
from lz77_decompressor import LZ77Decompressor
from block_analyzer import analyze_blocks
from PyQt6.QtCore import Qt

class MDLToolsGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MDL Tools GUI")
        self.setGeometry(100, 100, 1000, 800)
        
        # Initialize tools
        self.decompressor = LZ77Decompressor(debug=True)
        
        # Create central widget with tabs
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # Create tabs
        self.create_decompressor_tab()
        self.create_analyzer_tab()
        self.create_batch_tab()
        self.create_tools_tab()
        
    def create_decompressor_tab(self):
        """Create the LZ77 Decompressor tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        # Input file selection
        input_layout = QHBoxLayout()
        input_label = QLabel("Input File:")
        self.input_path = QLineEdit()
        input_browse = QPushButton("Browse")
        input_browse.clicked.connect(self.browse_input)
        
        input_layout.addWidget(input_label)
        input_layout.addWidget(self.input_path)
        input_layout.addWidget(input_browse)
        file_layout.addLayout(input_layout)
        
        # Output directory selection
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Folder:")
        self.output_path = QLineEdit()
        output_browse = QPushButton("Browse")
        output_browse.clicked.connect(self.browse_output)
        
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(output_browse)
        file_layout.addLayout(output_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Options group
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout()
        
        self.debug_mode = QCheckBox("Enable Debug Mode")
        self.debug_mode.setChecked(True)
        options_layout.addWidget(self.debug_mode)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Buttons layout
        button_layout = QHBoxLayout()
        
        # Decompress button
        self.decompress_btn = QPushButton("Decompress LZ77")
        self.decompress_btn.clicked.connect(self.decompress)
        button_layout.addWidget(self.decompress_btn)
        
        # Show Info button
        self.info_btn = QPushButton("Show File Info")
        self.info_btn.clicked.connect(self.show_info)
        button_layout.addWidget(self.info_btn)
        
        # Analyze Blocks button
        self.analyze_btn = QPushButton("Analyze Blocks")
        self.analyze_btn.clicked.connect(self.analyze_blocks)
        button_layout.addWidget(self.analyze_btn)
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Log text area
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        self.tabs.addTab(tab, "LZ77 Decompressor")
        
    def create_analyzer_tab(self):
        """Create the Block Analyzer tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Analysis Options
        options_group = QGroupBox("Analysis Options")
        options_layout = QVBoxLayout()
        
        # Block size selection
        block_layout = QHBoxLayout()
        block_label = QLabel("Block Size:")
        self.block_size = QLineEdit("32768")
        block_layout.addWidget(block_label)
        block_layout.addWidget(self.block_size)
        options_layout.addLayout(block_layout)
        
        # Analysis options
        self.show_markers = QCheckBox("Show Alignment Markers")
        self.show_markers.setChecked(True)
        options_layout.addWidget(self.show_markers)
        
        self.show_statistics = QCheckBox("Show Block Statistics")
        self.show_statistics.setChecked(True)
        options_layout.addWidget(self.show_statistics)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Analysis results
        results_group = QGroupBox("Analysis Results")
        results_layout = QVBoxLayout()
        
        self.analysis_text = QTextEdit()
        self.analysis_text.setReadOnly(True)
        results_layout.addWidget(self.analysis_text)
        
        results_group.setLayout(results_layout)
        layout.addWidget(results_group)
        
        self.tabs.addTab(tab, "Block Analyzer")
        
    def create_batch_tab(self):
        """Create the Batch Processing tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Batch input/output selection
        batch_group = QGroupBox("Batch Processing")
        batch_layout = QVBoxLayout()
        
        # Input directory
        input_dir_layout = QHBoxLayout()
        input_dir_label = QLabel("Input Directory:")
        self.input_dir_path = QLineEdit()
        input_dir_browse = QPushButton("Browse")
        input_dir_browse.clicked.connect(self.browse_input_dir)
        
        input_dir_layout.addWidget(input_dir_label)
        input_dir_layout.addWidget(self.input_dir_path)
        input_dir_layout.addWidget(input_dir_browse)
        batch_layout.addLayout(input_dir_layout)
        
        # Output directory
        output_dir_layout = QHBoxLayout()
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_path = QLineEdit()
        output_dir_browse = QPushButton("Browse")
        output_dir_browse.clicked.connect(self.browse_output_dir)
        
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_path)
        output_dir_layout.addWidget(output_dir_browse)
        batch_layout.addLayout(output_dir_layout)
        
        # Batch options
        self.recursive_search = QCheckBox("Include Subdirectories")
        batch_layout.addWidget(self.recursive_search)
        
        # Process button
        self.batch_process_btn = QPushButton("Process All Files")
        self.batch_process_btn.clicked.connect(self.batch_process)
        batch_layout.addWidget(self.batch_process_btn)
        
        batch_group.setLayout(batch_layout)
        layout.addWidget(batch_group)
        
        # Batch progress
        self.batch_progress = QProgressBar()
        layout.addWidget(self.batch_progress)
        
        # Batch log
        self.batch_log = QTextEdit()
        self.batch_log.setReadOnly(True)
        layout.addWidget(self.batch_log)
        
        self.tabs.addTab(tab, "Batch Processing")

    def create_tools_tab(self):
        """Create the Additional Tools tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # File Type Selection
        type_group = QGroupBox("File Type")
        type_layout = QVBoxLayout()
        
        self.file_type = QComboBox()
        self.file_type.addItems([
            "MDL File",
            "Voice File",
            "Text File",
            "Image File",
            "Font File"
        ])
        type_layout.addWidget(self.file_type)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Extraction Options
        options_group = QGroupBox("Extraction Options")
        options_layout = QVBoxLayout()
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        self.format_select = QComboBox()
        self.format_select.addItems(["Raw", "Decoded", "Converted"])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_select)
        options_layout.addLayout(format_layout)
        
        # Extraction mode
        self.extract_all = QRadioButton("Extract All")
        self.extract_selected = QRadioButton("Extract Selected")
        self.extract_all.setChecked(True)
        options_layout.addWidget(self.extract_all)
        options_layout.addWidget(self.extract_selected)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # File List/Preview
        preview_group = QGroupBox("File Contents")
        preview_layout = QVBoxLayout()
        
        self.file_table = QTableWidget()
        self.file_table.setColumnCount(4)
        self.file_table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Offset"])
        self.file_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        preview_layout.addWidget(self.file_table)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # Action Buttons
        button_layout = QHBoxLayout()
        
        self.scan_btn = QPushButton("Scan File")
        self.scan_btn.clicked.connect(self.scan_file)
        button_layout.addWidget(self.scan_btn)
        
        self.extract_btn = QPushButton("Extract")
        self.extract_btn.clicked.connect(self.extract_contents)
        button_layout.addWidget(self.extract_btn)
        
        layout.addLayout(button_layout)
        
        # Add the tab
        self.tabs.addTab(tab, "Additional Tools")

    # Add new methods for block analysis
    def analyze_blocks(self):
        input_file = self.input_path.text()
        
        if not input_file:
            QMessageBox.critical(self, "Error", "Please select an input file")
            return
            
        try:
            with open(input_file, 'rb') as f:
                data = f.read()
                
            block_size = int(self.block_size.text())
            blocks = analyze_blocks(data, block_size)
            
            # Display analysis results
            self.analysis_text.clear()
            self.analysis_text.append(f"Block Analysis for: {input_file}\n")
            self.analysis_text.append(f"Total file size: {len(data):,} bytes\n")
            self.analysis_text.append(f"Number of blocks: {len(blocks)}\n\n")
            
            for i, block in enumerate(blocks):
                self.analysis_text.append(f"Block {i+1}:")
                self.analysis_text.append(f"  Start: 0x{block['start']:08X}")
                self.analysis_text.append(f"  Size: {block['size']:,} bytes")
                
                if self.show_markers.isChecked() and block['markers']:
                    self.analysis_text.append("  Alignment Markers:")
                    for pos, value in block['markers']:
                        self.analysis_text.append(f"    Position: 0x{pos:08X}, Value: 0x{value:02X}")
                self.analysis_text.append("")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error analyzing blocks:\n{str(e)}")

    def browse_input_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Input Directory"
        )
        if directory:
            self.input_dir_path.setText(directory)
            
    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        if directory:
            self.output_dir_path.setText(directory)
            
    def batch_process(self):
        input_dir = self.input_dir_path.text()
        output_dir = self.output_dir_path.text()
        
        if not input_dir or not output_dir:
            QMessageBox.critical(self, "Error", "Please select both input and output directories")
            return
            
        try:
            # Get list of files to process
            files = []
            if self.recursive_search.isChecked():
                for root, _, filenames in os.walk(input_dir):
                    for filename in filenames:
                        files.append(os.path.join(root, filename))
            else:
                files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                        if os.path.isfile(os.path.join(input_dir, f))]
            
            if not files:
                QMessageBox.warning(self, "Warning", "No files found to process")
                return
                
            self.batch_progress.setMaximum(len(files))
            self.batch_progress.setValue(0)
            
            for i, input_file in enumerate(files):
                try:
                    # Create relative output path
                    rel_path = os.path.relpath(input_file, input_dir)
                    output_path = os.path.join(output_dir, rel_path)
                    output_path = os.path.splitext(output_path)[0] + "_decompressed.bin"
                    
                    # Create output directory if needed
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Decompress file
                    self.batch_log.append(f"Processing: {input_file}")
                    decompressed_data = self.decompressor.decompress_file(input_file)
                    
                    with open(output_path, 'wb') as f:
                        f.write(decompressed_data)
                        
                    self.batch_log.append(f"Successfully decompressed to: {output_path}\n")
                    
                except Exception as e:
                    self.batch_log.append(f"Error processing {input_file}: {str(e)}\n")
                    
                self.batch_progress.setValue(i + 1)
                QApplication.processEvents()
                
            QMessageBox.information(self, "Success", "Batch processing completed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during batch processing:\n{str(e)}")
        finally:
            self.batch_progress.setValue(0)

    def browse_input(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Input File",
            "",
            "All Files (*.*)"
        )
        if filename:
            self.input_path.setText(filename)
            # Auto-generate output folder
            output_folder = os.path.join(os.path.dirname(filename), "decompressed")
            self.output_path.setText(output_folder)
            
    def browse_output(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder"
        )
        if directory:
            self.output_path.setText(directory)
            
    def log_message(self, message):
        self.log_text.append(message)
        
    def show_info(self):
        input_file = self.input_path.text()
        
        if not input_file:
            QMessageBox.critical(
                self,
                "Error",
                "Please select an input file"
            )
            return
            
        try:
            # Redirect stdout to capture the output
            from io import StringIO
            import sys
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output
            
            # Call the show_file_info function
            from lz77_decompressor import show_file_info
            show_file_info(input_file)
            
            # Restore stdout and get the output
            sys.stdout = old_stdout
            file_info = redirected_output.getvalue()
            
            # Display the information in the log
            self.log_text.clear()
            self.log_message(file_info)
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Error showing file info:\n{str(e)}"
            )
        
    def decompress(self):
        input_file = self.input_path.text()
        output_dir = self.output_path.text()
        
        if not input_file or not output_dir:
            QMessageBox.critical(
                self,
                "Error",
                "Please select both input file and output folder"
            )
            return
            
        try:
            self.status_label.setText("Decompressing...")
            self.progress.setValue(0)
            self.log_text.clear()
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            output_filename = os.path.basename(input_file)
            base_name = os.path.splitext(output_filename)[0]
            output_file = os.path.join(output_dir, f"{base_name}_decompressed.bin")
            
            # Call the decompress function
            self.log_message(f"Starting decompression from {input_file}")
            decompressed_data = self.decompressor.decompress_file(input_file)
            
            # Write the decompressed data
            with open(output_file, 'wb') as f:
                f.write(decompressed_data)
            
            self.progress.setValue(100)
            self.status_label.setText("Decompression completed successfully!")
            self.log_message(f"Decompression completed successfully!")
            self.log_message(f"Output file: {output_file}")
            self.log_message(f"Output size: {len(decompressed_data):,} bytes")
            
            QMessageBox.information(
                self,
                "Success",
                f"Decompression completed successfully!\nOutput file: {output_file}"
            )
            
        except Exception as e:
            self.status_label.setText("Error occurred during decompression")
            self.log_message(f"Error: {str(e)}")
            QMessageBox.critical(
                self,
                "Error",
                f"An error occurred during decompression:\n{str(e)}"
            )
            
        finally:
            self.progress.setValue(0)

    def scan_file(self):
        """Scan file for extractable contents"""
        input_file = self.input_path.text()
        if not input_file:
            QMessageBox.critical(self, "Error", "Please select an input file")
            return
            
        try:
            self.file_table.setRowCount(0)
            self.status_label.setText("Scanning file...")
            
            # Example scanning logic (replace with actual scanning)
            with open(input_file, 'rb') as f:
                data = f.read()
                
            # Add sample entries (replace with actual scan results)
            self.add_table_entry("Header", "MDL", "256 bytes", "0x0000")
            self.add_table_entry("Texture1", "Image", "2048 bytes", "0x0100")
            self.add_table_entry("Sound1", "Voice", "4096 bytes", "0x0900")
            
            self.status_label.setText("Scan completed")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error scanning file:\n{str(e)}")

    def add_table_entry(self, name, type_, size, offset):
        """Add entry to the file table"""
        row = self.file_table.rowCount()
        self.file_table.insertRow(row)
        self.file_table.setItem(row, 0, QTableWidgetItem(name))
        self.file_table.setItem(row, 1, QTableWidgetItem(type_))
        self.file_table.setItem(row, 2, QTableWidgetItem(size))
        self.file_table.setItem(row, 3, QTableWidgetItem(offset))

    def extract_contents(self):
        """Extract selected contents from file"""
        if self.extract_all.isChecked():
            rows = range(self.file_table.rowCount())
        else:
            rows = [item.row() for item in self.file_table.selectedItems()]
            
        if not rows:
            QMessageBox.warning(self, "Warning", "No items selected for extraction")
            return
            
        try:
            output_dir = self.output_path.text()
            if not output_dir:
                QMessageBox.critical(self, "Error", "Please select an output folder")
                return
                
            os.makedirs(output_dir, exist_ok=True)
            
            for row in rows:
                name = self.file_table.item(row, 0).text()
                type_ = self.file_table.item(row, 1).text()
                offset = self.file_table.item(row, 3).text()
                
                self.log_message(f"Extracting: {name} ({type_}) at {offset}")
                # Add actual extraction logic here
                
            QMessageBox.information(self, "Success", "Extraction completed!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error during extraction:\n{str(e)}")

def main():
    app = QApplication(sys.argv)
    window = MDLToolsGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 