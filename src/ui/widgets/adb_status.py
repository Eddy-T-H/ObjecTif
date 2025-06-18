# src/ui/widgets/adb_status.py
import subprocess

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from loguru import logger

from src.core.device import ADBManager
from src.ui.widgets.stream_window import StreamWindow
from src.ui.widgets.operation_popup import OperationPopup


class ADBStatusWidget(QWidget):
    """Widget affichant l'état de la connexion ADB avec qt-material."""

    connection_changed = pyqtSignal(bool)

    def __init__(self, adb_manager=None, parent=None):
        try:
            super().__init__(parent)
            self.adb_manager = adb_manager or ADBManager()

            # Initialisation du gestionnaire de streaming
            try:
                self.stream_window = StreamWindow(self.adb_manager, self)
                # Connexion des signaux détaillés
                self.stream_window.starting.connect(
                    lambda: self._show_operation_popup(
                        "Démarrage de la prévisualisation...", "Streaming"
                    )
                )
                self.stream_window.started.connect(self._on_streaming_started)
                self.stream_window.stopping.connect(
                    lambda: self._show_operation_popup(
                        "Arrêt de la prévisualisation...", "Streaming"
                    )
                )
                self.stream_window.stopped.connect(self._on_streaming_stopped)
                self.stream_window.window_closed.connect(self._on_stream_window_closed)
                self.stream_window.critical_error.connect(self._handle_stream_error)
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du streaming: {e}")
                self.stream_window = None

            # Popup d'opération réutilisable
            self.operation_popup = None

            self._setup_ui()

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de ADBStatusWidget: {e}")
            raise

    def _setup_ui(self):
        """Configure l'interface utilisateur avec qt-material (styles supprimés)."""
        # Layout principal vertical pour les 3 lignes
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(8, 8, 8, 8)
        main_layout.setSpacing(8)

        # === PREMIÈRE LIGNE : Status et informations ===
        status_layout = QHBoxLayout()
        status_layout.setSpacing(8)

        # Indicateur d'état - SUPPRESSION du setStyleSheet
        self.status_label = QLabel()
        self.status_label.setMinimumHeight(32)
        self.status_label.setMaximumHeight(32)
        # qt-material gère le style de base automatiquement
        status_layout.addWidget(self.status_label)

        # Informations détaillées sur l'appareil - SUPPRESSION du setStyleSheet
        self.device_info = QLabel()
        # qt-material gère le style automatiquement
        status_layout.addWidget(self.device_info, 1)
        main_layout.addLayout(status_layout)

        # === DEUXIÈME LIGNE : Sélection appareil et rafraîchissement ===
        devices_layout = QHBoxLayout()
        devices_layout.setSpacing(8)

        # Liste déroulante des appareils - SUPPRESSION du setStyleSheet
        self.devices_combo = QComboBox()
        self.devices_combo.setMinimumWidth(200)
        self.devices_combo.setEnabled(False)
        self.devices_combo.setFixedHeight(32)
        # qt-material applique automatiquement un style moderne
        devices_layout.addWidget(self.devices_combo)

        main_layout.addLayout(devices_layout)

        # === TROISIÈME LIGNE : Boutons de connexion ===
        connect_layout = QHBoxLayout()
        connect_layout.setSpacing(8)

        # Bouton de rafraîchissement - SUPPRESSION du setStyleSheet
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self._refresh_devices)
        # qt-material applique le style automatiquement

        # Bouton principal de connexion - SUPPRESSION du setStylesheet
        self.connect_btn = QPushButton("Se connecter")

        self.connect_btn.clicked.connect(self._toggle_connection)
        # qt-material applique le style automatiquement
        # Bouton d'erreur ADB - SUPPRESSION du setStyleSheet
        self.retry_adb_btn = QPushButton("⚠️ Réessayer ADB")
        self.retry_adb_btn.setFixedHeight(32)
        self.retry_adb_btn.clicked.connect(self._retry_adb)
        self.retry_adb_btn.setVisible(False)
        # qt-material applique le style automatiquement

        connect_layout.addWidget(self.refresh_btn)
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addWidget(self.retry_adb_btn)

        main_layout.addLayout(connect_layout)

        # État initial
        self._check_adb_availability()
        self._refresh_devices()

    def _create_operation_popup(
        self, title: str = "Opération en cours"
    ) -> OperationPopup:
        """Crée une nouvelle popup d'opération."""
        popup = OperationPopup(self)
        popup.setWindowTitle(title)
        return popup

    def _show_operation_popup(self, message: str, title: str = "Opération en cours"):
        """Affiche une popup d'opération."""
        if self.operation_popup:
            self.operation_popup.close_popup()

        self.operation_popup = self._create_operation_popup(title)
        self.operation_popup.update_message(message)
        self.operation_popup.show()
        QApplication.processEvents()

    def _close_operation_popup(self):
        """Ferme la popup d'opération actuelle."""
        if self.operation_popup:
            self.operation_popup.close_popup()
            self.operation_popup = None

    def _check_adb_availability(self):
        """Vérifie si ADB est disponible avec indicateurs visuels qt-material."""
        if not self.adb_manager.is_adb_available():
            self.status_label.setText("⚠️ ADB INDISPONIBLE")
            self.device_info.setText("🚫 ADB non trouvé sur le système")
            # qt-material gère la couleur automatiquement

            self.connect_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.retry_adb_btn.setVisible(True)
        else:
            self.retry_adb_btn.setVisible(False)
            self.refresh_btn.setEnabled(True)
            self._update_ui(False)

    def _retry_adb(self):
        """Tente de réinitialiser ADB avec feedback visuel qt-material."""
        # Popup de progression
        self._show_operation_popup("Réinitialisation d'ADB...", "Configuration ADB")

        # Désactive le bouton temporairement
        self.retry_adb_btn.setEnabled(False)

        # Simule un petit délai pour que l'utilisateur voit la popup
        QTimer.singleShot(500, self._perform_adb_retry)

    def _perform_adb_retry(self):
        """Effectue la réinitialisation ADB."""
        try:
            if self.adb_manager.retry_adb_initialization():
                # Succès
                self._close_operation_popup()
                self.retry_adb_btn.setVisible(False)
                self.connect_btn.setEnabled(True)
                self.refresh_btn.setEnabled(True)
                self._update_ui(False)
                self._refresh_devices()

                # Message de succès dans la status bar seulement
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        "✅ ADB initialisé avec succès", 3000
                    )
                logger.info("ADB réinitialisé avec succès")
            else:
                # Échec
                self._close_operation_popup()
                self.retry_adb_btn.setEnabled(True)
                # Message d'erreur dans la status bar seulement
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        "❌ ADB toujours indisponible - Vérifiez l'installation", 5000
                    )
        except Exception as e:
            self._close_operation_popup()
            self.retry_adb_btn.setEnabled(True)
            # Message d'erreur dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(f"❌ Erreur ADB: {str(e)}", 5000)

    def _refresh_devices(self):
        """Rafraîchit la liste des appareils avec feedback visuel qt-material."""
        if not self.adb_manager.is_adb_available():
            self.devices_combo.clear()
            self.devices_combo.addItem("ADB indisponible")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
            return

        # Popup de progression pour le rafraîchissement
        self._show_operation_popup("Recherche d'appareils...", "Détection d'appareils")

        # Désactive les contrôles temporairement
        self.refresh_btn.setEnabled(False)
        self.connect_btn.setEnabled(False)

        # Effectue la recherche après un délai pour que la popup soit visible
        QTimer.singleShot(300, self._perform_device_refresh)

    def _perform_device_refresh(self):
        """Effectue la recherche d'appareils."""
        try:
            result = subprocess.run(
                f'"{self.adb_manager.adb_command}" devices',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5,
            )

            self.devices_combo.clear()
            devices = []
            for line in result.stdout.splitlines()[1:]:
                if "\tdevice" in line:
                    device_id = line.split("\t")[0]
                    devices.append(device_id)

            self._close_operation_popup()

            if devices:
                self.devices_combo.addItems(devices)
                self.devices_combo.setEnabled(True)
                self.connect_btn.setEnabled(True)

                # Message de succès dans la status bar
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        f"✅ {len(devices)} appareil(s) détecté(s)", 2000
                    )
            else:
                self.devices_combo.addItem("Aucun appareil détecté")
                self.devices_combo.setEnabled(False)
                self.connect_btn.setEnabled(False)

                # Message d'info
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        "ℹ️ Aucun appareil Android détecté", 3000
                    )

        except subprocess.TimeoutExpired:
            self._close_operation_popup()
            logger.error("Timeout lors du rafraîchissement des appareils")
            self.devices_combo.clear()
            self.devices_combo.addItem("⏱️ Timeout - Réessayez")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)

            # Message dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    "⏱️ Timeout recherche d'appareils - Réessayez", 5000
                )
        except Exception as e:
            self._close_operation_popup()
            logger.error(f"Erreur lors du rafraîchissement des appareils: {e}")
            self.devices_combo.clear()
            self.devices_combo.addItem("❌ Erreur de détection")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)

            # Message dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    f"❌ Erreur détection: {str(e)}", 5000
                )
        finally:
            # Réactive les contrôles
            self.refresh_btn.setEnabled(True)
            # Le bouton connect dépend de s'il y a des appareils
            if (
                self.devices_combo.count() > 0
                and self.devices_combo.currentText() != "Aucun appareil détecté"
            ):
                self.connect_btn.setEnabled(True)
            else:
                self.connect_btn.setEnabled(False)

    def _toggle_connection(self):
        """Gère la connexion/déconnexion avec popup de feedback."""
        try:
            if self.adb_manager.is_connected():
                # === DÉCONNEXION ===
                logger.debug("Déconnexion demandée")

                # Popup de déconnexion
                self._show_operation_popup("Déconnexion en cours...", "Déconnexion")

                # Désactive les contrôles
                self.connect_btn.setEnabled(False)

                # Délai pour que l'utilisateur voit la popup
                QTimer.singleShot(500, self._perform_disconnection)

            else:
                # === CONNEXION ===
                selected_device = self.devices_combo.currentText()
                if selected_device and selected_device != "Aucun appareil détecté":
                    logger.debug(f"Tentative de connexion à {selected_device}")

                    # Popup de connexion
                    self._show_operation_popup(
                        f"Connexion à {selected_device}...", "Connexion Android"
                    )

                    # Désactive les contrôles
                    self.connect_btn.setEnabled(False)
                    self.refresh_btn.setEnabled(False)
                    self.devices_combo.setEnabled(False)

                    # Stocke l'appareil sélectionné et lance la connexion
                    self.adb_manager.current_device = selected_device
                    QTimer.singleShot(300, self._perform_connection)

        except Exception as e:
            self._close_operation_popup()
            logger.error(f"Erreur lors du toggle de connexion: {e}")
            self._handle_connection_error()

    def _perform_connection(self):
        """Effectue la connexion à l'appareil."""
        try:
            success = self.adb_manager.connect()

            if success:
                # Connexion réussie
                self._close_operation_popup()
                self._update_ui(True)

                # Message de succès dans la status bar seulement
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        f"✅ Connecté à {self.adb_manager.current_device}", 3000
                    )

            else:
                # Connexion échouée
                self._close_operation_popup()
                self._update_ui(False)

                # Message d'erreur dans la status bar seulement
                if hasattr(self.parent(), "statusBar"):
                    self.parent().statusBar().showMessage(
                        "❌ Échec de connexion - Vérifiez le débogage USB", 5000
                    )

        except Exception as e:
            self._close_operation_popup()
            logger.error(f"Erreur lors de la connexion: {e}")
            self._handle_connection_error()
        finally:
            # Réactive les contrôles selon l'état
            self._restore_controls_state()

    def _perform_disconnection(self):
        """
        Effectue la déconnexion de l'appareil.
        Garde toujours ADB actif - reset juste la référence de l'appareil.
        """
        try:
            # Déconnexion douce TOUJOURS - garde ADB actif
            logger.info("Déconnexion - ADB reste actif")
            self.adb_manager.current_device = None

            self._close_operation_popup()
            self._update_ui(False)

            # Message de déconnexion dans la status bar
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    "✅ Appareil déconnecté - ADB actif", 2000
                )

        except Exception as e:
            self._close_operation_popup()
            logger.error(f"Erreur lors de la déconnexion: {e}")
            # Message d'erreur dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    f"⚠️ Erreur de déconnexion: {str(e)}", 5000
                )
        finally:
            self._restore_controls_state()

    def _restore_controls_state(self):
        """Restaure l'état des contrôles selon la situation."""
        self.connect_btn.setEnabled(True)
        if self.adb_manager.is_adb_available():
            self.refresh_btn.setEnabled(True)
            if not self.adb_manager.is_connected():
                self.devices_combo.setEnabled(True)

    def _handle_connection_error(self):
        """Gère les erreurs de connexion avec qt-material."""
        try:
            self.status_label.setText("❌ ERREUR")
            self.connect_btn.setText("Se connecter")
            self.device_info.clear()

            # Message d'erreur dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    "❌ Erreur de connexion - Vérifiez l'appareil", 5000
                )

        except Exception as e:
            logger.error(f"Erreur lors de la gestion d'erreur de connexion: {e}")

    def _update_ui(self, is_connected: bool):
        """Met à jour l'interface selon l'état de connexion avec qt-material."""
        try:
            if is_connected:
                # État connecté avec qt-material
                self.status_label.setText("🟢 CONNECTÉ")
                # Bouton de déconnexion - qt-material gère le style
                self.connect_btn.setText("Se déconnecter")
                # Pas de setStyleSheet - qt-material s'en charge

                self.devices_combo.setEnabled(False)

                # Affichage des informations de l'appareil
                try:
                    if device_info := self.adb_manager.get_device_info():
                        info_text = f"📱 {device_info['manufacturer']} {device_info['model']} (Android {device_info['android_version']})"
                        self.device_info.setText(info_text)
                        # qt-material gère la couleur automatiquement
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la récupération des infos appareil: {e}"
                    )
                    self.device_info.setText("⚠️ Erreur infos appareil")

                # Démarrage du streaming automatique
                if self.stream_window:
                    self.stream_window.start_stream()

            else:
                # État déconnecté avec qt-material
                self.status_label.setText("🔴 DÉCONNECTÉ")
                # Bouton de connexion - qt-material gère le style
                self.connect_btn.setText("Se connecter")
                # Pas de setStyleSheet - qt-material s'en charge

                self.device_info.clear()
                self.devices_combo.setEnabled(True)

                # Arrêt du streaming
                if self.stream_window:
                    self.stream_window.stop_stream()

            # Émission du signal de changement d'état
            self.connection_changed.emit(is_connected)

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'interface: {e}")
            self._handle_ui_error()

    def _handle_stream_error(self, error_msg: str):
        """Gère les erreurs critiques du streaming - déconnexion automatique."""
        try:
            logger.error(f"Erreur critique du streaming: {error_msg}")

            # Popup d'information simple (sans interaction)
            self._show_operation_popup("Erreur de streaming, déconnexion...", "Erreur")

            # Déconnexion automatique après un court délai
            QTimer.singleShot(1500, self._process_stream_error)

        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'erreur de streaming: {e}")

    def _process_stream_error(self):
        """Traite l'erreur de streaming et déconnecte automatiquement."""
        try:
            self._close_operation_popup()

            # Déconnexion automatique sans demander confirmation
            if self.adb_manager.is_connected():
                logger.info("Déconnexion automatique suite à erreur de streaming")
                self._toggle_connection()

            # Message dans la status bar seulement
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    "❌ Erreur de streaming - Appareil déconnecté", 5000
                )

        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'erreur de streaming: {e}")

    def _on_stream_window_closed(self):
        """Gère la fermeture de la fenêtre de streaming - déconnexion automatique."""
        try:
            if self.adb_manager.is_connected():
                logger.info(
                    "Fenêtre de streaming fermée par l'utilisateur, déconnexion automatique"
                )

                # Popup d'information simple
                self._show_operation_popup(
                    "Fenêtre fermée, déconnexion...", "Fermeture"
                )

                # Déconnexion automatique après un court délai
                QTimer.singleShot(1000, self._process_window_closure)

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la fermeture: {e}")
            self._handle_ui_error()

    def _process_window_closure(self):
        """Traite la fermeture de la fenêtre et déconnecte."""
        try:
            self._close_operation_popup()

            # Déconnexion douce (garde ADB actif)
            logger.info("Déconnexion après fermeture de la fenêtre - ADB reste actif")
            self._perform_disconnection()

            # Message dans la status bar
            if hasattr(self.parent(), "statusBar"):
                self.parent().statusBar().showMessage(
                    "🖼️ Fenêtre fermée - Reconnexion disponible", 3000
                )

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la fermeture: {e}")

    def _on_streaming_started(self):
        """Appelé quand le streaming démarre avec succès."""
        self._close_operation_popup()
        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage("🎥 Prévisualisation démarrée", 2000)

    def _on_streaming_stopped(self):
        """Appelé quand le streaming s'arrête."""
        self._close_operation_popup()
        if hasattr(self.parent(), "statusBar"):
            self.parent().statusBar().showMessage("🎥 Prévisualisation arrêtée", 2000)

    def _handle_ui_error(self):
        """Tente de récupérer après une erreur d'interface."""
        try:
            self._close_operation_popup()

            self.status_label.setText("❌ ERREUR")
            self.connect_btn.setText("Se connecter")
            # Pas de setStyleSheet - qt-material s'en charge

            self.device_info.clear()
            self.devices_combo.setEnabled(True)

            if self.stream_window:
                self.stream_window.stop_stream()

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'interface: {e}")