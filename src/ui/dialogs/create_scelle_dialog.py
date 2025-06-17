# src/ui/dialogs/create_scelle_dialog.py


from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QLabel,
    QPushButton,
)
from src.utils.validation import FilenameValidator


class CreateScelleDialog(QDialog):
    """Dialogue pour la création d'un nouveau scellé avec validation robuste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau Scellé")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)

        # Champ de saisie avec validation
        self.numero_edit = QLineEdit()
        self.numero_edit.textChanged.connect(self._validate_input)
        layout.addRow("Numéro du scellé:", self.numero_edit)

        # Label pour les messages d'aide/erreur
        self.help_label = QLabel()
        self.help_label.setStyleSheet("color: gray; font-size: 10pt;")
        self.help_label.setWordWrap(True)
        layout.addRow(self.help_label)

        # Bouton de correction automatique
        self.fix_btn = QPushButton("Corriger automatiquement")
        self.fix_btn.clicked.connect(self._auto_fix)
        self.fix_btn.setVisible(False)
        layout.addRow(self.fix_btn)

        # Boutons OK/Cancel
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        layout.addRow(self.button_box)

        # Message d'aide initial
        self._show_help_message()

    def _validate_input(self, text: str):
        """Valide le texte saisi avec validation robuste."""
        is_valid, error_msg = FilenameValidator.validate(text)

        if is_valid:
            self._show_valid_state()
        else:
            self._show_error_state(error_msg)

        # Active/désactive le bouton OK
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(is_valid)

    def _show_valid_state(self):
        """Affiche l'état valide."""
        self.numero_edit.setStyleSheet("")
        self.help_label.setStyleSheet("color: green; font-size: 10pt;")
        self.help_label.setText("✓ Nom valide")
        self.fix_btn.setVisible(False)

    def _show_error_state(self, error_msg: str):
        """Affiche l'état d'erreur avec possibilité de correction."""
        self.numero_edit.setStyleSheet("background-color: #ffe6e6;")
        self.help_label.setStyleSheet("color: red; font-size: 10pt;")
        self.help_label.setText(f"❌ {error_msg}")

        # Affiche le bouton de correction si on peut proposer une solution
        current_text = self.numero_edit.text()
        if current_text and FilenameValidator.suggest_fix(current_text) != current_text:
            self.fix_btn.setVisible(True)
        else:
            self.fix_btn.setVisible(False)

    def _show_help_message(self):
        """Affiche le message d'aide initial."""
        self.help_label.setStyleSheet("color: gray; font-size: 10pt;")
        self.help_label.setText(
            "Évitez les caractères spéciaux, noms réservés Windows, "
            "et les espaces en début/fin."
        )

    def _auto_fix(self):
        """Applique la correction automatique."""
        current_text = self.numero_edit.text()
        fixed_text = FilenameValidator.suggest_fix(current_text)
        self.numero_edit.setText(fixed_text)

    def get_numero(self) -> str:
        """Retourne le numéro du scellé."""
        return self.numero_edit.text().strip()
