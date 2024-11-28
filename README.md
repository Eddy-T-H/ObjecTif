# ObjecTif - Gestionnaire de Preuves Numériques

ObjecTif est une application de bureau moderne conçue pour faciliter la gestion et la documentation des preuves numériques dans le cadre d'investigations. Elle permet de gérer efficacement les photos de scellés et d'objets tout en assurant une traçabilité complète des manipulations.

## Caractéristiques Principales

ObjecTif permet la documentation photographique systématique des éléments suivants :
- Scellés fermés avant ouverture
- Contenu des scellés lors de l'ouverture
- Objets d'essai individuels
- Scellés reconditionnés après examen

L'application offre également :
- Une interface utilisateur moderne et intuitive
- Une gestion automatisée des connexions aux appareils Android
- Un système de nommage standardisé des fichiers
- Une organisation structurée des dossiers
- Une traçabilité complète des opérations

## Prérequis Techniques

- Python 3.13 ou supérieur
- Windows 10/11
- Appareil Android avec le débogage USB activé
- Pilotes ADB installés sur le système

## Installation

1. Clonez le dépôt :
```bash
git clone [URL_du_depot]
cd ObjecTif
```

2. Créez un environnement virtuel :
```bash
python -m venv .venv
```

3. Activez l'environnement virtuel :
```bash
# Windows
.venv\Scripts\activate

# Linux/macOS
source .venv/bin/activate
```

4. Installez les dépendances :
```bash
pip install -r requirements.txt
```

5. Créez un fichier `.env` à la racine du projet :
```env
DEBUG_MODE=true
APP_BASE_PATH=chemin/vers/dossier/stockage
```

## Utilisation

1. Activez l'environnement virtuel (si ce n'est pas déjà fait)
2. Lancez l'application :
```bash
python src/main.py
```

## Structure du Projet

```
ObjecTif/
├── src/                    # Code source
│   ├── core/              # Logique métier
│   ├── ui/                # Interface utilisateur
│   └── utils/             # Utilitaires
├── tests/                 # Tests unitaires
├── resources/             # Ressources
└── docs/                  # Documentation
```

## Architecture

L'application est construite selon une architecture modulaire :
- Interface utilisateur : PyQt6 pour une interface moderne et réactive
- Gestion ADB : adb-shell pour une communication sécurisée avec les appareils Android
- Stockage : Organisation hiérarchique des dossiers avec traçabilité


## Sécurité

- L'application utilise adb-shell pour une communication sécurisée avec les appareils Android
- Toutes les opérations sont journalisées pour assurer la traçabilité
- Les manipulations de preuves suivent les bonnes pratiques d'investigation numérique

## License

[À définir selon vos besoins]

## Contact

[informations de contact]

## Acknowledgements

- PyQt6 pour l'interface graphique
- adb-shell pour la communication Android
- Autres bibliothèques Python utilisées

## Roadmap

Fonctionnalités prévues :
- Support multi-plateforme complet
- Interface multilingue
- Export de rapports automatisés
- Signatures numériques des photos