# src/ui/widgets/photo_list.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem, \
    QSizePolicy
from PyQt6.QtCore import Qt
from pathlib import Path
from loguru import logger

class PhotoListWidget(QWidget):
    """Widget affichant la liste des photos existantes."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Titre
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        # Liste des photos - utilisation du style natif
        self.photo_list = QListWidget()
        self.photo_list.setAlternatingRowColors(True)
        layout.addWidget(self.photo_list)

    def update_photos(self, photos: list[str]):
        """Met à jour la liste des photos."""
        self.photo_list.clear()
        for photo in sorted(photos):
            item = QListWidgetItem(photo)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.photo_list.addItem(item)

    def clear(self):
        """Vide la liste des photos."""
        self.photo_list.clear()