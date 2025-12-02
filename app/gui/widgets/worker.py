from PyQt6.QtCore import QThread, pyqtSignal

class WorkerThread(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal()
    result = pyqtSignal(object)  # Signal to emit return value
    error = pyqtSignal(str)

    def __init__(self, function, args=None):
        super().__init__()
        self.function = function
        self.args = args if args is not None else []

    def run(self):
        try:
            if callable(self.function):
                ret = self.function(*self.args) if self.args else self.function()
                if ret is not None:
                    self.result.emit(ret)
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e)) 