# core/evidence/objet.py
import threading

from .base import EvidenceBase, EvidenceItem, Photo
from pathlib import Path
from typing import List, Optional
from loguru import logger

from .naming import PhotoType, PhotoNaming


class ObjetEssai(EvidenceBase):
    """Gestion des objets d'essai basée uniquement sur les photos existantes."""

    def __init__(self, scelle_path: Path):
        """
        Initialise le gestionnaire d'objets d'essai.

        Args:
            scelle_path: Chemin du dossier du scellé parent
        """
        logger.debug(f"Initialisation ObjetEssai: {scelle_path}")
        super().__init__(scelle_path)

        # Extrait l'ID et le nom du scellé parent depuis le nom du dossier
        try:
            self.scelle_id = self.base_path.name.split('_')[0]
            self.scelle_name = '_'.join(self.base_path.name.split('_')[1:])
            logger.debug(f"Scellé parent: ID={self.scelle_id}, Nom={self.scelle_name}")
        except Exception as e:
            logger.error(f"Erreur lors du parsing du nom du scellé: {e}")
            raise

    def get_existing_objects(self) -> List[str]:
        """
        Découvre les objets existants en analysant les photos.
        Complète automatiquement les lettres manquantes.

        Returns:
            List[str]: Liste triée des lettres d'objets trouvées
        """
        logger.debug("Recherche des objets existants")
        objects = set()

        # Analyse les photos pour trouver les lettres d'objets
        for photo_path in self.base_path.glob("*.jpg"):
            try:
                parts = photo_path.stem.split('_')
                if len(parts) >= 4:
                    object_letter = parts[2]
                    if len(object_letter) == 1 and object_letter.isalpha():
                        objects.add(object_letter)
                        logger.debug(f"Objet trouvé: {object_letter}")
            except Exception as e:
                logger.warning(f"Erreur lors de l'analyse de {photo_path}: {e}")

        # Complète les lettres manquantes si des objets ont été trouvés
        if objects:
            max_letter = max(objects)
            all_letters = set(chr(i) for i in range(ord('A'), ord(max_letter) + 1))
            missing_letters = all_letters - objects
            if missing_letters:
                logger.debug(f"Ajout des lettres manquantes: {missing_letters}")
            objects.update(all_letters)

        result = sorted(list(objects))
        logger.debug(f"Objets trouvés: {result}")
        return result

    def get_item(self, item_id: str) -> Optional[EvidenceItem]:
        """
        Récupère un objet par sa lettre.

        Args:
            item_id: Lettre de l'objet (A, B, C, etc.)

        Returns:
            Optional[EvidenceItem]: L'objet trouvé ou None
        """
        if len(item_id) != 1 or not item_id.isalpha():
            logger.warning(f"ID d'objet invalide: {item_id}")
            return None

        # Vérifie si l'objet existe dans les photos
        if item_id not in self.get_existing_objects():
            logger.warning(f"Objet {item_id} non trouvé")
            return None

        return EvidenceItem(
            id=item_id,
            name=f"Objet {item_id}",
            path=self.base_path,
            photos=self.get_photos(item_id)
        )

    def get_photos(self, item_id: str, photo_type: Optional[str] = None) -> List[Photo]:
        """
        Récupère les photos d'un objet.

        Args:
            item_id: Lettre de l'objet
            photo_type: Non utilisé pour les objets

        Returns:
            List[Photo]: Liste des photos triées par numéro de séquence
        """
        logger.debug(f"Recherche des photos pour l'objet {item_id}")
        photos = []

        for photo_path in self.base_path.glob(f"*{item_id}*.jpg"):
            try:
                parts = photo_path.stem.split("_")
                if len(parts) >= 4 and parts[2] == item_id:
                    seq = int(parts[3])
                    photos.append(
                        Photo(
                            path=photo_path,
                            type=item_id,
                            sequence=seq
                        )
                    )
            except Exception as e:
                logger.warning(f"Erreur lors du parsing de {photo_path}: {e}")

        return sorted(photos, key=lambda p: p.sequence)

    def create_item(self, item_id: str, name: str) -> EvidenceItem:
        """
        Crée un nouvel objet d'essai.

        Args:
            item_id: Lettre de l'objet
            name: Nom de l'objet

        Returns:
            EvidenceItem: Le nouvel objet créé
        """
        logger.debug(f"Création de l'objet {item_id}")

        if len(item_id) != 1 or not item_id.isalpha():
            logger.error(f"ID d'objet invalide: {item_id}")
            raise ValueError("L'identifiant doit être une lettre unique")

        existing_objects = self.get_existing_objects()
        if item_id in existing_objects:
            logger.error(f"L'objet {item_id} existe déjà")
            raise ValueError(f"L'objet {item_id} existe déjà")

        return EvidenceItem(
            id=item_id,
            name=name,
            path=self.base_path,
            photos=[]
        )
