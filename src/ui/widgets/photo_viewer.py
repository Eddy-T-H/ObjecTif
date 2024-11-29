from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QGridLayout,
    QLabel,
    QDialog, QMainWindow,
)
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from pathlib import Path
from typing import Dict, List, Optional

from .photo_loader import PhotoLoaderThread
from .photo_thumbnail import PhotoThumbnail


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

        # Charge l'image
        pixmap = QPixmap(str(self.photo_path))

        # Calcule la taille maximale en gardant les proportions
        screen = self.screen().geometry()
        max_size = QSize(int(screen.width() * 0.8), int(screen.height() * 0.8))

        scaled_pixmap = pixmap.scaled(
            max_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.image_label.setPixmap(scaled_pixmap)
        layout.addWidget(self.image_label)

        # Ajuste la taille de la fenêtre
        self.resize(scaled_pixmap.size())

    def _on_image_click(self, event):
        """Ferme le dialogue au clic sur l'image."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.close()


class PhotoViewer(QWidget):
    """Widget principal pour la visualisation des photos."""
    loading_finished = pyqtSignal()  # Nouveau signal pour signaler que le chargement des images est terminé

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = "all"
        self.photos_dict = {}
        self.loader_thread = None
        self.thumbnails = {}
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du visualiseur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Boutons de filtrage dans un conteneur avec style
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(5, 5, 5, 5)

        # Définition des boutons de filtre avec leurs catégories
        filter_definitions = {
            'all': ('Toutes', 'all'),
            'sealed': ('Scellé fermé', 'sealed'),
            'content': ('Contenu', 'content'),
            'objects': ('Objets', 'objects'),
            'resealed': ('Reconditionnement', 'resealed')
        }
        self.filter_buttons = {}

        for key, (label, category) in filter_definitions.items():
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setProperty("filter_category",
                            category)  # Stocke la catégorie comme propriété
            filter_layout.addWidget(btn)
            btn.clicked.connect(self._on_filter_clicked)
            self.filter_buttons[key] = btn

        self.filter_buttons['all'].setChecked(True)
        layout.addWidget(filter_container)

        # Zone de défilement avec style adaptatif
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: palette(base);
                border: none;
            }
            QScrollBar {
                background-color: palette(base);
            }
        """)

        # Widget contenant la grille
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        scroll.setWidget(self.grid_widget)

        layout.addWidget(scroll)

    def load_photos(self, photos_dict: dict):
        """Charge les photos dans la grille."""
        self.photos_dict = photos_dict
        self._refresh_grid()

    def _refresh_grid(self):
        """Rafraîchit l'affichage de la grille selon le filtre actuel."""
        # Désactive les boutons pendant le chargement
        for btn in self.filter_buttons.values():
            btn.setEnabled(False)

        # Arrête le thread précédent s'il existe
        if self.loader_thread and self.loader_thread.isRunning():
            self.loader_thread.stop()
            self.loader_thread.wait()

        # Efface la grille
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Vide le dictionnaire des miniatures
        self.thumbnails.clear()

        # Détermine les photos à afficher selon le filtre
        photos_to_show = []
        if self.current_filter == "all":
            for category, photos in self.photos_dict.items():
                if isinstance(photos, list):
                    photos_to_show.extend(photos)
                elif isinstance(photos, dict):
                    for letter_photos in photos.values():
                        photos_to_show.extend(letter_photos)
        else:
            category_map = {
                "sealed": "scelle_ferme",
                "content": "contenu",
                "objects": "objets",
                "resealed": "reconditionnement",
            }
            category = category_map.get(self.current_filter)
            if category in self.photos_dict:
                photos = self.photos_dict[category]
                if isinstance(photos, list):
                    photos_to_show.extend(photos)
                elif isinstance(photos, dict):
                    for letter_photos in photos.values():
                        photos_to_show.extend(letter_photos)

        if not photos_to_show:
            # Réactive les boutons car pas de chargement nécessaire
            for btn in self.filter_buttons.values():
                btn.setEnabled(True)
            empty_label = QLabel("Aucune photo dans cette catégorie")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.grid_layout.addWidget(empty_label, 0, 0)
            return

        # Ajoute les miniatures à la grille
        row = col = 0
        max_cols = 4

        for photo_path in photos_to_show:
            thumb = PhotoThumbnail(photo_path, loading=True)
            thumb.clicked.connect(self._on_thumbnail_clicked)
            self.thumbnails[str(photo_path)] = thumb
            self.grid_layout.addWidget(thumb, row, col)

            col += 1
            if col >= max_cols:
                col = 0
                row += 1

        # Lance le thread de chargement
        self.loader_thread = PhotoLoaderThread(photos_to_show)
        self.loader_thread.photo_loaded.connect(self._update_thumbnail)
        self.loader_thread.finished.connect(self._loading_finished)
        self.loader_thread.start()

    def _on_filter_clicked(self):
        """Gère le clic sur un bouton de filtre."""
        sender = self.sender()
        if not isinstance(sender, QPushButton):
            return

        if not sender.isChecked():
            sender.setChecked(True)
            return

        # Décoche les autres boutons
        for btn in self.filter_buttons.values():
            if btn != sender:
                btn.setChecked(False)

        self.current_filter = sender.property("filter_category")
        self._refresh_grid()  # Appel direct


    def _on_thumbnail_clicked(self, photo_path: Path):
        """Ouvre la photo en grand format."""
        dialog = PhotoViewerDialog(photo_path, self)
        dialog.exec()

    def _update_thumbnail(self, photo_path: Path, pixmap: QPixmap):
        """Met à jour une miniature quand sa photo est chargée."""
        if str(photo_path) in self.thumbnails:
            thumb = self.thumbnails[str(photo_path)]
            if not thumb.isHidden() and thumb.parent() is not None:
                thumb.set_pixmap(pixmap)

    def _loading_finished(self):
        """Appelé quand toutes les photos sont chargées."""
        self.loader_thread = None
        # Réactive les boutons
        for btn in self.filter_buttons.values():
            btn.setEnabled(True)
        # Réactive l'arbre des scellés
        # Émet le signal
        self.loading_finished.emit()

    def is_loading(self) -> bool:
        """Indique si un chargement est en cours."""
        return self.loader_thread is not None and self.loader_thread.isRunning()
