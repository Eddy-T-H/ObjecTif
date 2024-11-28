"""
Gestionnaire de preuves simplifié qui suit une convention de nommage stricte pour les fichiers.
La structure est basée sur un dossier par scellé, avec tous les fichiers photos au même niveau.

Convention de nommage :
- Photos de scellé fermé : [NUM_SCELLE]_[NOM]_Ferme_[N].jpg
- Photos de contenu : [NUM_SCELLE]_[NOM]_Contenu_[N].jpg
- Photos d'objets : [NUM_SCELLE]_[NOM]_[LETTRE]_[N].jpg
- Photos reconditionnement : [NUM_SCELLE]_[NOM]_Reconditionne_[N].jpg
"""

from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import re
from loguru import logger


@dataclass
class Photo:
    """Représente une photo avec ses métadonnées extraites du nom de fichier."""

    path: Path
    scelle_num: str
    scelle_name: str
    photo_type: (
        str  # 'Ferme', 'Contenu', 'Reconditionne' ou lettre d'objet (A, B, C...)
    )
    sequence: int

    @classmethod
    def from_filename(cls, path: Path) -> Optional["Photo"]:
        """Crée un objet Photo à partir d'un nom de fichier."""
        # Pattern pour extraire les informations du nom de fichier
        pattern = r"(\d+)_([A-Za-z0-9]+)_([A-Za-z0-9]+)_(\d+)\.jpg"
        match = re.match(pattern, path.name)

        if match:
            scelle_num, scelle_name, photo_type, sequence = match.groups()
            return cls(
                path=path,
                scelle_num=scelle_num,
                scelle_name=scelle_name,
                photo_type=photo_type,
                sequence=int(sequence),
            )
        return None


@dataclass
class Scelle:
    """Représente un scellé avec ses photos."""

    number: str
    name: str
    path: Path
    creation_date: datetime

    def get_next_photo_number(self, photo_type: str) -> int:
        """Détermine le prochain numéro de séquence pour un type de photo."""
        pattern = f"{self.number}_{self.name}_{photo_type}_(\d+)\.jpg"
        max_sequence = 0

        for file in self.path.glob(f"{self.number}_{self.name}_{photo_type}_*.jpg"):
            match = re.match(pattern, file.name)
            if match:
                sequence = int(match.group(1))
                max_sequence = max(max_sequence, sequence)

        return max_sequence + 1

    def get_next_object_letter(self) -> str:
        """Détermine la prochaine lettre disponible pour un objet d'essai."""
        used_letters = set()
        pattern = f"{self.number}_{self.name}_([A-Z])_\d+\.jpg"

        for file in self.path.glob(f"{self.number}_{self.name}_[A-Z]_*.jpg"):
            match = re.match(pattern, file.name)
            if match:
                used_letters.add(match.group(1))

        # Trouve la première lettre non utilisée
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if letter not in used_letters:
                return letter

        raise ValueError("Toutes les lettres sont utilisées")


class CaseManager:
    """Gère une affaire et ses scellés."""

    def __init__(self, case_path: Path):
        """Initialise le gestionnaire avec le chemin du dossier d'affaire."""
        self.case_path = Path(case_path)
        if not self.case_path.exists():
            raise ValueError(f"Le dossier d'affaire n'existe pas : {case_path}")

        # Charge la structure existante
        self.scelles = self._load_existing_structure()

    def _load_existing_structure(self) -> Dict[str, Scelle]:
        """Analyse le dossier d'affaire et identifie les scellés existants."""
        scelles = {}

        for item in self.case_path.iterdir():
            if item.is_dir():
                # Extrait le numéro et le nom du scellé depuis le nom du dossier
                match = re.match(r"(\d+)_([A-Za-z0-9]+)", item.name)
                if match:
                    num, name = match.groups()
                    creation_time = datetime.fromtimestamp(item.stat().st_ctime)

                    scelles[item.name] = Scelle(
                        number=num, name=name, path=item, creation_date=creation_time
                    )
                    logger.info(f"Chargé scellé existant : {item.name}")

        return scelles

    def create_scelle(self, number: str, name: str) -> Scelle:
        """Crée un nouveau dossier de scellé."""
        scelle_name = f"{number}_{name}"
        if scelle_name in self.scelles:
            raise ValueError(f"Le scellé {scelle_name} existe déjà")

        scelle_path = self.case_path / scelle_name
        scelle_path.mkdir(exist_ok=False)

        scelle = Scelle(
            number=number, name=name, path=scelle_path, creation_date=datetime.now()
        )

        self.scelles[scelle_name] = scelle
        logger.info(f"Créé nouveau scellé : {scelle_name}")

        return scelle

    def add_photo(self, scelle: Scelle, source_path: Path, photo_type: str) -> Path:
        """
        Ajoute une photo à un scellé avec le bon nommage.

        Args:
                scelle: Le scellé concerné
                source_path: Chemin de la photo source
                photo_type: 'Ferme', 'Contenu', 'Reconditionne' ou lettre d'objet
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Photo source introuvable : {source_path}")

        # Détermine le numéro de séquence
        sequence = scelle.get_next_photo_number(photo_type)

        # Crée le nouveau nom de fichier
        new_name = f"{scelle.number}_{scelle.name}_{photo_type}_{sequence}.jpg"
        dest_path = scelle.path / new_name

        # Copie le fichier
        import shutil

        shutil.copy2(source_path, dest_path)

        logger.info(f"Photo ajoutée : {new_name}")
        return dest_path
