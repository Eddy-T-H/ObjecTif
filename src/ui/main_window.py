# ui/main_window.py
"""
Interface principale avec gestion correcte de l'initialisation des composants.
"""

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTreeView, QLabel, QPushButton, QFileDialog,
    QStatusBar, QMessageBox, QSplitter, QGroupBox, QTreeWidget, QTreeWidgetItem,
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QTabWidget
)
from PyQt6.QtCore import Qt, QModelIndex, pyqtSlot
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem
from pathlib import Path
from loguru import logger
from typing import Optional, Dict, List
from src.config import AppConfig

from .dialogs.create_affaire_dialog import CreateAffaireDialog
from .dialogs.create_scelle_dialog import CreateScelleDialog
from .widgets.photo_viewer import PhotoViewer
from ..core.evidence.base import EvidenceItem
from ..core.evidence.naming import PhotoType
from ..core.evidence.objet import ObjetEssai
from ..core.evidence.scelle import Scelle


class MainWindow(QMainWindow):

    """
    Fenêtre principale de l'application.
    Gère l'interface utilisateur et coordonne les différentes fonctionnalités.
    """

    def __init__(self, config: AppConfig):
        """
        Initialise la fenêtre principale.

        Args:
            config: Configuration de l'application
        """
        super().__init__()
        self.config = config

        # Gestionnaires de preuves
        self.scelle_manager: Optional[Scelle] = None
        self.objet_manager: Optional[ObjetEssai] = None

        # État actuel
        self.current_case_path: Optional[Path] = None
        self.current_scelle: Optional[EvidenceItem] = None
        self.current_object: Optional[str] = None

        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setMinimumSize(1024, 768)

        self._setup_ui()
        self._check_workspace()
        self._update_workspace_label()

        if self.config.paths.workspace_path:
            self._refresh_workspace_view()

        self.photo_viewer.loading_finished.connect(self._on_photos_loaded)

    def _setup_ui(self):
        """Configure l'interface utilisateur complète avec tous ses composants."""
        # Widget central avec disposition horizontale pour diviser gauche/droite
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # --- PANNEAU GAUCHE ---
        left_panel = self._setup_left_panel()
        main_layout.addWidget(left_panel, stretch=1)  # stretch=1 pour la proportion

        # --- PANNEAU DROIT ---
        right_panel = self._setup_right_panel()
        main_layout.addWidget(right_panel, stretch=2)  # stretch=2 pour donner plus d'espace

        # Création de la barre d'état
        self._create_status_bar()

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

    def _setup_right_panel(self):
        """Configure le panneau droit avec la prévisualisation et les actions."""
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Création des onglets
        preview_tabs = QTabWidget()

        # Onglet Preview (zone noire actuelle)
        preview_widget = QWidget()
        preview_widget.setMinimumSize(400, 300)
        preview_widget.setStyleSheet("background-color: black;")
        preview_tabs.addTab(preview_widget, "Preview")

        # Onglet Photos
        self.photo_viewer = PhotoViewer()
        preview_tabs.addTab(self.photo_viewer, "Photos")

        right_layout.addWidget(preview_tabs)

        # Groupe des boutons d'action
        actions_group = QGroupBox("Actions Photos")
        actions_layout = QVBoxLayout()

        # Création des boutons
        self.btn_photo_ferme = QPushButton("Photo Scellé Fermé")
        self.btn_photo_content = QPushButton("Photo Contenu")
        self.btn_photo_objet = QPushButton("Photo Objet d'Essai")
        self.btn_photo_recond = QPushButton("Photo Reconditionnement")

        # Configuration des boutons
        for btn in [self.btn_photo_ferme, self.btn_photo_content,
                    self.btn_photo_objet, self.btn_photo_recond]:
            btn.setEnabled(False)  # Désactivés par défaut
            actions_layout.addWidget(btn)
            # TODO: Connecter les boutons à leurs actions respectives

        actions_group.setLayout(actions_layout)
        right_layout.addWidget(actions_group)

        return right_panel

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
                self._enable_photo_buttons()
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
        Trouve automatiquement la prochaine lettre disponible.
        """
        logger.debug("Ajout d'un nouvel objet")

        if not self.objet_manager or not self.current_scelle:
            logger.warning("Pas de scellé sélectionné")
            return

        try:
            # Trouve la prochaine lettre disponible
            existing = self.objet_manager.get_existing_objects()
            if not existing:
                next_letter = 'A'
            else:
                last_letter = existing[-1]
                if ord(last_letter) >= ord('Z'):
                    raise ValueError("Plus de lettres disponibles")
                next_letter = chr(ord(last_letter) + 1)

            logger.debug(f"Nouvelle lettre: {next_letter}")

            # Crée le nouvel objet
            item = self.objet_manager.create_item(
                item_id=next_letter,
                name=f"Objet {next_letter}"
            )

            # Met à jour l'interface
            tree_item = QTreeWidgetItem([f"{self.current_scelle.name}_{next_letter}"])
            tree_item.setData(0, Qt.ItemDataRole.UserRole, next_letter)
            self.objects_list.addTopLevelItem(tree_item)

            # Sélectionne le nouvel objet
            self.objects_list.setCurrentItem(tree_item)
            self._on_object_selected(tree_item)

            logger.info(f"Objet {next_letter} créé")

        except Exception as e:
            logger.error(f"Erreur lors de la création de l'objet: {e}")
            QMessageBox.warning(self, "Erreur", str(e))

    def _enable_photo_buttons(self):
        """Active les boutons photo selon le contexte."""
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
            # Active tous les boutons photo, y compris celui des objets
            self._enable_photo_buttons()
            self.btn_photo_objet.setEnabled(True)
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

    def _enable_scelle_photo_buttons(self):
        """
        Active les boutons de photos du scellé.
        Les photos du scellé sont disponibles dès qu'un scellé est sélectionné.
        """
        self.btn_photo_ferme.setEnabled(True)
        self.btn_photo_content.setEnabled(True)
        self.btn_photo_recond.setEnabled(True)
        self.btn_photo_objet.setEnabled(False)  # Désactivé jusqu'à sélection d'un objet

    def _enable_object_photo_buttons(self):
        """
        Active les boutons quand un objet est sélectionné.
        Les photos du scellé parent restent disponibles.
        """
        # On garde les boutons du scellé actifs
        self.btn_photo_ferme.setEnabled(True)
        self.btn_photo_content.setEnabled(True)
        self.btn_photo_recond.setEnabled(True)
        # On active en plus la photo d'objet
        self.btn_photo_objet.setEnabled(True)

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
        """Gère la sélection d'une affaire."""
        path = Path(self.cases_model.filePath(index))
        if path.is_dir():
            self.current_case_path = path
            # Initialise le gestionnaire de scellés pour cette affaire
            self.scelle_manager = Scelle(path)
            self._load_scelles(path)
            self._disable_photo_buttons()
            self.statusBar().showMessage(f"Affaire sélectionnée : {path.name}")

    def _create_status_bar(self):
        """Crée la barre d'état avec les informations de l'application."""
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
        status_bar.showMessage("Prêt")

        status_bar.addPermanentWidget(
            QLabel(f"Version: {self.config.app_version}")
        )
        if self.config.debug_mode:
            status_bar.addPermanentWidget(QLabel("Mode Debug"))
