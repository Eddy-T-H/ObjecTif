# src/ui/main_window.py
"""
Interface principale allégée avec délégation aux panels spécialisés.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSlot
from pathlib import Path
from loguru import logger
from typing import Optional

from src.config import AppConfig
# SUPPRIMÉ: from src.ui.theme.design_system import apply_global_theme
from src.ui.panels.navigation_panel import NavigationPanel
from src.ui.panels.control_panel import ControlPanel
from src.ui.panels.log_panel import LogPanel
from src.ui.widgets.operation_popup import OperationPopup
from src.utils.error_handler import UserFriendlyErrorHandler

from src.core.device import ADBManager
from src.core.evidence.base import EvidenceItem
from src.core.evidence.objet import ObjetEssai
from src.core.evidence.scelle import Scelle


class MainWindow(QMainWindow):
    """
    Fenêtre principale allégée qui coordonne les différents panels.
    Délègue la logique métier aux composants spécialisés.
    """

    def __init__(self, config: AppConfig, log_buffer):
        super().__init__()
        self.config = config
        self.log_buffer = log_buffer

        # === ÉTAT DE L'APPLICATION ===
        self.adb_manager = ADBManager()
        self.scelle_manager: Optional[Scelle] = None
        self.objet_manager: Optional[ObjetEssai] = None

        # État actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle: Optional[EvidenceItem] = None
        self.current_object: Optional[str] = None

        # === CONFIGURATION FENÊTRE ===
        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setMinimumSize(800, 600)
        self.resize(1280, 800)
        # SUPPRIMÉ: self.setStyleSheet(apply_global_theme())

        # === INITIALISATION ===
        self._create_panels()
        self._setup_layout()
        self._connect_signals()
        self._initialize_workspace()

    def _create_panels(self):
        """Crée les différents panels de l'interface."""
        # Panel de navigation (gauche)
        self.navigation_panel = NavigationPanel(
            config=self.config,
            adb_manager=self.adb_manager,
            parent=self
        )

        # Panel de contrôle (droite)
        self.control_panel = ControlPanel(
            adb_manager=self.adb_manager,
            parent=self
        )

        # Panel de logs (bas)
        self.log_panel = LogPanel(
            log_buffer=self.log_buffer,
            parent=self
        )

    def _setup_layout(self):
        """Configure le layout principal de la fenêtre."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Zone principale horizontale (navigation + contrôle)
        upper_area = QWidget()
        upper_layout = QHBoxLayout(upper_area)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(8)

        # Ajout des panels avec tailles minimales
        self.navigation_panel.setMinimumWidth(280)
        self.control_panel.setMinimumWidth(280)

        upper_layout.addWidget(self.navigation_panel)
        upper_layout.addWidget(self.control_panel)

        # Splitter vertical principal
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(upper_area)
        main_splitter.addWidget(self.log_panel)
        main_splitter.setStretchFactor(0, 3)  # Zone haute prioritaire
        main_splitter.setStretchFactor(1, 1)  # Zone logs plus petite

        main_layout.addWidget(main_splitter)

    def _connect_signals(self):
        """Connecte les signaux entre les différents panels."""
        # Signaux du panel de navigation vers le panel de contrôle
        self.navigation_panel.case_selected.connect(self._on_case_selected)
        self.navigation_panel.scelle_selected.connect(self._on_scelle_selected)
        self.navigation_panel.object_selected.connect(self._on_object_selected)

        # Signaux du panel de contrôle
        self.control_panel.connection_changed.connect(self._on_connection_changed)
        self.control_panel.photo_taken.connect(self._on_photo_taken)

        # Signaux de suppression de photos
        self.navigation_panel.photo_deleted.connect(self._on_photo_deleted)

    def _initialize_workspace(self):
        """Initialise le workspace et charge les données."""
        self.navigation_panel.initialize_workspace()

    # === GESTIONNAIRES D'ÉVÉNEMENTS ===

    @pyqtSlot(Path)
    def _on_case_selected(self, case_path: Path):
        """Gère la sélection d'une affaire."""
        logger.info(f"Affaire sélectionnée : {case_path.name}")

        # Met à jour l'état
        self.current_case_path = case_path
        self.current_scelle = None
        self.current_object = None

        # Crée les gestionnaires
        self.scelle_manager = Scelle(case_path)
        self.objet_manager = None

        # Met à jour les panels
        self.control_panel.update_context(
            case_path=case_path,
            scelle_path=None,
            object_id=None
        )

        self.statusBar().showMessage(f"Affaire sélectionnée : {case_path.name}")

    @pyqtSlot(Path)
    def _on_scelle_selected(self, scelle_path: Path):
        """Gère la sélection d'un scellé."""
        logger.info(f"Scellé sélectionné : {scelle_path.name}")

        # Met à jour l'état
        self.current_scelle = scelle_path
        self.current_object = None
        self.objet_manager = ObjetEssai(scelle_path)

        # Met à jour le panel de contrôle
        self.control_panel.update_context(
            case_path=self.current_case_path,
            scelle_path=scelle_path,
            object_id=None
        )

        self.statusBar().showMessage(f"Scellé sélectionné : {scelle_path.name}")

    @pyqtSlot(str)
    def _on_object_selected(self, object_id: str):
        """Gère la sélection d'un objet."""
        logger.info(f"Objet sélectionné : {object_id}")

        # Met à jour l'état
        self.current_object = object_id

        # Met à jour le panel de contrôle
        self.control_panel.update_context(
            case_path=self.current_case_path,
            scelle_path=self.current_scelle,
            object_id=object_id
        )

        self.statusBar().showMessage(f"Objet {object_id} sélectionné")

    @pyqtSlot(bool)
    def _on_connection_changed(self, is_connected: bool):
        """Gère les changements d'état de connexion ADB."""
        status = "connecté" if is_connected else "déconnecté"
        logger.info(f"État connexion ADB : {status}")

        # Propage l'information au panel de navigation si nécessaire
        self.navigation_panel.update_connection_state(is_connected)

    @pyqtSlot(str, str)
    def _on_photo_taken(self, photo_type: str, file_path: str):
        """Gère la prise d'une photo."""
        logger.info(f"Photo prise : {photo_type} -> {file_path}")

        # Rafraîchit les listes de photos dans le panel de navigation
        self.navigation_panel.refresh_photos()

        self.statusBar().showMessage(f"Photo {photo_type} sauvegardée")

    @pyqtSlot(str)
    def _on_photo_deleted(self, photo_name: str):
        """Gère la suppression d'une photo."""
        logger.info(f"Photo supprimée : {photo_name}")

        # Rafraîchit les listes de photos
        self.navigation_panel.refresh_photos()

        self.statusBar().showMessage(f"Photo supprimée : {photo_name}")

    # === MÉTHODES PUBLIQUES POUR L'INTÉGRATION ===

    def get_current_context(self):
        """Retourne le contexte actuel pour les autres composants."""
        return {
            'case_path': self.current_case_path,
            'scelle_path': self.current_scelle,
            'object_id': self.current_object,
            'scelle_manager': self.scelle_manager,
            'objet_manager': self.objet_manager
        }

    def show_operation_popup(self, title: str = "Opération en cours"):
        """Affiche une popup d'opération et retourne sa référence."""
        popup = OperationPopup(self)
        popup.setWindowTitle(title)
        popup.show()
        return popup

    def handle_error(self, exception: Exception, operation: str = ""):
        """Gère les erreurs de manière centralisée."""
        title, message = UserFriendlyErrorHandler.handle_adb_error(exception, operation)
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.warning(self, title, message)