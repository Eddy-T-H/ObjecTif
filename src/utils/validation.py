"""
Utilitaires de validation pour les noms de fichiers et dossiers.
"""

import re
from typing import Tuple


class FilenameValidator:
    """Validation robuste des noms de fichiers/dossiers Windows."""

    # Caractères interdits sur Windows
    FORBIDDEN_CHARS = '<>:"/\\|?*'

    # Noms réservés Windows (insensible à la casse)
    RESERVED_NAMES = {
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",
        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",
    }

    # Longueur maximale recommandée (Windows limite à 255, on garde une marge)
    MAX_LENGTH = 200

    @classmethod
    def validate(cls, name: str) -> Tuple[bool, str]:
        """
        Valide un nom de fichier/dossier.

        Args:
                name: Nom à valider

        Returns:
                Tuple[bool, str]: (est_valide, message_erreur)
        """
        if not name:
            return False, "Le nom ne peut pas être vide"

        # Supprime les espaces en début/fin
        name_clean = name.strip()
        if not name_clean:
            return False, "Le nom ne peut contenir que des espaces"

        # Vérifie si différent après nettoyage
        if name != name_clean:
            return False, "Le nom ne peut pas commencer ou finir par des espaces"

        # Vérifie les caractères interdits
        forbidden_found = [char for char in cls.FORBIDDEN_CHARS if char in name]
        if forbidden_found:
            return False, f"Caractères interdits trouvés : {', '.join(forbidden_found)}"

        # Vérifie la longueur
        if len(name) > cls.MAX_LENGTH:
            return False, f"Le nom est trop long (max {cls.MAX_LENGTH} caractères)"

        # Vérifie les noms réservés Windows
        name_upper = name.upper()
        if name_upper in cls.RESERVED_NAMES:
            return False, f"'{name}' est un nom réservé Windows"

        # Vérifie les noms réservés avec extension
        name_base = name_upper.split(".")[0]
        if name_base in cls.RESERVED_NAMES:
            return False, f"'{name}' utilise un nom réservé Windows"

        # Vérifie qu'il ne finit pas par un point ou un espace (problématique sur Windows)
        if name.endswith(".") or name.endswith(" "):
            return False, "Le nom ne peut pas finir par un point ou un espace"

        # Vérifie la présence de caractères de contrôle
        if any(ord(char) < 32 for char in name):
            return False, "Le nom contient des caractères de contrôle invalides"

        return True, ""

    @classmethod
    def suggest_fix(cls, name: str) -> str:
        """
        Propose une version corrigée du nom.

        Args:
                name: Nom à corriger

        Returns:
                str: Version corrigée du nom
        """
        if not name:
            return "nouveau_dossier"

        # Nettoie les espaces
        fixed = name.strip()

        # Supprime les caractères interdits
        for char in cls.FORBIDDEN_CHARS:
            fixed = fixed.replace(char, "_")

        # Supprime les caractères de contrôle
        fixed = "".join(char for char in fixed if ord(char) >= 32)

        # Supprime les points/espaces en fin
        fixed = fixed.rstrip(". ")

        # Vérifie les noms réservés
        if fixed.upper() in cls.RESERVED_NAMES:
            fixed = f"{fixed}_dossier"

        # Vérifie la longueur
        if len(fixed) > cls.MAX_LENGTH:
            fixed = fixed[: cls.MAX_LENGTH].rstrip(". ")

        # Si vide après nettoyage
        if not fixed:
            fixed = "nouveau_dossier"

        return fixed
