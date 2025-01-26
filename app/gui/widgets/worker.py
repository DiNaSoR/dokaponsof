from PyQt6.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, function, args):
        super().__init__()
        self.function = function
        self.args = args

    def run(self):
        try:
            self.function(*self.args)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e)) 