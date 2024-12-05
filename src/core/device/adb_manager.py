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

    def take_photo(self, save_path: Path) -> bool:
        """
        Prend une photo avec l'appareil Android et la transfère vers le PC.

        Args:
            save_path: Chemin où sauvegarder la photo

        Returns:
            bool: True si la photo est prise et transférée avec succès
        """
        try:
            if not self.is_connected():
                logger.error("Pas d'appareil connecté")
                return False

            #VOIR POUR DETECTER SI APPAREIL PHOTO DEJA LANCE ? SI NON, OUVRIR

            # # Lance l'appareil photo
            # subprocess.run(
            #     f'"{self.adb_command}" -s {self.current_device} shell '
            #     f'am start -a android.media.action.IMAGE_CAPTURE',
            #     shell=True, check=True
            # )
            #
            # # Attend que l'app soit lancée
            # time.sleep(1.5)

            # Prend la photo avec KEYCODE_CAMERA
            # Ne semble pas fonctionner
            subprocess.run(
                f'"{self.adb_command}" -s {self.current_device} shell '
                f'input keyevent 27',
                shell=True, check=True
            )

            # Attend que la photo soit sauvegardée
            time.sleep(2)

            # Scan le dossier DCIM pour trouver la nouvelle photo
            path_dcim = "/sdcard/DCIM"
            list_file = []

            # Liste les sous-dossiers de DCIM
            cmd = f'"{self.adb_command}" -s {self.current_device} shell ls {path_dcim}'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            subdirs = [d for d in result.stdout.splitlines() if d]

            # Cherche les photos dans chaque sous-dossier
            for subdir in subdirs:
                cmd = f'"{self.adb_command}" -s {self.current_device} shell ls {path_dcim}/{subdir}'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                files = result.stdout.splitlines()

                for f in files:
                    if re.search(r"(.jpg|.jpeg|.png)$", f, re.IGNORECASE):
                        list_file.append(f"{path_dcim}/{subdir}/{f}")

            if not list_file:
                logger.error("Aucune photo trouvée")
                return False

            # Prend la dernière photo de la liste (la plus récente)
            latest_photo = list_file[0]

            # Transfère la photo
            subprocess.run(
                f'"{self.adb_command}" -s {self.current_device} pull "{latest_photo}" "{save_path}"',
                shell=True, check=True
            )

            # Supprime la photo de l'appareil
            subprocess.run(
                f'"{self.adb_command}" -s {self.current_device} shell rm "{latest_photo}"',
                shell=True
            )

            logger.info(f"Photo sauvegardée : {save_path}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"Erreur lors de la prise de photo : {e}")
            return False
        except Exception as e:
            logger.error(f"Erreur inattendue : {e}")
            return False