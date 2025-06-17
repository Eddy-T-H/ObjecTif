# src/ui/widgets/operation_popup.py

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class OperationPopup(QDialog):
	"""Popup simple pour afficher l'état d'une opération en cours."""

	def __init__(self, parent=None):
		super().__init__(parent)
		self.setWindowTitle("Opération en cours")
		self.setMinimumWidth(300)
		self.setMinimumHeight(100)
		# Popup modale qui bloque l'interface parent
		self.setModal(True)
		# Empêche la fermeture par l'utilisateur
		self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.CustomizeWindowHint | Qt.WindowType.WindowTitleHint)
		self._setup_ui()

	def _setup_ui(self):
		layout = QVBoxLayout(self)
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(10)

		# Label pour le message principal
		self.message_label = QLabel("Opération en cours...")
		self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

		# Style plus visible
		font = QFont()
		font.setPointSize(12)
		self.message_label.setFont(font)
		self.message_label.setStyleSheet("color: #333; padding: 10px;")

		layout.addWidget(self.message_label)

	def update_message(self, message: str):
		"""Met à jour le message affiché."""
		self.message_label.setText(message)
		# Force le rafraîchissement immédiat
		self.repaint()

	def close_popup(self):
		"""Ferme la popup."""
		self.accept()