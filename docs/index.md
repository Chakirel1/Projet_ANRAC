```markdown
# Projet ANRAC - Plateforme de Télédétection

Bienvenue sur la documentation technique de l'application de télédétection développée pour l'**ANRAC**. Cette plateforme permet l'acquisition, le traitement et la visualisation d'images satellites pour l'analyse des dynamiques territoriales.

## Présentation Générale

L'application offre une interface moderne et intuitive (propulsée par **Streamlit**) permettant de croiser des données géospatiales complexes à travers deux modes opérationnels majeurs :

* **Mode API (Sentinel Hub)** : Connexion directe aux serveurs de l'Agence Spatiale Européenne (ESA) pour récupérer, filtrer et afficher des imageries satellites en temps réel selon des coordonnées géographiques précises.
* **Mode Local (Démo)** : Chargement de banques de données locales sécurisées pour simuler des analyses temporelles et spatiales sans nécessiter de connexion internet active.

## Architecture du Code Source

Le projet adopte une architecture logicielle modulaire et hautement découplée :

```text
Projet_ANRAC/
├── .streamlit/
│   └── secrets.toml        # Identifiants API privés (ignorés par Git)
├── src/
│   ├── app.py              # Interface utilisateur (UI) et routage Streamlit
│   └── core_processing.py  # Moteur de calcul, algorithmes et logique métier
├── requirements.txt        # Dépendances logicielles du projet
└── mkdocs.yml              # Configuration de cette documentation
