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
from typing import Optional
from src.config import AppConfig
from src.core.test_item_manager import TestObjectsManager

from .dialogs.create_affaire_dialog import CreateAffaireDialog
from .dialogs.create_scelle_dialog import CreateScelleDialog
from .widgets.photo_viewer import PhotoViewer



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

        # Configuration de base de la fenêtre
        self.setWindowTitle(f"{config.app_name} v{config.app_version}")
        self.setMinimumSize(1024, 768)

        # Initialisation des attributs qui seront utilisés dans l'interface
        self.cases_tree = None  # Arborescence des affaires
        self.cases_model = None  # Modèle de données des affaires
        self.scelles_tree = None  # Arborescence des scellés
        self.scelles_model = None  # Modèle de données des scellés
        self.workspace_label = None  # Étiquette du dossier de travail
        self.current_scelle = None  # Scellé actuellement sélectionné

        # Configuration de l'interface et vérification du workspace
        self._setup_ui()
        self._check_workspace()
        # Met à jour l'affichage du workspace
        self._update_workspace_label()

        # Si un workspace existe, on rafraîchit la vue
        if self.config.paths.workspace_path:
            self._refresh_workspace_view()

        # Connexion du signal
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
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Section du dossier de travail (inchangée)
        workspace_widget = QWidget()
        workspace_layout = QHBoxLayout(workspace_widget)
        self.workspace_label = QLabel("Non configuré")
        change_workspace_btn = QPushButton("Changer")
        change_workspace_btn.clicked.connect(self._select_workspace)

        workspace_layout.addWidget(QLabel("Dossier de travail :"))
        workspace_layout.addWidget(self.workspace_label, stretch=1)
        workspace_layout.addWidget(change_workspace_btn)
        left_layout.addWidget(workspace_widget)

        # Création d'un double splitter pour les trois zones
        main_splitter = QSplitter(Qt.Orientation.Vertical)

        # Zone des affaires
        cases_group = QGroupBox("Dossiers")
        cases_layout = QVBoxLayout()


        # Bouton pour ajouter une affaire
        add_affaire_btn = QPushButton("Nouveau Dossier")
        add_affaire_btn.clicked.connect(self._create_new_affaire)  # Connexion au bon slot
        cases_layout.addWidget(add_affaire_btn)

        self.cases_tree = QTreeView()
        self.cases_model = QFileSystemModel()
        self.cases_model.setRootPath("")
        self.cases_tree.setModel(self.cases_model)
        for i in range(1, self.cases_model.columnCount()):
            self.cases_tree.hideColumn(i)
        self.cases_tree.clicked.connect(self._on_case_selected)
        cases_layout.addWidget(self.cases_tree)
        cases_group.setLayout(cases_layout)

        # Zone des scellés avec bouton d'ajout
        scelles_group = QGroupBox("Scellés")
        scelles_layout = QVBoxLayout()

        # Bouton pour ajouter un scellé
        add_scelle_btn = QPushButton("Nouveau Scellé")
        add_scelle_btn.clicked.connect(self._create_new_scelle)
        scelles_layout.addWidget(add_scelle_btn)

        # Liste des scellés
        self.scelles_tree = QTreeView()
        self.scelles_model = QStandardItemModel()
        self.scelles_model.setHorizontalHeaderLabels(['Scellés'])
        self.scelles_tree.setModel(self.scelles_model)
        self.scelles_tree.clicked.connect(self._on_scelle_selected)
        scelles_layout.addWidget(self.scelles_tree)

        scelles_group.setLayout(scelles_layout)

        # Zone des objets d'essai
        objects_group = QGroupBox("Objets d'essai")
        objects_layout = QVBoxLayout()

        # Bouton pour ajouter un objet
        self.add_object_btn = QPushButton("Ajouter un objet d'essai")
        self.add_object_btn.clicked.connect(self._add_new_object)
        self.add_object_btn.setEnabled(False)  # Désactivé par défaut
        objects_layout.addWidget(self.add_object_btn)

        # Liste des objets
        self.objects_list = QTreeWidget()
        self.objects_list.setHeaderLabels(["Objets"])
        self.objects_list.itemClicked.connect(self._on_object_selected)
        objects_layout.addWidget(self.objects_list)


        objects_group.setLayout(objects_layout)

        # Ajout des trois zones au splitter
        main_splitter.addWidget(cases_group)
        main_splitter.addWidget(scelles_group)
        main_splitter.addWidget(objects_group)

        # Définition des tailles relatives initiales
        main_splitter.setSizes([300, 200, 200])

        left_layout.addWidget(main_splitter)
        return left_panel

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
        """Ouvre le dialogue de création d'un nouveau scellé."""
        if not hasattr(self, 'current_case_path'):
            QMessageBox.warning(self, "Erreur",
                                "Veuillez d'abord sélectionner une affaire.")
            return

        dialog = CreateScelleDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            numero = dialog.get_numero()
            if numero:
                try:
                    # Crée le dossier du scellé
                    scelle_path = self.current_case_path / f"{numero}"
                    scelle_path.mkdir(exist_ok=False)

                    # Initialise le gestionnaire d'objets pour ce scellé
                    objects_manager = TestObjectsManager(scelle_path)

                    # Rafraîchit la liste des scellés
                    self._load_scelles(self.current_case_path)

                    self.statusBar().showMessage(f"Scellé {numero} créé")
                    logger.info(f"Nouveau scellé créé : {numero}")
                except FileExistsError:
                    QMessageBox.warning(self, "Erreur",
                                        "Ce numéro de scellé existe déjà.")

    @pyqtSlot(QModelIndex)
    def _on_scelle_selected(self, index: QModelIndex):
        """
        Gère la sélection d'un scellé.
        Met à jour la liste des objets d'essai et active les boutons appropriés.
        """
        # Vérifie si un chargement est déjà en cours
        if hasattr(self.photo_viewer,
                   'loader_thread') and self.photo_viewer.loader_thread:
            return  # Ignore complètement la sélection si un chargement est en cours

        # Désactive immédiatement l'arbre des scellés
        self.scelles_tree.setEnabled(False)

        item = self.scelles_model.itemFromIndex(index)
        if not item:
            return

        # Récupère le chemin du scellé
        path_data = item.data()
        if not path_data:
            return

        scelle_path = Path(path_data)
        self.current_scelle = scelle_path

        # Met à jour la barre de statut
        self.statusBar().showMessage(f"Scellé sélectionné : {item.text()}")

        # Active les boutons de photo pour le scellé
        self._enable_scelle_photo_buttons()

        # Active le bouton d'ajout d'objet
        self.add_object_btn.setEnabled(True)

        # Charge les objets existants
        self._load_existing_objects(scelle_path)

        # On charge les photos existantes du scellé et de ses objets
        photos = self._organize_photos(scelle_path)
        self.photo_viewer.load_photos(photos)

    def _load_existing_objects(self, scelle_path: Path):
        """Charge la liste des objets depuis le fichier de configuration."""
        self.objects_list.clear()

        # Utilise le gestionnaire d'objets pour obtenir la liste
        objects_manager = TestObjectsManager(scelle_path)
        scelle_num = scelle_path.name  # Récupère le nom du scellé depuis le chemin

        # Ajoute chaque objet à la liste
        for letter in objects_manager.get_object_letters():
            item = QTreeWidgetItem([f"{scelle_num}_{letter}"])
            item.setData(0, Qt.ItemDataRole.UserRole, letter)
            self.objects_list.addTopLevelItem(item)

    def _add_new_object(self):
        """Ajoute un nouvel objet via le gestionnaire."""
        if not self.current_scelle:
            return

        try:
            # Utilise le gestionnaire pour ajouter un objet
            objects_manager = TestObjectsManager(self.current_scelle)
            new_letter = objects_manager.add_object()

            # Ajoute le nouvel objet à la liste avec le format NUM_SCELLE_LETTRE
            scelle_num = self.current_scelle.name
            new_item = QTreeWidgetItem([f"{scelle_num}_{new_letter}"])
            new_item.setData(0, Qt.ItemDataRole.UserRole, new_letter)
            self.objects_list.addTopLevelItem(new_item)

            # Sélectionne le nouvel objet
            self.objects_list.setCurrentItem(new_item)
            self._on_object_selected(new_item, 0)

            logger.info(
                f"Nouvel objet {new_letter} créé pour le scellé {self.current_scelle.name}")
        except ValueError as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _on_object_selected(self, item, column=0):
        """
        Gère la sélection d'un objet d'essai dans la liste.
        """
        object_letter = item.data(0, Qt.ItemDataRole.UserRole)
        if object_letter:
            self.statusBar().showMessage(f"Objet {object_letter} sélectionné")
            self._enable_object_photo_buttons()

            # Stocke l'objet actuellement sélectionné
            self.current_object = object_letter

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
        self.scelles_model.clear()
        self.scelles_model.setHorizontalHeaderLabels(['Scellés'])

        # Parcourt les dossiers de scellés
        for scelle_path in case_path.iterdir():
            if scelle_path.is_dir():
                # Crée uniquement l'item du scellé
                scelle_item = QStandardItem(scelle_path.name)
                scelle_item.setData(str(scelle_path))
                self.scelles_model.appendRow(scelle_item)


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

    def _check_workspace(self):
        """Vérifie l'existence du dossier de travail ou demande sa sélection."""
        if not self.config.paths.workspace_path:
            QMessageBox.information(
                self,
                "Configuration initiale",
                "Veuillez sélectionner le dossier contenant vos dossiers en cours."
            )
            self._select_workspace()
        elif not self.config.paths.workspace_path.exists():
            QMessageBox.warning(
                self,
                "Dossier introuvable",
                "Le dossier de travail configuré n'existe plus. Veuillez en sélectionner un nouveau."
            )
            self._select_workspace()

    def _select_workspace(self):
        """Ouvre un dialogue pour sélectionner le dossier de travail."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Sélectionner le dossier de travail",
            str(Path.home())
        )

        if folder:
            self.config.set_workspace(Path(folder))
            self._update_workspace_label()
            self._refresh_workspace_view()
        elif not self.config.paths.workspace_path:
            QMessageBox.critical(
                self,
                "Configuration requise",
                "L'application ne peut pas fonctionner sans dossier de travail."
            )
            self.close()

    def _update_workspace_label(self):
        """Met à jour l'affichage du chemin du dossier de travail."""
        if self.config.paths.workspace_path:
            self.workspace_label.setText(str(self.config.paths.workspace_path))

    def _refresh_workspace_view(self):
        """Actualise la vue des affaires avec le contenu du dossier de travail."""
        if self.config.paths.workspace_path and self.cases_tree:
            self.cases_tree.setRootIndex(
                self.cases_model.index(str(self.config.paths.workspace_path))
            )
            self.statusBar().showMessage("Dossier de travail chargé")

    def _on_case_selected(self, index: QModelIndex):
        """Gère la sélection d'une affaire."""
        path = Path(self.cases_model.filePath(index))
        if path.is_dir():
            self.current_case_path = path
            self._load_scelles(path)
            # Désactive tous les boutons car aucun scellé n'est sélectionné
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

    def _organize_photos(self, scelle_path: Path) -> dict:
        """
        Organise les photos par catégorie.
        """
        photos = {
            'scelle_ferme': [],
            'contenu': [],
            'objets': {},  # Par lettre d'objet
            'reconditionnement': []
        }

        # Parcourt tous les fichiers jpg du dossier
        for photo in scelle_path.glob('*.jpg'):
            if '_Ferm' in photo.name:
                photos['scelle_ferme'].append(photo)
            elif 'Contenu' in photo.name:
                photos['contenu'].append(photo)
            elif '_Reconditionn' in photo.name:
                photos['reconditionnement'].append(photo)
            else:
                # Cherche les photos d'objets - vérifie toutes les parties
                parts = photo.stem.split('_')
                # Cherche une partie qui est une seule lettre
                for part in parts:
                    if len(part) == 1 and part.isalpha():
                        if part not in photos['objets']:
                            photos['objets'][part] = []
                        photos['objets'][part].append(photo)
                        break

        return photos

    def _on_photos_loaded(self):
        """Appelé quand le chargement des photos est terminé."""
        self.scelles_tree.setEnabled(True)