# src/utils/error_handler.py

"""
Gestionnaire d'erreurs avec messages utilisateur conviviaux.
"""

from typing import Tuple
from loguru import logger
import subprocess


class UserFriendlyErrorHandler:
    """Convertit les erreurs techniques en messages utilisateur clairs."""

    @staticmethod
    def handle_adb_error(exception: Exception, operation: str = "") -> Tuple[str, str]:
        """
        Gère les erreurs ADB et retourne un message utilisateur.

        Args:
                exception: Exception technique
                operation: Description de l'opération en cours

        Returns:
                Tuple[str, str]: (titre_erreur, message_detaille)
        """
        error_str = str(exception).lower()

        if "timeout" in error_str:
            return (
                "Appareil non réactif",
                "L'appareil Android ne répond pas.\n\n"
                "Solutions :\n"
                "• Vérifiez que l'appareil est déverrouillé\n"
                "• Débranchez et rebranchez le câble USB\n"
                "• Redémarrez l'appareil si nécessaire",
            )

        if "device not found" in error_str or "no devices" in error_str:
            return (
                "Appareil introuvable",
                "Aucun appareil Android détecté.\n\n"
                "Solutions :\n"
                "• Vérifiez que le câble USB est bien connecté\n"
                "• Activez le débogage USB dans les options développeur\n"
                "• Autorisez la connexion sur l'appareil\n"
                "• Cliquez sur 'Rafraîchir' pour rechercher à nouveau",
            )

        if "permission denied" in error_str:
            return (
                "Accès refusé",
                "L'accès à l'appareil est refusé.\n\n"
                "Solutions :\n"
                "• Autorisez la connexion de débogage sur l'appareil\n"
                "• Vérifiez que le mode développeur est activé\n"
                "• Redémarrez la connexion ADB",
            )

        if "no such file" in error_str:
            return (
                "Photo introuvable",
                "La photo n'a pas pu être trouvée sur l'appareil.\n\n"
                "Solutions :\n"
                "• Vérifiez que la photo a bien été prise\n"
                "• Attendez quelques secondes et réessayez\n"
                "• Ouvrez l'appareil photo pour vérifier",
            )

        # Erreur générique
        return (
            f"Erreur lors de {operation}" if operation else "Erreur de connexion",
            f"Une erreur technique s'est produite.\n\n"
            f"Détails : {str(exception)}\n\n"
            f"Solutions :\n"
            f"• Redémarrez la connexion\n"
            f"• Vérifiez la connexion USB\n"
            f"• Contactez le support si le problème persiste",
        )

    @staticmethod
    def handle_file_error(exception: Exception, file_path: str = "") -> Tuple[str, str]:
        """
        Gère les erreurs de fichiers/dossiers.

        Args:
                exception: Exception technique
                file_path: Chemin du fichier concerné

        Returns:
                Tuple[str, str]: (titre_erreur, message_detaille)
        """
        error_str = str(exception).lower()

        if "permission denied" in error_str or "access is denied" in error_str:
            return (
                "Accès au fichier refusé",
                f"Impossible d'accéder au dossier.\n\n"
                f"Chemin : {file_path}\n\n"
                f"Solutions :\n"
                f"• Vérifiez que le dossier n'est pas en lecture seule\n"
                f"• Fermez les applications qui utilisent ce dossier\n"
                f"• Exécutez en tant qu'administrateur si nécessaire",
            )

        if "file exists" in error_str or "already exists" in error_str:
            return (
                "Fichier déjà existant",
                f"Un dossier avec ce nom existe déjà.\n\n"
                f"Solutions :\n"
                f"• Choisissez un nom différent\n"
                f"• Supprimez le dossier existant si nécessaire\n"
                f"• Ajoutez un suffixe au nom (ex: _2)",
            )

        if "no space left" in error_str:
            return (
                "Espace disque insuffisant",
                f"Plus d'espace disponible sur le disque.\n\n"
                f"Solutions :\n"
                f"• Libérez de l'espace disque\n"
                f"• Choisissez un autre emplacement\n"
                f"• Supprimez des fichiers temporaires",
            )

        if "not found" in error_str:
            return (
                "Dossier introuvable",
                f"Le dossier spécifié n'existe pas.\n\n"
                f"Chemin : {file_path}\n\n"
                f"Solutions :\n"
                f"• Vérifiez que le chemin est correct\n"
                f"• Reconfigurer le dossier de travail\n"
                f"• Créez le dossier manuellement",
            )

        # Erreur générique
        return (
            "Erreur de fichier",
            f"Impossible de créer ou d'accéder au fichier.\n\n"
            f"Détails : {str(exception)}\n"
            f"Chemin : {file_path}",
        )

    @staticmethod
    def handle_scrcpy_error(exception: Exception) -> Tuple[str, str]:
        """
        Gère les erreurs de streaming scrcpy.

        Args:
                exception: Exception technique

        Returns:
                Tuple[str, str]: (titre_erreur, message_detaille)
        """
        error_str = str(exception).lower()

        if "scrcpy introuvable" in error_str or "not found" in error_str:
            return (
                "Scrcpy non trouvé",
                "L'outil de streaming n'est pas disponible.\n\n"
                "Solutions :\n"
                "• Vérifiez l'installation de scrcpy\n"
                "• Redémarrez l'application\n"
                "• Réinstallez si nécessaire",
            )

        if "timeout" in error_str:
            return (
                "Délai d'attente dépassé",
                "Le streaming n'a pas pu se lancer.\n\n"
                "Solutions :\n"
                "• Vérifiez la connexion de l'appareil\n"
                "• Redémarrez la connexion ADB\n"
                "• Réessayez dans quelques instants",
            )

        # Erreur générique scrcpy
        return (
            "Erreur de streaming",
            f"Impossible de démarrer la prévisualisation.\n\n"
            f"Détails : {str(exception)}\n\n"
            f"Solutions :\n"
            f"• Vérifiez la connexion de l'appareil\n"
            f"• Redémarrez l'application\n"
            f"• Vérifiez que l'appareil supporte le streaming",
        )
