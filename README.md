# Application de Gestion de Budget

Une application professionnelle de gestion budgétaire construite avec PyQt6. Cette application vous aide à suivre vos dépenses, gérer vos budgets et générer des rapports financiers avec intégration des prix du Bitcoin.

## Fonctionnalités

- **Gestion des Dépenses**: Ajoutez, modifiez et supprimez des dépenses avec catégories, dates et montants
- **Organisation par Catégories**: Organisez les dépenses selon des catégories personnalisées
- **Validation des Données**: Validation intégrée pour tous les saisies de données
- **Gestion de Base de Données**: Base de données SQLite pour stockage persistant
- **Import/Export**: Importez et exportez les données financières vers/depuis divers formats
- **Intégration Bitcoin**: Intégration API Bitcoin en temps réel pour le suivi des cryptomonnaies
- **Visualisation Graphique**: Représentation visuelle des données de dépenses
- **Rapports PDF**: Générez des rapports PDF professionnels de votre budget
- **Thème Sombre**: Interface utilisateur avec thème sombre professionnel (PyQt Dark Theme)
- **Travailleurs Asynchrones**: Traitement des tâches asynchrone pour une expérience utilisateur fluide

## Structure du Projet

```
budget/
├── main.py                      # Point d'entrée de l'application
├── controller.py                # Contrôleur logique métier (pattern MVC)
├── view.py                      # Vue principale de l'interface (pattern MVC)
├── graph_view.py                # Composant de visualisation graphique
├── migrate_json_to_sqlite.py   # Utilitaire de migration des données
├── bob.sh                       # Utilitaire script shell
├── requirements.txt             # Dépendances du projet
│
├── core/                        # Modules applicatifs principaux
│   ├── __init__.py
│   ├── model.py                # Modèle de données (pattern MVC)
│   ├── data_models.py          # Classes de données et exceptions
│   ├── database.py             # Gestion de base de données et requêtes
│   ├── services.py             # Services métier (import/export, API)
│   └── validation.py           # Logique de validation des données
│
├── ui/                          # Composants d'interface utilisateur
│   ├── __init__.py
│   └── custom_widgets.py       # Widgets PyQt6 personnalisés
│
├── workers/                     # Travailleurs de tâches asynchrones
│   ├── __init__.py
│   └── task_workers.py         # Traitement des tâches en arrière-plan
│
└── tests/                       # Suite de tests
    ├── test_bitcoin_service.py
    ├── test_database.py
    ├── test_model_filtering.py
    └── test_pdf_report.py
```

## Architecture

Cette application suit le pattern **Model-View-Controller (MVC)**:

- **Modèle** (`core/model.py`): Gère les données et la logique métier de l'application
- **Vue** (`view.py`): Gère l'interface utilisateur avec PyQt6
- **Contrôleur** (`controller.py`): Fait la médiation entre le Modèle et la Vue

### Composants Principaux

- **DatabaseManager**: Gère toutes les opérations de base de données SQLite
- **DataValidator**: Valide les entrées utilisateur et l'intégrité des données
- **ImportExportService**: Gère les opérations d'import/export de données
- **BitcoinAPIService**: Intègre l'API Bitcoin pour les données en temps réel

## Installation

### Prérequis

- Python 3.7+
- pip (gestionnaire de paquets Python)

### Configuration

1. Clonez ou téléchargez ce projet:
```bash
cd budget
```

2. Installez les dépendances:
```bash
pip install -r requirements.txt
```

## Dépendances

- **PyQt6**: Framework d'interface graphique
- **matplotlib**: Visualisation et graphiques de données
- **requests**: Bibliothèque HTTP pour les appels API
- **openpyxl**: Gestion des fichiers Excel
- **pyqtdarktheme**: Thème sombre pour PyQt6
- **reportlab**: Génération de PDF

## Utilisation

### Lancer l'Application

```bash
python main.py
```

### Migration des Données

Pour migrer les données de JSON vers SQLite:

```bash
python migrate_json_to_sqlite.py
```

## Tests

Exécutez la suite de tests:

```bash
pytest tests/
```

Modules de test individuels:
- `test_bitcoin_service.py`: Tests d'intégration de l'API Bitcoin
- `test_database.py`: Tests des opérations de base de données
- `test_model_filtering.py`: Tests de filtrage des données
- `test_pdf_report.py`: Tests de génération de rapports PDF

## Développement

### Fonctionnalités Principales à Explorer

1. **Gestion des Dépenses**: Suivez les dépenses avec dates, montants et catégories
2. **Analyse Budgétaire**: Visualisez les tendances de dépenses via des graphiques
3. **Génération de Rapports**: Créez des rapports PDF de résumés budgétaires
4. **Import/Export de Données**: Transférez les données vers d'autres formats
5. **Suivi du Bitcoin**: Surveillez les prix du Bitcoin en parallèle de vos dépenses

### Conventions de Projet

- Toutes les opérations de base de données passent par `DatabaseManager`
- Toutes les entrées utilisateur sont validées via `DataValidator`
- La logique métier est gérée dans `core/services.py`
- Les composants d'interface utilisateur sont dans `view.py` et `ui/custom_widgets.py`
- Les tâches asynchrones utilisent `task_workers.py`

## Configuration

Les fichiers de configuration sont généralement stockés dans `~/.config/` ou dans les répertoires du projet. Les fichiers de base de données sont stockés localement pour un accès facile et une sauvegarde.

## Dépannage

### Problèmes Courants

- **Erreurs d'Import**: Assurez-vous que toutes les dépendances sont installées via `pip install -r requirements.txt`
- **Erreurs de Base de Données**: Vérifiez que vous avez les permissions d'écriture dans le répertoire du projet
- **Erreurs d'API**: Vérifiez la connexion Internet pour les appels API Bitcoin

## Licence

[Ajoutez votre licence ici]

## Contribution

[Ajoutez les directives de contribution ici]

## Support

Pour les problèmes ou questions, veuillez consulter les fichiers de test pour des exemples d'utilisation de chaque composant.

---

**Dernière mise à jour**: 2026-09-12
