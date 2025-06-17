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
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QCursor
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from src.core.device import ADBManager
from src.ui.widgets.stream_window import StreamWindow


class ADBStatusWidget(QWidget):
    """Widget affichant l'état de la connexion ADB."""

    connection_changed = pyqtSignal(bool)

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
        status_layout.addWidget(self.device_info, 1)
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
        self.connect_btn.setMinimumWidth(120)
        self.connect_btn.clicked.connect(self._toggle_connection)

        # Bouton pour réessayer ADB si non disponible
        self.retry_adb_btn = QPushButton("Réessayer ADB")
        self.retry_adb_btn.setFixedHeight(24)
        self.retry_adb_btn.clicked.connect(self._retry_adb)
        self.retry_adb_btn.setVisible(False)  # Caché par défaut

        connect_layout.addStretch()
        connect_layout.addWidget(self.connect_btn)
        connect_layout.addWidget(self.retry_adb_btn)
        connect_layout.addStretch()

        main_layout.addLayout(connect_layout)

        # État initial - vérifie la disponibilité d'ADB
        self._check_adb_availability()
        self._refresh_devices()

    def _check_adb_availability(self):
        """Vérifie si ADB est disponible et met à jour l'interface."""
        if not self.adb_manager.is_adb_available():
            self.status_label.setText("⚠️ ADB INDISPONIBLE")
            self.status_label.setStyleSheet("""
                QLabel { 
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                               stop:0 #ff5722, stop:1 #e64a19);
                    color: white; 
                    padding: 8px 16px; 
                    border-radius: 8px; 
                    font-weight: bold;
                    font-size: 12px;
                    border: 2px solid #d84315;
                }
            """)
            self.device_info.setText("🚫 ADB non trouvé sur le système")
            self.device_info.setStyleSheet("color: #d84315; font-size: 11px;")
            self.connect_btn.setEnabled(False)
            self.refresh_btn.setEnabled(False)
            self.retry_adb_btn.setVisible(True)
            self.retry_adb_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ff9800;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 8px 16px;
                    font-weight: bold;
                    font-size: 11px;
                }
                QPushButton:hover {
                    background-color: #f57c00;
                }
            """)
        else:
            self.retry_adb_btn.setVisible(False)
            self._update_ui(False)

    def _retry_adb(self):
        """Tente de réinitialiser ADB."""
        self.retry_adb_btn.setEnabled(False)
        self.retry_adb_btn.setText("Tentative...")

        if self.adb_manager.retry_adb_initialization():
            # ADB maintenant disponible
            self.retry_adb_btn.setVisible(False)
            self.connect_btn.setEnabled(True)
            self.refresh_btn.setEnabled(True)
            self._update_ui(False)
            self._refresh_devices()
            QMessageBox.information(self, "Succès", "ADB initialisé avec succès !")
        else:
            # Toujours pas disponible
            self.retry_adb_btn.setEnabled(True)
            self.retry_adb_btn.setText("Réessayer ADB")
            QMessageBox.warning(self, "Erreur",
                                "ADB toujours indisponible.\n"
                                "Vérifiez l'installation d'Android SDK Platform Tools.")

    def _refresh_devices(self):
        """Rafraîchit la liste des appareils avec feedback visuel."""
        if not self.adb_manager.is_adb_available():
            self.devices_combo.clear()
            self.devices_combo.addItem("ADB indisponible")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
            return

        try:
            # Feedback visuel pour le rafraîchissement
            self.refresh_btn.setEnabled(False)
            self.refresh_btn.setText("...")
            QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

            result = subprocess.run(
                f'"{self.adb_manager.adb_command}" devices',
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
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

        except subprocess.TimeoutExpired:
            logger.error("Timeout lors du rafraîchissement des appareils")
            self.devices_combo.clear()
            self.devices_combo.addItem("Timeout - Réessayez")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
        except Exception as e:
            logger.error(f"Erreur lors du rafraîchissement des appareils: {e}")
            self.devices_combo.clear()
            self.devices_combo.addItem("Erreur de détection")
            self.devices_combo.setEnabled(False)
            self.connect_btn.setEnabled(False)
        finally:
            # Restaure l'interface
            QApplication.restoreOverrideCursor()
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText("Rafraîchir")

    def _toggle_connection(self):
        """Gère la connexion/déconnexion avec feedback visuel."""
        try:
            if self.adb_manager.is_connected():
                logger.debug("Déconnexion demandée")
                self._start_operation("Déconnexion...")

                self.adb_manager.disconnect()
                self._update_ui(False)
                self._end_operation("Déconnecté")

            else:
                selected_device = self.devices_combo.currentText()
                if selected_device and selected_device != "Aucun appareil détecté":
                    logger.debug(f"Tentative de connexion à {selected_device}")
                    self._start_operation(f"Connexion à {selected_device}...")

                    self.adb_manager.current_device = selected_device
                    success = self.adb_manager.connect()

                    if success:
                        self._update_ui(True)
                        self._end_operation("Connecté avec succès")
                    else:
                        self._end_operation("Échec de la connexion")

        except Exception as e:
            logger.error(f"Erreur lors du toggle de connexion: {e}")
            self._handle_connection_error()
            self._end_operation("Erreur de connexion")

    def _start_operation(self, message: str):
        """Démarre l'indication visuelle d'une opération."""
        # Change le curseur
        QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))

        # Désactive les contrôles
        self.connect_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.devices_combo.setEnabled(False)

        # Message temporaire dans le bouton
        self.original_button_text = self.connect_btn.text()
        self.connect_btn.setText("...")

        # Message de statut si le parent (MainWindow) a une statusBar
        try:
            if hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(message)
        except:
            pass

    def _end_operation(self, result_message: str):
        """Termine l'indication visuelle d'une opération."""
        # Restaure le curseur
        QApplication.restoreOverrideCursor()

        # Restaure le texte du bouton
        if hasattr(self, 'original_button_text'):
            self.connect_btn.setText(self.original_button_text)

        # Réactive les contrôles selon l'état
        self.connect_btn.setEnabled(True)
        if self.adb_manager.is_adb_available():
            self.refresh_btn.setEnabled(True)
            if not self.adb_manager.is_connected():
                self.devices_combo.setEnabled(True)

        # Message de résultat
        try:
            if hasattr(self.parent(), 'statusBar'):
                self.parent().statusBar().showMessage(result_message)
                # Efface le message après 3 secondes
                QTimer.singleShot(3000,
                                  lambda: self.parent().statusBar().showMessage(""))
        except:
            pass

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
        """Met à jour l'interface selon l'état de connexion avec bouton corrigé."""
        try:
            if is_connected:
                # Mise à jour de l'interface pour l'état connecté
                self.status_label.setText("🟢 CONNECTÉ")
                self.status_label.setStyleSheet("""
                    QLabel { 
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #4CAF50, stop:1 #45a049);
                        color: white; 
                        padding: 8px 16px; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 12px;
                        border: 2px solid #388E3C;
                    }
                """)
                self.connect_btn.setText("Déconnecter")
                self.connect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f44336;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: bold;
                        font-size: 12px;
                        min-height: 30px;
                        min-width: 100px;
                    }
                    QPushButton:hover {
                        background-color: #d32f2f;
                        border: 2px solid white;
                    }
                """)
                self.devices_combo.setEnabled(False)

                # Affichage des informations de l'appareil
                try:
                    if device_info := self.adb_manager.get_device_info():
                        info_text = f"📱 {device_info['manufacturer']} {device_info['model']} (Android {device_info['android_version']})"
                        self.device_info.setText(info_text)
                        self.device_info.setStyleSheet(
                            "color: #2e7d32; font-size: 11px; font-weight: bold;")
                except Exception as e:
                    logger.error(
                        f"Erreur lors de la récupération des infos appareil: {e}")
                    self.device_info.setText("⚠️ Erreur infos appareil")
                    self.device_info.setStyleSheet("color: #ff9800; font-size: 11px;")

                # Démarrage du streaming
                if self.stream_window:
                    if not self.stream_window.start_stream():
                        logger.error("Échec du démarrage du streaming")

            else:
                # Mise à jour de l'interface pour l'état déconnecté
                self.status_label.setText("🔴 DÉCONNECTÉ")
                self.status_label.setStyleSheet("""
                    QLabel { 
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                   stop:0 #f44336, stop:1 #d32f2f);
                        color: white; 
                        padding: 8px 16px; 
                        border-radius: 8px; 
                        font-weight: bold;
                        font-size: 12px;
                        border: 2px solid #c62828;
                    }
                """)
                self.connect_btn.setText("Connecter")
                self.connect_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #4CAF50;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 10px 20px;
                        font-weight: bold;
                        font-size: 12px;
                        min-height: 30px;
                        min-width: 100px;
                    }
                    QPushButton:hover {
                        background-color: #45a049;
                        border: 2px solid white;
                    }
                """)
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
