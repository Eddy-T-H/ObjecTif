from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QGridLayout,
    QLabel, QSlider,
)
from PyQt6.QtGui import QPixmap, QImage, QPalette, QColor
from PyQt6.QtCore import Qt, QSize, pyqtSignal, QObject, QTimer
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

    # Tailles min/max pour les miniatures
    MIN_THUMB_SIZE = 150
    MAX_THUMB_SIZE = 600
    DEFAULT_THUMB_SIZE = 400
    # attention à changer dans photothumbnail aussi

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_filter = PhotoFilter.ALL
        self.photos_dict = {}
        self.loader_thread = None
        self.thumbnails = {}
        self.thumb_size = self.DEFAULT_THUMB_SIZE
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du visualiseur."""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)  # Réduit l'espacement vertical

        # === Première ligne : Slider de taille ===
        size_container = QWidget()
        size_layout = QHBoxLayout(size_container)
        size_layout.setSpacing(10)
        size_layout.setContentsMargins(5, 5, 5, 5)

        size_label = QLabel("Taille des miniatures:")
        size_layout.addWidget(size_label)

        self.size_slider = QSlider(Qt.Orientation.Horizontal)
        self.size_slider.setMinimum(self.MIN_THUMB_SIZE)
        self.size_slider.setMaximum(self.MAX_THUMB_SIZE)
        self.size_slider.setValue(self.DEFAULT_THUMB_SIZE)
        self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.size_slider.setTickInterval(50)
        self.size_slider.valueChanged.connect(self._on_size_changed)
        size_layout.addWidget(self.size_slider,
                              stretch=1)  # stretch=1 pour prendre l'espace disponible

        self.size_value_label = QLabel(f"{self.DEFAULT_THUMB_SIZE}px")
        self.size_value_label.setMinimumWidth(
            50)  # Assure une largeur minimale pour éviter les sauts
        size_layout.addWidget(self.size_value_label)

        layout.addWidget(size_container)

        # === Deuxième ligne : Boutons de filtre ===
        filter_container = QWidget()
        filter_layout = QHBoxLayout(filter_container)
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(5, 0, 5, 5)  # Réduit la marge en haut

        self.filter_buttons = {}
        for filter_type in PhotoFilter:
            btn = QPushButton(filter_type.display_name)
            btn.setCheckable(True)
            btn.setProperty("filter_category", filter_type)
            filter_layout.addWidget(btn)
            btn.clicked.connect(self._on_filter_clicked)
            self.filter_buttons[filter_type] = btn

        # Active le filtre "Toutes" par défaut
        self.filter_buttons[PhotoFilter.ALL].setChecked(True)
        layout.addWidget(filter_container)

        # === Partie scrollable pour les photos ===
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setStyleSheet("""
            QScrollArea {
                background-color: palette(base);
                border: none;
            }
            QScrollBar {
                background-color: palette(base);
            }
        """)

        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        self.scroll.setWidget(self.grid_widget)

        layout.addWidget(self.scroll)

    # def _setup_ui(self):
    #     """Configure l'interface du visualiseur."""
    #     layout = QVBoxLayout(self)
    #     layout.setSpacing(10)
    #
    #     # Conteneur pour les contrôles supérieurs
    #     controls_container = QWidget()
    #     controls_layout = QHBoxLayout(controls_container)
    #     controls_layout.setSpacing(10)
    #     controls_layout.setContentsMargins(5, 5, 5, 5)
    #
    #     # Slider de taille avec labels
    #     size_label = QLabel("Taille des miniatures:")
    #     controls_layout.addWidget(size_label)
    #
    #     self.size_slider = QSlider(Qt.Orientation.Horizontal)
    #     self.size_slider.setMinimum(self.MIN_THUMB_SIZE)
    #     self.size_slider.setMaximum(self.MAX_THUMB_SIZE)
    #     self.size_slider.setValue(self.DEFAULT_THUMB_SIZE)
    #     self.size_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
    #     self.size_slider.setTickInterval(50)
    #     self.size_slider.valueChanged.connect(self._on_size_changed)
    #     controls_layout.addWidget(self.size_slider)
    #
    #     # Valeur numérique
    #     self.size_value_label = QLabel(f"{self.DEFAULT_THUMB_SIZE}px")
    #     controls_layout.addWidget(self.size_value_label)
    #
    #     # Boutons de filtrage
    #     filter_layout = QHBoxLayout()
    #     filter_layout.setSpacing(5)
    #
    #
    #     # Création des boutons de filtre
    #     self.filter_buttons = {}
    #     for filter_type in PhotoFilter:
    #         btn = QPushButton(filter_type.display_name)
    #         btn.setCheckable(True)
    #         btn.setProperty("filter_category", filter_type)
    #         filter_layout.addWidget(btn)
    #         btn.clicked.connect(self._on_filter_clicked)
    #         self.filter_buttons[filter_type] = btn
    #
    #     # Activer le filtre "Toutes" par défaut
    #     controls_layout.addLayout(filter_layout)
    #     self.filter_buttons[PhotoFilter.ALL].setChecked(True)
    #
    #     layout.addWidget(controls_container)
    #
    #     # Zone de défilement avec style adaptatif
    #     self.scroll = QScrollArea()  # Stocké dans self maintenant
    #     self.scroll.setWidgetResizable(True)
    #     self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    #     self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    #     self.scroll.setStyleSheet("""
    #         QScrollArea {
    #             background-color: palette(base);
    #             border: none;
    #         }
    #         QScrollBar {
    #             background-color: palette(base);
    #         }
    #     """)
    #
    #     # Widget contenant la grille
    #     self.grid_widget = QWidget()
    #     self.grid_layout = QGridLayout(self.grid_widget)
    #     self.grid_layout.setSpacing(10)
    #     self.grid_layout.setContentsMargins(10, 10, 10, 10)
    #     self.scroll.setWidget(self.grid_widget)
    #
    #     layout.addWidget(self.scroll)

    def _on_size_changed(self, value):
        """Gère le changement de taille des miniatures."""
        self.thumb_size = value
        self.size_value_label.setText(f"{value}px")

        # Met à jour la taille de toutes les miniatures existantes
        new_size = QSize(value, value)
        for thumb in self.thumbnails.values():
            thumb.resize_thumbnail(new_size)

        # Réorganise la grille avec les nouvelles tailles
        self._refresh_grid()

    def resizeEvent(self, event):
        """Réorganise la grille lors du redimensionnement de la fenêtre."""
        super().resizeEvent(event)
        # Attend que le widget ait sa nouvelle taille avant de recalculer
        QTimer.singleShot(0, self._refresh_grid)

    def _calculate_columns(self):
        """Calcule le nombre optimal de colonnes basé sur la largeur disponible."""
        available_width = self.scroll.viewport().width() - (
                self.grid_layout.contentsMargins().left() +
                self.grid_layout.contentsMargins().right()
        )
        thumb_total_width = self.thumb_size
        columns = max(1, available_width // thumb_total_width)

        logger.debug(f"Calcul colonnes - Largeur disponible: {available_width}, "
                     f"Largeur thumb: {thumb_total_width}, "
                     f"Colonnes: {columns}")

        return int(columns)

    def load_photos(self, photos_dict: dict):
        """Charge les photos dans la grille."""
        logger.debug("Début de load_photos")
        logger.debug(f"Photos reçues: {photos_dict}")

        # Nettoie proprement les anciennes miniatures
        for thumb in self.thumbnails.values():
            thumb.deleteLater()
        self.thumbnails.clear()

        self.photos_dict = photos_dict
        self._refresh_grid()
        logger.debug("_refresh_grid appelé")

    def _refresh_grid(self):
        """Rafraîchit l'affichage de la grille selon le filtre actuel."""
        logger.debug(f"Rafraîchissement de la grille avec le filtre: {self.current_filter}")

        # Si un chargement est en cours, on ne fait rien
        if self.loader_thread and self.loader_thread.isRunning():
            return

        # Nettoie toujours d'abord la grille
        for i in reversed(range(self.grid_layout.count())):
            widget = self.grid_layout.itemAt(i).widget()
            if widget:
                self.grid_layout.removeWidget(widget)
                widget.setParent(None)
                if isinstance(widget, QLabel) and not isinstance(widget,
                                                                 PhotoThumbnail):
                    widget.deleteLater()

        # Premier chargement ou changement de filtre
        if not self.thumbnails:
            # Désactive les boutons pendant le chargement
            for btn in self.filter_buttons.values():
                btn.setEnabled(False)

            # Collecte les photos selon le filtre
            photos_to_show = self._get_filtered_photos()

            if not photos_to_show:
                # Nettoie la grille existante
                for i in reversed(range(self.grid_layout.count())):
                    widget = self.grid_layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)
                        widget.deleteLater()

                empty_label = QLabel("Aucune photo dans cette catégorie")
                empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.grid_layout.addWidget(empty_label, 0, 0)
                for btn in self.filter_buttons.values():
                    btn.setEnabled(True)
                self.loading_finished.emit()
                return

            # Crée les nouvelles miniatures
            for photo_path in photos_to_show:
                thumb = PhotoThumbnail(Path(photo_path), loading=True)
                thumb.clicked.connect(self._on_thumbnail_clicked)
                self.thumbnails[str(photo_path)] = thumb

            # Lance le thread de chargement
            self.loader_thread = PhotoLoaderThread(photos_to_show)
            self.loader_thread.photo_loaded.connect(self._update_thumbnail)
            self.loader_thread.finished.connect(self._loading_finished)
            self.loader_thread.start()

        # Dans tous les cas, réorganise les miniatures existantes
        try:
            num_columns = self._calculate_columns()
            logger.debug(f"Nombre de colonnes calculé: {num_columns}")

            # Place les miniatures dans la grille
            row = col = 0
            for thumb in self.thumbnails.values():
                self.grid_layout.addWidget(thumb, row, col)
                col += 1
                if col >= num_columns:
                    col = 0
                    row += 1

        except Exception as e:
            logger.error(f"Erreur lors de la réorganisation de la grille: {e}")

        # Réactive les boutons
        for btn in self.filter_buttons.values():
            btn.setEnabled(True)


    def _get_filtered_photos(self):
        """Retourne la liste des photos selon le filtre actuel."""
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

        except Exception as e:
            logger.error(f"Erreur lors du filtrage des photos: {e}")

        return photos_to_show

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

        # Met à jour le filtre et vide le dictionnaire de miniatures pour forcer le rechargement
        self.current_filter = sender.property("filter_category")
        self.thumbnails.clear()  # Force le rechargement avec le nouveau filtre
        self._refresh_grid()


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
        logger.debug("Chargement des photos terminé")

        # Réactive les boutons de filtre
        for btn in self.filter_buttons.values():
            btn.setEnabled(True)

        self.loader_thread = None

        # Réorganise la grille une dernière fois pour s'assurer de l'alignement
        self._refresh_grid()

        # Émet le signal de fin de chargement
        self.loading_finished.emit()

    def is_loading(self) -> bool:
        """Indique si un chargement est en cours."""
        return self.loader_thread is not None and self.loader_thread.isRunning()
