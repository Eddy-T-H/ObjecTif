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

    def get_existing_objects(self) -> List[str]:
        """
        Découvre les objets existants en analysant les identifiants utilisés.
        Retourne uniquement les lettres réellement utilisées.

        Returns:
            List[str]: Liste triée des lettres d'objets
        """
        logger.debug("Recherche des objets existants")
        objects = set()

        # Garde une trace des identifiants déjà créés pendant cette session
        if not hasattr(self, '_created_objects'):
            self._created_objects = set()

        # Ajoute les objets trouvés dans les photos
        for photo_path in self.base_path.glob("*.jpg"):
            try:
                parts = photo_path.stem.split('_')
                if len(parts) >= 4:
                    object_letter = parts[2]
                    if len(object_letter) == 1 and object_letter.isalpha():
                        objects.add(object_letter)
                        logger.debug(f"Objet trouvé dans les photos: {object_letter}")
            except Exception as e:
                logger.warning(f"Erreur lors de l'analyse de {photo_path}: {e}")

        # Ajoute les objets créés dans cette session
        objects.update(self._created_objects)

        # Trie et retourne la liste complète
        result = sorted(list(objects))
        logger.debug(f"Objets trouvés au total: {result}")
        return result

    def create_item(self, item_id: str, name: str) -> EvidenceItem:
        """
        Crée un nouvel objet d'essai.
        """
        logger.debug(f"Création de l'objet {item_id}")

        if not item_id.isalpha() or not item_id.isupper():
            logger.error(f"Code d'objet invalide: {item_id}")
            raise ValueError(
                "Le code doit être composé uniquement de lettres majuscules")

        existing_objects = self.get_existing_objects()
        if item_id in existing_objects:
            logger.error(f"L'objet {item_id} existe déjà")
            raise ValueError(f"L'objet {item_id} existe déjà")

        # Ajoute l'objet à la liste des objets créés
        if not hasattr(self, '_created_objects'):
            self._created_objects = set()
        self._created_objects.add(item_id)

        return EvidenceItem(
            id=item_id,
            name=name,
            path=self.base_path,
            photos=[]
        )


    def _get_next_letter_code(self, current: str) -> str:
        """
        Génère le prochain code alphabétique dans la séquence.
        Fonctionne comme Excel : A, B, C... Z, AA, AB, AC... ZZ, AAA, etc.

        Args:
            current: Code actuel (par exemple 'A', 'Z', 'AA')

        Returns:
            str: Prochain code dans la séquence
        """
        if not current:
            return 'A'

        # Convertit le code en liste de nombres (A=0, B=1, etc.)
        values = [ord(c) - ord('A') for c in current]

        # Incrémente comme un nombre en base 26
        pos = len(values) - 1
        while pos >= 0:
            values[pos] += 1
            if values[pos] < 26:  # Si pas de retenue nécessaire
                break
            values[pos] = 0
            pos -= 1

        # Si nous avons dépassé le début, nous devons ajouter une nouvelle position
        if pos < 0:
            values = [0] + values

        # Convertit les nombres en lettres
        return ''.join(chr(v + ord('A')) for v in values)

    def get_next_available_code(self) -> str:
        """
        Détermine le prochain code disponible pour un nouvel objet.
        Utilise la logique de séquençage A, B, C... Z, AA, AB, AC...

        Returns:
            str: Le prochain code disponible dans la séquence
        """
        existing = self.get_existing_objects()
        if not existing:
            return 'A'  # Premier objet

        last_code = existing[-1]
        return self._get_next_letter_code(last_code)  # Utilisation interne correcte