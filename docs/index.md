![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28-FF4B4B?logo=streamlit&logoColor=white)
![MkDocs](https://img.shields.io/badge/MkDocs-Material-526CFE?logo=markdown&logoColor=white)
![License](https://img.shields.io/badge/Licence-MIT-green)
# Plateforme Avancée de Télédétection pour l'ANRAC

## Contextualisation Institutionnelle
Ce projet s'inscrit dans le cadre de la modernisation technologique et du suivi réglementaire mené par l'**ANRAC** (Agence Nationale de Réglementation des Activités relatives au Cannabis). Face aux enjeux de contrôle, de traçabilité et de conformité des parcelles de culture autorisées, l'intégration des technologies géospatiales s'avère indispensable.

Cette application web interactive a été conçue comme une solution d'aide à la décision, permettant aux ingénieurs et inspecteurs de l'agence d'accéder à des analyses cartographiques de pointe sans nécessiter d'expertise approfondie en programmation de scripts de télédétection.

## Objectifs Principaux de l'Application

L'outil répond à des impératifs opérationnels et académiques précis :

1. **Suivi Temporel et Spatial** : Permettre l'observation continue des parcelles agricoles cibles à travers différentes époques de l'année grâce à l'imagerie satellite.
2. **Optimisation du Contrôle de Conformité** : Faciliter la détection des limites de parcelles (Bounding Boxes) et assurer l'adéquation entre les autorisations accordées et la réalité du terrain.
3. **Démocratisation de la Télédétection** : Masquer la complexité des requêtes API brutes envoyées aux constellations satellites en proposant une interface de visualisation épurée et interactive.
4. **Fiabilité Institutionnelle** : Garantir la continuité des audits et des démonstrations grâce à un système résilient, capable de simuler des scénarios locaux même en cas de rupture de flux de données externes.

## Architecture du Code Source

Le projet adopte une architecture logicielle modulaire et hautement découplée :

```text
Projet_ANRAC/
├── .streamlit/
│   └── secrets.toml          # Identifiants API privés (générés localement)
├── src/
│   ├── app.py                # Interface utilisateur (UI) et routage Streamlit
│   └── core_processing.py    # Moteur de calcul et logique métier
├── requirements.txt          # Dépendances logicielles du projet
└── mkdocs.yml                # Configuration de cette documentation
