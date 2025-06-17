# ui/main_window.py
"""
Interface principale avec gestion correcte de l'initialisation des composants.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QLabel, QPushButton, QFileDialog,
    QStatusBar, QMessageBox, QSplitter, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QTabWidget, QPlainTextEdit,
    QFrame, QSizePolicy, QDockWidget
)
from PyQt6.QtCore import Qt, QModelIndex, pyqtSlot
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem, QColor, \
    QTextCursor, QPalette
from PyQt6.QtCore import Qt, QModelIndex, pyqtSlot, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, List
from src.config import AppConfig

from .dialogs.create_affaire_dialog import CreateAffaireDialog
from .dialogs.create_scelle_dialog import CreateScelleDialog
from .widgets.adb_status import ADBStatusWidget
from .widgets.log_viewer import ColoredLogViewer, QtHandler
from .widgets.photo_list import PhotoListWidget
from .widgets.operation_popup import OperationPopup
from src.utils.error_handler import UserFriendlyErrorHandler

from ..core.device import ADBManager
from ..core.evidence.base import EvidenceItem
from ..core.evidence.objet import ObjetEssai
from ..core.evidence.scelle import Scelle

import subprocess

class MainWindow(QMainWindow):

    """
    Fenêtre principale de l'application.
    Gère l'interface utilisateur et coordonne les différentes fonctionnalités.
    """

    def __init__(self, config: AppConfig, log_buffer):
        """
        Initialise la fenêtre principale.

        Args:
            config: Configuration de l'application
        """
        super().__init__()
        self.config = config
        self.log_buffer = log_buffer  # Peut être None en mode compilé

        # Créer une seule instance d'ADBManager qui sera partagée
        self.adb_manager = ADBManager()

        # Gestionnaires de preuves
        self.scelle_manager: Optional[Scelle] = None
        self.objet_manager: Optional[ObjetEssai] = None

        # État actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle: Optional[EvidenceItem] = None
        self.current_object: Optional[str] = None

        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setMinimumSize(800, 600)
        self.resize(1280, 800)  # Taille par défaut au lancement

        # Initialisation de l'interface
        self._initialize_ui()
        self._check_workspace()
        self._update_workspace_label()

        if self.config.paths.workspace_path:
            self._refresh_workspace_view()

        # Connecte le signal de changement de connexion
        self.adb_status.connection_changed.connect(self._update_photo_buttons)

    def _initialize_ui(self):
        """Configure l'interface utilisateur principale."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Zone principale avec navigation et contrôles
        upper_area = QWidget()
        upper_layout = QHBoxLayout(upper_area)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(8)

        # Zone de navigation (gauche)
        navigation_panel = self._setup_left_panel()
        navigation_panel.setMinimumWidth(280)

        # Zone de contrôle (droite)
        control_panel = self._setup_right_panel()
        control_panel.setMinimumWidth(280)

        upper_layout.addWidget(navigation_panel)
        upper_layout.addWidget(control_panel)

        # Terminal de logs (bas)
        log_viewer = self._setup_log_viewer()

        # Ajout des zones dans le layout principal
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(upper_area)
        main_splitter.addWidget(log_viewer)
        main_splitter.setStretchFactor(0, 3)  # Zone haute plus grande
        main_splitter.setStretchFactor(1, 1)  # Zone basse plus petite

        main_layout.addWidget(main_splitter)

    def _handle_stream_error(self, error_msg: str):
        """Affiche les erreurs de streaming dans la barre d'état."""
        self.statusBar().showMessage(f"Erreur de streaming : {error_msg}")

    def _setup_right_panel(self) -> QWidget:
        """Configure le panneau droit avec les contrôles ADB et les boutons photo."""
        right_panel = QWidget()
        right_panel.setMinimumWidth(200)
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Widget de status ADB en haut
        self.adb_status = ADBStatusWidget(self.adb_manager)
        layout.addWidget(self.adb_status)

        # Groupe des boutons photo
        photo_group = QGroupBox("Actions Photos")
        photo_layout = QVBoxLayout(photo_group)
        photo_layout.setSpacing(6)

        # Bouton pour ouvrir l'appareil photo
        self.btn_open_camera = QPushButton("Ouvrir appareil photo")
        self.btn_open_camera.setEnabled(False)
        self.btn_open_camera.clicked.connect(self._open_camera)
        photo_layout.addWidget(self.btn_open_camera)

        # Création des boutons photo
        self.btn_photo_ferme = QPushButton("Photo Scellé Fermé")
        self.btn_photo_content = QPushButton("Photo Contenu")
        self.btn_photo_objet = QPushButton("Photo Objet d'Essai")
        self.btn_photo_recond = QPushButton("Photo Reconditionnement")

        self.photo_buttons = {
            "ferme": self.btn_photo_ferme,
            "contenu": self.btn_photo_content,
            "objet": self.btn_photo_objet,
            "recond": self.btn_photo_recond
        }

        for photo_type, btn in self.photo_buttons.items():
            btn.setEnabled(False)
            btn.clicked.connect(lambda checked, t=photo_type: self._take_photo(t))
            photo_layout.addWidget(btn)

        layout.addWidget(photo_group)
        layout.addStretch()  # Espace flexible en bas

        return right_panel

    def _open_camera(self):
        """
        Ouvre l'application appareil photo sur le téléphone Android.
        Gère d'abord le déverrouillage de l'appareil avant de lancer l'application.
        """
        try:
            if not self.adb_manager.is_connected():
                logger.warning("Pas de connexion ADB active")
                self.statusBar().showMessage("Erreur : Aucun appareil connecté")
                return

            # Séquence de déverrouillage
            # 1. Réveille l'appareil
            wake_command = f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell input keyevent KEYCODE_WAKEUP'
            subprocess.run(wake_command, shell=True, capture_output=True, text=True,
                           timeout=2)

            # 2. Un petit délai pour laisser l'écran s'allumer
            import time
            time.sleep(0.5)

            # 3. Simule le glissement vers le haut pour déverrouiller
            # Les coordonnées sont en pourcentage de l'écran (50% horizontal, du bas vers 40% vertical)
            unlock_command = f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell input swipe 500 1800 500 1000'
            subprocess.run(unlock_command, shell=True, capture_output=True, text=True,
                           timeout=2)

            # 4. Petit délai pour laisser l'animation de déverrouillage se terminer
            time.sleep(0.5)

            # Maintenant on peut ouvrir l'appareil photo
            camera_command = f'"{self.adb_manager.adb_command}" -s {self.adb_manager.current_device} shell am start -a android.media.action.STILL_IMAGE_CAMERA'
            result = subprocess.run(camera_command, shell=True, capture_output=True,
                                    text=True, timeout=5)

            if result.returncode == 0:
                logger.info("Application appareil photo ouverte avec succès")
                self.statusBar().showMessage("Appareil photo ouvert")
            else:
                error_msg = f"Erreur lors de l'ouverture de l'appareil photo: {result.stderr}"
                logger.error(error_msg)
                self.statusBar().showMessage(error_msg)

        except subprocess.TimeoutExpired:
            error_msg = "Timeout lors de l'ouverture de l'appareil photo"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg)
        except Exception as e:
            error_msg = f"Erreur lors de l'ouverture de l'appareil photo: {e}"
            logger.error(error_msg)
            self.statusBar().showMessage(error_msg)

    def _setup_lower_area(self) -> QWidget:
        """Configure la zone inférieure de l'interface."""
        lower_widget = QWidget()
        lower_layout = QHBoxLayout(lower_widget)
        lower_layout.setContentsMargins(0, 0, 0, 0)
        lower_layout.setSpacing(8)

        # Terminal de logs
        log_viewer = self._setup_log_viewer()

        # # Boutons de photos
        # photo_controls = self._setup_photo_controls()

        lower_layout.addWidget(log_viewer, stretch=2)
        # lower_layout.addWidget(photo_controls, stretch=1)

        return lower_widget

    def _setup_log_viewer(self) -> QPlainTextEdit:
        """Configure le visualiseur de logs."""
        log_viewer = ColoredLogViewer()

        # Charge les logs initiaux seulement si le buffer existe
        if self.log_buffer:
            log_viewer.load_initial_logs(self.log_buffer)

        # Configuration du handler Loguru
        logger.add(
            QtHandler(log_viewer).write,
            format="{time:HH:mm:ss} | {level: <8} | {message}"
        )

        return log_viewer

    def _setup_left_panel(self):
        """
        Configure le panneau gauche avec une navigation à trois niveaux :
        - Affaires
        - Scellés
        - Objets d'essai
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(4, 4, 4, 4)  # Réduire les marges
        layout.setSpacing(4)  # Réduire l'espacement

        # Section du dossier de travail plus compacte
        workspace_widget = QWidget()
        workspace_layout = QHBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(4)

        # Créer et configurer les widgets du workspace
        workspace_label_title = QLabel("Dossier de travail :")
        self.workspace_label = QLabel("Non configuré")  # Important: assigner à self
        change_workspace_btn = QPushButton("Changer")
        change_workspace_btn.clicked.connect(self._select_workspace)

        # Ajouter les widgets au layout du workspace
        workspace_layout.addWidget(workspace_label_title)
        workspace_layout.addWidget(self.workspace_label, stretch=1)
        workspace_layout.addWidget(change_workspace_btn)

        # Ajouter le widget workspace au layout principal
        workspace_widget.setLayout(workspace_layout)
        layout.addWidget(workspace_widget)

        # Splitter pour les trois zones avec contraintes minimales réduites
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Zone des affaires
        cases_group = self._setup_cases_group()
        cases_group.setMinimumHeight(100)
        splitter.addWidget(cases_group)

        # Zone des scellés
        scelles_group = self._setup_scelles_group()
        scelles_group.setMinimumHeight(100)
        splitter.addWidget(scelles_group)

        # Zone des objets
        objects_group = self._setup_objects_group()
        objects_group.setMinimumHeight(100)
        splitter.addWidget(objects_group)

        # Proportions plus équilibrées
        splitter.setSizes([200, 200, 200])
        layout.addWidget(splitter)

        panel.setMinimumWidth(200)  # Largeur minimale du panneau gauche
        return panel

    def _setup_cases_group(self) -> QGroupBox:
        """Configure la zone des affaires."""
        group = QGroupBox("Dossiers")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)

        # Layout horizontal pour les boutons
        btn_layout = QHBoxLayout()

        add_btn = QPushButton("Nouveau Dossier")
        add_btn.clicked.connect(self._create_new_affaire)
        btn_layout.addWidget(add_btn)

        open_btn = QPushButton("Ouvrir dans l'explorateur")
        open_btn.setEnabled(False)  # Désactivé par défaut
        open_btn.clicked.connect(lambda: self._open_explorer(
            self.current_case_path) if self.current_case_path else None)
        btn_layout.addWidget(open_btn)
        self.case_explorer_btn = open_btn  # Gardez une référence pour l'activer/désactiver

        layout.addLayout(btn_layout)

        self.cases_tree = QTreeView()
        self.cases_model = QFileSystemModel()
        self.cases_model.setRootPath("")
        self.cases_tree.setModel(self.cases_model)
        for i in range(1, self.cases_model.columnCount()):
            self.cases_tree.hideColumn(i)
        self.cases_tree.clicked.connect(self._on_case_selected)
        layout.addWidget(self.cases_tree)

        return group

    def _setup_scelles_group(self) -> QGroupBox:
        """Configure la zone des scellés avec gestion améliorée du redimensionnement."""
        group = QGroupBox("Scellés")
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Bouton d'ajout
        add_btn = QPushButton("Ajouter un scellé (nom de dossier)")
        add_btn.clicked.connect(self._create_new_scelle)
        add_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        layout.addWidget(add_btn)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(
            False)  # Empêche de réduire complètement les widgets
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Expanding)

        # Arborescence des scellés
        self.scelles_tree = QTreeView()
        self.scelles_tree.setMinimumWidth(150)
        self.scelles_tree.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Expanding)
        self.scelles_model = QStandardItemModel()
        self.scelles_model.setHorizontalHeaderLabels(['Scellés'])
        self.scelles_tree.setModel(self.scelles_model)
        self.scelles_tree.clicked.connect(self._on_scelle_selected)
        splitter.addWidget(self.scelles_tree)

        # Liste des photos
        self.scelle_photos = PhotoListWidget("Photos du scellé:")
        splitter.addWidget(self.scelle_photos)

        # Ajuster les tailles minimales
        self.scelles_tree.setMinimumWidth(100)  # Au lieu de 150
        self.scelle_photos.setMinimumWidth(100)  # Taille minimale réduite

        # Définit les proportions initiales
        splitter.setSizes([100, 100])

        layout.addWidget(splitter)
        return group

    def _setup_objects_group(self) -> QGroupBox:
        """Configure la zone des objets avec gestion améliorée du redimensionnement."""
        group = QGroupBox("Objets d'essai")
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Bouton d'ajout
        self.add_object_btn = QPushButton("Ajouter un objet d'essai")
        self.add_object_btn.clicked.connect(self._add_new_object)
        self.add_object_btn.setEnabled(False)
        self.add_object_btn.setSizePolicy(QSizePolicy.Policy.Preferred,
                                          QSizePolicy.Policy.Fixed)
        layout.addWidget(self.add_object_btn)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Expanding)

        # Liste des objets
        self.objects_list = QTreeWidget()
        self.objects_list.setMinimumWidth(150)
        self.objects_list.setSizePolicy(QSizePolicy.Policy.Expanding,
                                        QSizePolicy.Policy.Expanding)
        self.objects_list.setHeaderLabels(["Objets"])
        self.objects_list.itemClicked.connect(self._on_object_selected)
        splitter.addWidget(self.objects_list)

        # Liste des photos
        self.object_photos = PhotoListWidget("Photos de l'objet:")
        splitter.addWidget(self.object_photos)

        # Ajuster les tailles minimales
        self.objects_list.setMinimumWidth(100)  # Au lieu de 150
        self.object_photos.setMinimumWidth(100)  # Taille minimale réduite

        # Ajuster les proportions du splitter
        splitter.setSizes([100, 100])  # Proportions plus équilibrées

        layout.addWidget(splitter)
        return group

    def _create_new_affaire(self):
        """
        Ouvre le dialogue de création d'une nouvelle affaire et crée le dossier correspondant.
        """
        if not self.config.paths.workspace_path:
            QMessageBox.warning(self, "Erreur",
                                "Veuillez d'abord configurer un dossier de travail.")
            return

        dialog = CreateAffaireDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            numero = dialog.get_data()[0]
            if numero:
                try:
                    # Crée le dossier de l'affaire dans le workspace
                    affaire_path = self.config.paths.workspace_path / numero
                    affaire_path.mkdir(exist_ok=False)

                    # Rafraîchit la vue des affaires
                    self._refresh_workspace_view()

                    self.statusBar().showMessage(f"Dossier {numero} créé")
                    logger.info(f"Nouvelle affaire créée : {numero}")

                    # Sélectionne automatiquement la nouvelle affaire
                    index = self.cases_model.index(str(affaire_path))
                    self.cases_tree.setCurrentIndex(index)
                    self._on_case_selected(index)

                except FileExistsError:
                    QMessageBox.warning(self, "Dossier existant",
                                        f"Un dossier portant le nom '{numero}' existe déjà.\n\n"
                                        f"Veuillez choisir un nom différent.")
                except PermissionError as e:
                    title, message = UserFriendlyErrorHandler.handle_file_error(e,
                                                                                str(affaire_path))
                    QMessageBox.critical(self, title, message)
                except Exception as e:
                    title, message = UserFriendlyErrorHandler.handle_file_error(e,
                                                                                str(affaire_path))
                    QMessageBox.critical(self, title, message)

    def _create_new_scelle(self):
        """
        Crée un nouveau scellé dans l'affaire actuelle avec gestion d'erreur améliorée.
        """
        if not self.scelle_manager:
            QMessageBox.warning(self, "Aucune affaire sélectionnée",
                                "Veuillez d'abord sélectionner une affaire dans la liste.")
            return

        if not self.current_case_path:
            QMessageBox.warning(self, "Erreur",
                                "Aucune affaire sélectionnée.")
            return

        dialog = CreateScelleDialog(self)

        if dialog.exec():
            try:
                numero = dialog.get_numero()
                if not numero:
                    raise ValueError("Le numéro du scellé est requis")

                # Crée le dossier du scellé
                scelle_path = self.current_case_path / numero
                if scelle_path.exists():
                    QMessageBox.warning(self, "Scellé existant",
                                        f"Un scellé portant le nom '{numero}' existe déjà dans cette affaire.\n\n"
                                        f"Veuillez choisir un nom différent.")
                    return

                # Crée le dossier
                scelle_path.mkdir(parents=True)

                # Met à jour la liste des scellés
                self._load_scelles(self.current_case_path)

                # Met à jour la barre d'état
                self.statusBar().showMessage(f"Scellé {numero} créé")
                logger.info(f"Nouveau scellé créé : {numero}")

            except ValueError as e:
                QMessageBox.warning(self, "Données invalides", str(e))
            except PermissionError as e:
                title, message = UserFriendlyErrorHandler.handle_file_error(e,
                                                                            str(scelle_path))
                QMessageBox.critical(self, title, message)
            except Exception as e:
                title, message = UserFriendlyErrorHandler.handle_file_error(e,
                                                                            str(scelle_path))
                QMessageBox.critical(self, title, message)

    @pyqtSlot(QModelIndex)
    def _on_scelle_selected(self, index):
        """Gère la sélection d'un scellé."""
        logger.debug("Sélection d'un scellé")

        self.objects_list.clear()
        self.object_photos.clear()  # Vide la liste des photos d'objet

        try:
            item = self.scelles_model.itemFromIndex(index)
            if not item:
                return

            scelle_name = item.text()
            logger.debug(f"Scellé sélectionné: {scelle_name}")

            scelle = self.scelle_manager.get_item(scelle_name)
            if scelle:
                self.current_scelle = scelle.path
                self.objet_manager = ObjetEssai(scelle.path)

                # Met à jour l'interface
                self._update_photo_buttons()
                self._load_existing_objects()
                self.add_object_btn.setEnabled(True)

                # Met à jour la liste des photos du scellé (uniquement photos générales)
                self._update_scelle_photos()

        except Exception as e:
            logger.error(f"Erreur lors de la sélection du scellé: {e}")
            QMessageBox.critical(self, "Erreur", str(e))
            self.scelles_tree.setEnabled(True)

    def _update_scelle_photos(self):
        """Met à jour la liste des photos du scellé en excluant les photos d'objets."""
        photos = []
        if self.current_scelle and self.current_scelle.exists():
            for photo in self.current_scelle.glob("*.jpg"):
                # Vérifie si le nom de la photo contient un identifiant d'objet
                stem_parts = photo.stem.split('_')
                # On regarde si l'avant-dernier élément est une lettre seule (identificateur d'objet)
                if len(stem_parts) >= 2:
                    type_id = stem_parts[-2]
                    if not (len(type_id) == 1 and type_id.isalpha()):
                        photos.append(photo.name)

        self.scelle_photos.update_photos(photos)

    def _load_existing_objects(self):
        """Charge la liste des objets existants."""
        logger.debug("Chargement des objets")
        self.objects_list.clear()

        if not self.objet_manager:
            return

        try:
            for object_id in self.objet_manager.get_existing_objects():
                item = QTreeWidgetItem([f"{self.current_scelle.name}_{object_id}"])
                item.setData(0, Qt.ItemDataRole.UserRole, object_id)
                self.objects_list.addTopLevelItem(item)
                logger.debug(f"Objet ajouté: {object_id}")

        except Exception as e:
            logger.error(f"Erreur lors du chargement des objets: {e}")

    def _add_new_object(self):
        """
        Ajoute un nouvel objet au scellé actuel.
        Attribue automatiquement le prochain code alphabétique disponible.
        La séquence suit le modèle Excel : A, B, C... Z, AA, AB, AC...
        """
        logger.debug("Ajout d'un nouvel objet")

        if not self.objet_manager or not self.current_scelle:
            logger.warning("Pas de scellé sélectionné")
            return

        try:
            # Utilise la méthode publique au lieu d'accéder directement à la méthode protégée
            next_code = self.objet_manager.get_next_available_code()
            logger.debug(f"Création de l'objet avec le code {next_code}")

            # Crée le nouvel objet
            item = self.objet_manager.create_item(
                item_id=next_code,
                name=f"Objet {next_code}"
            )

            # Met à jour l'interface
            tree_item = QTreeWidgetItem([f"{self.current_scelle.name}_{next_code}"])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, next_code)
            self.objects_list.addTopLevelItem(tree_item)

            # Sélectionne le nouvel objet
            self.objects_list.setCurrentItem(tree_item)
            self._on_object_selected(tree_item)

            logger.info(f"Nouvel objet {next_code} créé avec succès")

        except Exception as e:
            logger.error(f"Erreur lors de la création de l'objet: {e}")
            QMessageBox.warning(self, "Erreur", str(e))


    def _enable_photo_buttons(self):
        """Active les boutons photo selon le contexte."""
        # Active le bouton d'appareil photo si ADB est connecté
        self.btn_open_camera.setEnabled(self.adb_manager.is_connected())
        # Active les boutons de base du scellé
        self.btn_photo_ferme.setEnabled(True)
        self.btn_photo_content.setEnabled(True)
        self.btn_photo_recond.setEnabled(True)
        # Le bouton photo d'objet reste désactivé jusqu'à sélection d'un objet
        self.btn_photo_objet.setEnabled(False)

    def _on_object_selected(self, item):
        """
        Gère la sélection d'un objet dans la liste.
        Active le bouton de photo d'objet et met à jour la liste des photos.
        """
        logger.debug("Sélection d'un objet")

        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if object_id and self.current_scelle:
            self.current_object = object_id
            self._update_photo_buttons()
            logger.debug(f"Objet sélectionné: {object_id}")

            # Met à jour la liste des photos de l'objet
            photos = []
            for photo in self.current_scelle.glob(f"*_{object_id}_*.jpg"):
                photos.append(photo.name)
            self.object_photos.update_photos(photos)

            self.statusBar().showMessage(f"Objet {object_id} sélectionné")

    def _check_workspace(self):
        """Vérifie et initialise le dossier de travail."""
        if not self.config.paths.workspace_path:
            QMessageBox.information(
                self,
                "Configuration initiale",
                "Veuillez sélectionner le dossier de travail."
            )
            self._select_workspace()
        elif not self.config.paths.workspace_path.exists():
            QMessageBox.warning(
                self,
                "Dossier introuvable",
                "Le dossier de travail n'existe plus. Veuillez en sélectionner un nouveau."
            )
            self._select_workspace()

    def _select_workspace(self):
        """Ouvre un dialogue pour choisir le dossier de travail."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de travail",
            str(Path.home())
        )

        if folder:
            self.config.set_workspace(Path(folder))
            self.workspace_label.setText(str(self.config.paths.workspace_path))
            self._refresh_workspace_view()
        elif not self.config.paths.workspace_path:
            QMessageBox.critical(
                self,
                "Configuration requise",
                "L'application nécessite un dossier de travail."
            )
            self.close()

    def _refresh_workspace_view(self):
        """Actualise l'arborescence des affaires."""
        if self.config.paths.workspace_path and self.cases_tree:
            self.cases_tree.setRootIndex(
                self.cases_model.index(str(self.config.paths.workspace_path))
            )
            self.statusBar().showMessage("Dossier de travail chargé")

    def _disable_photo_buttons(self):
        """Désactive tous les boutons photo."""
        for btn in [self.btn_photo_ferme, self.btn_photo_content,
                    self.btn_photo_objet, self.btn_photo_recond]:
            btn.setEnabled(False)

    def _load_scelles(self, case_path: Path):
        """
        Charge la liste des scellés pour une affaire donnée.
        Affiche uniquement les scellés sans leurs objets d'essai.

        Args:
            case_path: Chemin du dossier de l'affaire
        """
        logger.debug(f"Chargement des scellés depuis: {case_path}")

        self.scelles_model.clear()
        self.scelles_model.setHorizontalHeaderLabels(['Scellés'])

        # Vérifie que le dossier existe
        if not case_path.exists():
            logger.error(f"Le dossier {case_path} n'existe pas")
            return

        # Parcourt les dossiers de scellés
        for scelle_path in case_path.iterdir():
            if scelle_path.is_dir():
                logger.debug(f"Dossier trouvé: {scelle_path.name}")
                # Crée uniquement l'item du scellé
                scelle_item = QStandardItem(scelle_path.name)
                scelle_item.setData(str(scelle_path))
                self.scelles_model.appendRow(scelle_item)
                logger.debug(f"Scellé ajouté au modèle: {scelle_path.name}")


    def get_next_photo_number(self, scelle_path: Path, prefix: str) -> int:
        """Détermine le prochain numéro pour une photo."""
        max_num = 0
        pattern = f"{prefix}_*.jpg"

        for photo in scelle_path.glob(pattern):
            try:
                num = int(photo.stem.split('_')[-1])
                max_num = max(max_num, num)
            except (ValueError, IndexError):
                continue

        return max_num + 1


    def _update_workspace_label(self):
        """Met à jour l'affichage du chemin du dossier de travail."""
        if self.config.paths.workspace_path:
            self.workspace_label.setText(str(self.config.paths.workspace_path))

    def _on_case_selected(self, index: QModelIndex):
        """
        Gère la sélection d'une affaire.
        Réinitialise l'interface pour commencer proprement avec la nouvelle affaire.
        """
        path = Path(self.cases_model.filePath(index))
        if path.is_dir():
            # Réinitialise l'état
            self.current_case_path = path
            self.current_scelle = None  # Réinitialise le scellé sélectionné
            self.current_object = None  # Réinitialise l'objet sélectionné

            # Active le bouton d'explorateur
            self.case_explorer_btn.setEnabled(True)

            # Réinitialise les gestionnaires
            self.scelle_manager = Scelle(path)
            self.objet_manager = None  # Réinitialise le gestionnaire d'objets

            # Nettoie l'interface
            self.objects_list.clear()  # Vide la liste des objets


            # Met à jour les autres éléments de l'interface
            self._load_scelles(path)
            self._disable_photo_buttons()
            self.add_object_btn.setEnabled(False)  # Désactive le bouton d'ajout d'objet

            # Mise à jour de la barre de statut
            self.statusBar().showMessage(f"Affaire sélectionnée : {path.name}")
            logger.info(f"Changement d'affaire : {path.name}")

    def _update_photo_buttons(self):
        """
        Met à jour l'état des boutons photo selon le contexte actuel.
        Suit une logique progressive :
        1. Le bouton appareil photo ne dépend que de la connexion Android
        2. Les boutons de scellé nécessitent connexion + scellé sélectionné
        3. Le bouton d'objet nécessite connexion + scellé + objet sélectionné
        """
        # Vérifie d'abord la connexion Android
        android_connected = self.adb_manager.is_connected()

        # Le bouton d'appareil photo ne dépend que de la connexion
        self.btn_open_camera.setEnabled(android_connected)

        # Pour les boutons de scellé, il faut la connexion ET un scellé sélectionné
        scelle_buttons_enabled = android_connected and self.current_scelle is not None
        self.btn_photo_ferme.setEnabled(scelle_buttons_enabled)
        self.btn_photo_content.setEnabled(scelle_buttons_enabled)
        self.btn_photo_recond.setEnabled(scelle_buttons_enabled)

        # Pour le bouton d'objet, il faut la connexion ET un objet sélectionné
        self.btn_photo_objet.setEnabled(
            android_connected and
            self.current_scelle is not None and
            self.current_object is not None
        )

    def _take_photo(self, photo_type: str):
        """
        Prend une photo avec popup d'état simple.

        Args:
            photo_type: Type de photo ('ferme', 'contenu', 'objet', 'recond')
        """
        if not self.adb_manager.is_connected() or not self.current_scelle:
            return

        try:
            # Détermine le préfixe selon le type
            prefix_map = {
                'ferme': 'Ferme',
                'contenu': 'Contenu',
                'objet': self.current_object,
                'recond': 'Reconditionne'
            }

            # Vérifie que l'objet est sélectionné pour les photos d'objet
            if photo_type == 'objet' and not self.current_object:
                logger.error("Aucun objet sélectionné")
                self.statusBar().showMessage("Aucun objet sélectionné")
                return

            prefix = prefix_map[photo_type]

            # Trouve le prochain numéro disponible
            max_num = 0
            pattern = f"*{prefix}_*.jpg"
            for photo in self.current_scelle.glob(pattern):
                try:
                    num = int(photo.stem.split('_')[-1])
                    max_num = max(max_num, num)
                except (ValueError, IndexError):
                    continue

            next_num = max_num + 1

            # Crée le nom de fichier
            scelle_name = self.current_scelle.name
            file_name = f"{scelle_name}_{prefix}_{next_num}.jpg"
            save_path = self.current_scelle / file_name

            # === DÉBUT DE L'OPÉRATION AVEC POPUP ===
            # Désactive les boutons photo pour éviter les clics multiples
            for btn in self.photo_buttons.values():
                btn.setEnabled(False)
            self.btn_open_camera.setEnabled(False)

            # Crée et affiche la popup modale
            popup = OperationPopup(self)
            popup.show()

            # Fonction de callback pour les messages d'état
            def update_status(message):
                popup.update_message(message)
                # Force le traitement des événements Qt pour mettre à jour l'interface
                QApplication.processEvents()

            # Prend la photo avec suivi d'état
            success = self.adb_manager.take_photo(save_path, update_status)

            # Ferme la popup
            popup.close_popup()

            if success:
                # Met à jour la liste appropriée selon le type de photo
                if photo_type == 'objet':
                    photos = []
                    for photo in self.current_scelle.glob(
                            f"*_{self.current_object}_*.jpg"):
                        photos.append(photo.name)
                    self.object_photos.update_photos(photos)
                else:
                    self._update_scelle_photos()

                # Message de succès adapté
                self.statusBar().showMessage(f"Photo(s) sauvegardée(s) pour {prefix}")
                # Efface le message après 3 secondes
                QTimer.singleShot(3000, lambda: self.statusBar().showMessage(""))
            else:
                QMessageBox.warning(self, "Échec de la photo",
                                    "La photo n'a pas pu être prise ou transférée.\n\n"
                                    "Solutions :\n"
                                    "• Vérifiez que l'appareil photo fonctionne\n"
                                    "• Prenez une photo manuellement puis réessayez\n"
                                    "• Vérifiez la connexion de l'appareil")


        except subprocess.TimeoutExpired:

            title, message = UserFriendlyErrorHandler.handle_adb_error(

                Exception("timeout"), "la prise de photo"

            )

            QMessageBox.warning(self, title, message)


        except Exception as e:

            title, message = UserFriendlyErrorHandler.handle_adb_error(e,"la prise de photo")

            QMessageBox.warning(self, title, message)

        finally:
            # Réactive toujours les boutons à la fin
            if 'popup' in locals():
                popup.close_popup()
            self._update_photo_buttons()

    def _start_photo_operation(self, photo_type: str):
        """Démarre l'indication visuelle d'une opération photo."""
        # Change le curseur en sablier
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        # Désactive tous les boutons photo
        for btn in self.photo_buttons.values():
            btn.setEnabled(False)
        self.btn_open_camera.setEnabled(False)

        # Message dans la barre d'état
        type_names = {
            'ferme': 'scellé fermé',
            'contenu': 'contenu',
            'objet': 'objet d\'essai',
            'recond': 'reconditionnement'
        }
        type_name = type_names.get(photo_type, photo_type)
        self.statusBar().showMessage(f"Prise de photo {type_name}...")

    def _end_photo_operation(self, success: bool, message: str):
        """Termine l'indication visuelle d'une opération photo."""
        # Restaure le curseur normal
        QApplication.restoreOverrideCursor()

        # Réactive les boutons selon l'état de connexion
        self._update_photo_buttons()

        # Message de résultat
        self.statusBar().showMessage(message)

        # Si succès, efface le message après 3 secondes
        if success:
            QTimer.singleShot(3000, lambda: self.statusBar().showMessage(""))

    def _start_connection_operation(self):
        """Démarre l'indication visuelle d'une opération de connexion."""
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        # Le widget ADB gère déjà la désactivation de ses boutons

    def _end_connection_operation(self):
        """Termine l'indication visuelle d'une opération de connexion."""
        QApplication.restoreOverrideCursor()

    def _open_explorer(self, path: Path):
        """Ouvre l'explorateur Windows au chemin spécifié."""
        try:
            if not path.exists():
                logger.warning(f"Le chemin n'existe pas: {path}")
                return

            # Utilise la commande explorer de Windows
            import os
            os.startfile(str(path))
            logger.info(f"Explorateur ouvert sur: {path}")
        except Exception as e:
            logger.error(f"Erreur lors de l'ouverture de l'explorateur: {e}")
            self.statusBar().showMessage("Erreur lors de l'ouverture de l'explorateur")