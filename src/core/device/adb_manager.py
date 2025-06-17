# core/device/adb_manager.py
import sys
from pathlib import Path
from typing import List, Optional, Dict
from loguru import logger
import time
import subprocess
import platform
import os
import shutil

from PyQt6.QtCore import QProcess

class ADBManager:
    """Gère les interactions avec les appareils Android via adb et scrcpy."""

    def __init__(self):
        """
        Initialise le gestionnaire ADB.
        """
        self.current_device = None
        self.adb_command = None  # Sera None si ADB non trouvé
        self.adb_available = False
        self._initialize_adb()

    def _initialize_adb(self):
        """Initialise ADB de manière sécurisée sans planter l'application."""
        try:
            self._start_adb_server()
            self.adb_available = True
            logger.info("ADB initialisé avec succès")
        except Exception as e:
            self.adb_available = False
            logger.warning(f"ADB non disponible : {e}")
            # On ne lance plus d'exception, on continue sans ADB

    def is_adb_available(self) -> bool:
        """Vérifie si ADB est disponible."""
        return self.adb_available

    def retry_adb_initialization(self) -> bool:
        """Tente de réinitialiser ADB. Retourne True si succès."""
        try:
            self._start_adb_server()
            self.adb_available = True
            logger.info("ADB réinitialisé avec succès")
            return True
        except Exception as e:
            self.adb_available = False
            logger.error(f"Échec de réinitialisation ADB : {e}")
            return False

    def _start_adb_server(self):
        """Démarre le serveur ADB en essayant différentes versions."""
        tried_paths = []

        for adb_path in self._get_adb_paths():
            try:
                logger.debug(f"Tentative avec ADB : {adb_path}")
                if not self._test_adb(adb_path):
                    tried_paths.append(f"{adb_path} (test échoué)")
                    continue

                # Stocke le chemin ADB fonctionnel pour une utilisation ultérieure
                self.adb_command = adb_path

                # Démarre le serveur avec l'ADB trouvé
                subprocess.run(
                    f'"{adb_path}" start-server',
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=10  # Timeout de 10 secondes
                )
                logger.info(f"Serveur ADB démarré avec succès via {adb_path}")
                return True

            except Exception as e:
                tried_paths.append(f"{adb_path} (erreur: {str(e)})")
                continue

        # Si on arrive ici, aucun ADB n'a fonctionné
        error_msg = "Aucune version d'ADB n'a fonctionné.\nTentatives :\n" + "\n".join(
            tried_paths)
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    def connect(self) -> bool:
        """Tente de se connecter à un appareil USB."""
        if not self.adb_available:
            logger.error("ADB n'est pas disponible, impossible de se connecter")
            return False

        try:
            # Redémarre le serveur ADB
            if not hasattr(self, 'adb_command') or not self.adb_command:
                logger.error("ADB n'est pas initialisé correctement")
                return False

            result = subprocess.run(
                f'"{self.adb_command}" devices',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5  # Timeout de 5 secondes
            )

            logger.debug(f"Résultat de adb devices: {result.stdout}")

            devices = []
            for line in result.stdout.splitlines()[1:]:
                if '\tdevice' in line:
                    device_id = line.split('\t')[0]
                    devices.append(device_id)
                    logger.debug(f"Appareil trouvé: {device_id}")

            if devices:
                self.current_device = devices[0]
                logger.info(f"Connecté à l'appareil: {self.current_device}")
                return True

            logger.warning("Aucun appareil trouvé")
            return False

        except subprocess.TimeoutExpired:
            logger.error("Timeout lors de la connexion ADB")
            return False
        except Exception as e:
            logger.error(f"Erreur de connexion ADB: {e}")
            return False

    def is_connected(self) -> bool:
        """Vérifie si un appareil est connecté."""
        return bool(self.current_device)

    def _get_adb_paths(self) -> List[str]:
        """Retourne une liste de chemins ADB possibles dans l'ordre de préférence."""
        paths = []

        if platform.system() == "Windows":
            # Chemins système courants
            system_paths = [
                os.path.expandvars(
                    "%LOCALAPPDATA%\\Android\\Sdk\\platform-tools\\adb.exe"),
                os.path.expandvars(
                    "%USERPROFILE%\\AppData\\Local\\Android\\Sdk\\platform-tools\\adb.exe"),
                "C:\\platform-tools\\adb.exe",  # Chemin additionnel
                str(Path.home() / "platform-tools" / "adb.exe"),
                # Au cas où dans le home user
                str(Path("C:/") / "platform-tools" / "adb.exe"),
                # Version avec Path
            ]
            paths.extend(system_paths)

            # Chemin dans le package de l'application (pour la prod)
            if getattr(sys, 'frozen', False):
                app_path = Path(sys._MEIPASS) / "tools" / "adb" / "adb.exe"
                paths.append(str(app_path))

            # ADB dans le venv ou PATH
            paths.append("adb")
        else:
            # Chemins Unix
            unix_paths = [
                "/usr/bin/adb",
                "/usr/local/bin/adb",
                str(Path.home() / "platform-tools" / "adb"),
                "adb"  # Dans le PATH
            ]
            paths.extend(unix_paths)

        return paths

    def _test_adb(self, adb_path: str) -> bool:
        """Teste si un chemin ADB fonctionne."""
        try:
            result = subprocess.run(
                f'"{adb_path}" version',
                shell=True,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_device_info(self) -> Optional[Dict[str, str]]:
        """Récupère les informations sur l'appareil connecté."""
        if not self.is_connected():
            return None

        try:
            cmd_props = {
                'model': 'ro.product.model',
                'manufacturer': 'ro.product.manufacturer',
                'android_version': 'ro.build.version.release'
            }

            device_info = {}
            for key, prop in cmd_props.items():
                result = subprocess.run(
                    f'"{self.adb_command}" -s {self.current_device} shell getprop {prop}',
                    shell=True,
                    capture_output=True,
                    text=True
                )
                device_info[key] = result.stdout.strip()

            return device_info

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des infos: {e}")
            return None

    def disconnect(self):
        """Déconnecte l'appareil et arrête scrcpy."""
        try:
            # Arrête le serveur ADB
            if self.adb_command:
                subprocess.run(
                    f'"{self.adb_command}" kill-server',
                    shell=True,
                    capture_output=True,
                    text=True
                )
            logger.info("Serveur ADB arrêté")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du serveur ADB: {e}")
        finally:
            self.device = None
            self.current_device = None

    def _list_dcim_photos(self) -> list[str]:
        """Liste toutes les photos dans les dossiers possibles de l'appareil."""
        try:
            paths = [
                "/storage/emulated/0/DCIM/100ANDRO",
                "/storage/emulated/0/DCIM/Camera",
                "/storage/emulated/0/Pictures/Camera",
                "/sdcard/DCIM/Camera",
                "/storage/emulated/0/DCIM/100MEDIA",
                "/storage/emulated/0/Pictures",
                "/storage/emulated/0/DCIM"
            ]

            all_photos = []

            for dir_path in paths:
                logger.debug(f"Recherche de photos dans: {dir_path}")

                # Liste d'abord le contenu du dossier sans filtre
                cmd_list = f'"{self.adb_command}" -s {self.current_device} shell ls "{dir_path}"'
                result_list = subprocess.run(cmd_list, shell=True, capture_output=True,
                                             text=True)

                if result_list.returncode == 0:
                    logger.debug(f"Contenu de {dir_path}: {result_list.stdout}")
                else:
                    logger.debug(f"Erreur listing {dir_path}: {result_list.stderr}")

                # Cherche les photos avec les deux patterns (JPG et jpg)
                patterns = ["*.JPG", "*.jpg"]
                for pattern in patterns:
                    cmd_photos = f'"{self.adb_command}" -s {self.current_device} shell ls "{dir_path}/{pattern}"'
                    result_photos = subprocess.run(cmd_photos, shell=True,
                                                   capture_output=True, text=True)

                    if result_photos.returncode == 0 and not "No such file or directory" in result_photos.stderr:
                        photos = [f.strip() for f in result_photos.stdout.splitlines()
                                  if
                                  f.strip() and not "*" in f]  # Évite les wildcards non résolus

                        # Ajoute le chemin complet
                        full_path_photos = [
                            f if f.startswith('/') else f"{dir_path}/{f}" for f in
                            photos]
                        all_photos.extend(full_path_photos)
                        if photos:
                            logger.debug(
                                f"Trouvé {len(photos)} photos en {pattern} dans {dir_path}")
                            logger.debug(f"Exemple de photo: {full_path_photos[0]}")

            # Log le résultat final
            if all_photos:
                logger.info(f"Total des photos trouvées: {len(all_photos)}")
            else:
                logger.warning("Aucune photo trouvée dans aucun des dossiers testés")

            return all_photos

        except Exception as e:
            logger.error(f"Erreur lors du listing des photos: {e}")
            logger.exception(e)
            return []

    def take_photo(self, save_path: Path, status_callback=None) -> bool:
        """
        Prend une photo et transfère toutes les photos du téléphone.

        Args:
            save_path: Chemin de sauvegarde sur le PC (détermine le format de nommage)
            status_callback: Fonction appelée avec le message d'état

        Returns:
            bool: True si au moins une photo a été transférée
        """
        try:
            # Étape 1 : Prise de photo
            if status_callback:
                status_callback("Prise de photo...")

            logger.debug("Déclenchement de la capture via bouton volume")
            volume_cmd = f'"{self.adb_command}" -s {self.current_device} shell input keyevent 24'
            subprocess.run(volume_cmd, shell=True, check=True)

            # Étape 2 : Attente enregistrement
            if status_callback:
                status_callback("Enregistrement en cours...")

            time.sleep(3)  # Attends que la photo soit enregistrée

            # Étape 3 : Transfert de toutes les photos
            return self._transfer_all_photos(save_path, status_callback)

        except Exception as e:
            logger.error(f"Erreur lors de la prise de photo: {e}")
            if status_callback:
                status_callback(f"Erreur: {str(e)}")
            return False

    def _transfer_all_photos(self, save_path: Path, status_callback=None) -> bool:
        """
        Transfère toutes les photos du téléphone en les renommant selon le modèle.

        Args:
            save_path: Chemin de sauvegarde qui sert de modèle pour le nommage
            status_callback: Fonction appelée avec le message d'état
        """
        try:
            # Recherche des photos
            if status_callback:
                status_callback("Recherche des photos...")

            phone_photos = self._list_dcim_photos()
            if not phone_photos:
                logger.error("Aucune photo trouvée sur le téléphone")
                if status_callback:
                    status_callback("Aucune photo trouvée")
                return False

            # Crée le dossier de destination si nécessaire
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Détermine le type de photo à partir du nom cible
            photo_type = save_path.stem.split('_')[-2]

            # Trouve le dernier numéro utilisé dans le dossier pour ce type
            existing_photos = list(save_path.parent.glob(f"*_{photo_type}_*.jpg"))
            last_num = 0
            for photo in existing_photos:
                try:
                    num = int(photo.stem.split('_')[-1])
                    last_num = max(last_num, num)
                except (ValueError, IndexError):
                    continue

            # Transfère chaque photo avec un nouveau nom
            success = False
            total_photos = len(phone_photos)

            for i, phone_photo in enumerate(phone_photos, 1):
                last_num += 1
                new_name = save_path.parent / f"{save_path.stem[:-1]}{last_num}.jpg"

                # Message d'état selon le nombre de photos
                if total_photos == 1:
                    if status_callback:
                        status_callback("Transfert de la photo...")
                else:
                    if status_callback:
                        status_callback(f"Transfert photo {i}/{total_photos}...")

                pull_cmd = f'"{self.adb_command}" -s {self.current_device} pull "{phone_photo}" "{new_name}"'
                result = subprocess.run(pull_cmd, shell=True, capture_output=True,
                                        text=True)

                if result.returncode == 0:
                    logger.info(f"Photo transférée avec succès vers {new_name}")
                    success = True
                else:
                    logger.error(
                        f"Erreur lors du transfert de {phone_photo}: {result.stderr}")

            # Supprime les photos du téléphone après transfert réussi
            if success:
                if status_callback:
                    status_callback("Nettoyage du téléphone...")

                for phone_photo in phone_photos:
                    rm_cmd = f'"{self.adb_command}" -s {self.current_device} shell rm "{phone_photo}"'
                    subprocess.run(rm_cmd, shell=True)
                logger.info("Photos supprimées du téléphone après transfert")

                if status_callback:
                    if total_photos == 1:
                        status_callback("Photo transférée")
                    else:
                        status_callback(f"{total_photos} photos transférées")

            return success

        except Exception as e:
            logger.error(f"Erreur lors du transfert des photos: {e}")
            if status_callback:
                status_callback(f"Erreur: {str(e)}")
            return False