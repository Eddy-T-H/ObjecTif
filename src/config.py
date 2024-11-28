"""
Configuration de l'application avec gestion complète des chemins et du dossier de travail.
"""

from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import json
import os
from loguru import logger

class AppPaths(BaseModel):
    """Gestion des chemins de l'application."""
    base_path: Path            # Dossier racine de l'application
    config_file: Path         # Fichier de configuration
    logs_path: Path           # Dossier des logs
    workspace_path: Optional[Path] = None  # Dossier de travail principal

    def ensure_all_paths(self) -> None:
        """Crée les répertoires nécessaires pour l'application."""
        paths_to_create = ['base_path', 'logs_path']
        for path_attr in paths_to_create:
            path = getattr(self, path_attr)
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Création du répertoire : {path}")

class AppConfig(BaseModel):
    """Configuration principale de l'application."""

    # Métadonnées de l'application
    app_name: str = "ObjecTif"
    app_version: str = "1.0.0"

    # Mode de fonctionnement
    debug_mode: bool = Field(
        default_factory=lambda: os.getenv('DEBUG_MODE', 'false').lower() == 'true'
    )

    # Chemins de l'application
    paths: AppPaths

    def save_config(self) -> None:
        """Sauvegarde la configuration dans un fichier JSON."""
        config_data = {
            "workspace_path": str(self.paths.workspace_path) if self.paths.workspace_path else None
        }

        # Assure que le dossier parent existe
        self.paths.config_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.paths.config_file, 'w') as f:
            json.dump(config_data, f, indent=4)
        logger.info("Configuration sauvegardée")

    def load_saved_config(self) -> None:
        """Charge la configuration depuis le fichier JSON."""
        if self.paths.config_file.exists():
            with open(self.paths.config_file, 'r') as f:
                config_data = json.load(f)
                if workspace_path := config_data.get("workspace_path"):
                    self.paths.workspace_path = Path(workspace_path)
                    logger.info(f"Dossier de travail chargé : {self.paths.workspace_path}")

    @classmethod
    def load_config(cls) -> 'AppConfig':
        """Charge ou crée une nouvelle configuration."""
        load_dotenv()

        # Détermine les chemins de base selon l'OS
        if os.name == 'nt':  # Windows
            base_path = Path(os.getenv('LOCALAPPDATA')) / "ObjecTif"
        else:  # Linux/MacOS
            base_path = Path.home() / ".objectif"

        # Création des chemins de l'application
        paths = AppPaths(
            base_path=base_path,
            config_file=base_path / "config.json",
            logs_path=base_path / "logs"
        )

        # Création de la configuration
        config = cls(paths=paths)

        # Assure l'existence des dossiers
        paths.ensure_all_paths()

        # Charge la configuration sauvegardée
        config.load_saved_config()

        return config

    def set_workspace(self, path: Path) -> None:
        """Définit le dossier de travail et sauvegarde la configuration."""
        self.paths.workspace_path = path
        self.save_config()
        logger.info(f"Nouveau dossier de travail défini : {path}")