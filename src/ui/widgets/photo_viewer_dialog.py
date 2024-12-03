# ui/widgets/photo_viewer_dialog.py
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
from loguru import logger


class PhotoViewerDialog(QDialog):
    """Dialogue pour afficher une photo en grand format."""

    def __init__(self, photo_path: Path, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du dialogue."""
        self.setWindowTitle(f"{self.photo_path.name} (cliquez pour fermer)")
        self.setModal(True)

        layout = QVBoxLayout(self)

        # Label pour l'image
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.mousePressEvent = self._on_image_click

        try:
            # Charge et dimensionne l'image
            pixmap = QPixmap(str(self.photo_path))
            if pixmap.isNull():
                logger.error(f"Impossible de charger l'image: {self.photo_path}")
                self.image_label.setText("Erreur de chargement")
                return

            # Calcule la taille maximale (80% de l'écran)
            screen = self.screen().geometry()
            max_size = QSize(int(screen.width() * 0.8), int(screen.height() * 0.8))

            # Redimensionne l'image
            scaled_pixmap = pixmap.scaled(
                max_size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

            self.image_label.setPixmap(scaled_pixmap)

        except Exception as e:
            logger.error(f"Erreur lors du chargement de l'image: {e}")
            self.image_label.setText("Erreur")

        layout.addWidget(self.image_label)
        self.resize(
            self.image_label.pixmap().size() if self.image_label.pixmap() else max_size
        )

    def _on_image_click(self, event):
        """Ferme le dialogue au clic."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()
