from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QPixmap
from pathlib import Path
from loguru import logger
import time

class PhotoLoaderThread(QThread):
    """Thread pour charger les photos en arrière-plan."""
    photo_loaded = pyqtSignal(Path, QPixmap)  # Signal émis quand une photo est chargée
    finished = pyqtSignal()  # Signal émis quand toutes les photos sont chargées

    def __init__(self, photos_to_load):
        super().__init__()
        logger.debug(f"Initialisation de PhotoLoaderThread avec {len(photos_to_load)} photos")
        # Convertir tous les chemins en objets Path
        self.photos_to_load = [Path(p) if isinstance(p, str) else p for p in photos_to_load]
        self._is_running = True

    def run(self):
        """Charge les photos une par une avec délai pour éviter la surcharge."""
        try:
            for photo_path in self.photos_to_load:
                if not self._is_running:
                    logger.debug("Chargement interrompu")
                    break

                logger.debug(f"Chargement de la photo : {photo_path}")

                # Vérifie l'existence du fichier
                if not photo_path.exists():
                    logger.error(f"Le fichier n'existe pas : {photo_path}")
                    continue

                try:
                    # Charge la photo
                    pixmap = QPixmap(str(photo_path))
                    if pixmap.isNull():
                        logger.error(f"Erreur lors du chargement de {photo_path}")
                        continue

                    self.photo_loaded.emit(photo_path, pixmap)
                    logger.debug(f"Photo chargée avec succès : {photo_path}")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement de {photo_path}: {e}")

                # Petit délai pour éviter de surcharger le thread principal
                time.sleep(0.05)

            logger.debug("Chargement terminé")

        except Exception as e:
            logger.exception("Erreur dans le thread de chargement")

        finally:
            self.finished.emit()

    def stop(self):
        """Arrête le chargement."""
        logger.debug("Demande d'arrêt du thread")
        self._is_running = False