# src/ui/dialogs/create_multiple_scelles_dialog.py
"""
Dialogue pour créer plusieurs scellés en une fois.
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QDialogButtonBox,
)
from PyQt6.QtCore import Qt


class CreateMultipleScellesDialog(QDialog):
    """Dialogue pour créer plusieurs scellés en une fois."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📝 Créer Plusieurs Scellés")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du dialogue."""
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # === INSTRUCTIONS ===
        instructions = QLabel(
            "📝 <b>Saisissez les noms des scellés à créer (un par ligne):</b><br><br>"
            "Exemple:<br>"
            "• Scelle_001<br>"
            "• Scelle_002<br>"
            "• TELEPHONE_SAMSUNG<br>"
            "• TABLETTE_APPLE<br>"
            "• USB_CLEF"
        )
        instructions.setStyleSheet(
            "color: #333; "
            "background-color: #f8f9fa; "
            "padding: 15px; "
            "border: 1px solid #dee2e6; "
            "border-radius: 5px; "
            "margin-bottom: 10px;"
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # === ZONE DE SAISIE ===
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText(
            "Saisissez un nom de scellé par ligne...\n\n"
            "Exemples valides :\n"
            "Scelle_001\n"
            "TELEPHONE_SAMSUNG\n"
            "ORDINATEUR_PORTABLE\n"
            "CLE_USB_16GO"
        )
        self.text_edit.setStyleSheet(
            "QTextEdit {"
            "    font-family: 'Consolas', 'Monaco', monospace;"
            "    font-size: 12px;"
            "    line-height: 1.4;"
            "    padding: 10px;"
            "    border: 2px solid #dee2e6;"
            "    border-radius: 5px;"
            "}"
            "QTextEdit:focus {"
            "    border-color: #007bff;"
            "}"
        )
        layout.addWidget(self.text_edit)

        # === COMPTEUR DE SCELLÉS ===
        self.count_label = QLabel("📊 Scellés à créer: 0")
        self.count_label.setStyleSheet(
            "font-weight: bold; "
            "color: #007bff; "
            "font-size: 14px; "
            "padding: 8px; "
            "background-color: #e3f2fd; "
            "border-radius: 4px;"
        )
        layout.addWidget(self.count_label)

        # === VALIDATION EN TEMPS RÉEL ===
        self.validation_label = QLabel()
        self.validation_label.setWordWrap(True)
        self.validation_label.setVisible(False)
        layout.addWidget(self.validation_label)

        # Connecte la validation en temps réel
        self.text_edit.textChanged.connect(self._validate_and_update_count)

        # === BOUTONS ===
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Désactive OK au début
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

        layout.addWidget(self.button_box)

    def _validate_and_update_count(self):
        """Valide le contenu et met à jour le compteur en temps réel."""
        text = self.text_edit.toPlainText().strip()

        if not text:
            self._update_display(0, [], [])
            return

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        valid_names = []
        duplicates = []
        invalid_names = []
        seen = set()

        for line in lines:
            if not line:
                continue

            # Vérifie les doublons
            if line in seen:
                if line not in duplicates:
                    duplicates.append(line)
                continue

            # Vérifie la validité (basique)
            if self._is_valid_scelle_name(line):
                valid_names.append(line)
                seen.add(line)
            else:
                invalid_names.append(line)

        self._update_display(len(valid_names), duplicates, invalid_names)

    def _is_valid_scelle_name(self, name: str) -> bool:
        """Vérifie si un nom de scellé est valide (validation basique)."""
        if not name or len(name.strip()) == 0:
            return False

        # Évite les caractères problématiques
        forbidden_chars = '<>:"/\\|?*'
        if any(char in name for char in forbidden_chars):
            return False

        # Évite les noms trop longs
        if len(name) > 100:
            return False

        return True

    def _update_display(self, valid_count: int, duplicates: list, invalid_names: list):
        """Met à jour l'affichage du compteur et des validations."""
        # Met à jour le compteur
        self.count_label.setText(f"📊 Scellés à créer: {valid_count}")

        # Active/désactive le bouton OK
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            valid_count > 0
        )

        # Affiche les problèmes éventuels
        if duplicates or invalid_names:
            problems = []

            if duplicates:
                dup_text = ", ".join(duplicates[:3])
                if len(duplicates) > 3:
                    dup_text += f" (+{len(duplicates) - 3} autres)"
                problems.append(f"🔄 <b>Doublons ignorés:</b> {dup_text}")

            if invalid_names:
                inv_text = ", ".join(invalid_names[:3])
                if len(invalid_names) > 3:
                    inv_text += f" (+{len(invalid_names) - 3} autres)"
                problems.append(f"❌ <b>Noms invalides:</b> {inv_text}")

            self.validation_label.setText("<br>".join(problems))
            self.validation_label.setStyleSheet(
                "color: #856404; "
                "background-color: #fff3cd; "
                "border: 1px solid #ffeaa7; "
                "padding: 8px; "
                "border-radius: 4px; "
                "font-size: 11px;"
            )
            self.validation_label.setVisible(True)
        else:
            self.validation_label.setVisible(False)

    def get_scelle_names(self) -> list[str]:
        """Retourne la liste des noms de scellés valides et uniques."""
        text = self.text_edit.toPlainText().strip()
        if not text:
            return []

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        valid_names = []
        seen = set()

        for line in lines:
            if line and line not in seen and self._is_valid_scelle_name(line):
                valid_names.append(line)
                seen.add(line)

        return valid_names
