"""
Cette classe gère le compteur d'objets d'essai pour chaque scellé via un fichier de configuration.
Elle s'occupe de la création, lecture et mise à jour du nombre d'objets.
"""

import json
from pathlib import Path
from loguru import logger


class TestObjectsManager:
    """Gère les objets d'essai d'un scellé via un fichier de configuration."""

    def __init__(self, scelle_path: Path):
        """
        Initialise le gestionnaire pour un scellé spécifique.
        Crée le fichier de configuration s'il n'existe pas.
        """
        self.scelle_path = scelle_path
        self.config_file = scelle_path / "objets_essai.json"
        self.config = self._load_or_create_config()

    def _load_or_create_config(self) -> dict:
        """Charge la configuration ou crée un nouveau fichier si nécessaire."""
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(
                    f"Fichier de configuration corrompu pour {self.scelle_path.name}"
                )
                return {"nombre_objets": 0}
        else:
            # Crée un nouveau fichier de configuration
            config = {"nombre_objets": 0}
            self._save_config(config)
            return config

    def _save_config(self, config: dict):
        """Sauvegarde la configuration dans le fichier."""
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

    def get_object_count(self) -> int:
        """Retourne le nombre actuel d'objets d'essai."""
        return self.config.get("nombre_objets", 0)

    def add_object(self) -> str:
        """
        Ajoute un nouvel objet d'essai.
        Retourne la lettre attribuée au nouvel objet.
        """
        current_count = self.get_object_count()
        if current_count >= 26:  # Limite aux 26 lettres de l'alphabet
            raise ValueError("Nombre maximum d'objets atteint (26)")

        # Incrémente le compteur
        self.config["nombre_objets"] = current_count + 1
        self._save_config(self.config)

        # Retourne la lettre correspondante (A=0, B=1, etc.)
        return chr(65 + current_count)  # 65 est le code ASCII de 'A'

    def get_object_letters(self) -> list[str]:
        """Retourne la liste des lettres des objets existants."""
        count = self.get_object_count()
        return [chr(65 + i) for i in range(count)]
