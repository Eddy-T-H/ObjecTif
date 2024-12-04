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
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, List
from src.config import AppConfig

from .dialogs.create_affaire_dialog import CreateAffaireDialog
from .dialogs.create_scelle_dialog import CreateScelleDialog
from .widgets.adb_status import ADBStatusWidget
from .widgets.log_viewer import ColoredLogViewer, QtHandler

from .widgets.photo_viewer import PhotoViewer
from .widgets.stream_window import StreamWindow
from ..core.device import ADBManager
from ..core.evidence.base import EvidenceItem
from ..core.evidence.naming import PhotoType
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
        self.log_buffer = log_buffer  # Stocke le buffer

        # Créer une seule instance d'ADBManager qui sera partagée
        self.adb_manager = ADBManager()

        # Gestionnaires de preuves
        self.scelle_manager: Optional[Scelle] = None
        self.objet_manager: Optional[ObjetEssai] = None

        # État actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle: Optional[EvidenceItem] = None
        self.current_object: Optional[str] = None

        # Initialisation des composants de l'interface
        self.stream_window = None  # Sera initialisé dans _setup_stream_dock
        self.stream_dock = None    # Sera initialisé dans _initialize_ui

        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setMinimumSize(1024, 768)
        # Initialisation de l'interface
        self._initialize_ui()
        self._check_workspace()
        self._update_workspace_label()

        if self.config.paths.workspace_path:
            self._refresh_workspace_view()

        self.photo_viewer.loading_finished.connect(self._on_photos_loaded)

        # Connecte le signal de changement de connexion
        self.adb_status.connection_changed.connect(self._update_photo_buttons)

    def _initialize_ui(self):
        """Initialise l'interface utilisateur principale."""
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # Zone principale (haut)
        upper_area = self._setup_upper_area()

        # Zone inférieure (bas)
        lower_area = self._setup_lower_area()

        # Splitter principal vertical
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.addWidget(upper_area)
        main_splitter.addWidget(lower_area)
        main_splitter.setStretchFactor(0, 4)  # Zone haute plus grande
        main_splitter.setStretchFactor(1, 1)  # Zone basse plus petite

        main_layout.addWidget(main_splitter)

        # Connection aux signaux d'erreur de streaming
        self.adb_status.stream_error.connect(
            lambda msg: self.statusBar().showMessage(f"Erreur de streaming : {msg}")
        )

    def _handle_stream_error(self, error_msg: str):
        """Affiche les erreurs de streaming dans la barre d'état."""
        self.statusBar().showMessage(f"Erreur de streaming : {error_msg}")

    def _handle_preview_toggle(self, enabled: bool):
        """Gère l'activation/désactivation du streaming."""
        logger.debug(f"Handling preview toggle: {enabled}")
        try:
            if enabled:
                success = self.stream_window.start_stream()
                if not success:
                    # En cas d'échec, réinitialiser le bouton
                    self.adb_status.preview_active = False
                    self.adb_status.preview_btn.setText("Prévisualisation")
            else:
                self.stream_window.stop_stream()
        except Exception as e:
            logger.error(f"Erreur lors de la gestion du streaming: {e}")
            # Réinitialiser le bouton en cas d'erreur
            self.adb_status.preview_active = False
            self.adb_status.preview_btn.setText("Prévisualisation")

    def _setup_upper_area(self) -> QWidget:
        """Configure la zone supérieure de l'interface."""
        upper_widget = QWidget()
        upper_layout = QHBoxLayout(upper_widget)
        upper_layout.setContentsMargins(0, 0, 0, 0)
        upper_layout.setSpacing(8)

        # Panneau gauche (arborescence)
        left_panel = self._setup_left_panel()
        left_panel.setMinimumWidth(280)
        left_panel.setMaximumWidth(400)

        # Zone centrale (photos)
        center_panel = self._setup_photos_panel()

        # Panneau droit (contrôles)
        right_panel = self._setup_right_panel()
        right_panel.setMinimumWidth(280)
        right_panel.setMaximumWidth(400)

        # Ajout des panneaux
        upper_layout.addWidget(left_panel)
        upper_layout.addWidget(center_panel, stretch=1)
        upper_layout.addWidget(right_panel)

        return upper_widget

    def _setup_right_panel(self) -> QWidget:
        """Configure le panneau droit avec les contrôles ADB et les boutons photo."""
        right_panel = QWidget()
        layout = QVBoxLayout(right_panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

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

    def _setup_photos_panel(self) -> QWidget:
        """Configure le panneau central des photos."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        self.photo_viewer = PhotoViewer()
        self.photo_viewer.loading_finished.connect(self._on_photos_loaded)
        layout.addWidget(self.photo_viewer)

        return panel

    def _setup_stream_dock(self) -> QDockWidget:
        """Configure le dock pour le streaming Android."""
        self.stream_window = StreamWindow(adb_manager=self.adb_manager, parent=self)
        stream_dock = QDockWidget("Android Stream", self)
        stream_dock.setWidget(self.stream_window)
        stream_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetFloatable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        return stream_dock


    def _setup_log_viewer(self) -> QPlainTextEdit:
        """Configure le visualiseur de logs."""
        log_viewer = ColoredLogViewer()
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
        panel  = QWidget()
        layout  = QVBoxLayout(panel)

        # Section du dossier de travail (inchangée)
        workspace_widget = QWidget()
        workspace_layout = QHBoxLayout(workspace_widget)
        self.workspace_label = QLabel("Non configuré")
        change_workspace_btn = QPushButton("Changer")
        change_workspace_btn.clicked.connect(self._select_workspace)

        workspace_layout.addWidget(QLabel("Dossier de travail :"))
        workspace_layout.addWidget(self.workspace_label, stretch=1)
        workspace_layout.addWidget(change_workspace_btn)
        layout.addWidget(workspace_widget)


        # Splitter pour les trois zones
        splitter = QSplitter(Qt.Orientation.Vertical)

        # Zone des affaires
        cases_group = self._setup_cases_group()
        splitter.addWidget(cases_group)

        # Zone des scellés
        scelles_group = self._setup_scelles_group()
        splitter.addWidget(scelles_group)

        # Zone des objets
        objects_group = self._setup_objects_group()
        splitter.addWidget(objects_group)


        splitter.setSizes([300, 200, 200])
        layout.addWidget(splitter)


        # Définition des tailles relatives initiales
        splitter.setSizes([300, 200, 200])
        layout.addWidget(splitter)

        return panel

    def _setup_cases_group(self) -> QGroupBox:
        """Configure la zone des affaires."""
        group = QGroupBox("Dossiers")
        layout = QVBoxLayout(group)

        add_btn = QPushButton("Nouveau Dossier")
        add_btn.clicked.connect(self._create_new_affaire)
        layout.addWidget(add_btn)

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
        """Configure la zone des scellés."""
        group = QGroupBox("Scellés")
        layout = QVBoxLayout(group)

        add_btn = QPushButton("Ajouter un scellé (nom de dossier)")
        add_btn.clicked.connect(self._create_new_scelle)
        layout.addWidget(add_btn)

        self.scelles_tree = QTreeView()
        self.scelles_model = QStandardItemModel()
        self.scelles_model.setHorizontalHeaderLabels(['Scellés'])
        self.scelles_tree.setModel(self.scelles_model)
        self.scelles_tree.clicked.connect(self._on_scelle_selected)
        layout.addWidget(self.scelles_tree)

        return group

    def _setup_objects_group(self) -> QGroupBox:
        """Configure la zone des objets."""
        group = QGroupBox("Objets d'essai")
        layout = QVBoxLayout(group)

        self.add_object_btn = QPushButton("Ajouter un objet d'essai")
        self.add_object_btn.clicked.connect(self._add_new_object)
        self.add_object_btn.setEnabled(False)
        layout.addWidget(self.add_object_btn)

        self.objects_list = QTreeWidget()
        self.objects_list.setHeaderLabels(["Objets"])
        self.objects_list.itemClicked.connect(self._on_object_selected)
        layout.addWidget(self.objects_list)

        return group

    def _create_new_affaire(self):
        """
        Ouvre le dialogue de création d'une nouvelle affaire et crée le dossier correspondant.
        Vérifie que le workspace est configuré avant de permettre la création.
        """
        if not self.config.paths.workspace_path:
            QMessageBox.warning(self, "Erreur",
                                "Veuillez d'abord configurer un dossier de travail.")
            return

        dialog = CreateAffaireDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            numero = dialog.get_numero()
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
                    QMessageBox.warning(self, "Erreur",
                                        f"Un dossier portant le numéro {numero} existe déjà.")
                except Exception as e:
                    QMessageBox.critical(self, "Erreur",
                                         f"Erreur lors de la création du dossier : {str(e)}")

    def _create_new_scelle(self):
        """
        Crée un nouveau scellé dans l'affaire actuelle.
        Crée un dossier pour le scellé dans le répertoire de l'affaire.
        """
        if not self.scelle_manager:
            QMessageBox.warning(self, "Erreur",
                                "Veuillez d'abord sélectionner une affaire.")
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
                    raise FileExistsError(f"Le scellé {numero} existe déjà")

                # Crée le dossier
                scelle_path.mkdir(parents=True)

                # Force le rafraîchissement du modèle pour le dossier parent
                parent_path = str(self.current_case_path)
                self.cases_model.setRootPath("")  # Reset le chemin racine
                self.cases_model.setRootPath(
                str(self.config.paths.workspace_path))  # Conversion en str

                # Réexpand le dossier parent pour montrer le nouveau contenu
                parent_index = self.cases_model.index(parent_path)
                self.cases_tree.expand(parent_index)

                # Met à jour la liste des scellés
                self._load_scelles(self.current_case_path)

                # Met à jour la barre d'état
                self.statusBar().showMessage(f"Scellé {numero} créé")
                logger.info(f"Nouveau scellé créé : {numero}")


            except ValueError as e:
                logger.error(f"Erreur de validation lors de la création du scellé: {e}")
                QMessageBox.warning(self, "Erreur de validation", str(e))
            except FileExistsError as e:
                logger.error(f"Erreur: le scellé existe déjà: {e}")
                QMessageBox.warning(self, "Erreur", "Ce scellé existe déjà")
            except PermissionError as e:
                logger.error(
                f"Erreur de permissions lors de la création du dossier: {e}")
                QMessageBox.critical(self, "Erreur",
                                 "Impossible de créer le dossier (erreur de permissions)")
            except Exception as e:
                logger.error(f"Erreur inattendue lors de la création du scellé: {e}")
                QMessageBox.critical(self, "Erreur",
                                     f"Une erreur inattendue s'est produite: {str(e)}")

    @pyqtSlot(QModelIndex)
    def _on_scelle_selected(self, index):
        """Gère la sélection d'un scellé."""
        logger.debug("Sélection d'un scellé")

        # Réinitialise l'affichage
        self.photo_viewer.load_photos({'scelle_ferme': [], 'contenu': [],
                                       'objets': {}, 'reconditionnement': []})
        self.objects_list.clear()

        try:
            # Désactive l'interface pendant le chargement
            self.scelles_tree.setEnabled(False)

            item = self.scelles_model.itemFromIndex(index)
            if not item:
                return

            scelle_name = item.text()
            logger.debug(f"Scellé sélectionné: {scelle_name}")

            scelle = self.scelle_manager.get_item(scelle_name)
            if scelle:
                self.current_scelle = scelle.path
                self.objet_manager = ObjetEssai(scelle.path)

                # Charge et organise les photos
                photos_dict = self._organize_photos()

                # Met à jour l'interface
                self._update_photo_buttons()
                self._load_existing_objects()
                self.add_object_btn.setEnabled(True)
                self.photo_viewer.load_photos(photos_dict)

        except Exception as e:
            logger.error(f"Erreur lors de la sélection du scellé: {e}")
            QMessageBox.critical(self, "Erreur", str(e))
            self.scelles_tree.setEnabled(True)

    def _organize_photos(self) -> Dict[str, List[str]]:
        """Organise les photos par catégorie."""
        logger.debug("Organisation des photos")
        photos = {
            'scelle_ferme': [],
            'contenu': [],
            'objets': {},
            'reconditionnement': []
        }

        if not self.current_scelle:
            return photos

        try:
            for photo in self.scelle_manager.get_photos(
                    self.current_scelle.name):
                photo_path = str(photo.path)

                # Détermine la catégorie de la photo
                if photo.type.isalpha() and len(photo.type) == 1:
                    # Photo d'objet
                    if photo.type not in photos['objets']:
                        photos['objets'][photo.type] = []
                    photos['objets'][photo.type].append(photo_path)
                elif "Ferme" in photo.type:
                    photos['scelle_ferme'].append(photo_path)
                elif "Contenu" in photo.type:
                    photos['contenu'].append(photo_path)
                elif "Reconditionne" in photo.type:
                    photos['reconditionnement'].append(photo_path)

        except Exception as e:
            logger.error(f"Erreur lors de l'organisation des photos: {e}")

        return photos

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
        Active le bouton de photo d'objet.
        """
        logger.debug("Sélection d'un objet")

        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if object_id:
            self.current_object = object_id
            self._update_photo_buttons()
            logger.debug(f"Objet sélectionné: {object_id}")
            self.statusBar().showMessage(f"Objet {object_id} sélectionné")

    def _on_photos_loaded(self):
        """Appelé quand le chargement des photos est terminé."""
        logger.debug("Chargement des photos terminé")
        self.scelles_tree.setEnabled(True)

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

            # Réinitialise les gestionnaires
            self.scelle_manager = Scelle(path)
            self.objet_manager = None  # Réinitialise le gestionnaire d'objets

            # Nettoie l'interface
            self.objects_list.clear()  # Vide la liste des objets
            self.photo_viewer.load_photos({  # Réinitialise l'affichage des photos
                'scelle_ferme': [],
                'contenu': [],
                'objets': {},
                'reconditionnement': []
            })

            # Met à jour les autres éléments de l'interface
            self._load_scelles(path)
            self._disable_photo_buttons()
            self.add_object_btn.setEnabled(False)  # Désactive le bouton d'ajout d'objet

            # Mise à jour de la barre de statut
            self.statusBar().showMessage(f"Affaire sélectionnée : {path.name}")
            logger.info(f"Changement d'affaire : {path.name}")

    # def _on_case_selected(self, index: QModelIndex):
    #     """Gère la sélection d'une affaire."""
    #     path = Path(self.cases_model.filePath(index))
    #     if path.is_dir():
    #         self.current_case_path = path
    #         # Initialise le gestionnaire de scellés pour cette affaire
    #         self.scelle_manager = Scelle(path)
    #         self._load_scelles(path)
    #         self._disable_photo_buttons()
    #         self.statusBar().showMessage(f"Affaire sélectionnée : {path.name}")

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
        Prend une photo avec l'appareil connecté.

        Args:
            photo_type: Type de photo à prendre
        """
        if not self.adb_manager.is_connected():
            return

        try:
            # Configure le chemin de sauvegarde selon le type
            if photo_type == "objet" and not self.current_object:
                return

            # Détermine le nom de fichier
            next_num = self.get_next_photo_number(
                self.current_scelle,
                photo_type if photo_type != "objet" else self.current_object
            )

            save_path = (
                    self.current_scelle /
                    f"{photo_type}_{next_num}.jpg"
            )

            # Prend la photo
            if self.adb_status.adb_manager.take_photo(save_path):
                self.statusBar().showMessage(f"Photo sauvegardée: {save_path.name}")
                # Rafraîchit l'affichage des photos
                self._refresh_photos()
            else:
                self.statusBar().showMessage("Erreur lors de la prise de photo")

        except Exception as e:
            logger.error(f"Erreur lors de la prise de photo: {e}")
            self.statusBar().showMessage("Erreur lors de la prise de photo")