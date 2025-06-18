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
    QGroupBox,
    QPushButton, QInputDialog, QLineEdit, QApplication,
)
from PyQt6.QtCore import Qt, QModelIndex, pyqtSignal, QTimer
from PyQt6.QtGui import QFileSystemModel, QStandardItemModel, QStandardItem
from pathlib import Path
from loguru import logger
from typing import Optional
from src.config import AppConfig
from src.ui.dialogs.create_affaire_dialog import CreateAffaireDialog
from src.ui.dialogs.create_multiple_scelles_dialog import CreateMultipleScellesDialog
from src.ui.dialogs.create_scelle_dialog import CreateScelleDialog
from src.ui.widgets.operation_popup import OperationPopup
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
    multiple_scelles_created = pyqtSignal(int)  # nombre de scellés créés

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
        """Configure l'interface du panel de navigation avec qt-material."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # === SECTION WORKSPACE AVEC GROUPBOX ===
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

        # Répartition équilibrée
        splitter.setSizes([200, 200, 200])
        layout.addWidget(splitter)

    def _setup_workspace_section(self, layout):
        """Configure la section de sélection du workspace avec GroupBox."""
        # Utilise un GroupBox comme les autres sections
        workspace_group = QGroupBox("📂 Espace de Travail")
        workspace_layout = QHBoxLayout(workspace_group)
        workspace_layout.setContentsMargins(12, 20, 12, 12)
        workspace_layout.setSpacing(8)

        # Label du chemin actuel
        self.workspace_label = QLabel("Non configuré")
        self.workspace_label.setWordWrap(
            True)  # Permet le retour à la ligne si chemin long
        workspace_layout.addWidget(self.workspace_label, stretch=1)

        # Bouton pour changer le workspace
        change_workspace_btn = QPushButton("📁 Changer")
        change_workspace_btn.setToolTip("Changer le dossier de travail")
        change_workspace_btn.setFixedWidth(80)  # Un peu plus large pour le texte
        change_workspace_btn.setFixedHeight(28)  # Cohérent avec les autres boutons
        change_workspace_btn.clicked.connect(self._select_workspace)
        workspace_layout.addWidget(change_workspace_btn)

        # Limite la hauteur pour éviter l'étirement
        workspace_group.setMaximumHeight(70)

        layout.addWidget(workspace_group)

    def _setup_cases_section(self):
        """Configure la section des affaires avec possibilité de suppression."""
        group = QGroupBox("📁 Dossiers")
        layout = QVBoxLayout(group)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 12, 8, 8)

        # Boutons d'action
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        # Bouton pour créer
        add_btn = QPushButton("➕ Nouveau")
        add_btn.clicked.connect(self._create_new_case)
        add_btn.setToolTip("Créer un nouveau dossier")
        btn_layout.addWidget(add_btn)

        # Bouton explorateur
        self.explorer_btn = QPushButton("📂 Explorer")
        self.explorer_btn.setToolTip("Ouvrir dans l'explorateur")
        self.explorer_btn.setEnabled(False)
        self.explorer_btn.clicked.connect(self._open_explorer)
        btn_layout.addWidget(self.explorer_btn)

        layout.addLayout(btn_layout)

        # TreeView des affaires
        self.cases_tree = QTreeView()
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
        """Configure la section des scellés avec TreeView enrichi (approche sécurisée)."""
        group = QGroupBox("🔒 Scellés")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        # PREMIÈRE ligne de boutons (existante)
        scelle_btn_layout = QHBoxLayout()
        scelle_btn_layout.setSpacing(4)

        add_scelle_btn = QPushButton("➕ Ajouter")
        add_scelle_btn.clicked.connect(self._create_new_scelle)
        add_scelle_btn.setToolTip("Ajouter un nouveau scellé")
        scelle_btn_layout.addWidget(add_scelle_btn)

        self.delete_scelle_btn = QPushButton("🗑️")
        self.delete_scelle_btn.setEnabled(False)
        self.delete_scelle_btn.clicked.connect(self._delete_current_scelle)
        self.delete_scelle_btn.setToolTip("Supprimer le scellé sélectionné")
        self.delete_scelle_btn.setFixedWidth(35)
        scelle_btn_layout.addWidget(self.delete_scelle_btn)

        layout.addLayout(scelle_btn_layout)

        # NOUVELLE deuxième ligne de boutons À AJOUTER :
        multiple_btn_layout = QHBoxLayout()
        multiple_btn_layout.setSpacing(4)

        # Bouton création multiple
        self.btn_create_multiple = QPushButton("➕➕ Créer Plusieurs")
        self.btn_create_multiple.setEnabled(False)  # Activé quand dossier sélectionné
        self.btn_create_multiple.clicked.connect(self._create_multiple_scelles)
        self.btn_create_multiple.setToolTip("Créer plusieurs scellés en une fois")
        multiple_btn_layout.addWidget(self.btn_create_multiple)

        # Bouton explorateur compact
        self.btn_open_explorer = QPushButton("📂")
        self.btn_open_explorer.setEnabled(False)
        self.btn_open_explorer.clicked.connect(self._open_current_folder)
        self.btn_open_explorer.setToolTip("Ouvrir le dossier dans l'explorateur")
        self.btn_open_explorer.setFixedWidth(35)
        multiple_btn_layout.addWidget(self.btn_open_explorer)

        layout.addLayout(multiple_btn_layout)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # === TREEVIEW ENRICHI (SÉCURISÉ) ===
        self.scelles_tree = QTreeView()
        self.scelles_tree.setMinimumWidth(100)
        self.scelles_model = QStandardItemModel()
        self.scelles_model.setHorizontalHeaderLabels(["🔒 Scellés"])
        self.scelles_tree.setModel(self.scelles_model)

        # Configuration pour un affichage plus aéré
        self.scelles_tree.setRootIsDecorated(False)  # Pas d'indicateurs d'arbre
        self.scelles_tree.setAlternatingRowColors(True)
        self.scelles_tree.setStyleSheet("""
            QTreeView {
                font-size: 12px;
                show-decoration-selected: 1;
            }
            QTreeView::item {
                height: 45px;  /* Plus de hauteur pour l'effet aéré */
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QTreeView::item:selected {
                background-color: #d1ecf1;
                color: #0c5460;
            }
            QTreeView::item:hover {
                background-color: #e9ecef;
            }
        """)

        self.scelles_tree.clicked.connect(self._on_scelle_clicked)
        splitter.addWidget(self.scelles_tree)

        # Liste des photos de scellé
        self.scelle_photos = PhotoListWidget("Photos du scellé:")
        self.scelle_photos.photo_deleted.connect(self.photo_deleted.emit)
        splitter.addWidget(self.scelle_photos)

        splitter.setSizes([200, 100])
        layout.addWidget(splitter)
        return group

    def _setup_objects_section(self):
        """Configure la section des objets avec qt-material."""
        group = QGroupBox("📱 Objets d'essai")
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 12, 8, 8)
        layout.setSpacing(4)

        # Bouton de navigation pour créer des objets
        self.add_object_btn = QPushButton("➕ Ajouter un objet")
        self.add_object_btn.clicked.connect(self._create_new_object)
        self.add_object_btn.setEnabled(False)
        self.add_object_btn.setToolTip("Ajouter un nouvel objet d'essai")
        layout.addWidget(self.add_object_btn)

        # Splitter horizontal
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Liste des objets - SUPPRESSION du setStyleSheet
        self.objects_list = QTreeWidget()
        # qt-material applique automatiquement un style moderne aux TreeWidget
        self.objects_list.setMinimumWidth(100)
        self.objects_list.setHeaderLabels(["📱 Objets"])
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
        """Gère le clic sur une affaire """
        path = Path(self.cases_model.filePath(index))
        if path.is_dir():
            self.current_case_path = path
            self.current_scelle_path = None

            # Active les boutons
            self.explorer_btn.setEnabled(True)
            self.btn_create_multiple.setEnabled(True)
            self.btn_open_explorer.setEnabled(True)

            # Désactive les boutons de scellé
            self.delete_scelle_btn.setEnabled(False)

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
        """Gère le clic sur un scellé avec récupération du bon chemin."""
        item = self.scelles_model.itemFromIndex(index)
        if not item:
            return

        # Récupère le chemin stocké dans les données de l'item (pas le texte affiché)
        scelle_path_str = item.data()
        if not scelle_path_str:
            logger.warning("Aucun chemin stocké dans l'item")
            return

        scelle_path = Path(scelle_path_str)

        # Vérifie que le chemin existe
        if not scelle_path.exists():
            logger.error(f"Le chemin du scellé n'existe pas: {scelle_path}")
            return

        logger.debug(f"Scellé sélectionné: {scelle_path.name}")

        # Met à jour l'état local
        self.current_scelle_path = scelle_path

        # Active le bouton de suppression de scellé
        self.delete_scelle_btn.setEnabled(True)

        # Crée le gestionnaire d'objets
        self.objet_manager = ObjetEssai(scelle_path)

        # Configure les dossiers pour les photos
        self.scelle_photos.set_photo_folder(scelle_path)
        self.object_photos.set_photo_folder(scelle_path)

        # Active le bouton d'ajout d'objet
        self.add_object_btn.setEnabled(True)

        # Charge les données
        self._load_scelle_photos()
        self._load_objects()

        # Nettoie la sélection d'objet
        self._clear_object_selection()

        # Émet le signal avec le bon chemin
        self.scelle_selected.emit(scelle_path)

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
        """Charge la liste des scellés avec affichage enrichi et stockage du chemin."""
        self.scelles_model.clear()
        self.scelles_model.setHorizontalHeaderLabels(["Scellés"])

        if not case_path.exists():
            return

        scelle_folders = [p for p in case_path.iterdir() if p.is_dir()]
        scelle_folders.sort(key=lambda x: x.name.lower())

        for scelle_path in scelle_folders:
            # Analyse du contenu
            analysis = self._analyze_scelle_photos(scelle_path)

            # Création des indicateurs visuels
            ferme_icon = "🔒✅" if analysis["ferme"] else "🔒❌"
            contenu_icon = "🔍✅" if analysis["contenu"] else "🔍❌"
            recond_icon = "📦✅" if analysis["reconditionne"] else "📦❌"

            # Texte des objets
            if analysis["objects"]:
                objects_text = f"📱{','.join(analysis['objects'])}"
            else:
                objects_text = "📱∅"

            # Construction du texte sur DEUX LIGNES avec \n
            line1 = f"▸ {scelle_path.name}"
            line2 = f"  {ferme_icon} {contenu_icon} {recond_icon} | {objects_text} | 📸 {analysis['total']}"
            display_text = f"{line1}\n{line2}"

            # Création de l'item
            scelle_item = QStandardItem(display_text)

            # IMPORTANT: Stocke le chemin COMPLET dans les données
            scelle_item.setData(str(scelle_path))

            # Tooltip détaillé
            tooltip = (
                f"Scellé: {scelle_path.name}\n"
                f"Photos totales: {analysis['total']}\n\n"
                f"Photos du scellé:\n"
                f"🔒 Fermé: {'✓' if analysis['ferme'] else '✗'}\n"
                f"🔍 Contenu: {'✓' if analysis['contenu'] else '✗'}\n"
                f"📦 Reconditionné: {'✓' if analysis['reconditionne'] else '✗'}\n\n"
                f"Objets d'essai ({len(analysis['objects'])}):\n"
            )

            if analysis["objects"]:
                tooltip += "\n".join([f"📱 Objet {obj}" for obj in analysis["objects"]])
            else:
                tooltip += "Aucun objet d'essai"

            scelle_item.setToolTip(tooltip)

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
        """Rafraîchit les listes de photos et les indicateurs."""
        # Recharge les scellés avec les nouveaux indicateurs
        if self.current_case_path:
            self._load_scelles(self.current_case_path)

            # Restaure la sélection si possible
            if self.current_scelle_path:
                self._restore_scelle_selection()

        # Rafraîchit les photos du scellé actuel
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

    def _delete_current_scelle(self):
        """Supprime le scellé actuellement sélectionné."""
        if not self.current_scelle_path or not self.current_scelle_path.exists():
            QMessageBox.warning(self, "Erreur", "Aucun scellé sélectionné.")
            return

        scelle_name = self.current_scelle_path.name

        try:
            photos_count = len(list(self.current_scelle_path.glob("*.jpg")))

            confirm_msg = (
                f"Supprimer le scellé '{scelle_name}' ?\n\n"
                f"Contenu : {photos_count} photo(s)\n"
                f"⚠️ Action irréversible\n\n"
                f"Tapez 'oui' pour confirmer :"
            )

            text, ok = QInputDialog.getText(
                self,
                "Confirmer la suppression",
                confirm_msg,
                QLineEdit.EchoMode.Normal
            )

            if ok and text.lower() in ['oui', 'yes']:
                # Suppression effective
                import shutil
                shutil.rmtree(self.current_scelle_path)

                logger.info(f"Scellé supprimé : {scelle_name}")

                # Nettoie l'interface
                self.current_scelle_path = None
                self.objet_manager = None

                # Désactive les boutons
                self.delete_scelle_btn.setEnabled(False)
                self.add_object_btn.setEnabled(False)

                # Nettoie les sections
                self._clear_objects_section()
                self.scelle_photos.clear()

                # Recharge les scellés
                if self.current_case_path:
                    self._load_scelles(self.current_case_path)

                # Émet un signal de déselection
                self.scelle_selected.emit(Path())  # Path vide
            else:
                logger.info("Suppression scellé annulée par l'utilisateur")

        except Exception as e:
            logger.error(f"Erreur lors de la suppression du scellé {scelle_name}: {e}")
            QMessageBox.critical(
                self,
                "Erreur de suppression",
                f"Impossible de supprimer le scellé '{scelle_name}'.\n\n"
                f"Erreur : {str(e)}"
            )

    def _analyze_scelle_photos(self, scelle_path: Path) -> dict:
        """Analyse les photos d'un scellé pour créer les indicateurs."""
        analysis = {
            "ferme": False,
            "contenu": False,
            "reconditionne": False,
            "objects": [],
            "total": 0
        }

        try:
            photos = list(scelle_path.glob("*.jpg"))
            analysis["total"] = len(photos)

            objects_found = set()

            for photo in photos:
                parts = photo.stem.split("_")
                if len(parts) >= 2:
                    type_id = parts[-2].lower()

                    # Photos du scellé
                    if type_id in ["ferme", "fermé"]:
                        analysis["ferme"] = True
                    elif type_id == "contenu":
                        analysis["contenu"] = True
                    elif type_id in ["reconditionne", "reconditionné",
                                     "reconditionnement"]:
                        analysis["reconditionne"] = True
                    # Photos d'objets (une seule lettre)
                    elif len(parts[-2]) == 1 and parts[-2].isalpha():
                        objects_found.add(parts[-2].upper())

            analysis["objects"] = sorted(list(objects_found))

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse de {scelle_path}: {e}")

        return analysis

    def _restore_scelle_selection(self):
        """Restaure la sélection du scellé après rechargement."""
        if not self.current_scelle_path:
            return

        for row in range(self.scelles_model.rowCount()):
            item = self.scelles_model.item(row)
            if item and item.data() == str(self.current_scelle_path):
                index = self.scelles_model.indexFromItem(item)
                self.scelles_tree.setCurrentIndex(index)
                logger.debug(
                    f"Sélection restaurée pour: {self.current_scelle_path.name}")
                break

    def _create_multiple_scelles(self):
        """Ouvre le dialogue de création multiple de scellés."""
        if not self.current_case_path:
            QMessageBox.warning(
                self, "❌ Erreur",
                "Sélectionnez d'abord un dossier dans la liste des dossiers."
            )
            return

        dialog = CreateMultipleScellesDialog(self)
        if dialog.exec():
            scelle_names = dialog.get_scelle_names()
            if scelle_names:
                self._perform_multiple_creation(scelle_names)

    def _perform_multiple_creation(self, scelle_names: list[str]):
        """Effectue la création multiple de scellés."""
        if not self.current_case_path:
            return

        logger.info(f"🔒 Début création multiple de {len(scelle_names)} scellés")

        # Popup de progression
        popup = OperationPopup(self)
        popup.setWindowTitle("🔒 Création de Scellés")
        popup.show()
        QApplication.processEvents()

        created_count = 0
        skipped_count = 0
        errors = []

        try:
            for i, scelle_name in enumerate(scelle_names, 1):
                try:
                    popup.update_message(
                        f"Création {i}/{len(scelle_names)}: {scelle_name}")
                    QApplication.processEvents()

                    scelle_path = self.current_case_path / scelle_name

                    if scelle_path.exists():
                        skipped_count += 1
                        logger.warning(f"Scellé '{scelle_name}' existe déjà - ignoré")
                        continue

                    scelle_path.mkdir(parents=True, exist_ok=False)
                    created_count += 1
                    logger.info(f"✅ Scellé créé : {scelle_name}")

                except Exception as e:
                    error_msg = f"Erreur avec '{scelle_name}': {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)

        finally:
            popup.close_popup()

        # Rapport final
        self._show_creation_report(created_count, skipped_count, errors,
                                   len(scelle_names))

        # Rafraîchissement automatique
        if created_count > 0:
            self._load_scelles(self.current_case_path)
            self.multiple_scelles_created.emit(created_count)

    def _show_creation_report(self, created: int, skipped: int, errors: list,
                              total: int):
        """Affiche un rapport détaillé de la création."""
        if created == total:
            title = "✅ Création Réussie"
            icon = "✅"
        elif created > 0:
            title = "⚠️ Création Partielle"
            icon = "⚠️"
        else:
            title = "❌ Échec de Création"
            icon = "❌"

        summary = f"{icon} <b>Résumé:</b><br>"
        summary += f"• ✅ <b>Créés:</b> {created}<br>"
        if skipped > 0:
            summary += f"• 🔄 <b>Ignorés (existants):</b> {skipped}<br>"
        if errors:
            summary += f"• ❌ <b>Erreurs:</b> {len(errors)}<br>"
        summary += f"• 📊 <b>Total:</b> {total}"

        if errors:
            error_details = "<br><br>🔍 <b>Erreurs:</b><br>"
            for error in errors[:5]:  # Limite à 5
                error_details += f"• {error}<br>"
            if len(errors) > 5:
                error_details += f"• ... et {len(errors) - 5} autres"
            summary += error_details

        if created > 0:
            QMessageBox.information(self, title, summary)
        else:
            QMessageBox.warning(self, title, summary)

    def _open_current_folder(self):
        """Ouvre le dossier actuel dans l'explorateur."""
        if not self.current_case_path or not self.current_case_path.exists():
            QMessageBox.warning(self, "❌ Erreur", "Aucun dossier sélectionné.")
            return

        try:
            import os
            import platform
            import subprocess

            if platform.system() == "Windows":
                os.startfile(str(self.current_case_path))
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(self.current_case_path)])
            else:  # Linux
                subprocess.run(["xdg-open", str(self.current_case_path)])

            logger.info(f"📂 Explorateur ouvert : {self.current_case_path}")

        except Exception as e:
            logger.error(f"Erreur explorateur: {e}")
            QMessageBox.warning(self, "❌ Erreur",
                                f"Impossible d'ouvrir l'explorateur.\n{e}")