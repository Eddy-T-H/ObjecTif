# core/evidence/scelle.py
from .base import EvidenceBase, EvidenceItem, Photo
from typing import List, Optional
from loguru import logger

class Scelle(EvidenceBase):
    """Gestion des scellés et de leurs photos."""

    def create_item(self, item_id: str, name: str) -> EvidenceItem:
        """
        Crée un nouveau scellé.

        Args:
            item_id: Numéro du scellé
            name: Description du scellé

        Returns:
            EvidenceItem: Le scellé créé
        """
        logger.debug(f"Création du scellé {item_id}")
        item_path = self.base_path / f"{item_id}_{name}"

        if item_path.exists():
            logger.error(f"Le scellé {item_id} existe déjà")
            raise ValueError(f"Le scellé {item_id} existe déjà")

        item_path.mkdir(parents=True)
        logger.info(f"Dossier créé: {item_path}")

        return EvidenceItem(
            id=item_id,
            name=name,
            path=item_path,
            photos=[]
        )

    def get_item(self, item_name: str) -> Optional[EvidenceItem]:
        """
        Récupère un scellé par son nom de dossier complet.

        Args:
            item_name: Nom du dossier du scellé

        Returns:
            Optional[EvidenceItem]: Le scellé trouvé ou None
        """
        logger.debug(f"Recherche du scellé: {item_name}")

        try:
            for path in self.base_path.iterdir():
                if path.is_dir() and path.name == item_name:
                    logger.debug(f"Scellé trouvé: {path}")
                    return EvidenceItem(
                        id=item_name,
                        name=item_name,
                        path=path,
                        photos=self.get_photos(item_name)
                    )

            logger.warning(f"Scellé non trouvé: {item_name}")
            return None

        except Exception as e:
            logger.error(f"Erreur lors de la recherche du scellé {item_name}: {e}")
            return None

    def get_photos(self, item_name: str, photo_type: Optional[str] = None) -> List[
        Photo]:
        """
        Récupère les photos d'un scellé avec filtrage optionnel par type.

        Args:
            item_name: Nom du dossier du scellé
            photo_type: Type de photo à filtrer (optionnel)

        Returns:
            List[Photo]: Liste des photos triées
        """
        logger.debug(f"Récupération des photos pour {item_name}")
        photos = []

        # Au lieu d'appeler get_item(), on construit directement le chemin
        scelle_path = self.base_path / item_name
        if not scelle_path.exists() or not scelle_path.is_dir():
            logger.warning(f"Scellé {item_name} non trouvé")
            return []

        pattern = "*.jpg"
        for photo_path in scelle_path.glob(pattern):
            try:
                # On part de la fin du nom pour trouver le numéro de séquence et le type
                parts = photo_path.stem.split("_")
                if len(parts) < 2:  # Il nous faut au minimum type_sequence
                    continue

                # Le dernier élément est toujours le numéro de séquence
                try:
                    seq = int(parts[-1])
                except ValueError:
                    continue

                # L'avant-dernier élément est le type
                type_ = parts[-2]

                # Vérifie si c'est une photo d'objet (une seule lettre)
                # ou un des types connus
                if (len(type_) == 1 and type_.isalpha()) or \
                        type_.lower() in ['ferme', 'fermé', 'contenu', 'reconditionne', 'reconditionné',
                                          'reconditionnement']:

                    # Normalisation du type
                    photo_type_norm = type_
                    if type_.lower() in ['ferme', 'fermé']:
                        photo_type_norm = 'Ferme'
                    elif type_.lower() == 'contenu':
                        photo_type_norm = 'Contenu'
                    elif type_.lower() in ['reconditionne', 'reconditionné', 'reconditionnement']:
                        photo_type_norm = 'Reconditionne'
                    # Pour les objets, on garde la lettre telle quelle

                    # Si un type spécifique est demandé et ne correspond pas, on saute
                    if photo_type and photo_type_norm != photo_type:
                        continue

                    photos.append(
                        Photo(
                            path=photo_path,
                            type=photo_type_norm,
                            sequence=seq
                        )
                    )
                    logger.debug(
                        f"Photo ajoutée: {photo_path.name} (type: {photo_type_norm})")
                else:
                    logger.debug(f"Type de photo non reconnu: {type_}")

            except Exception as e:
                logger.warning(f"Erreur lors du parsing de {photo_path}: {e}")

        return sorted(photos, key=lambda p: (p.type, p.sequence))