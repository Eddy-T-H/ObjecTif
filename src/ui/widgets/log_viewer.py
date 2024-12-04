# src/ui/widgets/log_viewer.py

from PyQt6.QtWidgets import QPlainTextEdit
from PyQt6.QtGui import QColor, QPalette, QTextCursor


class ColoredLogViewer(QPlainTextEdit):
    """Terminal avec coloration syntaxique pour les logs."""

    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setMaximumHeight(200)
        self.setMinimumHeight(100)
        self.document().setMaximumBlockCount(5000)  # Limite le nombre de lignes

    def append_log(self, message, level="INFO"):
        cursor = self.textCursor()
        format = self.currentCharFormat()

        # Utilise QPalette pour les couleurs système
        if level == "DEBUG":
            format.setForeground(
                self.palette().color(QPalette.ColorRole.PlaceholderText)
            )
        elif level == "WARNING":
            format.setForeground(QColor(255, 165, 0))  # Orange
        elif level == "ERROR" or level == "CRITICAL":
            format.setForeground(QColor(255, 0, 0))  # Rouge
        else:  # INFO et autres
            format.setForeground(self.palette().color(QPalette.ColorRole.Text))

        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(f"{message}\n", format)
        self.verticalScrollBar().setValue(self.verticalScrollBar().maximum())

    def load_initial_logs(self, buffer):
        """Charge les logs du buffer dans l'interface."""
        for message in buffer.logs:
            self.append_log(message)


class QtHandler:
    """Handler personnalisé pour Loguru."""

    def __init__(self, widget):
        self.widget = widget

    def write(self, message):
        try:
            # Extrait le niveau de log
            level = "INFO"
            for possible_level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
                if possible_level in message:
                    level = possible_level
                    break
            self.widget.append_log(message.strip(), level)
        except Exception as e:
            print(f"Erreur dans le handler de log: {e}")