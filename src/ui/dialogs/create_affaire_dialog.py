from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QLabel,
    QMessageBox,
)
from typing import Optional


class CreateAffaireDialog(QDialog):
    """
    Dialogue pour la création d'une nouvelle affaire.
    Vérifie la validité du nom pour le système de fichiers.
    """

    # Caractères interdits dans les noms de fichiers (Windows + Unix)
    FORBIDDEN_CHARS = '<>:"/\\|?*'

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau dossier")
        self.setMinimumWidth(300)

        # Configuration du layout
        layout = QFormLayout(self)

        # Champ de saisie avec validation temps réel
        self.numero_edit = QLineEdit()
        self.numero_edit.textChanged.connect(self._validate_input)
        layout.addRow("Nom de dossier:", self.numero_edit)

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

    def get_numero(self) -> Optional[str]:
        """Retourne le numéro saisi nettoyé ou None si invalide."""
        numero = self.numero_edit.text().strip()
        return numero if numero else None

    def accept(self):
        """Validation finale avant acceptation."""
        numero = self.get_numero()
        if not numero:
            QMessageBox.warning(self, "Erreur", "Veuillez entrer un numéro d'UNA.")
            return

        if any(char in numero for char in self.FORBIDDEN_CHARS):
            QMessageBox.warning(
                self,
                "Erreur",
                f"Le numéro contient des caractères interdits: {self.FORBIDDEN_CHARS}",
            )
            return

        super().accept()
