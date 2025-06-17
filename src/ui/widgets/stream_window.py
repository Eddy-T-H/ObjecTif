import sys
import threading

from PyQt6.QtCore import QProcess, pyqtSignal, QObject
from pathlib import Path
from loguru import logger


class StreamWindow(QObject):
    """Gestionnaire du streaming Android via scrcpy.

    Cette classe utilise scrcpy pour créer une fenêtre de prévisualisation du périphérique
    Android. Elle gère le lancement et l'arrêt du processus scrcpy, ainsi que la gestion
    des erreurs potentielles.
    """

    # Signal émis lors de la fermeture de la fenêtre par l'utilisateur
    window_closed = pyqtSignal()
    # Signal émis en cas d'erreur critique nécessitant une déconnexion
    critical_error = pyqtSignal(str)

    def __init__(self, adb_manager, parent):
        """
        Initialise le gestionnaire de streaming.

        Args:
            adb_manager: Instance de ADBManager pour la communication avec l'appareil
            parent: Widget parent Qt pour la gestion du cycle de vie des processus
        """
        QObject.__init__(self, parent)
        try:
            self.adb_manager = adb_manager
            self.parent = parent
            self.scrcpy_process = None
            self._stopping_manually = False

            # Verrou thread-safe pour éviter les lancements multiples
            self._start_lock = threading.Lock()

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de StreamWindow: {e}")
            raise

    def start_stream(self):
        """
		Démarre le streaming dans une fenêtre scrcpy.
		Thread-safe pour éviter les lancements multiples.

		Returns:
			bool: True si le démarrage réussit, False sinon
		"""
        # Acquisition non-bloquante du verrou
        if not self._start_lock.acquire(blocking=False):
            logger.warning("Démarrage déjà en cours, requête ignorée")
            return False

        try:
            logger.debug("====== Démarrage stream ======")

            # Vérification de la connexion ADB
            if not self.adb_manager.is_connected():
                logger.warning("Tentative de streaming sans connexion ADB")
                return False

            # Arrêt de tout processus existant
            self.stop_stream()

            # Obtention du chemin scrcpy avec gestion d'erreur
            try:
                scrcpy_path = self._get_scrcpy_path()
            except FileNotFoundError as e:
                logger.error(f"Configuration scrcpy invalide: {e}")
                self.critical_error.emit("scrcpy introuvable")
                return False

            # Création et configuration du processus
            try:
                self.scrcpy_process = QProcess(self.parent)
                self.scrcpy_process.finished.connect(self._on_process_finished)
                self.scrcpy_process.errorOccurred.connect(self._on_process_error)

                # Configuration des arguments
                args = [
                    "--window-title", "Prévisualisation Android",
                    "--window-width", "400",
                    "--window-height", "800",
                    "--render-driver", "software",
                    "--stay-awake",
                    "--serial", self.adb_manager.current_device,
                    "--always-on-top"
                ]

                # Configuration du répertoire de travail
                working_dir = Path(scrcpy_path).parent
                self.scrcpy_process.setWorkingDirectory(str(working_dir))

                # Démarrage avec surveillance du timeout
                logger.debug(f"Lancement de scrcpy depuis {working_dir}")
                self.scrcpy_process.start(str(scrcpy_path), args)

                if not self.scrcpy_process.waitForStarted(5000):
                    raise TimeoutError("Timeout lors du démarrage de scrcpy")

                logger.info("Streaming démarré avec succès")
                return True

            except Exception as e:
                logger.error(f"Erreur lors du démarrage du processus: {e}")
                self.stop_stream()
                self.critical_error.emit(str(e))
                return False

        except Exception as e:
            logger.error(f"Erreur inattendue lors du démarrage du stream: {e}")
            return False

        finally:
            # Libération du verrou dans tous les cas
            self._start_lock.release()

    def stop_stream(self):
        """
		Arrête proprement le streaming en cours.
		Thread-safe.
		"""
        if self.scrcpy_process is not None:
            try:
                logger.debug("Arrêt du stream demandé")
                self._stopping_manually = True

                # Garde une référence locale pour le nettoyage
                process = self.scrcpy_process
                self.scrcpy_process = None

                process.terminate()
                if not process.waitForFinished(3000):
                    logger.warning("Le processus ne répond pas, arrêt forcé")
                    process.kill()
                    process.waitForFinished(1000)

                process.deleteLater()
                logger.info("Streaming arrêté avec succès")

            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt du stream: {e}")
            finally:
                self._stopping_manually = False

    def _on_process_finished(self, exit_code, exit_status):
        """
		Gère la fin du processus scrcpy en distinguant les différents cas de sortie.

		Les codes de sortie de scrcpy :
		0 : Sortie normale (fenêtre fermée par l'utilisateur)
		1 : Erreur d'initialisation
		2 : Sortie normale après terminate()
		"""
        logger.debug(
            f"Processus scrcpy terminé (code: {exit_code}, status: {exit_status})")

        try:
            # Nettoyage du processus
            if self.scrcpy_process is not None:
                self.scrcpy_process.deleteLater()
                self.scrcpy_process = None

            # Analyse du code de sortie
            if self._stopping_manually:
                # Si l'arrêt était demandé, pas d'action particulière nécessaire
                logger.debug("Arrêt normal du streaming")
            elif exit_code == 0:
                # Fermeture normale par l'utilisateur
                logger.debug("Fenêtre fermée par l'utilisateur")
                self.window_closed.emit()
            elif exit_code == 1:
                # Erreur réelle
                error_msg = "Erreur d'initialisation de scrcpy"
                logger.error(error_msg)
                self.critical_error.emit(error_msg)
            elif not self._stopping_manually:
                # Autres codes d'erreur non attendus
                error_msg = f"Erreur inattendue de scrcpy (code {exit_code})"
                logger.error(error_msg)
                self.critical_error.emit(error_msg)

        except Exception as e:
            logger.error(f"Erreur lors du traitement de fin de processus: {e}")

    def _on_process_error(self, error):
        """Gère les erreurs du processus scrcpy et arrête proprement le streaming."""
        try:
            error_msg = f"Erreur du processus scrcpy: {error}"
            logger.error(error_msg)
            self.critical_error.emit(error_msg)
            self.stop_stream()

        except Exception as e:
            logger.error(f"Erreur lors du traitement d'erreur: {e}")

    def _get_scrcpy_path(self):
        """
        Détermine le chemin de l'exécutable scrcpy de manière sécurisée.
        """
        try:
            if getattr(sys, 'frozen', False):
                # Si nous sommes dans un exe compilé
                base_path = Path(sys._MEIPASS)
            else:
                # En développement
                base_path = Path(__file__).resolve()
                while base_path.name != "ObjecTif" and base_path.parent != base_path:
                    base_path = base_path.parent

            scrcpy_path = base_path / "scrcpy" / "scrcpy.exe"

            if not scrcpy_path.exists():
                raise FileNotFoundError(f"scrcpy.exe non trouvé à {scrcpy_path}")

            return str(scrcpy_path)

        except Exception as e:
            logger.error(f"Erreur lors de la recherche de scrcpy: {e}")
            raise
