# src/main.py
"""
Point d'entrée utilisant le thème natif Qt6.
Qt6 détecte automatiquement le mode sombre/clair du système.
"""

import sys
import os
from loguru import logger
from PyQt6.QtWidgets import QApplication

from src.config import AppConfig
from src.ui.main_window import MainWindow
from src.ui.theme.native_theme import (
    apply_native_qt_theme,
    setup_native_theme_attributes,
    detect_system_theme_info,
)


class LogBuffer:
    def __init__(self):
        self.logs = []

    def write(self, message):
        self.logs.append(message)

    def flush(self):
        pass


def setup_logging(config: AppConfig):
    """Configure le système de journalisation."""
    logger.remove()

    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    if getattr(sys, "frozen", False):
        # Mode compilé -> log vers fichier
        log_path = os.path.join(os.path.dirname(sys.executable), "objectif.log")
        logger.add(
            log_path, rotation="10 MB", level="DEBUG", format=log_format, diagnose=True
        )
    else:
        # Mode développement -> buffer + console + fichier
        log_buffer = LogBuffer()
        logger.add(log_buffer.write, format=log_format)
        logger.add(sys.stderr, level="DEBUG", format=log_format, diagnose=True)
        logger.add(
            config.paths.logs_path / "objectif.log",
            rotation="10 MB",
            level="DEBUG",
            format=log_format,
            diagnose=True,
        )
        return log_buffer


def main():
    """
    Fonction principale utilisant le thème natif Qt6.
    """
    # Charge la configuration globale
    config = AppConfig.load_config()

    # Met en place le système de logging
    log_buffer = setup_logging(config)

    # Log le démarrage
    logger.info("Démarrage de l'application ObjecTif")
    logger.debug(f"Configuration: {config}")

    # Crée l'application Qt
    app = QApplication(sys.argv)

    # === CONFIGURATION DU THÈME NATIF QT6 ===

    # Configure les attributs pour une meilleure détection du thème
    setup_native_theme_attributes(app)

    # Détecte et log les informations du thème système
    theme_info = detect_system_theme_info(app)
    logger.info(f"Thème système détecté: {theme_info['theme_name']}")
    logger.debug(f"Détails du thème: {theme_info}")

    # Applique les améliorations au thème natif
    theme_applied = apply_native_qt_theme(app)

    if theme_applied:
        logger.info("Thème natif Qt6 appliqué avec améliorations")
    else:
        logger.warning("Utilisation du thème Qt6 par défaut sans améliorations")

    # Crée et affiche la fenêtre principale
    window = MainWindow(config, log_buffer)
    window.show()

    # Lance la boucle d'événements Qt
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
