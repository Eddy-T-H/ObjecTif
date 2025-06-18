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
from PyQt6.QtWidgets import QScrollArea, QWidget as QWidgetBase

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
from src.ui.widgets.log_viewer import QtHandler, ColoredLogViewer
from src.ui.widgets.operation_popup import OperationPopup
from src.utils.error_handler import UserFriendlyErrorHandler


class ControlPanel(QWidget):
    """Panel de contrôle pour les actions ADB et la prise de photos."""

    # Signaux émis vers la fenêtre principale
    connection_changed = pyqtSignal(bool)
    photo_taken = pyqtSignal(str, str)  # type, chemin_fichier

    def __init__(self, adb_manager: ADBManager, log_buffer=None, parent=None):
        super().__init__(parent)
        self.adb_manager = adb_manager
        self.log_buffer = log_buffer  # buffer de logs pour console

        # État du contexte actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle_path: Optional[Path] = None
        self.current_object_id: Optional[str] = None

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du panel de contrôle avec console intégrée."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        # === STATUS ADB DANS UN GROUPBOX ===
        adb_group = QGroupBox("🔗 Connexion Android")
        adb_layout = QVBoxLayout(adb_group)
        adb_layout.setContentsMargins(12, 20, 12, 12)
        adb_layout.setSpacing(8)

        self.adb_status = ADBStatusWidget(self.adb_manager)
        self.adb_status.connection_changed.connect(self._on_connection_changed)
        adb_layout.addWidget(self.adb_status)

        layout.addWidget(adb_group)

        # === ACTIONS PHOTO ===
        self._setup_photo_section(layout)

        # === INFORMATIONS CONTEXTUELLES ===
        self._setup_info_section(layout)

        # === CONSOLE DE LOGS ===
        self._setup_logs_section(layout)


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
        self.btn_photo_ferme = QPushButton("🔒\nScellé\nFermé")
        self.btn_photo_content = QPushButton("🔍\nContenu\nScellé")
        self.btn_photo_objet = QPushButton("📱\nObjet\nd'Essai")
        self.btn_photo_recond = QPushButton("📦\nScellé\nReconditionné")

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
        """Configure la section d'informations contextuelles avancée."""
        info_group = QGroupBox("ℹ️ Informations")
        info_layout = QVBoxLayout(info_group)
        info_layout.setContentsMargins(10, 15, 10, 10)
        info_layout.setSpacing(8)

        # === INFORMATIONS GÉNÉRALES ===
        general_layout = QVBoxLayout()
        general_layout.setSpacing(4)

        # Dossier actuel
        self.info_case = QLabel("📁 Aucun dossier sélectionné")
        general_layout.addWidget(self.info_case)

        # Compteurs globaux
        self.info_counts = QLabel("🔒 Scellés: 0 | 📱 Objets: 0")
        general_layout.addWidget(self.info_counts)

        # Scellé et objet actuels
        self.info_scelle = QLabel("📁 Aucun scellé sélectionné")
        general_layout.addWidget(self.info_scelle)

        self.info_objet = QLabel("📱 Aucun objet sélectionné")
        general_layout.addWidget(self.info_objet)

        info_layout.addLayout(general_layout)

        # === SÉPARATEUR ===
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: #ccc; margin: 5px 0;")
        info_layout.addWidget(separator)

        # === AIDE RAPIDE ===
        help_label = QLabel("💡 Aide Rapide")
        help_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        info_layout.addWidget(help_label)

        help_text = QLabel(
            "• Sélectionnez un dossier dans le panel gauche\n"
            "• Choisissez un scellé pour voir ses indicateurs\n"
            "• Les icônes montrent l'état des photos :\n"
            "  🔒✅/❌ Fermé, 🔍✅/❌ Contenu, 📦✅/❌ Reconditionné\n"
            "• 📱 indique les objets d'essai présents"
        )
        help_text.setStyleSheet("color: #666; font-size: 11px; padding: 5px;")
        help_text.setWordWrap(True)
        info_layout.addWidget(help_text)

        layout.addWidget(info_group)

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
        """Met à jour les informations contextuelles affichées."""
        # Informations sur le dossier
        if self.current_case_path:
            case_name = self.current_case_path.name
            self.info_case.setText(f"📁 Dossier: {case_name}")
        else:
            self.info_case.setText("📁 Aucun dossier sélectionné")

        # Informations sur le scellé
        if self.current_scelle_path:
            scelle_name = self.current_scelle_path.name
            photo_count = self._count_scelle_photos()
            self.info_scelle.setText(f"🔒 Scellé: {scelle_name} ({photo_count} photos)")
        else:
            self.info_scelle.setText("🔒 Aucun scellé sélectionné")

        # Informations sur l'objet
        if self.current_object_id and self.current_scelle_path:
            object_photo_count = self._count_object_photos(self.current_object_id)
            object_full_name = f"{self.current_scelle_path.name}_{self.current_object_id}"
            self.info_objet.setText(
                f"📱 Objet: {object_full_name} ({object_photo_count} photos)")
        else:
            self.info_objet.setText("📱 Aucun objet sélectionné")

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
        """Met à jour le contexte actuel du panel avec analyse complète."""
        self.current_case_path = case_path
        self.current_scelle_path = scelle_path
        self.current_object_id = object_id

        # Met à jour l'interface
        self._update_photo_buttons_state()
        self._update_context_info()

        # Analyse simplifiée du dossier si sélectionné
        if case_path:
            self._update_simple_case_info(case_path)
        else:
            # Reset l'affichage
            self.info_case.setText("📁 Aucun dossier sélectionné")
            self.info_counts.setText("🔒 Scellés: 0 | 📱 Objets: 0")

        logger.debug(
            f"Contexte mis à jour - Dossier: {case_path}, Scellé: {scelle_path}, Objet: {object_id}")


    def _update_simple_case_info(self, case_path: Path):
        """Met à jour les informations basiques du dossier."""
        if not case_path or not case_path.exists():
            return

        try:
            # Compte simple des scellés et objets
            scelle_folders = [p for p in case_path.iterdir() if p.is_dir()]
            scelles_count = len(scelle_folders)

            total_objects = 0
            for scelle_path in scelle_folders:
                # Compte rapide des objets (photos avec une seule lettre)
                objects_in_scelle = set()
                for photo in scelle_path.glob("*_[A-Z]_*.jpg"):
                    try:
                        obj_letter = photo.stem.split("_")[-2]
                        if len(obj_letter) == 1 and obj_letter.isalpha():
                            objects_in_scelle.add(obj_letter)
                    except:
                        pass
                total_objects += len(objects_in_scelle)

            self.info_counts.setText(
                f"🔒 Scellés: {scelles_count} | 📱 Objets: {total_objects}")

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse simple du dossier {case_path}: {e}")

    def _setup_logs_section(self, layout):
        """Configure la section console de logs."""
        logs_group = QGroupBox("📝 Console")
        logs_layout = QVBoxLayout(logs_group)
        logs_layout.setContentsMargins(12, 20, 12, 12)
        logs_layout.setSpacing(8)

        # Créer le viewer de logs
        self.log_viewer = ColoredLogViewer()
        self.log_viewer.setMinimumHeight(100)

        # Charge les logs initiaux si le buffer existe
        if self.log_buffer:
            self.log_viewer.load_initial_logs(self.log_buffer)

        # Configure le handler Loguru pour rediriger vers ce viewer
        logger.add(
            QtHandler(self.log_viewer).write,
            format="{time:HH:mm:ss} | {level: <8} | {message}"
        )

        logs_layout.addWidget(self.log_viewer)


        layout.addWidget(logs_group)

    #  méthode publique pour accéder aux logs
    def clear_logs(self):
        """Vide les logs affichés."""
        if hasattr(self, 'log_viewer'):
            self.log_viewer.clear()

    def append_log(self, message: str, level: str = "INFO"):
        """Ajoute un message de log."""
        if hasattr(self, 'log_viewer'):
            self.log_viewer.append_log(message, level)