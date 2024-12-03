# src/ui/dialogs/create_affaire_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QFormLayout, QLineEdit, QDialogButtonBox,
    QLabel, QMessageBox, QVBoxLayout
)
from typing import Optional, Tuple


class CreateAffaireDialog(QDialog):
    """Dialogue pour la création d'une nouvelle affaire."""

    FORBIDDEN_CHARS = '<>:"/\\|?*'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau Dossier")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du dialogue."""
        layout = QVBoxLayout(self)

        # Formulaire principal
        form_layout = QFormLayout()

        # Champ pour le numéro d'affaire
        self.numero_edit = QLineEdit()
        self.numero_edit.setPlaceholderText("ex: 2024-001")
        self.numero_edit.textChanged.connect(self._validate_input)
        form_layout.addRow("Identifiant du dossier:", self.numero_edit)

        layout.addLayout(form_layout)

        # Texte d'aide
        help_text = QLabel(f"Caractères interdits : {self.FORBIDDEN_CHARS}")
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addWidget(help_text)

        # Boutons OK/Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(
            QDialogButtonBox.StandardButton.Ok
        ).setEnabled(False)

        layout.addWidget(self.button_box)

    def _validate_input(self, _):
        """Valide les champs en temps réel."""
        numero = self.numero_edit.text().strip()

        # Vérifie les caractères interdits
        has_forbidden_numero = any(char in numero for char in self.FORBIDDEN_CHARS)

        # Met à jour les styles visuels
        self.numero_edit.setStyleSheet(
            "background-color: #ffe6e6;" if has_forbidden_numero else ""
        )

        # Active/désactive le bouton OK
        is_valid = bool(numero) and not has_forbidden_numero
        self.button_box.button(
            QDialogButtonBox.StandardButton.Ok
        ).setEnabled(is_valid)

    def get_data(self) -> Tuple[str]:
        """Retourne le numéro de l'affaire."""
        return (
            self.numero_edit.text().strip(),
        )