# src/ui/widgets/adb_status.py
import subprocess

from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStatusBar,
    QComboBox, QVBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

from src.core.device import ADBManager


class ADBStatusWidget(QWidget):
    """Widget affichant l'état de la connexion ADB."""

    connection_changed = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.adb_manager = ADBManager()
        self._setup_ui()

    def _setup_ui(self):
        """Configure l'interface du widget."""
        # Layout principal vertical pour les 3 lignes
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)  # Espacement réduit entre les lignes

        # === PREMIÈRE LIGNE : Status ===
        status_layout = QHBoxLayout()
        status_layout.setSpacing(5)

        # Indicateur d'état avec style compact
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

        # Infos sur l'appareil
        self.device_info = QLabel()
        status_layout.addWidget(self.device_info,
                                1)  # stretch=1 pour prendre l'espace restant
        main_layout.addLayout(status_layout)

        # === DEUXIÈME LIGNE : Sélection appareil ===
        devices_layout = QHBoxLayout()
        devices_layout.setSpacing(5)

        # Liste déroulante des appareils
        self.devices_combo = QComboBox()
        self.devices_combo.setMinimumWidth(200)
        self.devices_combo.setEnabled(False)
        self.devices_combo.setFixedHeight(24)  # Hauteur fixe réduite
        devices_layout.addWidget(self.devices_combo)

        # Bouton rafraîchir plus compact
        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.setFixedHeight(24)  # Même hauteur que la combobox
        self.refresh_btn.clicked.connect(self._refresh_devices)
        devices_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(devices_layout)

        # === TROISIÈME LIGNE : Boutons d'action ===
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)

        # Bouton connexion
        self.connect_btn = QPushButton()
        self.connect_btn.setFixedHeight(24)
        self.connect_btn.clicked.connect(self._toggle_connection)
        buttons_layout.addWidget(self.connect_btn)

        # Bouton prévisualisation
        self.preview_btn = QPushButton("Prévisualisation")
        self.preview_btn.setFixedHeight(24)
        self.preview_btn.setEnabled(False)
        self.preview_btn.clicked.connect(self._toggle_preview)
        buttons_layout.addWidget(self.preview_btn)
        main_layout.addLayout(buttons_layout)

        # État initial
        self._update_ui(False)
        self.preview_active = False
        self._refresh_devices()

    # def _setup_ui(self):
    #     """Configure l'interface du widget."""
    #     layout = QHBoxLayout(self)
    #     layout.setContentsMargins(5, 5, 5, 5)
    #
    #     # Indicateur d'état
    #     self.status_label = QLabel()
    #     self.status_label.setStyleSheet(
    #         """
    #         QLabel {
    #             padding: 3px 8px;
    #             border-radius: 3px;
    #             font-weight: bold;
    #         }
    #     """
    #     )
    #     layout.addWidget(self.status_label)
    #
    #     # Liste déroulante des appareils
    #     self.devices_combo = QComboBox()
    #     self.devices_combo.setMinimumWidth(200)
    #     self.devices_combo.setEnabled(False)
    #     layout.addWidget(self.devices_combo)
    #
    #     # Infos sur l'appareil
    #     self.device_info = QLabel()
    #     layout.addWidget(self.device_info)
    #     layout.addStretch()
    #
    #     # Bouton de rafraîchissement
    #     self.refresh_btn = QPushButton("Rafraîchir")
    #     self.refresh_btn.clicked.connect(self._refresh_devices)
    #     layout.addWidget(self.refresh_btn)
    #
    #     # Bouton de connexion/déconnexion
    #     self.connect_btn = QPushButton()
    #     self.connect_btn.clicked.connect(self._toggle_connection)
    #     layout.addWidget(self.connect_btn)
    #
    #     # Bouton de prévisualisation
    #     self.preview_btn = QPushButton("Prévisualisation")
    #     self.preview_btn.setEnabled(False)
    #     self.preview_btn.clicked.connect(self._toggle_preview)
    #     layout.addWidget(self.preview_btn)
    #
    #     # État initial
    #     self._update_ui(False)
    #     self.preview_active = False
    #
    #     # Premier rafraîchissement
    #     self._refresh_devices()

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
        """Gère la connexion/déconnexion."""
        if self.adb_manager.is_connected():
            self.adb_manager.disconnect()
            self._update_ui(False)
        else:
            selected_device = self.devices_combo.currentText()
            if selected_device and selected_device != "Aucun appareil détecté":
                self.adb_manager.current_device = selected_device
                if self.adb_manager.connect():
                    self._update_ui(True)

    def _update_ui(self, is_connected: bool):
        """Met à jour l'interface selon l'état de connexion."""
        if is_connected:
            self.status_label.setText("CONNECTÉ")
            self.status_label.setStyleSheet(
                """
                QLabel {
                    background-color: #4CAF50;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """
            )
            self.connect_btn.setText("Déconnecter")
            self.preview_btn.setEnabled(True)
            self.devices_combo.setEnabled(False)  # Désactive pendant la connexion

            # Affiche les infos de l'appareil
            if device_info := self.adb_manager.get_device_info():
                self.device_info.setText(
                    f"{device_info['manufacturer']} {device_info['model']} "
                    f"(Android {device_info['android_version']})"
                )
        else:
            self.status_label.setText("DÉCONNECTÉ")
            self.status_label.setStyleSheet(
                """
                QLabel {
                    background-color: #f44336;
                    color: white;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-weight: bold;
                }
            """
            )
            self.connect_btn.setText("Connecter")
            self.device_info.clear()
            self.preview_btn.setEnabled(False)
            self.preview_active = False
            self.preview_btn.setText("Prévisualisation")
            self.devices_combo.setEnabled(True)  # Réactive la sélection
            self._refresh_devices()  # Rafraîchit la liste des appareils

        self.connection_changed.emit(is_connected)

    def _toggle_preview(self):
        """Active/désactive la prévisualisation."""
        if not self.preview_active:
            if self.adb_manager.is_connected():
                self.preview_active = True
                self.preview_btn.setText("Arrêter prévisualisation")
                self.connection_changed.emit(True)  # Déclenche le démarrage du stream
        else:
            self.preview_active = False
            self.preview_btn.setText("Prévisualisation")
            self.connection_changed.emit(False)  # Arrête le stream