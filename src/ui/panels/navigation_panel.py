# src/ui/panels/navigation_panel.py
"""
Panel de navigation gauche - Gestion des affaires, scellés et objets.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QSplitter,
    QTreeView,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QFileDialog,
)
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem
from pathlib import Path
from loguru import logger
from typing import Optional

from src.config import AppConfig
from src.ui.theme.design_system import DesignTokens, ComponentFactory
from src.ui.dialogs.create_affaire_dialog import CreateAffaireDialog
from src.ui.dialogs.create_scelle_dialog import CreateScelleDialog
from src.ui.widgets.photo_list import PhotoListWidget
from src.core.device import ADBManager
from src.core.evidence.scelle import Scelle
from src.core.evidence.objet import ObjetEssai
from src.utils.error_handler import UserFriendlyErrorHandler


class NavigationPanel(QWidget):
    """Panel de navigation pour affaires, scellés et objets."""

    # Signaux émis vers la fenêtre principale
    case_selected = pyqtSignal(Path)
    scelle_selected = pyqtSignal(Path)
    object_selected = pyqtSignal(str)
    photo_deleted = pyqtSignal(str)

    def __init__(self, config: AppConfig, adb_manager: ADBManager, parent=None):
        super().__init__(parent)
        self.config = config
        self.adb_manager = adb_manager

        # État local
        self.scelle_manager: Optional[Scelle] = None
        self.objet_manager: Optional[ObjetEssai] = None
        self.current_case_path: Optional[Path] = None
        self.current_scelle_path: Optional[Path] = None

        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du panel de navigation."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            DesignTokens.Spacing.XS,
            DesignTokens.Spacing.XS,
            DesignTokens.Spacing.XS,
            DesignTokens.Spacing.XS,
        )
        layout.setSpacing(DesignTokens.Spacing.XS)

        # === SECTION WORKSPACE ===
        self._setup_workspace_section(layout)

        # === SPLITTER POUR LES TROIS ZONES ===
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)

        # Zone des affaires
        cases_group = self._setup_cases_section()
        cases_group.setMinimumHeight(100)
        splitter.addWidget(cases_group)

        # Zone des scellés
        scelles_group = self._setup_scelles_section()
        scelles_group.setMinimumHeight(100)
        splitter.addWidget(scelles_group)

        # Zone des objets
        objects_group = self._setup_objects_section()
        objects_group.setMinimumHeight(100)
        splitter.addWidget(objects_group)

        splitter.setSizes([200, 200, 200])
        layout.addWidget(splitter)

    def _setup_workspace_section(self, layout):
        """Configure la section de sélection du workspace."""
        workspace_widget = QWidget()
        workspace_layout = QHBoxLayout(workspace_widget)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(DesignTokens.Spacing.XS)

        # Label titre
        workspace_label_title = QLabel("Dossier de travail :")
        workspace_label_title.setStyleSheet(
            f"""
            QLabel {{
                font-weight: {DesignTokens.Typography.MEDIUM};
                color: {DesignTokens.Colors.TEXT_SECONDARY};
                font-size: {DesignTokens.Typography.CAPTION}px;
            }}
        """
        )

        # Label du chemin actuel
        self.workspace_label = QLabel("Non configuré")
        self.workspace_label.setStyleSheet(
            f"""
            QLabel {{
                color: {DesignTokens.Colors.TEXT_PRIMARY};
                font-size: {DesignTokens.Typography.CAPTION}px;
            }}
        """
        )

        # Bouton compact pour changer le workspace
        change_workspace_btn = ComponentFactory.create_compact_button("...")
        change_workspace_btn.setToolTip("Changer le dossier de travail")
        change_workspace_btn.clicked.connect(self._select_workspace)

        workspace_layout.addWidget(workspace_label_title)
        workspace_layout.addWidget(self.workspace_label, stretch=1)
        workspace_layout.addWidget(change_workspace_btn)

        layout.addWidget(workspace_widget)

    def _setup_cases_section(self):
        """Configure la section des affaires avec boutons navigation."""
        group = ComponentFactory.create_group_box("📁 Dossiers",
                                                  DesignTokens.Colors.PRIMARY)
        layout = QVBoxLayout(group)
        layout.setSpacing(DesignTokens.Spacing.XS)
        layout.setContentsMargins(
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.MD,
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.SM,
        )

        # Boutons d'action
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(DesignTokens.Spacing.XS)

        # Bouton principal pour créer → Navigation
        add_btn = ComponentFactory.create_navigation_button("Nouveau")
        add_btn.clicked.connect(self._create_new_case)
        btn_layout.addWidget(add_btn)

        # Bouton utilitaire → Compact
        self.explorer_btn = ComponentFactory.create_navigation_button("Ouvrir dans l'explorateur")
        self.explorer_btn.setToolTip(
            "Ouvrir dans l'explorateur")  # Tooltip car plus petit
        self.explorer_btn.setEnabled(False)
        self.explorer_btn.clicked.connect(self._open_explorer)
        btn_layout.addWidget(self.explorer_btn)

        layout.addLayout(btn_layout)

        # TreeView des affaires
        self.cases_tree = ComponentFactory.create_tree_view()
        self.cases_model = QFileSystemModel()
        self.cases_model.setRootPath("")
        self.cases_tree.setModel(self.cases_model)

        # Cache les colonnes inutiles
        for i in range(1, self.cases_model.columnCount()):
            self.cases_tree.hideColumn(i)

        self.cases_tree.clicked.connect(self._on_case_clicked)
        layout.addWidget(self.cases_tree)

        return group

    def _setup_scelles_section(self):
        """Configure la section des scellés."""
        group = ComponentFactory.create_group_box("🔒 Scellés", DesignTokens.Colors.SUCCESS)

        layout = QVBoxLayout(group)
        layout.setContentsMargins(
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.MD,
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.SM,
        )
        layout.setSpacing(DesignTokens.Spacing.XS)

        # Bouton de taille navigation pour créer des scellés
        add_scelle_btn = ComponentFactory.create_navigation_button("Ajouter un scellé")
        add_scelle_btn.clicked.connect(self._create_new_scelle)
        layout.addWidget(add_scelle_btn)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Arborescence des scellés
        self.scelles_tree = ComponentFactory.create_tree_view()
        self.scelles_tree.setMinimumWidth(100)
        self.scelles_model = QStandardItemModel()
        self.scelles_model.setHorizontalHeaderLabels(["Scellés"])
        self.scelles_tree.setModel(self.scelles_model)
        self.scelles_tree.clicked.connect(self._on_scelle_clicked)
        splitter.addWidget(self.scelles_tree)

        # Liste des photos de scellé
        self.scelle_photos = PhotoListWidget("Photos du scellé:")
        self.scelle_photos.photo_deleted.connect(self.photo_deleted.emit)
        splitter.addWidget(self.scelle_photos)

        splitter.setSizes([100, 100])
        layout.addWidget(splitter)
        return group

    def _setup_objects_section(self):
        """Configure la section des objets."""
        group = ComponentFactory.create_group_box("📱 Objets d'essai", "#9C27B0")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.MD,
            DesignTokens.Spacing.SM,
            DesignTokens.Spacing.SM,
        )
        layout.setSpacing(DesignTokens.Spacing.XS)

        # Bouton de taille navigation pour créer des objets
        self.add_object_btn = ComponentFactory.create_navigation_button(
            "Ajouter un objet")
        self.add_object_btn.clicked.connect(self._create_new_object)
        self.add_object_btn.setEnabled(False)
        layout.addWidget(self.add_object_btn)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Liste des objets
        self.objects_list = QTreeWidget()
        self.objects_list.setStyleSheet(
            ComponentFactory.create_tree_view().styleSheet()
        )
        self.objects_list.setMinimumWidth(100)
        self.objects_list.setHeaderLabels(["Objets"])
        self.objects_list.itemClicked.connect(self._on_object_clicked)
        splitter.addWidget(self.objects_list)

        # Liste des photos d'objet
        self.object_photos = PhotoListWidget("Photos de l'objet:")
        self.object_photos.photo_deleted.connect(self.photo_deleted.emit)
        splitter.addWidget(self.object_photos)

        splitter.setSizes([100, 100])
        layout.addWidget(splitter)
        return group

    # === GESTION DES ÉVÉNEMENTS ===

    def _on_case_clicked(self, index: QModelIndex):
        """Gère le clic sur une affaire."""
        path = Path(self.cases_model.filePath(index))
        if path.is_dir():
            self.current_case_path = path
            self.current_scelle_path = None

            # Active le bouton explorateur
            self.explorer_btn.setEnabled(True)

            # Crée le gestionnaire de scellé
            self.scelle_manager = Scelle(path)
            self.objet_manager = None

            # Nettoie les autres sections
            self._clear_scelles_section()
            self._clear_objects_section()

            # Charge les scellés
            self._load_scelles(path)

            # Émet le signal
            self.case_selected.emit(path)

    def _on_scelle_clicked(self, index: QModelIndex):
        """Gère le clic sur un scellé."""
        item = self.scelles_model.itemFromIndex(index)
        if not item:
            return

        scelle_name = item.text()
        scelle = self.scelle_manager.get_item(scelle_name)

        if scelle:
            self.current_scelle_path = scelle.path

            # Crée le gestionnaire d'objets
            self.objet_manager = ObjetEssai(scelle.path)

            # Configure les dossiers pour les photos
            self.scelle_photos.set_photo_folder(scelle.path)
            self.object_photos.set_photo_folder(scelle.path)

            # Active le bouton d'ajout d'objet
            self.add_object_btn.setEnabled(True)

            # Charge les données
            self._load_scelle_photos()
            self._load_objects()

            # Nettoie la sélection d'objet
            self._clear_object_selection()

            # Émet le signal
            self.scelle_selected.emit(scelle.path)

    def _on_object_clicked(self, item: QTreeWidgetItem):
        """Gère le clic sur un objet."""
        object_id = item.data(0, Qt.ItemDataRole.UserRole)
        if object_id and self.current_scelle_path:
            # Charge les photos de l'objet
            self._load_object_photos(object_id)

            # Émet le signal
            self.object_selected.emit(object_id)

    # === ACTIONS UTILISATEUR ===

    def _create_new_case(self):
        """Crée une nouvelle affaire."""
        if not self.config.paths.workspace_path:
            QMessageBox.warning(
                self, "Erreur", "Configurez d'abord un dossier de travail."
            )
            return

        dialog = CreateAffaireDialog(self)
        if dialog.exec():
            numero = dialog.get_data()[0]
            if numero:
                try:
                    case_path = self.config.paths.workspace_path / numero
                    case_path.mkdir(exist_ok=False)
                    self._refresh_workspace_view()
                    logger.info(f"Affaire créée : {numero}")

                    # Sélectionne automatiquement la nouvelle affaire
                    index = self.cases_model.index(str(case_path))
                    self.cases_tree.setCurrentIndex(index)
                    self._on_case_clicked(index)

                except FileExistsError:
                    QMessageBox.warning(
                        self, "Erreur", f"L'affaire '{numero}' existe déjà."
                    )
                except Exception as e:
                    title, message = UserFriendlyErrorHandler.handle_file_error(
                        e, str(case_path)
                    )
                    QMessageBox.critical(self, title, message)

    def _create_new_scelle(self):
        """Crée un nouveau scellé."""
        if not self.scelle_manager or not self.current_case_path:
            QMessageBox.warning(self, "Erreur", "Sélectionnez d'abord une affaire.")
            return

        dialog = CreateScelleDialog(self)
        if dialog.exec():
            try:
                numero = dialog.get_numero()
                if not numero:
                    raise ValueError("Le numéro du scellé est requis")

                scelle_path = self.current_case_path / numero
                if scelle_path.exists():
                    QMessageBox.warning(
                        self, "Erreur", f"Le scellé '{numero}' existe déjà."
                    )
                    return

                scelle_path.mkdir(parents=True)
                self._load_scelles(self.current_case_path)
                logger.info(f"Scellé créé : {numero}")

            except Exception as e:
                title, message = UserFriendlyErrorHandler.handle_file_error(
                    e, str(scelle_path)
                )
                QMessageBox.critical(self, title, message)

    def _create_new_object(self):
        """Crée un nouvel objet."""
        if not self.objet_manager or not self.current_scelle_path:
            return

        try:
            next_code = self.objet_manager.get_next_available_code()
            item = self.objet_manager.create_item(next_code, f"Objet {next_code}")

            # Ajoute à la liste
            tree_item = QTreeWidgetItem(
                [f"{self.current_scelle_path.name}_{next_code}"]
            )
            tree_item.setData(0, Qt.ItemDataRole.UserRole, next_code)
            self.objects_list.addTopLevelItem(tree_item)

            # Sélectionne le nouvel objet
            self.objects_list.setCurrentItem(tree_item)
            self._on_object_clicked(tree_item)

            logger.info(f"Objet créé : {next_code}")

        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))

    def _select_workspace(self):
        """Sélectionne un nouveau dossier de travail."""
        folder = QFileDialog.getExistingDirectory(
            self, "Sélectionner le dossier de travail", str(Path.home())
        )

        if folder:
            self.config.set_workspace(Path(folder))
            self.workspace_label.setText(str(self.config.paths.workspace_path))
            self._refresh_workspace_view()

    def _open_explorer(self):
        """Ouvre l'explorateur sur l'affaire actuelle."""
        if self.current_case_path and self.current_case_path.exists():
            import os

            os.startfile(str(self.current_case_path))

    # === MÉTHODES DE CHARGEMENT DE DONNÉES ===

    def _load_scelles(self, case_path: Path):
        """Charge la liste des scellés."""
        self.scelles_model.clear()
        self.scelles_model.setHorizontalHeaderLabels(["Scellés"])

        if not case_path.exists():
            return

        scelle_folders = [p for p in case_path.iterdir() if p.is_dir()]
        scelle_folders.sort(key=lambda x: x.name.lower())

        for scelle_path in scelle_folders:
            scelle_item = QStandardItem(scelle_path.name)
            scelle_item.setData(str(scelle_path))
            self.scelles_model.appendRow(scelle_item)

    def _load_objects(self):
        """Charge la liste des objets du scellé actuel."""
        self.objects_list.clear()

        if not self.objet_manager:
            return

        objects = self.objet_manager.get_existing_objects()
        objects.sort()

        for object_id in objects:
            display_name = f"{self.current_scelle_path.name}_{object_id}"
            item = QTreeWidgetItem([display_name])
            item.setData(0, Qt.ItemDataRole.UserRole, object_id)
            self.objects_list.addTopLevelItem(item)

    def _load_scelle_photos(self):
        """Charge les photos du scellé (hors objets)."""
        if not self.current_scelle_path:
            return

        photos = []
        for photo in self.current_scelle_path.glob("*.jpg"):
            # Exclut les photos d'objets
            stem_parts = photo.stem.split("_")
            if len(stem_parts) >= 2:
                type_id = stem_parts[-2]
                if not (len(type_id) == 1 and type_id.isalpha()):
                    photos.append(photo.name)

        # Tri intelligent par type puis séquence
        def sort_key(photo_name):
            try:
                parts = photo_name.replace(".jpg", "").split("_")
                if len(parts) >= 3:
                    type_order = {"Ferme": 1, "Contenu": 2, "Reconditionne": 3}
                    photo_type = parts[-2]
                    sequence = int(parts[-1])
                    return (type_order.get(photo_type, 99), sequence)
            except:
                pass
            return (99, photo_name)

        photos.sort(key=sort_key)
        self.scelle_photos.update_photos(photos)

    def _load_object_photos(self, object_id: str):
        """Charge les photos d'un objet spécifique."""
        if not self.current_scelle_path:
            return

        photos = []
        for photo in self.current_scelle_path.glob(f"*_{object_id}_*.jpg"):
            photos.append(photo.name)

        # Tri par numéro de séquence
        def sort_object_photos(photo_name):
            try:
                parts = photo_name.replace(".jpg", "").split("_")
                return int(parts[-1])
            except:
                return 999

        photos.sort(key=sort_object_photos)
        self.object_photos.update_photos(photos)

    # === MÉTHODES DE NETTOYAGE ===

    def _clear_scelles_section(self):
        """Nettoie la section des scellés."""
        self.scelles_model.clear()
        self.scelles_model.setHorizontalHeaderLabels(["Scellés"])
        self.scelle_photos.clear()

    def _clear_objects_section(self):
        """Nettoie la section des objets."""
        self.objects_list.clear()
        self.object_photos.clear()
        self.add_object_btn.setEnabled(False)

    def _clear_object_selection(self):
        """Nettoie la sélection d'objet."""
        self.objects_list.clearSelection()
        self.object_photos.clear()

    # === MÉTHODES PUBLIQUES ===

    def initialize_workspace(self):
        """Initialise le workspace au démarrage."""
        self._update_workspace_label()
        if self.config.paths.workspace_path:
            self._refresh_workspace_view()

    def _update_workspace_label(self):
        """Met à jour l'affichage du workspace."""
        if self.config.paths.workspace_path:
            self.workspace_label.setText(str(self.config.paths.workspace_path))
        else:
            self.workspace_label.setText("Non configuré")

    def _refresh_workspace_view(self):
        """Rafraîchit la vue du workspace."""
        if self.config.paths.workspace_path and self.cases_tree:
            self.cases_tree.setRootIndex(
                self.cases_model.index(str(self.config.paths.workspace_path))
            )

    def refresh_photos(self):
        """Rafraîchit les listes de photos (appelé après prise/suppression)."""
        if self.current_scelle_path:
            self._load_scelle_photos()

        # Rafraîchit aussi les photos d'objet si un objet est sélectionné
        current_item = self.objects_list.currentItem()
        if current_item:
            object_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            if object_id:
                self._load_object_photos(object_id)

    def update_connection_state(self, is_connected: bool):
        """Met à jour l'état selon la connexion ADB (si nécessaire)."""
        # Pour l'instant, le panel de navigation n'a pas besoin de cette info
        # Mais la méthode est là pour l'extensibilité future
        pass
