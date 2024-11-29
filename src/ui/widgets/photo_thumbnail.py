from PyQt6.QtWidgets import QLabel, QWidget, QVBoxLayout
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from pathlib import Path


class PhotoThumbnail(QWidget):
    """
    Widget personnalisé pour afficher une miniature de photo.
    Inclut le nom du fichier et gère les clics.
    """

    clicked = pyqtSignal(Path)
    THUMBNAIL_SIZE = QSize(200, 200)  # Taille fixe pour toutes les miniatures

    def __init__(self, photo_path: Path, loading=False, parent=None):
        super().__init__(parent)
        self.photo_path = photo_path
        self.loading = loading
        self.selected = False
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface de la miniature."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Label pour l'image avec une taille fixe
        self.image_label = QLabel()
        self.image_label.setFixedSize(self.THUMBNAIL_SIZE)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Force une taille fixe pour le widget entier (image + texte)
        self.setFixedSize(self.THUMBNAIL_SIZE.width() + 10,  # +10 pour les marges
                          self.THUMBNAIL_SIZE.height() + 30)  # +30 pour le texte et les marges

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
        name_label = QLabel(self.photo_path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumHeight(20)  # Limite la hauteur du texte
        layout.addWidget(name_label)

        # Style adaptatif
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

    def set_pixmap(self, pixmap: QPixmap):
        """Met à jour l'image avec le pixmap chargé."""
        self.loading = False
        scaled_pixmap = pixmap.scaled(
            self.THUMBNAIL_SIZE,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        # Crée un pixmap de fond blanc de la taille cible
        final_pixmap = QPixmap(self.THUMBNAIL_SIZE)
        final_pixmap.fill(Qt.GlobalColor.transparent)

        # Dessine l'image mise à l'échelle au centre
        painter = QPainter(final_pixmap)
        x = (self.THUMBNAIL_SIZE.width() - scaled_pixmap.width()) // 2
        y = (self.THUMBNAIL_SIZE.height() - scaled_pixmap.height()) // 2
        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        self.image_label.setPixmap(final_pixmap)
        self.image_label.setStyleSheet("border: 1px solid palette(mid);")

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