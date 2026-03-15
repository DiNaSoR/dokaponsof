from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import pyqtSignal, QThread


class BaseTab(QWidget):
    """Base class for all tool tabs, providing common signals and cleanup."""
    status_updated = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.workers: list[QThread] = []
        self._game_path: str = ""

    def _log_status(self, message: str) -> None:
        self.status_updated.emit(message)

    def set_game_path(self, path: str) -> None:
        """Called by the main window when the global game directory changes.

        Subclasses override this to auto-populate their path fields.
        """
        self._game_path = path

    @property
    def game_path(self) -> str:
        return self._game_path

    def closeEvent(self, event):
        for w in self.workers:
            if w.isRunning():
                w.quit()
                w.wait(1000)
        event.accept()
