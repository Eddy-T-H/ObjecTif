# core/evidence/base.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class Photo:
    """Représente une photo avec ses métadonnées."""
    path: Path
    type: str      # Type de photo (Ferme, Contenu, lettre d'objet, etc.)
    sequence: int  # Numéro de séquence pour l'ordre des photos

    @property
    def filename(self) -> str:
        return self.path.name

@dataclass
class EvidenceItem:
    """Représente un élément de preuve (scellé ou objet d'essai)."""
    id: str               # Identifiant unique
    name: str            # Nom descriptif
    path: Path          # Chemin du dossier contenant
    photos: List[Photo] # Liste des photos associées

class EvidenceBase(ABC):
    """Classe de base abstraite pour la gestion des preuves."""

    def __init__(self, base_path: Path):
        """
        Initialise le gestionnaire de preuves.

        Args:
            base_path: Chemin du dossier racine
        """
        logger.debug(f"Initialisation de EvidenceBase avec le chemin: {base_path}")
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            logger.error(f"Le chemin {base_path} n'existe pas")
            raise ValueError(f"Le chemin {base_path} n'existe pas")

    @abstractmethod
    def create_item(self, item_id: str, name: str) -> EvidenceItem:
        """
        Crée un nouvel élément de preuve.

        Args:
            item_id: Identifiant unique de l'élément
            name: Nom descriptif

        Returns:
            EvidenceItem: L'élément créé
        """
        pass

    @abstractmethod
    def get_item(self, item_id: str) -> Optional[EvidenceItem]:
        """
        Récupère un élément par son identifiant.

        Args:
            item_id: Identifiant de l'élément à récupérer

        Returns:
            Optional[EvidenceItem]: L'élément trouvé ou None
        """
        pass

    @abstractmethod
    def get_photos(self, item_id: str, photo_type: Optional[str] = None) -> List[Photo]:
        """
        Récupère les photos d'un élément.

        Args:
            item_id: Identifiant de l'élément
            photo_type: Type de photo à filtrer (optionnel)

        Returns:
            List[Photo]: Liste des photos trouvées
        """
        pass
