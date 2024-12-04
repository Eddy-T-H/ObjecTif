# src/ui/widgets/adb_status.py
import subprocess

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStatusBar,
    QComboBox, QVBoxLayout, QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from src.core.device import ADBManager
from src.ui.widgets.stream_window import StreamWindow


class ADBStatusWidget(QWidget):
    """Widget affichant l'état de la connexion ADB."""

    connection_changed = pyqtSignal(bool)
    # preview_toggled = pyqtSignal(bool)
    stream_error = pyqtSignal(str)        # Pour notifier des erreurs de streaming

    def __init__(self, adb_manager=None, parent=None):
        # super().__init__(parent)
        # self.adb_manager = adb_manager or ADBManager()
        # self._setup_ui()
        try:
            super().__init__(parent)
            self.adb_manager = adb_manager or ADBManager()

            # Initialisation du gestionnaire de streaming
            try:
                self.stream_window = StreamWindow(self.adb_manager, self)
                self.stream_window.window_closed.connect(self._on_stream_window_closed)
                self.stream_window.critical_error.connect(self._handle_stream_error)
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du streaming: {e}")
                self.stream_window = None

            self._setup_ui()

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de ADBStatusWidget: {e}")
            raise

    def _setup_ui(self):
        """
        Configure l'interface utilisateur du widget avec trois lignes distinctes :
        1. Status et informations de l'appareil
        2. Sélection de l'appareil et rafraîchissement
        3. Bouton de connexion isolé
        """
        # Layout principal vertical pour les 3 lignes
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # === PREMIÈRE LIGNE : Status et informations ===
        status_layout = QHBoxLayout()
        status_layout.setSpacing(5)

        # Indicateur d'état avec style distinctif
        self.status_label = QLabel()
        self.status_label.setStyleSheet("""
            QLabel {
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
                min-height: 20px;
                max-height: 20px;
            }
        """)
        status_layout.addWidget(self.status_label)

        # Informations détaillées sur l'appareil
        self.device_info = QLabel()
        status_layout.addWidget(self.device_info,
                                1)  # stretch=1 pour utiliser l'espace disponible
        main_layout.addLayout(status_layout)

        # === DEUXIÈME LIGNE : Sélection appareil et rafraîchissement ===
        devices_layout = QHBoxLayout()
        devices_layout.setSpacing(5)

        # Liste déroulante des appareils
        self.devices_combo = QComboBox()
        self.devices_combo.setMinimumWidth(200)
        self.devices_combo.setEnabled(False)
        self.devices_combo.setFixedHeight(24)
        devices_layout.addWidget(self.devices_combo)

        # Bouton de rafraîchissement
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.setFixedHeight(24)
        self.refresh_btn.clicked.connect(self._refresh_devices)
        devices_layout.addWidget(self.refresh_btn)

        main_layout.addLayout(devices_layout)

        # === TROISIÈME LIGNE : Bouton de connexion ===
        connect_layout = QHBoxLayout()
        connect_layout.setSpacing(5)

        # Bouton de connexion centré et plus visible
        self.connect_btn = QPushButton("Connecter")
        self.connect_btn.setFixedHeight(24)
        self.connect_btn.setMinimumWidth(
            120)  # Largeur minimale pour une meilleure visibilité
        self.connect_btn.clicked.connect(self._toggle_connection)

        # Utilisation de spacers pour centrer le bouton
        connect_layout.addStretch()
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addStretch()

        main_layout.addLayout(connect_layout)

        # État initial
        self._update_ui(False)
        self._refresh_devices()

    def _refresh_devices(self):
        """Rafraîchit la liste des appareils disponibles."""
        try:
            result = subprocess.run(
                f'"{self.adb_manager.adb_command}" devices',
                shell=True,
                capture_output=True,
                text=True,
            )

            self.devices_combo.clear()
            devices = []
            for line in result.stdout.splitlines()[1:]:
                if "\tdevice" in line:
                    device_id = line.split("\t")[0]
                    devices.append(device_id)

            if devices:
                self.devices_combo.addItems(devices)
                self.devices_combo.setEnabled(True)
                self.connect_btn.setEnabled(True)
            else:
                self.devices_combo.addItem("Aucun appareil détecté")
                self.devices_combo.setEnabled(False)
                self.connect_btn.setEnabled(False)

        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement des appareils: {e}")
            self.devices_combo.clear()
            self.devices_combo.addItem("Erreur de détection")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)

    def _toggle_connection(self):
        """Gère la connexion/déconnexion avec démarrage/arrêt automatique du streaming."""
        try:
            if self.adb_manager.is_connected():
                logger.debug("Déconnexion demandée")
                self.adb_manager.disconnect()
                self._update_ui(False)
            else:
                selected_device = self.devices_combo.currentText()
                if selected_device and selected_device != "Aucun appareil détecté":
                    logger.debug(f"Tentative de connexion à {selected_device}")
                    self.adb_manager.current_device = selected_device
                    if self.adb_manager.connect():
                        self._update_ui(True)

        except Exception as e:
            logger.error(f"Erreur lors du toggle de connexion: {e}")
            self._handle_connection_error()

    def _handle_connection_error(self):
        """Gère les erreurs de connexion de manière élégante."""
        try:
            self.status_label.setText("ERREUR")
            self.status_label.setStyleSheet(
                "QLabel { background-color: #ff9800; color: white; "
                "padding: 3px 8px; border-radius: 3px; font-weight: bold; }"
            )
            self.connect_btn.setText("Connecter")
            self.device_info.clear()

            # Notification de l'erreur
            QMessageBox.warning(self, "Erreur de connexion",
                                "Une erreur est survenue lors de la connexion.\n"
                                "Veuillez vérifier votre appareil et réessayer.")

        except Exception as e:
            logger.error(f"Erreur lors de la gestion d'erreur de connexion: {e}")

    def _update_ui(self, is_connected: bool):
        """
        Met à jour l'interface selon l'état de connexion avec gestion des erreurs.
        Synchronise l'état du streaming avec la connexion.
        """
        try:
            if is_connected:
                # Mise à jour de l'interface pour l'état connecté
                self.status_label.setText("CONNECTÉ")
                self.status_label.setStyleSheet(
                    "QLabel { background-color: #4CAF50; color: white; "
                    "padding: 3px 8px; border-radius: 3px; font-weight: bold; }"
                )
                self.connect_btn.setText("Déconnecter")
                self.devices_combo.setEnabled(False)

                # Affichage des informations de l'appareil
                try:
                    if device_info := self.adb_manager.get_device_info():
                        self.device_info.setText(
                            f"{device_info['manufacturer']} {device_info['model']} "
                            f"(Android {device_info['android_version']})"
                        )
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la récupération des infos appareil: {e}")
                    self.device_info.setText("Erreur infos appareil")

                # Démarrage du streaming avec gestion d'erreur
                if self.stream_window:
                    if not self.stream_window.start_stream():
                        logger.error("Échec du démarrage du streaming")

            else:
                # Mise à jour de l'interface pour l'état déconnecté
                self.status_label.setText("DÉCONNECTÉ")
                self.status_label.setStyleSheet(
                    "QLabel { background-color: #f44336; color: white; "
                    "padding: 3px 8px; border-radius: 3px; font-weight: bold; }"
                )
                self.connect_btn.setText("Connecter")
                self.device_info.clear()
                self.devices_combo.setEnabled(True)

                # Arrêt du streaming
                if self.stream_window:
                    self.stream_window.stop_stream()

                # Rafraîchissement de la liste des appareils
                self._refresh_devices()

            # Émission du signal de changement d'état
            self.connection_changed.emit(is_connected)

        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'interface: {e}")
            # Tentative de récupération en cas d'erreur
            self._handle_ui_error()

    def _handle_stream_error(self, error_msg: str):
        """Gère les erreurs critiques du streaming."""
        try:
            logger.error(f"Erreur critique du streaming: {error_msg}")
            QMessageBox.critical(self, "Erreur de streaming",
                                 f"Erreur de streaming : {error_msg}\n"
                                 f"L'appareil va être déconnecté.")
            self._toggle_connection()  # Déconnexion de sécurité

        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'erreur de streaming: {e}")

    def _on_stream_window_closed(self):
        """Gère la fermeture de la fenêtre de streaming par l'utilisateur."""
        try:
            if self.adb_manager.is_connected():
                logger.info("Fenêtre de streaming fermée, déconnexion de l'appareil")
                self._toggle_connection()

        except Exception as e:
            logger.error(f"Erreur lors du traitement de la fermeture: {e}")
            self._handle_ui_error()

    def _handle_ui_error(self):
        """Tente de récupérer après une erreur d'interface."""
        try:
            # Réinitialisation de l'interface aux valeurs par défaut
            self.status_label.setText("ERREUR")
            self.status_label.setStyleSheet(
                "QLabel { background-color: #ff9800; color: white; "
                "padding: 3px 8px; border-radius: 3px; font-weight: bold; }"
            )
            self.connect_btn.setText("Connecter")
            self.device_info.clear()
            self.devices_combo.setEnabled(True)

            # Arrêt de sécurité du streaming
            if self.stream_window:
                self.stream_window.stop_stream()

        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'interface: {e}")
    # def _update_ui(self, is_connected: bool):
    #     """Met à jour l'interface selon l'état de connexion."""
    #     if is_connected:
    #         self.status_label.setText("CONNECTÉ")
    #         self.status_label.setStyleSheet(
    #             """
    #             QLabel {
    #                 background-color: #4CAF50;
    #                 color: white;
    #                 padding: 3px 8px;
    #                 border-radius: 3px;
    #                 font-weight: bold;
    #             }
    #         """
    #         )
    #         self.connect_btn.setText("Déconnecter")
    #         self.preview_btn.setEnabled(True)
    #         self.devices_combo.setEnabled(False)  # Désactive pendant la connexion
    #
    #         # Affiche les infos de l'appareil
    #         if device_info := self.adb_manager.get_device_info():
    #             self.device_info.setText(
    #                 f"{device_info['manufacturer']} {device_info['model']} "
    #                 f"(Android {device_info['android_version']})"
    #             )
    #     else:
    #         self.status_label.setText("DÉCONNECTÉ")
    #         self.status_label.setStyleSheet(
    #             """
    #             QLabel {
    #                 background-color: #f44336;
    #                 color: white;
    #                 padding: 3px 8px;
    #                 border-radius: 3px;
    #                 font-weight: bold;
    #             }
    #         """
    #         )
    #         self.connect_btn.setText("Connecter")
    #         self.device_info.clear()
    #         self.preview_btn.setEnabled(False)
    #         self.preview_active = False
    #         self.preview_btn.setText("Prévisualisation")
    #         self.devices_combo.setEnabled(True)  # Réactive la sélection
    #         self._refresh_devices()  # Rafraîchit la liste des appareils
    #
    #     self.connection_changed.emit(is_connected)


    def _toggle_preview(self):
        """Active/désactive la prévisualisation."""
        logger.debug("Toggle preview appelé")
        if not self.preview_active:
            if self.adb_manager.is_connected():
                logger.debug("Activation de la prévisualisation")
                self.preview_active = True
                self.preview_btn.setText("Arrêter prévisualisation")
                self.preview_toggled.emit(True)  # Émet le signal
        else:
            logger.debug("Désactivation de la prévisualisation")
            self.preview_active = False
            self.preview_btn.setText("Prévisualisation")
            self.preview_toggled.emit(False)  # Émet le signal