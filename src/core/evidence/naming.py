# evidence/naming.py
"""Gestion du nommage des fichiers photos."""

from pathlib import Path


def create_photo_filename(scelle_num: str, photo_type: str, sequence: int) -> str:
    """
    Crée un nom de fichier selon la convention de nommage.

    Args:
        scelle_num: Numéro du scellé (ex: "2024-001_A")
        photo_type: Type de photo (ex: "Ferme", "Contenu", "A")
        sequence: Numéro de séquence de la photo

    Returns:
        str: Nom du fichier formaté (ex: "2024-001_A_Ferme_1.jpg")
    """
    return f"{scelle_num}_{photo_type}_{sequence}.jpg"

# class PhotoNaming:
#     """Gestion du nommage des fichiers photos."""
#
#     @staticmethod
#     def get_photo_filename(scelle_num: str, scelle_name: str, photo_type: str,
#                            sequence: int) -> str:
#         """
#         Crée un nom de fichier selon la convention.
#
#         Args:
#             scelle_num: Numéro du scellé
#             scelle_name: Nom du scellé
#             photo_type: Type de photo
#             sequence: Numéro de séquence
#
#         Returns:
#             str: Nom du fichier formaté
#         """
#         return f"{scelle_num}_{scelle_name}_{photo_type}_{sequence}.jpg"
#
#     @staticmethod
#     def parse_filename(filename: str) -> tuple[str, str, str, int]:
#         """
#         Extrait les informations d'un nom de fichier.
#
#         Args:
#             filename: Nom du fichier à analyser
#
#         Returns:
#             tuple: (numéro_scellé, nom_scellé, type_photo, séquence)
#         """
#         parts = Path(filename).stem.split("_")
#         if len(parts) != 4:
#             raise ValueError(f"Format de fichier invalide : {filename}")
#         return parts[0], parts[1], parts[2], int(parts[3])
