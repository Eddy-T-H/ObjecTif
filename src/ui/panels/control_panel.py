# src/ui/panels/control_panel.py
"""
Panel de contrôle droit - Gestion ADB et actions photos.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QGridLayout,
    QMessageBox,
    QGroupBox,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtWidgets import QPushButton

from pathlib import Path
from loguru import logger
from typing import Optional
import subprocess

from src.core.device import ADBManager
from src.ui.widgets.adb_status import ADBStatusWidget
from src.ui.widgets.operation_popup import OperationPopup
from src.utils.error_handler import UserFriendlyErrorHandler


class ControlPanel(QWidget):
    """Panel de contrôle pour les actions ADB et la prise de photos."""

    # Signaux émis vers la fenêtre principale
    connection_changed = pyqtSignal(bool)
    photo_taken = pyqtSignal(str, str)  # type, chemin_fichier

    def __init__(self, adb_manager: ADBManager, parent=None):
        super().__init__(parent)
        self.adb_manager = adb_manager

        # État du contexte actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle_path: Optional[Path] = None
        self.current_object_id: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du panel de contrôle avec qt-material."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # === STATUS ADB ===
        self.adb_status = ADBStatusWidget(self.adb_manager)
        self.adb_status.connection_changed.connect(self._on_connection_changed)
        layout.addWidget(self.adb_status)

        # === ACTIONS PHOTO ===
        self._setup_photo_section(layout)

        # === INFORMATIONS CONTEXTUELLES ===
        self._setup_info_section(layout)

        # Espace flexible
        layout.addStretch()

    def _setup_photo_section(self, layout):
        """Configure la section des actions photo avec qt-material."""
        photo_group = QGroupBox("📸 Actions Photos")
        # SUPPRESSION de setStyleSheet - qt-material gère automatiquement
        photo_layout = QVBoxLayout(photo_group)
        photo_layout.setSpacing(8)
        photo_layout.setContentsMargins(12, 20, 12, 12)

        # === BOUTON APPAREIL PHOTO ===
        self.btn_open_camera = QPushButton("📱 Ouvrir appareil photo")
        self.btn_open_camera.setEnabled(False)
        self.btn_open_camera.clicked.connect(self._open_camera)

        photo_layout.addWidget(self.btn_open_camera)

        # === SÉPARATEUR ===
        separator = QLabel()
        separator.setFixedHeight(1)
        # SUPPRESSION du setStyleSheet - qt-material gère les séparateurs
        photo_layout.addWidget(separator)

        # === BOUTONS PHOTO PRINCIPAUX ===
        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setSpacing(8)
        grid_layout.setContentsMargins(0, 0, 0, 0)

        # Boutons d'action
        self.btn_photo_ferme = QPushButton("🔒 Scellé\nFermé")
        self.btn_photo_content = QPushButton("🔍 Contenu\nScellé")
        self.btn_photo_objet = QPushButton("📱 Objet\nd'Essai")
        self.btn_photo_recond = QPushButton("📦 Scellé\nReconditionné")

        # Organisation en grille 2x2
        grid_layout.addWidget(self.btn_photo_ferme, 0, 0)
        grid_layout.addWidget(self.btn_photo_content, 0, 1)
        grid_layout.addWidget(self.btn_photo_objet, 1, 0)
        grid_layout.addWidget(self.btn_photo_recond, 1, 1)

        photo_layout.addWidget(grid_widget)

        # Stockage des boutons pour gestion d'état
        self.photo_buttons = {
            "ferme": self.btn_photo_ferme,
            "contenu": self.btn_photo_content,
            "objet": self.btn_photo_objet,
            "recond": self.btn_photo_recond,
        }

        # Connexion des signaux
        for photo_type, btn in self.photo_buttons.items():
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, t=photo_type: self._take_photo(t))

        layout.addWidget(photo_group)

    def _setup_info_section(self, layout):
        """Configure la section d'informations contextuelles avec qt-material."""
        info_group = QGroupBox("ℹ️ Informations")
        # SUPPRESSION de setStyleSheet - qt-material gère automatiquement
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(10, 15, 10, 10)

        # Labels d'information - SUPPRESSION des setStyleSheet
        self.info_scelle = QLabel("📁 Aucun scellé sélectionné")
        self.info_objet = QLabel("📱 Aucun objet sélectionné")

        # qt-material applique automatiquement un style cohérent
        info_layout.addWidget(self.info_scelle)
        info_layout.addWidget(self.info_objet)

        layout.addWidget(info_group)

    # SUPPRESSION des méthodes _apply_info_style_active et _apply_info_style_inactive
    # qt-material gère automatiquement les styles actif/inactif

    # === GESTIONNAIRES D'ÉVÉNEMENTS ===

    def _on_connection_changed(self, is_connected: bool):
        """Gère les changements d'état de connexion ADB."""
        self._update_photo_buttons_state()
        self.connection_changed.emit(is_connected)

    # === ACTIONS PHOTO ===

    def _take_photo(self, photo_type: str):
        """Prend une photo du type spécifié."""
        if not self.adb_manager.is_connected() or not self.current_scelle_path:
            return

        try:
            # Mapping des types de photo
            prefix_map = {
                "ferme": "Ferme",
                "contenu": "Contenu",
                "objet": self.current_object_id,
                "recond": "Reconditionne",
            }

            # Vérification pour les photos d'objet
            if photo_type == "objet" and not self.current_object_id:
                logger.error("Aucun objet sélectionné")
                self._show_status_message("Aucun objet sélectionné")
                return

            prefix = prefix_map[photo_type]

            # Calcul du prochain numéro de séquence
            next_num = self._get_next_photo_number(prefix)

            # Création du nom de fichier
            scelle_name = self.current_scelle_path.name
            file_name = f"{scelle_name}_{prefix}_{next_num}.jpg"
            save_path = self.current_scelle_path / file_name

            # === DÉBUT DE L'OPÉRATION ===
            self._start_photo_operation()

            # Popup de progression
            popup = OperationPopup(self)
            popup.show()

            def update_status(message):
                popup.update_message(message)
                QApplication.processEvents()

            # Prise de photo avec suivi d'état
            success = self.adb_manager.take_photo(save_path, update_status)

            # Fermeture de la popup
            popup.close_popup()

            if success:
                self._show_status_message(f"Photo(s) sauvegardée(s) pour {prefix}")
                self.photo_taken.emit(photo_type, str(save_path))

                # Auto-effacement du message après 3 secondes
                QTimer.singleShot(3000, lambda: self._show_status_message(""))
            else:
                QMessageBox.warning(
                    self,
                    "Échec de la photo",
                    "La photo n'a pas pu être prise ou transférée.\n\n"
                    "Solutions :\n"
                    "• Vérifiez que l'appareil photo fonctionne\n"
                    "• Prenez une photo manuellement puis réessayez\n"
                    "• Vérifiez la connexion de l'appareil",
                )

        except Exception as e:
            title, message = UserFriendlyErrorHandler.handle_adb_error(
                e, "la prise de photo"
            )
            QMessageBox.warning(self, title, message)

        finally:
            self._end_photo_operation()

    def _open_camera(self):
        """Ouvre l'application appareil photo sur le téléphone."""
        try:
            if not self.adb_manager.is_connected():
                logger.warning("Pas de connexion ADB active")
                self._show_status_message("Erreur : Aucun appareil connecté")
                return

            # Séquence de déverrouillage et ouverture caméra
            commands = [
                # Réveil de l'appareil
                f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell input keyevent KEYCODE_WAKEUP',
                # Déverrouillage par swipe
                f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell input swipe 500 1800 500 1000',
                # Ouverture de l'appareil photo
                f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell am start -a android.media.action.STILL_IMAGE_CAMERA',
            ]

            import time

            for i, command in enumerate(commands):
                subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=5
                )
                if i < len(commands) - 1:  # Pause entre les commandes
                    time.sleep(0.5)

            logger.info("Application appareil photo ouverte avec succès")
            self._show_status_message("Appareil photo ouvert")

        except Exception as e:
            error_msg = f"Erreur lors de l'ouverture de l'appareil photo: {e}"
            logger.error(error_msg)
            self._show_status_message(error_msg)

    # === MÉTHODES UTILITAIRES ===

    def _get_next_photo_number(self, prefix: str) -> int:
        """Calcule le prochain numéro de photo pour un préfixe donné."""
        if not self.current_scelle_path:
            return 1

        max_num = 0
        pattern = f"*{prefix}_*.jpg"

        for photo in self.current_scelle_path.glob(pattern):
            try:
                num = int(photo.stem.split("_")[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue

        return max_num + 1

    def _start_photo_operation(self):
        """Démarre l'indication visuelle d'une opération photo."""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        # Désactive tous les boutons photo
        for btn in self.photo_buttons.values():
            btn.setEnabled(False)
        self.btn_open_camera.setEnabled(False)

    def _end_photo_operation(self):
        """Termine l'indication visuelle d'une opération photo."""
        QApplication.restoreOverrideCursor()

        # Réactive les boutons selon l'état actuel
        self._update_photo_buttons_state()

    def _update_photo_buttons_state(self):
        """Met à jour l'état des boutons photo selon le contexte."""
        android_connected = self.adb_manager.is_connected()

        # Bouton appareil photo : juste besoin de la connexion
        self.btn_open_camera.setEnabled(android_connected)

        # Boutons de scellé : connexion + scellé sélectionné
        scelle_buttons_enabled = (
            android_connected and self.current_scelle_path is not None
        )
        self.btn_photo_ferme.setEnabled(scelle_buttons_enabled)
        self.btn_photo_content.setEnabled(scelle_buttons_enabled)
        self.btn_photo_recond.setEnabled(scelle_buttons_enabled)

        # Bouton objet : connexion + scellé + objet sélectionné
        self.btn_photo_objet.setEnabled(
            android_connected
            and self.current_scelle_path is not None
            and self.current_object_id is not None
        )

    def _show_status_message(self, message: str):
        """Affiche un message dans la barre de statut de la fenêtre parent."""
        try:
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(message)
        except:
            pass

    def _update_context_info(self):
        """Met à jour les informations contextuelles affichées avec qt-material."""
        # Informations sur le scellé
        if self.current_scelle_path:
            scelle_name = self.current_scelle_path.name
            photo_count = self._count_scelle_photos()
            self.info_scelle.setText(f"📁 Scellé: {scelle_name} ({photo_count} photos)")
            # qt-material gère automatiquement le style "actif"
        else:
            self.info_scelle.setText("📁 Aucun scellé sélectionné")
            # qt-material gère automatiquement le style "inactif"

        # Informations sur l'objet
        if self.current_object_id and self.current_scelle_path:
            object_photo_count = self._count_object_photos(self.current_object_id)
            object_full_name = (
                f"{self.current_scelle_path.name}_{self.current_object_id}"
            )
            self.info_objet.setText(
                f"🎯 Objet: {object_full_name} ({object_photo_count} photos)"
            )
            # qt-material gère automatiquement le style "actif"
        else:
            self.info_objet.setText("📱 Aucun objet sélectionné")
            # qt-material gère automatiquement le style "inactif"

    def _count_scelle_photos(self) -> int:
        """Compte les photos du scellé (hors objets)."""
        if not self.current_scelle_path:
            return 0

        count = 0
        for photo in self.current_scelle_path.glob("*.jpg"):
            # Exclut les photos d'objets
            stem_parts = photo.stem.split("_")
            if len(stem_parts) >= 2:
                type_id = stem_parts[-2]
                if not (len(type_id) == 1 and type_id.isalpha()):
                    count += 1
        return count

    def _count_object_photos(self, object_id: str) -> int:
        """Compte les photos d'un objet spécifique."""
        if not self.current_scelle_path:
            return 0

        return len(list(self.current_scelle_path.glob(f"*_{object_id}_*.jpg")))

    # === MÉTHODES PUBLIQUES ===

    def update_context(
        self,
        case_path: Optional[Path] = None,
        scelle_path: Optional[Path] = None,
        object_id: Optional[str] = None,
    ):
        """Met à jour le contexte actuel du panel."""
        self.current_case_path = case_path
        self.current_scelle_path = scelle_path
        self.current_object_id = object_id

        # Met à jour l'interface
        self._update_photo_buttons_state()
        self._update_context_info()

        logger.debug(f"Contexte mis à jour - Scellé: {scelle_path}, Objet: {object_id}")

