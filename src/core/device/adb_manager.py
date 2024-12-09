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
import re

from PyQt6.QtCore import QProcess
from adb_shell.adb_device import AdbDeviceUsb
from adb_shell.auth.sign_pythonrsa import PythonRSASigner
from adb_shell.auth.keygen import keygen


class ADBManager:
    """Gère les interactions avec les appareils Android via adb et scrcpy."""

    def __init__(self, keys_path: Path = None):
        """
        Initialise le gestionnaire ADB.

        Args:
            keys_path: Chemin vers les fichiers de clés ADB. Si non fourni,
                      utilise le dossier par défaut de l'application
        """
        self.device = None
        self.signer = None
        self.current_device = None
        self.scrcpy_process = None
        self.keys_path = keys_path or Path.home() / ".android"
        self._ensure_keys()
        self._start_adb_server()

    def _ensure_keys(self):
        """Assure que les clés ADB existent, les génère si nécessaire."""
        key_file = self.keys_path / "adbkey"
        try:
            if not key_file.exists() or not (key_file.with_suffix(".pub")).exists():
                logger.info("Génération des clés ADB...")
                self.keys_path.mkdir(parents=True, exist_ok=True)
                keygen(str(key_file))

            # Charge les clés
            with open(key_file) as f:
                priv = f.read()
            with open(key_file.with_suffix(".pub")) as f:
                pub = f.read()

            self.signer = PythonRSASigner(pub, priv)
            logger.info("Clés ADB chargées avec succès")

        except Exception as e:
            logger.error(f"Erreur lors de la gestion des clés ADB: {e}")
            raise RuntimeError("Impossible d'initialiser les clés ADB")

    def start_scrcpy(self) -> bool:
        """
        Lance scrcpy pour le mirroring de l'écran.

        Returns:
            bool: True si le lancement est réussi
        """
        try:
            if not self.current_device:
                logger.error("Aucun appareil connecté")
                return False

            # Détermine le chemin de scrcpy selon l'OS
            if platform.system() == "Windows":
                scrcpy_cmd = ".\\scrcpy\\scrcpy.exe"
            else:
                # Sur Linux/MacOS, vérifie que scrcpy est installé
                if not shutil.which("scrcpy"):
                    logger.error("scrcpy n'est pas installé sur le système")
                    return False
                scrcpy_cmd = "scrcpy"

            # Prépare la commande avec les arguments
            command = [
                scrcpy_cmd,
                "--serial",
                self.current_device,
                "--window-title",
                "Prévisualisation Android",
                "--window-width",
                "400",
                "--window-height",
                "800",
            ]

            # Lance scrcpy dans un processus séparé
            self.scrcpy_process = QProcess()
            self.scrcpy_process.start(command[0], command[1:])

            logger.info("Mirroring scrcpy démarré")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du lancement de scrcpy: {e}")
            return False

    def stop_scrcpy(self):
        """Arrête le processus scrcpy s'il est en cours."""
        if (
            self.scrcpy_process
            and self.scrcpy_process.state() == QProcess.ProcessState.Running
        ):
            self.scrcpy_process.terminate()
            self.scrcpy_process.waitForFinished(3000)  # Attend 3 secondes max
            if self.scrcpy_process.state() == QProcess.ProcessState.Running:
                self.scrcpy_process.kill()
            logger.info("Mirroring scrcpy arrêté")
            self.scrcpy_process = None

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
                    text=True
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
        self.stop_scrcpy()
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

    def connect(self) -> bool:
        """Tente de se connecter à un appareil USB."""
        try:
            # Redémarre le serveur ADB
            self._start_adb_server()

            if not hasattr(self, 'adb_command'):
                logger.error("ADB n'est pas initialisé correctement")
                return False

            result = subprocess.run(
                f'"{self.adb_command}" devices',
                shell=True,
                capture_output=True,
                text=True
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

        except Exception as e:
            logger.error(f"Erreur de connexion ADB: {e}")
            return False

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

        except Exception as e:
            logger.error(f"Erreur lors du listing des photos: {e}")
            logger.exception(e)
            return []

    def take_photo(self, save_path: Path) -> bool:
        """
        Prend une photo et transfère toutes les photos du téléphone.

        Args:
            save_path: Chemin de sauvegarde sur le PC (détermine le format de nommage)

        Returns:
            bool: True si au moins une photo a été transférée
        """
        try:
            # Simule l'appui sur le bouton volume pour prendre la photo
            logger.debug("Déclenchement de la capture via bouton volume")
            volume_cmd = f'"{self.adb_command}" -s {self.current_device} shell input keyevent 24'
            subprocess.run(volume_cmd, shell=True, check=True)

            # Attends que la photo soit enregistrée
            time.sleep(3)

            # Récupère toutes les photos et les transfère
            return self._transfer_all_photos(save_path)

        except Exception as e:
            logger.error(f"Erreur lors de la prise de photo: {e}")
            return False

    def _transfer_all_photos(self, save_path: Path) -> bool:
        """
        Transfère toutes les photos du téléphone en les renommant selon le modèle.

        Args:
            save_path: Chemin de sauvegarde qui sert de modèle pour le nommage
        """
        try:
            # Liste toutes les photos sur le téléphone
            phone_photos = self._list_dcim_photos()
            if not phone_photos:
                logger.error("Aucune photo trouvée sur le téléphone")
                return False

            # Crée le dossier de destination si nécessaire
            save_path.parent.mkdir(parents=True, exist_ok=True)

            # Détermine le type de photo à partir du nom cible
            # Ex: si save_path est "scelle_01_Ferme_1.jpg", on extrait "Ferme"
            photo_type = save_path.stem.split('_')[
                -2]  # Attention aux noms d'objets (A, B, C...)

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
            for phone_photo in phone_photos:
                last_num += 1
                new_name = save_path.parent / f"{save_path.stem[:-1]}{last_num}.jpg"

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
                for phone_photo in phone_photos:
                    rm_cmd = f'"{self.adb_command}" -s {self.current_device} shell rm "{phone_photo}"'
                    subprocess.run(rm_cmd, shell=True)
                logger.info("Photos supprimées du téléphone après transfert")

            return success

        except Exception as e:
            logger.error(f"Erreur lors du transfert des photos: {e}")
            return False
