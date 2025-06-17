# src/ui/theme/design_system.py
"""
Système de design unifié pour ObjecTif.
Définit tous les styles et composants réutilisables.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any


class DesignTokens:
    """Tokens de design centralisés - source unique de vérité pour tous les styles."""

    # === COULEURS ===
    class Colors:
        # Palette principale
        PRIMARY = "#2196F3"
        PRIMARY_LIGHT = "#64B5F6"
        PRIMARY_DARK = "#1976D2"

        # Couleurs secondaires
        SUCCESS = "#4CAF50"
        WARNING = "#FF9800"
        ERROR = "#F44336"
        INFO = "#00BCD4"

        # Couleurs neutres
        BACKGROUND = "#FAFAFA"
        SURFACE = "#FFFFFF"
        SURFACE_VARIANT = "#F5F5F5"

        # Bordures et séparateurs
        BORDER = "#E0E0E0"
        BORDER_HOVER = "#BDBDBD"
        BORDER_FOCUS = PRIMARY

        # Texte
        TEXT_PRIMARY = "#212121"
        TEXT_SECONDARY = "#757575"
        TEXT_DISABLED = "#BDBDBD"
        TEXT_ON_PRIMARY = "#FFFFFF"

        # États
        HOVER = "#F5F5F5"
        PRESSED = "#EEEEEE"
        SELECTED = "#E3F2FD"
        DISABLED = "#F5F5F5"

    # === TYPOGRAPHIE ===
    class Typography:
        # Tailles
        HEADING_1 = 18
        HEADING_2 = 16
        HEADING_3 = 14
        BODY = 12
        CAPTION = 11

        # Poids
        LIGHT = 300
        REGULAR = 400
        MEDIUM = 500
        BOLD = 600

    # === ESPACEMENT ===
    class Spacing:
        XS = 4
        SM = 8
        MD = 12
        LG = 16
        XL = 20
        XXL = 24

    # === RAYONS DE COURBURE ===
    class BorderRadius:
        SMALL = 4
        MEDIUM = 6
        LARGE = 8
        XLARGE = 12

    # === OMBRES ===
    class Shadows:
        LIGHT = "0 1px 3px rgba(0,0,0,0.12)"
        MEDIUM = "0 2px 8px rgba(0,0,0,0.15)"
        STRONG = "0 4px 16px rgba(0,0,0,0.2)"


class StyleSheets:
    """Générateur de feuilles de style cohérentes."""

    @staticmethod
    def group_box(title_color: str = DesignTokens.Colors.TEXT_PRIMARY) -> str:
        """Style unifié pour tous les QGroupBox."""
        return f"""
        QGroupBox {{
            font-weight: {DesignTokens.Typography.MEDIUM};
            font-size: {DesignTokens.Typography.HEADING_3}px;
            border: 2px solid {DesignTokens.Colors.BORDER};
            border-radius: {DesignTokens.BorderRadius.LARGE}px;
            margin-top: {DesignTokens.Spacing.MD}px;
            padding-top: {DesignTokens.Spacing.SM}px;
            background-color: {DesignTokens.Colors.BACKGROUND};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: {DesignTokens.Spacing.MD}px;
            padding: 0 {DesignTokens.Spacing.SM}px 0 {DesignTokens.Spacing.SM}px;
            color: {title_color};
        }}
        """

    @staticmethod
    def button_primary() -> str:
        """Bouton principal - pour les actions importantes."""
        return f"""
        QPushButton {{
            background-color: {DesignTokens.Colors.PRIMARY};
            color: {DesignTokens.Colors.TEXT_ON_PRIMARY};
            border: none;
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            padding: {DesignTokens.Spacing.SM}px {DesignTokens.Spacing.MD}px;
            font-size: {DesignTokens.Typography.BODY}px;
            font-weight: {DesignTokens.Typography.MEDIUM};
            min-height: 32px;
        }}
        QPushButton:hover {{
            background-color: {DesignTokens.Colors.PRIMARY_LIGHT};
        }}
        QPushButton:pressed {{
            background-color: {DesignTokens.Colors.PRIMARY_DARK};
        }}
        QPushButton:disabled {{
            background-color: {DesignTokens.Colors.DISABLED};
            color: {DesignTokens.Colors.TEXT_DISABLED};
        }}
        """

    @staticmethod
    def button_secondary() -> str:
        """Bouton secondaire - pour les actions moins importantes."""
        return f"""
        QPushButton {{
            background-color: {DesignTokens.Colors.SURFACE};
            color: {DesignTokens.Colors.TEXT_PRIMARY};
            border: 1px solid {DesignTokens.Colors.BORDER};
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            padding: {DesignTokens.Spacing.SM}px {DesignTokens.Spacing.MD}px;
            font-size: {DesignTokens.Typography.BODY}px;
            font-weight: {DesignTokens.Typography.REGULAR};
            min-height: 32px;
        }}
        QPushButton:hover {{
            background-color: {DesignTokens.Colors.HOVER};
            border-color: {DesignTokens.Colors.BORDER_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {DesignTokens.Colors.PRESSED};
        }}
        QPushButton:disabled {{
            background-color: {DesignTokens.Colors.DISABLED};
            color: {DesignTokens.Colors.TEXT_DISABLED};
            border-color: {DesignTokens.Colors.BORDER};
        }}
        """

    @staticmethod
    def button_action(color: str, hover_color: str, pressed_color: str) -> str:
        """Bouton d'action coloré - pour les actions spécifiques (photos)."""
        return f"""
        QPushButton {{
            background-color: {color};
            color: {DesignTokens.Colors.TEXT_ON_PRIMARY};
            border: none;
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            padding: {DesignTokens.Spacing.MD}px {DesignTokens.Spacing.LG}px;
            font-size: {DesignTokens.Typography.BODY}px;
            font-weight: {DesignTokens.Typography.MEDIUM};
            min-height: 36px;
            min-width: 100px;
        }}
        QPushButton:hover {{
            background-color: {hover_color};
            transform: translateY(-1px);
        }}
        QPushButton:pressed {{
            background-color: {pressed_color};
            transform: translateY(0px);
        }}
        QPushButton:disabled {{
            background-color: {DesignTokens.Colors.DISABLED};
            color: {DesignTokens.Colors.TEXT_DISABLED};
        }}
        """

    @staticmethod
    def tree_view() -> str:
        """Style unifié pour tous les QTreeView."""
        return f"""
        QTreeView {{
            background-color: {DesignTokens.Colors.SURFACE};
            border: 1px solid {DesignTokens.Colors.BORDER};
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            selection-background-color: {DesignTokens.Colors.SELECTED};
            font-size: {DesignTokens.Typography.BODY}px;
            padding: {DesignTokens.Spacing.XS}px;
        }}
        QTreeView::item {{
            padding: {DesignTokens.Spacing.XS}px {DesignTokens.Spacing.SM}px;
            border-radius: {DesignTokens.BorderRadius.SMALL}px;
        }}
        QTreeView::item:hover {{
            background-color: {DesignTokens.Colors.HOVER};
        }}
        QTreeView::item:selected {{
            background-color: {DesignTokens.Colors.SELECTED};
            color: {DesignTokens.Colors.TEXT_PRIMARY};
        }}
        """

    @staticmethod
    def list_widget() -> str:
        """Style unifié pour tous les QListWidget."""
        return f"""
        QListWidget {{
            background-color: {DesignTokens.Colors.SURFACE};
            border: 1px solid {DesignTokens.Colors.BORDER};
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            selection-background-color: {DesignTokens.Colors.SELECTED};
            font-size: {DesignTokens.Typography.BODY}px;
            padding: {DesignTokens.Spacing.XS}px;
        }}
        QListWidget::item {{
            padding: {DesignTokens.Spacing.SM}px;
            border-radius: {DesignTokens.BorderRadius.SMALL}px;
            margin: 1px;
        }}
        QListWidget::item:hover {{
            background-color: {DesignTokens.Colors.HOVER};
        }}
        QListWidget::item:selected {{
            background-color: {DesignTokens.Colors.SELECTED};
            color: {DesignTokens.Colors.TEXT_PRIMARY};
        }}
        """

    @staticmethod
    def status_indicator(status: str) -> str:
        """Indicateurs d'état avec couleurs sémantiques."""
        colors = {
            "connected": DesignTokens.Colors.SUCCESS,
            "disconnected": DesignTokens.Colors.ERROR,
            "warning": DesignTokens.Colors.WARNING,
            "info": DesignTokens.Colors.INFO,
        }

        color = colors.get(status, DesignTokens.Colors.TEXT_SECONDARY)

        return f"""
        QLabel {{
            background-color: {color};
            color: {DesignTokens.Colors.TEXT_ON_PRIMARY};
            padding: {DesignTokens.Spacing.SM}px {DesignTokens.Spacing.MD}px;
            border-radius: {DesignTokens.BorderRadius.MEDIUM}px;
            font-weight: {DesignTokens.Typography.MEDIUM};
            font-size: {DesignTokens.Typography.BODY}px;
        }}
        """


class ComponentFactory:
    """Factory pour créer des composants avec des styles cohérents."""

    @staticmethod
    def create_group_box(
        title: str, title_color: str = DesignTokens.Colors.TEXT_PRIMARY
    ):
        """Crée un QGroupBox avec le style unifié."""
        from PyQt6.QtWidgets import QGroupBox

        group = QGroupBox(title)
        group.setStyleSheet(StyleSheets.group_box(title_color))
        return group

    @staticmethod
    def create_primary_button(text: str):
        """Crée un bouton principal."""
        from PyQt6.QtWidgets import QPushButton

        button = QPushButton(text)
        button.setStyleSheet(StyleSheets.button_primary())
        return button

    @staticmethod
    def create_secondary_button(text: str):
        """Crée un bouton secondaire."""
        from PyQt6.QtWidgets import QPushButton

        button = QPushButton(text)
        button.setStyleSheet(StyleSheets.button_secondary())
        return button

    @staticmethod
    def create_action_button(text: str, action_type: str):
        """Crée un bouton d'action coloré selon le type."""
        from PyQt6.QtWidgets import QPushButton

        # Définition des couleurs par type d'action
        action_colors = {
            "photo_scelle": (DesignTokens.Colors.SUCCESS, "#66BB6A", "#388E3C"),
            "photo_contenu": (DesignTokens.Colors.WARNING, "#FFB74D", "#F57C00"),
            "photo_objet": ("#9C27B0", "#BA68C8", "#7B1FA2"),
            "photo_recond": ("#607D8B", "#78909C", "#455A64"),
            "camera": (DesignTokens.Colors.INFO, "#4DD0E1", "#0097A7"),
        }

        colors = action_colors.get(action_type, action_colors["photo_scelle"])

        button = QPushButton(text)
        button.setStyleSheet(StyleSheets.button_action(*colors))
        return button

    @staticmethod
    def create_tree_view():
        """Crée un QTreeView avec le style unifié."""
        from PyQt6.QtWidgets import QTreeView

        tree = QTreeView()
        tree.setStyleSheet(StyleSheets.tree_view())
        return tree

    @staticmethod
    def create_list_widget():
        """Crée un QListWidget avec le style unifié."""
        from PyQt6.QtWidgets import QListWidget

        list_widget = QListWidget()
        list_widget.setStyleSheet(StyleSheets.list_widget())
        return list_widget


# === THÈMES ALTERNATIFS ===
class DarkTheme(DesignTokens):
    """Variante sombre des tokens de design."""

    class Colors(DesignTokens.Colors):
        # Couleurs principales adaptées au thème sombre
        BACKGROUND = "#121212"
        SURFACE = "#1E1E1E"
        SURFACE_VARIANT = "#2A2A2A"

        BORDER = "#333333"
        BORDER_HOVER = "#555555"

        TEXT_PRIMARY = "#FFFFFF"
        TEXT_SECONDARY = "#AAAAAA"
        TEXT_DISABLED = "#666666"

        HOVER = "#2A2A2A"
        PRESSED = "#333333"
        SELECTED = "#1A237E"


# === UTILITAIRES ===
def apply_global_theme():
    """Applique le thème global à l'application."""
    return f"""
    QMainWindow {{
        background-color: {DesignTokens.Colors.BACKGROUND};
        color: {DesignTokens.Colors.TEXT_PRIMARY};
    }}

    QWidget {{
        font-family: "Segoe UI", Arial, sans-serif;
        font-size: {DesignTokens.Typography.BODY}px;
    }}

    QSplitter::handle {{
        background-color: {DesignTokens.Colors.BORDER};
    }}

    QSplitter::handle:horizontal {{
        width: 2px;
    }}

    QSplitter::handle:vertical {{
        height: 2px;
    }}
    """
