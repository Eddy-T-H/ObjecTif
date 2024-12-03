# src/ui/widgets/phone_preview.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
import subprocess
from pathlib import Path
import tempfile
from loguru import logger


class PhonePreviewWidget(QWidget):
    """Widget affichant le preview en direct de l'écran du téléphone."""

    screenshot_taken = pyqtSignal(
        QPixmap
    )  # Émis quand un nouveau screenshot est capturé

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.temp_dir = Path(tempfile.gettempdir()) / "phone_preview"
        self.temp_dir.mkdir(exist_ok=True)

        # Timer pour le rafraîchissement
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._update_preview)
        self.is_updating = False

    def _setup_ui(self):
        """Configure l'interface du widget."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label pour l'affichage
        self.display = QLabel()
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setMinimumSize(400, 600)
        self.display.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Sunken)
        self.display.setStyleSheet(
            """
            QLabel {
                background-color: black;
                border: 1px solid #666;
                border-radius: 4px;
            }
        """
        )
        layout.addWidget(self.display)

        # Message par défaut
        self.display.setText("En attente de connexion...")

    def start_preview(self):
        """Démarre la mise à jour du preview."""
        self.update_timer.start(500)  # Toutes les 500ms
        logger.info("Preview démarré")

    def stop_preview(self):
        """Arrête la mise à jour du preview."""
        self.update_timer.stop()
        self.display.setText("En attente de connexion...")
        logger.info("Preview arrêté")

    def _update_preview(self):
        """Met à jour l'image du preview."""
        if self.is_updating:
            return

        self.is_updating = True
        try:
            # Capture l'écran avec adb
            temp_file = self.temp_dir / "screen.png"
            subprocess.run(
                f'adb shell screencap -p > "{temp_file}"',
                shell=True,
                capture_output=True,
            )

            # Charge et affiche l'image
            if temp_file.exists():
                pixmap = QPixmap(str(temp_file))
                if not pixmap.isNull():
                    # Redimensionne en gardant les proportions
                    scaled = pixmap.scaled(
                        self.display.size(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self.display.setPixmap(scaled)
                    self.screenshot_taken.emit(pixmap)

                # Nettoie le fichier temporaire
                temp_file.unlink()

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du preview: {e}")
            self.stop_preview()

        finally:
            self.is_updating = False
