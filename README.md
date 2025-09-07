# AutoSwitchTheme

[![Python Version](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Application Python qui change automatiquement le thème Windows (clair/sombre) en fonction des heures de lever et coucher du soleil.

## Fonctionnalités

- **Changement automatique** : Bascule automatiquement entre les thèmes clair et sombre selon les horaires solaires
- **API météo intégrée** : Utilise l'API Meteo-Concept pour récupérer les données de lever/coucher du soleil
- **Interface système** : Fonctionne en arrière-plan avec une icône dans la barre des tâches
- **Contrôle manuel** : Possibilité de forcer le thème clair ou sombre via le menu de l'icône
- **Cache intelligent** : Met en cache les données solaires pour éviter les appels API répétés
- **Logging complet** : Système de journalisation avec rotation automatique des fichiers

## Installation

### Prérequis

- Windows 10/11
- Python 3.8 ou supérieur
- Clé API Meteo-Concept (gratuite)

### Installation des dépendances

```bash
pip install -r requierement.txt
```

### Configuration

1. **Obtenir une clé API Meteo-Concept** :
   - Rendez-vous sur [https://api.meteo-concept.com/](https://api.meteo-concept.com/)
   - Créez un compte gratuit
   - Récupérez votre token API

2. **Configurer l'application** :
   - Modifiez le fichier `config.ini` :
     ```ini
     [api]
     token = VOTRE_TOKEN_API_ICI

     [location]
     insee = 06033  # Code INSEE de votre ville (ex: 06033 pour Nice)

     [log]
     path = logs
     debug = true
     ```

   - **Trouver votre code INSEE** : [https://www.insee.fr/fr/information/2560452](https://www.insee.fr/fr/information/2560452)

## Utilisation

### Mode développement

```bash
python main.py
```

### Création d'un exécutable

L'application peut être compilée en exécutable autonome avec PyInstaller :

```bash
pyinstaller -F -w --optimize=2 --icon app.ico -n AutoSwitchTheme main.py
```

### Utilisation de l'application

1. Lancez l'application
2. Elle se minimise automatiquement dans la barre des tâches
3. Cliquez droit sur l'icône pour accéder au menu :
   - **Show Status** : Affiche l'état actuel et les heures solaires
   - **Force Light Theme** : Force le thème clair
   - **Force Dark Theme** : Force le thème sombre
   - **Quit** : Quitte l'application

## Architecture

```
AutoSwitchTheme/
├── main.py                 # Point d'entrée principal
├── config.ini             # Configuration (API, localisation, logs)
├── requierement.txt       # Dépendances Python
└── README.md             # Ce fichier
```

### Composants principaux

- **TrayApp** : Gestion de l'interface système (icône et menu)
- **SunHoursMonitor** : Récupération et cache des données solaires via API
- **ThemeMonitor** : Changement du thème Windows via registre
- **Logger** : Système de journalisation avec rotation

## Configuration avancée

### Variables d'environnement

L'application utilise le dossier `%APPDATA%\AutoSwitchTheme` pour :
- Stocker les logs (`logs/`)
- Mettre en cache les données solaires (`sun_hours.json`)
- Sauvegarder la configuration (`config.ini`)

### Fréquence de mise à jour

- **Données solaires** : Actualisées quotidiennement à minuit
- **Vérification du thème** : Toutes les 60 secondes
- **Logs** : Rotation automatique tous les jours, conservation de 30 jours

## Dépendances

- **requests** : Appels API HTTP
- **schedule** : Planification des tâches
- **pystray** : Interface système tray
- **Pillow** : Création de l'icône système

## Dépannage

### Problèmes courants

1. **Erreur API** : Vérifiez votre token et code INSEE
2. **Thème ne change pas** : Redémarrez l'explorateur Windows (`explorer.exe`)
3. **Application ne démarre pas** : Vérifiez les logs dans `%APPDATA%\AutoSwitchTheme\logs\`

### Logs de débogage

Activez le mode debug dans `config.ini` :
```ini
[log]
debug = true
```

Les logs sont disponibles dans `%APPDATA%\AutoSwitchTheme\logs\app.log`

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.

**Note** : Cette application modifie les paramètres du registre Windows. Bien que conçue pour être sûre, il est recommandé de faire une sauvegarde du registre avant utilisation intensive.
