# src/ui/widgets/photo_list.py

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QMenu,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction
from pathlib import Path
from loguru import logger
import os
import subprocess
import platform


class PhotoListWidget(QWidget):
    """Widget affichant la liste des photos avec actions de visualisation et suppression."""

    # Signal émis quand une photo est supprimée (pour rafraîchir les listes)
    photo_deleted = pyqtSignal(str)  # nom du fichier supprimé

    def __init__(self, title: str, photo_folder: Path = None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self.photo_folder = photo_folder  # Dossier contenant les photos
        self._setup_ui(title)

    def _setup_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Titre
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(title_label)

        # Liste des photos avec actions
        self.photo_list = QListWidget()
        self.photo_list.setAlternatingRowColors(True)
        self.photo_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Connecte les événements
        self.photo_list.customContextMenuRequested.connect(self._show_context_menu)
        self.photo_list.itemDoubleClicked.connect(self._view_photo)
        self.photo_list.keyPressEvent = self._handle_key_press

        layout.addWidget(self.photo_list)

    def set_photo_folder(self, folder: Path):
        """Définit le dossier contenant les photos."""
        self.photo_folder = folder

    def update_photos(self, photos: list[str]):
        """Met à jour la liste des photos."""
        self.photo_list.clear()
        for photo in sorted(photos):
            item = QListWidgetItem(photo)
            # Permet la sélection pour les actions
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsSelectable)
            self.photo_list.addItem(item)

    def clear(self):
        """Vide la liste des photos."""
        self.photo_list.clear()

    def _show_context_menu(self, position):
        """Affiche le menu contextuel pour une photo."""
        item = self.photo_list.itemAt(position)
        if not item:
            return

        photo_name = item.text()

        # Crée le menu contextuel
        menu = QMenu(self)

        # Action Visualiser
        view_action = QAction("👁️ Visualiser", self)
        view_action.triggered.connect(lambda: self._view_photo(item))
        menu.addAction(view_action)

        menu.addSeparator()

        # Action Supprimer
        delete_action = QAction("🗑️ Supprimer", self)
        delete_action.triggered.connect(lambda: self._delete_photo(item))
        menu.addAction(delete_action)

        # Affiche le menu à la position de la souris
        menu.exec(self.photo_list.mapToGlobal(position))

    def _view_photo(self, item):
        """Ouvre la photo pour visualisation."""
        if not item or not self.photo_folder:
            return

        photo_name = item.text()
        photo_path = self.photo_folder / photo_name

        if not photo_path.exists():
            QMessageBox.warning(
                self, "Photo introuvable", f"Le fichier {photo_name} n'existe pas."
            )
            return

        try:
            # Ouvre avec l'application par défaut du système
            if platform.system() == "Windows":
                os.startfile(str(photo_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(photo_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(photo_path)])

            logger.info(f"Photo ouverte : {photo_name}")

        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture de {photo_name}: {e}")
            QMessageBox.warning(
                self,
                "Erreur d'ouverture",
                f"Impossible d'ouvrir la photo {photo_name}.\n\n"
                f"Vérifiez qu'une application de visualisation d'images est installée.",
            )

    def _delete_photo(self, item):
        """Supprime la photo après confirmation."""
        if not item or not self.photo_folder:
            return

        photo_name = item.text()
        photo_path = self.photo_folder / photo_name

        if not photo_path.exists():
            QMessageBox.warning(
                self, "Photo introuvable", f"Le fichier {photo_name} n'existe pas."
            )
            return

        # Demande confirmation
        reply = QMessageBox.question(
            self,
            "Confirmer la suppression",
            f"Êtes-vous sûr de vouloir supprimer la photo ?\n\n"
            f"📁 {photo_name}\n\n"
            f"⚠️ Cette action est irréversible.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Supprime le fichier
                photo_path.unlink()

                # Supprime l'item de la liste
                row = self.photo_list.row(item)
                self.photo_list.takeItem(row)

                # Émet le signal pour informer de la suppression
                self.photo_deleted.emit(photo_name)

                logger.info(f"Photo supprimée : {photo_name}")

            except Exception as e:
                logger.error(f"Erreur lors de la suppression de {photo_name}: {e}")
                QMessageBox.critical(
                    self,
                    "Erreur de suppression",
                    f"Impossible de supprimer la photo {photo_name}.\n\n"
                    f"Erreur : {str(e)}",
                )

    def _handle_key_press(self, event):
        """Gère les raccourcis clavier dans la liste."""
        # Appel de la méthode parente d'abord
        QListWidget.keyPressEvent(self.photo_list, event)

        # Gestion de la touche Suppr
        if event.key() == Qt.Key.Key_Delete:
            current_item = self.photo_list.currentItem()
            if current_item:
                self._delete_photo(current_item)

        # Gestion de la touche Entrée pour visualiser
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            current_item = self.photo_list.currentItem()
            if current_item:
                self._view_photo(current_item)
