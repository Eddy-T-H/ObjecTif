"""
Le fichier main.py est le point d'entrée principal de l'application.
Il coordonne le démarrage de tous les composants.
"""

import sys
from loguru import logger
from PyQt6.QtWidgets import QApplication

from src.config import AppConfig
from src.ui.main_window import MainWindow

def setup_logging(config: AppConfig):
    """
    Configure le système de journalisation.
    - Supprime la configuration par défaut
    - Ajoute des handlers pour fichier et console
    - Définit les formats et niveaux de log
    """
    # Supprime la configuration par défaut de loguru
    logger.remove()

    # Définit un format de log lisible et informatif
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "  # Horodatage
        "<level>{level: <8}</level> | "                 # Niveau de log
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> - "    # Fichier et ligne
        "<level>{message}</level>"                      # Message
    )

    # Configure le logging vers un fichier
    logger.add(
        config.paths.logs_path / "objectif.log",  # Chemin du fichier
        rotation="10 MB",                         # Rotation à 10 MB
        level="DEBUG" if config.debug_mode else "INFO",  # Niveau selon mode
        format=log_format
    )

    # Ajoute le logging console en mode debug
    if config.debug_mode:
        logger.add(sys.stderr, level="DEBUG", format=log_format)

def main():
    """
    Fonction principale qui :
    - Charge la configuration
    - Configure le logging
    - Initialise l'interface Qt
    - Lance l'application
    """
    # Charge la configuration globale
    config = AppConfig.load_config()

    # Met en place le système de logging
    setup_logging(config)

    # Log le démarrage
    logger.info("Démarrage de l'application ObjecTif")
    logger.debug(f"Configuration: {config}")

    # Crée l'application Qt
    app = QApplication(sys.argv)

    # Crée et affiche la fenêtre principale
    window = MainWindow(config)
    window.show()

    # Lance la boucle d'événements Qt
    sys.exit(app.exec())

# Point d'entrée standard Python
if __name__ == "__main__":
    main()