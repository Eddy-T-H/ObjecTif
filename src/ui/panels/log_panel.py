# src/ui/panels/log_panel.py
"""
Panel de logs - Affichage des logs avec qt-material.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from loguru import logger

# SUPPRESSION: from src.ui.theme.design_system import DesignTokens
from src.ui.widgets.log_viewer import ColoredLogViewer, QtHandler


class LogPanel(QWidget):
    """Panel dédié à l'affichage des logs avec qt-material."""

    def __init__(self, log_buffer=None, parent=None):
        super().__init__(parent)
        self.log_buffer = log_buffer
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du panel de logs avec qt-material."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Créer le viewer de logs - SUPPRESSION de setStyleSheet
        self.log_viewer = ColoredLogViewer()
        # qt-material + classe CSS "log-viewer" appliquent automatiquement :
        # - Police monospace (Consolas, Monaco)
        # - Couleurs adaptées au thème
        # - Bordures modernes
        # - Padding cohérent
        # - Adaptation clair/sombre automatique

        # Charge les logs initiaux si le buffer existe
        if self.log_buffer:
            self.log_viewer.load_initial_logs(self.log_buffer)

        # Configure le handler Loguru pour rediriger vers ce viewer
        logger.add(
            QtHandler(self.log_viewer).write,
            format="{time:HH:mm:ss} | {level: <8} | {message}"
        )

        layout.addWidget(self.log_viewer)

    def clear_logs(self):
        """Vide les logs affichés."""
        self.log_viewer.clear()

    def append_log(self, message: str, level: str = "INFO"):
        """Ajoute un message de log."""
        self.log_viewer.append_log(message, level)