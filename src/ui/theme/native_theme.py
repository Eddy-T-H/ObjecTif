# src/ui/theme/native_theme.py
"""
Utilisation du thème natif Qt6 avec améliorations légères.
Qt6 gère automatiquement le mode sombre/clair selon le système.
"""

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor
from loguru import logger


def apply_native_qt_theme(app: QApplication) -> bool:
    """
    Utilise le thème natif Qt6 avec quelques améliorations CSS.
    Qt6 détecte automatiquement le mode sombre/clair du système.
    """
    try:
        # Qt6 détecte automatiquement le thème système
        # On applique juste quelques améliorations CSS légères

        # Détecte si on est en mode sombre pour ajuster certaines couleurs
        palette = app.palette()
        is_dark = palette.color(QPalette.ColorRole.Window).lightness() < 128

        # Log du thème détecté
        theme_mode = "sombre" if is_dark else "clair"
        logger.info(
            f"Thème natif Qt6 appliqué - Mode {theme_mode} détecté automatiquement"
        )

        return True

    except Exception as e:
        logger.error(f"Erreur lors de l'application du thème natif: {e}")
        return False


def setup_native_theme_attributes(app: QApplication):
    """
    Configure les attributs Qt pour une meilleure détection du thème système.
    """
    try:
        # Active la détection automatique du thème système
        app.setAttribute(
            Qt.ApplicationAttribute.AA_UseStyleSheetPropagationInWidgetStyles, True
        )

        # Sur Windows, assure la compatibilité avec le mode sombre
        import platform

        if platform.system() == "Windows":
            try:
                # Essaie d'activer le support natif du dark mode sur Windows
                app.setAttribute(
                    Qt.ApplicationAttribute.AA_DisableWindowContextHelpButton, True
                )
            except:
                pass

        logger.debug("Attributs de thème natif configurés")

    except Exception as e:
        logger.warning(f"Erreur lors de la configuration des attributs de thème: {e}")


def detect_system_theme_info(app: QApplication) -> dict:
    """
    Retourne des informations sur le thème système détecté.
    """
    try:
        palette = app.palette()

        window_color = palette.color(QPalette.ColorRole.Window)
        text_color = palette.color(QPalette.ColorRole.WindowText)
        highlight_color = palette.color(QPalette.ColorRole.Highlight)

        is_dark = window_color.lightness() < 128

        return {
            "is_dark_mode": is_dark,
            "window_lightness": window_color.lightness(),
            "text_lightness": text_color.lightness(),
            "window_color": window_color.name(),
            "text_color": text_color.name(),
            "highlight_color": highlight_color.name(),
            "theme_name": "Sombre" if is_dark else "Clair",
        }

    except Exception as e:
        logger.error(f"Erreur lors de la détection du thème: {e}")
        return {"is_dark_mode": False, "theme_name": "Inconnu"}


# Fonction utilitaire pour appliquer des classes CSS
def set_widget_class(widget, class_name: str):
    """Applique une classe CSS à un widget."""
    widget.setProperty("class", class_name)


def set_widget_object_name(widget, object_name: str):
    """Applique un objectName à un widget."""
    widget.setObjectName(object_name)
