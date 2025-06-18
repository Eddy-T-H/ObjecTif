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

        # === LISTE DES SCELLÉS AVEC INDICATEURS ===
        scelles_label = QLabel("🔒 État des Scellés:")
        scelles_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        info_layout.addWidget(scelles_label)

        # Liste scrollable des scellés

        self.scelles_scroll = QScrollArea()
        self.scelles_scroll.setWidgetResizable(True)
        self.scelles_scroll.setMinimumHeight(150)

        # Widget conteneur pour les scellés
        self.scelles_container = QWidgetBase()
        self.scelles_layout = QVBoxLayout(self.scelles_container)
        self.scelles_layout.setContentsMargins(5, 5, 5, 5)
        self.scelles_layout.setSpacing(3)

        self.scelles_scroll.setWidget(self.scelles_container)
        info_layout.addWidget(self.scelles_scroll,1)

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

        # Analyse complète si un dossier est sélectionné
        if case_path:
            case_analysis = self._analyze_case_content(case_path)
            self._update_case_info_display(case_analysis)
        else:
            # Reset l'affichage
            self.info_case.setText("📁 Aucun dossier sélectionné")
            self.info_counts.setText("🔒 Scellés: 0 | 📱 Objets: 0")
            self._clear_scelles_status_list()

        logger.debug(
            f"Contexte mis à jour - Dossier: {case_path}, Scellé: {scelle_path}, Objet: {object_id}")

    # === MÉTHODES D'ANALYSE ET AFFICHAGE ===

    def _analyze_case_content(self, case_path: Path) -> dict:
        """Analyse complète du contenu d'un dossier d'affaire."""
        if not case_path or not case_path.exists():
            return {"scelles_count": 0, "objects_count": 0, "scelles": []}

        scelles_data = []
        total_objects = 0

        try:
            # Parcourt tous les dossiers de scellés
            scelle_folders = [p for p in case_path.iterdir() if p.is_dir()]
            scelle_folders.sort(key=lambda x: x.name.lower())

            for scelle_path in scelle_folders:
                scelle_info = self._analyze_scelle_content(scelle_path)
                scelles_data.append(scelle_info)
                total_objects += scelle_info["objects_count"]

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du dossier {case_path}: {e}")

        return {
            "scelles_count": len(scelles_data),
            "objects_count": total_objects,
            "scelles": scelles_data
        }


    def _analyze_scelle_content(self, scelle_path: Path) -> dict:
        """Analyse le contenu d'un scellé (photos et objets)."""
        scelle_info = {
            "name": scelle_path.name,
            "path": scelle_path,
            "photos": {
                "ferme": False,
                "contenu": False,
                "reconditionne": False
            },
            "objects": [],
            "objects_count": 0,
            "total_photos": 0
        }

        try:
            photos = list(scelle_path.glob("*.jpg"))
            scelle_info["total_photos"] = len(photos)

            objects_found = set()

            for photo in photos:
                parts = photo.stem.split("_")
                if len(parts) >= 2:
                    type_id = parts[-2].lower()

                    # Photos du scellé
                    if type_id in ["ferme", "fermé"]:
                        scelle_info["photos"]["ferme"] = True
                    elif type_id == "contenu":
                        scelle_info["photos"]["contenu"] = True
                    elif type_id in ["reconditionne", "reconditionné", "reconditionnement"]:
                        scelle_info["photos"]["reconditionne"] = True
                    # Photos d'objets (une seule lettre)
                    elif len(parts[-2]) == 1 and parts[-2].isalpha():
                        objects_found.add(parts[-2].upper())

            # Informations sur les objets
            scelle_info["objects"] = sorted(list(objects_found))
            scelle_info["objects_count"] = len(objects_found)

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du scellé {scelle_path}: {e}")

        return scelle_info


    def _create_scelle_status_widget(self, scelle_info: dict) -> QLabel:
        """Crée un widget d'affichage pour l'état d'un scellé."""
        # Icônes pour les types de photos
        ferme_icon = "🔒✅" if scelle_info["photos"]["ferme"] else "🔒❌"
        contenu_icon = "🔍✅" if scelle_info["photos"]["contenu"] else "🔍❌"
        recond_icon = "📦✅" if scelle_info["photos"]["reconditionne"] else "📦❌"

        # Texte des objets
        if scelle_info["objects"]:
            objects_text = f"📱 {','.join(scelle_info['objects'])}"
        else:
            objects_text = "📱 Aucun"

        # Assemblage du texte
        status_text = (
            f"▸ {scelle_info['name']}\n"
            f"  {ferme_icon} {contenu_icon} {recond_icon} | {objects_text} | 📸 {scelle_info['total_photos']}"
        )

        # Création du label
        status_label = QLabel(status_text)
        status_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px 10px;
                font-family: monospace;
                font-size: 12px;
                line-height: 1.3;
            }
        """)
        status_label.setWordWrap(True)

        # Tooltip explicatif
        tooltip = (
            f"Scellé: {scelle_info['name']}\n"
            f"Photos totales: {scelle_info['total_photos']}\n\n"
            f"Photos du scellé:\n"
            f"🔒 Fermé: {'✓' if scelle_info['photos']['ferme'] else '✗'}\n"
            f"🔍 Contenu: {'✓' if scelle_info['photos']['contenu'] else '✗'}\n"
            f"📦 Reconditionné: {'✓' if scelle_info['photos']['reconditionne'] else '✗'}\n\n"
            f"Objets d'essai ({scelle_info['objects_count']}):\n"
        )

        if scelle_info["objects"]:
            tooltip += "\n".join([f"📱 Objet {obj}" for obj in scelle_info["objects"]])
        else:
            tooltip += "Aucun objet d'essai"

        status_label.setToolTip(tooltip)

        return status_label


    def _update_case_info_display(self, case_analysis: dict):
        """Met à jour l'affichage des informations du dossier."""
        if not case_analysis:
            return

        # Met à jour les compteurs globaux
        self.info_counts.setText(
            f"🔒 Scellés: {case_analysis['scelles_count']} | "
            f"📱 Objets: {case_analysis['objects_count']}"
        )

        # Nettoie la liste des scellés
        self._clear_scelles_status_list()

        # Ajoute chaque scellé avec son statut
        for scelle_info in case_analysis["scelles"]:
            status_widget = self._create_scelle_status_widget(scelle_info)
            self.scelles_layout.addWidget(status_widget)

        # Ajoute un stretch pour pousser vers le haut
        self.scelles_layout.addStretch()


    def _clear_scelles_status_list(self):
        """Vide la liste des statuts de scellés."""
        # Supprime tous les widgets de la liste
        while self.scelles_layout.count():
            child = self.scelles_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()