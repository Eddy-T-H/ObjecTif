from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from pathlib import Path


class PhotoThumbnail(QWidget):
    """
    Widget personnalisé pour afficher une miniature de photo.
    Inclut le nom du fichier et gère les clics.
    """

    clicked = pyqtSignal(Path)        # Signal émis lors du clic
    THUMBNAIL_SIZE = QSize(400, 400)  # Taille par défaut, peut être modifiée

    def __init__(self, photo_path: Path, loading=False, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.loading = loading
        self.selected = False
        self.current_pixmap = None
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface de la miniature."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Label pour l'image
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMBNAIL_SIZE)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Ajuste la taille totale du widget
        self._update_widget_size()

        if self.loading:
            self.image_label.setText("Chargement...")
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: palette(base);
                    border: 2px dashed palette(mid);
                    border-radius: 5px;
                    color: palette(text);
                }
            """)
        else:
            self._load_thumbnail()

        # Label pour le nom du fichier
        self.name_label = QLabel(self.photo_path.name)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setMaximumHeight(20)
        layout.addWidget(self.name_label)

        self.setStyleSheet("""
            QWidget {
                background-color: palette(base);
                border: 2px solid palette(mid);
                border-radius: 5px;
            }
            QWidget:hover {
                border-color: palette(highlight);
            }
            QLabel {
                border: none;
                color: palette(text);
                font-size: 10px;
                background-color: transparent;
            }
        """)

    def _update_widget_size(self):
        """Met à jour la taille totale du widget en fonction de la taille de la miniature."""
        self.setFixedSize(
            self.THUMBNAIL_SIZE.width() + 10,  # +10 pour les marges
            self.THUMBNAIL_SIZE.height() + 30   # +30 pour le texte et les marges
        )

    def resize_thumbnail(self, new_size: QSize):
        """Redimensionne la miniature à une nouvelle taille."""
        self.THUMBNAIL_SIZE = new_size
        self.image_label.setFixedSize(new_size)

        # Redimensionne le pixmap si disponible
        if self.current_pixmap and not self.current_pixmap.isNull():
            scaled_pixmap = self._scale_pixmap(self.current_pixmap)
            self.image_label.setPixmap(scaled_pixmap)

        # Met à jour la taille totale du widget
        self._update_widget_size()


    def set_pixmap(self, pixmap: QPixmap):
        """Met à jour l'image avec le pixmap chargé."""
        self.loading = False
        self.current_pixmap = pixmap  # Stocke le pixmap original
        scaled_pixmap = self._scale_pixmap(pixmap)
        self.image_label.setPixmap(scaled_pixmap)
        self.image_label.setStyleSheet("border: 1px solid palette(mid);")

    def _scale_pixmap(self, pixmap: QPixmap) -> QPixmap:
        """Redimensionne le pixmap à la taille actuelle de la miniature."""
        scaled = pixmap.scaled(
            self.THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Crée un pixmap de fond transparent de la taille cible
        final = QPixmap(self.THUMBNAIL_SIZE)
        final.fill(Qt.GlobalColor.transparent)

        # Dessine l'image mise à l'échelle au centre
        painter = QPainter(final)
        x = (self.THUMBNAIL_SIZE.width() - scaled.width()) // 2
        y = (self.THUMBNAIL_SIZE.height() - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        return final

    def _load_thumbnail(self):
        """Charge et redimensionne la photo de manière optimale."""
        try:
            pixmap = QPixmap(str(self.photo_path))
            self.set_pixmap(pixmap)
        except Exception:
            self.image_label.setText("Erreur")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and not self.loading:
            self.clicked.emit(self.photo_path)

    def setSelected(self, selected: bool):
        """Change l'état de sélection de la miniature."""
        self.selected = selected
        if selected:
            self.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border: 2px solid palette(highlight);
                    border-radius: 5px;
                }
                QLabel {
                    border: none;
                    color: palette(highlighted-text);
                    font-size: 10px;
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: palette(transparent);
                    border: 2px solid palette(mid);
                    border-radius: 5px;
                }
                QWidget:hover {
                    border-color: palette(highlight);
                }
                QLabel {
                    border: none;
                    color: palette(text);
                    font-size: 10px;
                    background-color: transparent;
                }
            """)