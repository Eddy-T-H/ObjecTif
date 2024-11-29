from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from pathlib import Path
import time

class PhotoLoaderThread(QThread):
    """Thread pour charger les photos en arrière-plan."""
    photo_loaded = pyqtSignal(Path, QPixmap)  # Signal émis quand une photo est chargée
    finished = pyqtSignal()  # Signal émis quand toutes les photos sont chargées

    def __init__(self, photos_to_load):
        super().__init__()
        self.photos_to_load = photos_to_load
        self._is_running = True

    def run(self):
        """Charge les photos une par une."""
        for photo_path in self.photos_to_load:
            if not self._is_running:
                break

            # Charge la photo
            pixmap = QPixmap(str(photo_path))

            # Si le chargement a réussi, émet le signal
            if not pixmap.isNull():
                self.photo_loaded.emit(photo_path, pixmap)

            # Petit délai pour éviter de surcharger le thread principal
            time.sleep(0.05)

        self.finished.emit()

    def stop(self):
        """Arrête le chargement."""
        self._is_running = False