# src/ui/theme/theme_manager.py
"""
Gestionnaire de thème simple qui s'adapte automatiquement au thème système.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QSettings
from PyQt6.QtGui import QPalette
from loguru import logger

try:
    from qt_material import apply_stylesheet

    QT_MATERIAL_AVAILABLE = True
except ImportError:
    QT_MATERIAL_AVAILABLE = False
    logger.warning("qt-material non disponible - utilisation du thème par défaut")


def apply_system_theme(app: QApplication) -> bool:
    """
    Applique automatiquement le thème clair ou sombre selon le système.

    Args:
            app: Instance de QApplication

    Returns:
            bool: True si qt-material a été appliqué, False sinon
    """
    if not QT_MATERIAL_AVAILABLE:
        logger.info("qt-material non disponible - thème système par défaut")
        return False

    try:
        # Détecte le thème système
        is_dark = _is_system_dark_theme(app)

        # Choix du thème selon le système
        theme = "dark_blue.xml" if is_dark else "light_blue.xml"

        # Application du thème qt-material
        apply_stylesheet(app, theme=theme, extra=_get_custom_styles())

        theme_name = "sombre" if is_dark else "clair"
        logger.info(f"Thème {theme_name} appliqué automatiquement")
        return True

    except Exception as e:
        logger.error(f"Erreur lors de l'application du thème: {e}")
        return False


def _is_system_dark_theme(app: QApplication) -> bool:
    """
    Détecte si le système utilise un thème sombre.

    Args:
            app: Instance de QApplication

    Returns:
            bool: True si le thème système est sombre
    """
    try:
        # Méthode 1: Via la palette Qt
        palette = app.palette()
        window_color = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.WindowText)

        # Si la couleur de fond est plus sombre que le texte = thème sombre
        window_lightness = window_color.lightness()
        text_lightness = text_color.lightness()

        is_dark = window_lightness < text_lightness

        logger.debug(
            f"Détection thème: fond={window_lightness}, texte={text_lightness}, sombre={is_dark}"
        )
        return is_dark

    except Exception as e:
        logger.warning(
            f"Erreur détection thème système: {e}, utilisation thème clair par défaut"
        )
        return False


def _get_custom_styles() -> dict:
    """
    Retourne les styles personnalisés pour ObjecTif.
    Ces styles s'ajoutent au thème qt-material de base.
    """
    return {
        # Amélioration des boutons photo (gros boutons d'action)
        'QPushButton[class="photo-action"]': """
            QPushButton {
                font-weight: bold;
                font-size: 14px;
                min-height: 45px;
                min-width: 120px;
                border-radius: 8px;
                padding: 12px 16px;
            }
            QPushButton:hover {
                transform: translateY(-1px);
            }
        """,
        # Style pour les TreeView/ListView
        "QTreeView, QListWidget": """
            QTreeView, QListWidget {
                border-radius: 6px;
                padding: 4px;
            }
            QTreeView::item, QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
            }
        """,
        # Amélioration des GroupBox
        "QGroupBox": """
            QGroupBox {
                font-weight: bold;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
        """,
        # Style pour les indicateurs de statut ADB
        'QLabel[class="status-indicator"]': """
            QLabel {
                font-weight: bold;
                padding: 8px 12px;
                border-radius: 6px;
                min-height: 16px;
            }
        """,
        # Terminal de logs
        'QPlainTextEdit[class="log-viewer"]': """
            QPlainTextEdit {
                font-family: "Consolas", "Monaco", monospace;
                font-size: 11px;
                border-radius: 6px;
                padding: 8px;
            }
        """,
    }


# Fonction utilitaire pour appliquer une classe CSS à un widget
def set_widget_class(widget, class_name: str):
    """
    Applique une classe CSS à un widget pour le styling.

    Args:
            widget: Widget Qt à styler
            class_name: Nom de la classe CSS
    """
    widget.setProperty("class", class_name)
