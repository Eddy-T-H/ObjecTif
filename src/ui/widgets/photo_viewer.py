from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QGridLayout,
    QLabel,
)
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject
from pathlib import Path
from loguru import logger
from enum import Enum, auto

from .photo_loader import PhotoLoaderThread
from .photo_thumbnail import PhotoThumbnail
from .photo_viewer_dialog import PhotoViewerDialog

class PhotoFilter(Enum):
    """Types de filtres disponibles pour les photos."""
    ALL = "all"
    SEALED = "scelle_ferme"      # Correspond à la clé dans photos_dict
    CONTENT = "contenu"          # Correspond à la clé dans photos_dict
    OBJECTS = "objets"           # Correspond à la clé dans photos_dict
    RESEALED = "reconditionnement"  # Correspond à la clé dans photos_dict


    @property
    def display_name(self) -> str:
        """Nom à afficher dans l'interface."""
        DISPLAY_NAMES = {
            "all": "Toutes",
            "scelle_ferme": "Scellé fermé",
            "contenu": "Contenu",
            "objets": "Objets",
            "reconditionnement": "Reconditionnement"
        }
        return DISPLAY_NAMES[self.value]

class PhotoViewer(QWidget):
    """Widget principal pour la visualisation des photos."""
    loading_finished = pyqtSignal()  # Nouveau signal pour signaler que le chargement des images est terminé

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = PhotoFilter.ALL
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

        # Création des boutons de filtre
        self.filter_buttons = {}
        for filter_type in PhotoFilter:
            btn = QPushButton(filter_type.display_name)
            btn.setCheckable(True)
            btn.setProperty("filter_category", filter_type)
            filter_layout.addWidget(btn)
            btn.clicked.connect(self._on_filter_clicked)
            self.filter_buttons[filter_type] = btn

        # Activer le filtre "Toutes" par défaut
        self.filter_buttons[PhotoFilter.ALL].setChecked(True)
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
        logger.debug("Début de load_photos")
        logger.debug(f"Photos reçues: {photos_dict}")

        self.photos_dict = photos_dict
        self._refresh_grid()
        logger.debug("_refresh_grid appelé")

    def _refresh_grid(self):
        """Rafraîchit l'affichage de la grille selon le filtre actuel."""
        logger.debug(f"Début de _refresh_grid avec le filtre: {self.current_filter}")

        # Désactive les boutons pendant le chargement
        for btn in self.filter_buttons.values():
            btn.setEnabled(False)

        # Arrête le thread précédent s'il existe
        if self.loader_thread and self.loader_thread.isRunning():
            logger.debug("Arrêt du thread précédent")
            self.loader_thread.stop()
            self.loader_thread.wait()

        # Efface la grille existante
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

        # Vide le dictionnaire des miniatures
        self.thumbnails.clear()

        # Collecte les photos selon le filtre
        photos_to_show = []

        try:
            if self.current_filter == PhotoFilter.ALL:
                photos_to_show.extend(self.photos_dict.get('scelle_ferme', []))
                photos_to_show.extend(self.photos_dict.get('contenu', []))
                for object_photos in self.photos_dict.get('objets', {}).values():
                    photos_to_show.extend(object_photos)
                photos_to_show.extend(self.photos_dict.get('reconditionnement', []))
            elif self.current_filter == PhotoFilter.SEALED:
                photos_to_show.extend(self.photos_dict.get('scelle_ferme', []))
            elif self.current_filter == PhotoFilter.CONTENT:
                photos_to_show.extend(self.photos_dict.get('contenu', []))
            elif self.current_filter == PhotoFilter.OBJECTS:
                for object_photos in self.photos_dict.get('objets', {}).values():
                    photos_to_show.extend(object_photos)
            elif self.current_filter == PhotoFilter.RESEALED:
                photos_to_show.extend(self.photos_dict.get('reconditionnement', []))

            logger.debug(
                f"Photos trouvées pour le filtre {self.current_filter}: {len(photos_to_show)}")

            if not photos_to_show:
                logger.debug("Aucune photo à afficher")
                empty_label = QLabel("Aucune photo dans cette catégorie")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid_layout.addWidget(empty_label, 0, 0)

                # Réactive les boutons car pas de chargement nécessaire
                for btn in self.filter_buttons.values():
                    btn.setEnabled(True)

                self.loading_finished.emit()
                return

            # Crée les vignettes pour toutes les photos
            row = col = 0
            max_cols = 4

            for photo_path in photos_to_show:
                thumb = PhotoThumbnail(Path(photo_path), loading=True)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self.thumbnails[str(photo_path)] = thumb
                self.grid_layout.addWidget(thumb, row, col)

                col += 1
                if col >= max_cols:
                    col = 0
                    row += 1

            # Lance le thread de chargement
            logger.debug("Démarrage du thread de chargement")
            self.loader_thread = PhotoLoaderThread(photos_to_show)
            self.loader_thread.photo_loaded.connect(self._update_thumbnail)
            self.loader_thread.finished.connect(self._loading_finished)
            self.loader_thread.start()

        except Exception as e:
            logger.exception("Erreur lors du rafraîchissement de la grille")
            self.loading_finished.emit()

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
        logger.debug("Signal _loading_finished reçu dans PhotoViewer")
        # Réactive les boutons de filtre
        for btn in self.filter_buttons.values():
            btn.setEnabled(True)
        self.loader_thread = None
        logger.debug("Emission du signal loading_finished")
        self.loading_finished.emit()

    def is_loading(self) -> bool:
        """Indique si un chargement est en cours."""
        return self.loader_thread is not None and self.loader_thread.isRunning()
