# src/ui/dialogs/create_scelle_dialog.py
from PyQt6.QtWidgets import QDialog, QFormLayout, QLineEdit, QDialogButtonBox, QLabel

class CreateScelleDialog(QDialog):
    """Dialogue pour la création d'un nouveau scellé."""

    FORBIDDEN_CHARS = '<>:"/\\|?*'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau Scellé")
        self.setMinimumWidth(300)

        # Configuration du layout
        layout = QFormLayout(self)

        # Champ de saisie avec validation
        self.numero_edit = QLineEdit()
        self.numero_edit.textChanged.connect(self._validate_input)
        layout.addRow("Numéro du scellé:", self.numero_edit)

        # Ajout du texte d'aide
        help_text = QLabel(f"Caractères interdits : {self.FORBIDDEN_CHARS}")
        help_text.setStyleSheet("color: gray; font-size: 10pt;")
        layout.addRow(help_text)

        # Boutons OK/Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Le bouton OK est désactivé par défaut
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        layout.addRow(self.button_box)

    def _validate_input(self, text: str):
        """Vérifie que le texte ne contient pas de caractères interdits."""
        text = text.strip()
        has_forbidden = any(char in text for char in self.FORBIDDEN_CHARS)

        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(text) and not has_forbidden
        )

        if has_forbidden:
            self.numero_edit.setStyleSheet("background-color: #ffe6e6;")
            self.setToolTip(f"Caractères interdits: {self.FORBIDDEN_CHARS}")
        else:
            self.numero_edit.setStyleSheet("")
            self.setToolTip("")

    def get_numero(self) -> str:
        """Retourne le numéro du scellé."""
        return self.numero_edit.text().strip()