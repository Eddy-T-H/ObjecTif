# src/ui/widgets/interactive_stream_display.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMainWindow
from PyQt6.QtCore import Qt, QProcess, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QPainter
import platform
import win32gui
import win32con
from pathlib import Path
from loguru import logger

from src.ui.constants import ANDROID_SCREEN_WIDTH, ANDROID_SCREEN_HEIGHT


class InteractiveStreamDisplay(QWidget):
    """Widget permettant d'afficher et d'interagir avec un appareil Android."""

    stream_started = pyqtSignal()
    stream_stopped = pyqtSignal()

    def __init__(self, adb_manager, parent=None):
        super().__init__(parent)
        self.adb_manager = adb_manager
        self.scrcpy_process = None
        self.scrcpy_window = None
        self.is_streaming = False
        self.find_window_timer = QTimer(self)
        self.find_window_timer.timeout.connect(self._find_and_embed_window)
        self.find_window_timer.setInterval(100)  # Check every 100ms
        self._setup_ui()


    def _setup_ui(self):
        """Configure l'interface du widget."""
        self.setFixedSize(ANDROID_SCREEN_WIDTH, ANDROID_SCREEN_HEIGHT)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def _get_scrcpy_path(self):
        """Détermine le chemin de scrcpy."""
        current_dir = Path(__file__).resolve()
        while current_dir.name != "ObjecTif" and current_dir.parent != current_dir:
            current_dir = current_dir.parent

        if current_dir.name != "ObjecTif":
            raise FileNotFoundError("Dossier racine ObjecTif non trouvé")

        scrcpy_path = current_dir / "scrcpy" / "scrcpy.exe"

        if not scrcpy_path.exists():
            raise FileNotFoundError(f"scrcpy.exe non trouvé à {scrcpy_path}")

        return str(scrcpy_path)

    def start_stream(self):
        """Démarre le streaming interactif."""
        try:
            if not self.adb_manager.is_connected():
                raise RuntimeError("Aucun appareil connecté")

            logger.debug("Démarrage du streaming...")

            scrcpy_path = self._get_scrcpy_path()
            window_pos = self.mapToGlobal(QPoint(0, 0))

            args = [
                "--window-title", "Android Stream",
                "--window-width", str(ANDROID_SCREEN_WIDTH),
                "--window-height", str(ANDROID_SCREEN_HEIGHT),
                "--window-x", str(window_pos.x()),
                "--window-y", str(window_pos.y()),
                "--render-driver", "software",
                "--window-borderless",
                "--stay-awake",
                "--serial", self.adb_manager.current_device,
            ]

            self.scrcpy_process = QProcess(self)
            self.scrcpy_process.finished.connect(self._on_process_finished)
            self.scrcpy_process.errorOccurred.connect(self._on_process_error)
            self.scrcpy_process.setWorkingDirectory(str(Path(scrcpy_path).parent))

            self.scrcpy_process.start(scrcpy_path, args)

            if self.scrcpy_process.waitForStarted(5000):
                self.is_streaming = True
                self.find_window_timer.start()
                logger.info("Streaming interactif démarré avec succès")
            else:
                raise RuntimeError("Timeout lors du démarrage de scrcpy")

        except Exception as e:
            logger.error(f"Erreur lors du démarrage du stream: {e}")
            self.stop_stream()
            raise

    def stop_stream(self):
        """Arrête le streaming."""
        self.find_window_timer.stop()

        if self.scrcpy_process:
            logger.debug("Arrêt du processus scrcpy")
            self.scrcpy_process.terminate()
            if not self.scrcpy_process.waitForFinished(3000):
                self.scrcpy_process.kill()

        self.is_streaming = False
        self.scrcpy_window = None
        self.stream_stopped.emit()
        logger.info("Streaming arrêté")


    def _find_and_embed_window(self):
        try:
            def callback(hwnd, _):
                if win32gui.GetWindowText(hwnd) == "Android Stream":
                    self.scrcpy_window = hwnd
                    return False
                return True

            if not self.scrcpy_window:
                win32gui.EnumWindows(callback, None)

                if self.scrcpy_window:
                    parent_window = self.window()
                    if parent_window:
                        parent_hwnd = parent_window.winId().__int__()

                        style = win32gui.GetWindowLong(self.scrcpy_window,
                                                       win32con.GWL_STYLE)
                        style &= ~(win32con.WS_POPUP |
                                   win32con.WS_CAPTION |
                                   win32con.WS_THICKFRAME |
                                   win32con.WS_MINIMIZEBOX |
                                   win32con.WS_MAXIMIZEBOX |
                                   win32con.WS_SYSMENU)
                        style |= win32con.WS_CHILD
                        win32gui.SetWindowLong(self.scrcpy_window, win32con.GWL_STYLE,
                                               style)

                        # Supprime les styles étendus
                        ex_style = win32gui.GetWindowLong(self.scrcpy_window,
                                                          win32con.GWL_EXSTYLE)
                        ex_style &= ~(win32con.WS_EX_APPWINDOW |
                                      win32con.WS_EX_WINDOWEDGE)
                        win32gui.SetWindowLong(self.scrcpy_window, win32con.GWL_EXSTYLE,
                                               ex_style)

                        win32gui.SetParent(self.scrcpy_window, parent_hwnd)
                        self._update_window_position()

                        self.find_window_timer.stop()
                        logger.info("Fenêtre scrcpy intégrée avec succès")
            else:
                self._update_window_position()

        except Exception as e:
            logger.error(f"Erreur lors de l'intégration de la fenêtre: {e}")

    def _update_window_position(self):
        """Met à jour la position de la fenêtre scrcpy."""
        if self.scrcpy_window:
            try:
                # Obtient la position globale du widget de streaming
                pos = self.mapToGlobal(QPoint(0, 0))

                # Force la position et la taille de la fenêtre scrcpy
                win32gui.SetWindowPos(
                    self.scrcpy_window,
                    win32con.HWND_TOP,
                    pos.x(),
                    pos.y(),
                    ANDROID_SCREEN_WIDTH,
                    ANDROID_SCREEN_HEIGHT,
                    win32con.SWP_SHOWWINDOW | win32con.SWP_FRAMECHANGED
                )

                # Repositionne la fenêtre dans son parent
                parent_window = self.window()
                if parent_window:
                    parent_hwnd = parent_window.winId().__int__()
                    win32gui.SetParent(self.scrcpy_window, parent_hwnd)

            except Exception as e:
                logger.error(f"Erreur lors de la mise à jour de la position: {e}")

    def resizeEvent(self, event):
        """Gère le redimensionnement du widget."""
        super().resizeEvent(event)
        if self.scrcpy_window:
            self._update_window_position()

    # Ajouter également un gestionnaire pour les événements de redimensionnement de la fenêtre principale
    def moveEvent(self, event):
        """Gère le déplacement du widget."""
        super().moveEvent(event)
        if self.scrcpy_window:
            self._update_window_position()

    def closeEvent(self, event):
        """Gère la fermeture du widget."""
        self.stop_stream()
        super().closeEvent(event)

    def _on_process_finished(self, exit_code, exit_status):
        """Gère la fin du processus scrcpy."""
        logger.info(f"Processus scrcpy terminé: code={exit_code}, status={exit_status}")
        self.stop_stream()

    def _on_process_error(self, error):
        """Gère les erreurs du processus scrcpy."""
        logger.error(f"Erreur scrcpy: {error}")
        self.stop_stream()
