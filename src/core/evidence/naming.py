# evidence/naming.py
"""Système de nommage unifié pour les fichiers photos."""

from enum import Enum
from pathlib import Path


class PhotoType(Enum):
    """Types de photos standardisés."""
    FERME = "Ferme"
    CONTENU = "Contenu"
    RECONDITIONNE = "Reconditionne"
    OBJET = "Objet"  # Pour les photos d'objets, sera suffixé par la lettre


class PhotoNaming:
    """Gestion du nommage des fichiers photos."""

    @staticmethod
    def get_photo_filename(scelle_num: str, scelle_name: str, photo_type: str,
                           sequence: int) -> str:
        """
        Crée un nom de fichier selon la convention.

        Args:
            scelle_num: Numéro du scellé
            scelle_name: Nom du scellé
            photo_type: Type de photo
            sequence: Numéro de séquence

        Returns:
            str: Nom du fichier formaté
        """
        return f"{scelle_num}_{scelle_name}_{photo_type}_{sequence}.jpg"

    @staticmethod
    def parse_filename(filename: str) -> tuple[str, str, str, int]:
        """
        Extrait les informations d'un nom de fichier.

        Args:
            filename: Nom du fichier à analyser

        Returns:
            tuple: (numéro_scellé, nom_scellé, type_photo, séquence)
        """
        parts = Path(filename).stem.split("_")
        if len(parts) != 4:
            raise ValueError(f"Format de fichier invalide : {filename}")
        return parts[0], parts[1], parts[2], int(parts[3])
