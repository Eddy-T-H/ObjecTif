# src/ui/panels/log_panel.py
"""
Panel de logs - Affichage des logs avec style unifié.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout
from loguru import logger

from src.ui.theme.design_system import DesignTokens
from src.ui.widgets.log_viewer import ColoredLogViewer, QtHandler


class LogPanel(QWidget):
    """Panel dédié à l'affichage des logs."""

    def __init__(self, log_buffer=None, parent=None):
        super().__init__(parent)
        self.log_buffer = log_buffer
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du panel de logs."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Créer le viewer de logs avec style unifié
        self.log_viewer = ColoredLogViewer()
        self.log_viewer.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {DesignTokens.Colors.SURFACE};
                color: {DesignTokens.Colors.TEXT_PRIMARY};
                border: 1px solid {DesignTokens.Colors.BORDER};
                border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
                font-family: "Consolas", "Monaco", monospace;
                font-size: {DesignTokens.Typography.CAPTION}px;
                padding: {DesignTokens.Spacing.SM}px;
                selection-background-color: {DesignTokens.Colors.SELECTED};
            }}
        """)

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