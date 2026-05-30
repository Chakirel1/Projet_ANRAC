#  Référence Technique & Architecture Logicielle

Cette section détaille les choix architecturaux, la structure algorithmique et les mécanismes de résilience mis en œuvre dans l'application de télédétection de l'ANRAC.

---

## Principes de Conception : Séparation des Préoccupations

Pour garantir la maintenabilité, l'extensibilité et la testabilité du système, l'application applique strictement le patron de conception de **Séparation des Préoccupations** (*Separation of Concerns - SoC*). Le code est structurellement découplé en deux couches distinctes :

### 1. Couche Présentation : `src/app.py`
Le script `app.py` agit comme le chef d'orchestre de l'interface graphique. Ses responsabilités sont exclusivement limitées à :
* **La gestion de l'IHM** : Déclaration, stylisation et rendu des composants graphiques (widgets, barres latérales, curseurs) via le framework **Streamlit**.
* **La capture des événements** : Interception des interactions utilisateurs (saisie de coordonnées, choix des dates) et acheminement vers la couche métier.
* **La gestion de l'état (*Session State*)** : Utilisation des mécanismes de persistance de Streamlit (`st.session_state`) pour optimiser la mémoire et éviter les rechargements matriciels intempestifs lors des interactions de l'utilisateur.

### 2. Couche Métier & Algorithmique : `src/core_processing.py`
Ce module constitue le cœur computationnel indépendant de l'application. Totalement agnostique de l'interface graphique, il encapsule toute la logique métier :
* **Gestion Protocolaire** : Authentification et communication sécurisée via OAuth2 avec les fournisseurs d'imagerie satellitaire (Sentinel Hub).
* **Ingénierie des Données** : Manipulation des structures tabulaires matricielles (tableaux multidimensionnels **NumPy**) et traitement des métadonnées géospatiales complexes via **Pandas**.

---

## Schéma du Flux de Données

Le diagramme suivant illustre le cycle de vie d'une requête, depuis l'action utilisateur jusqu'au rendu cartographique final :

```mermaid
graph TD
    A[Opérateur / Utilisateur] -->|Définit BBox, Date & Cloud Cover| B(Couche Présentation : app.py)
    B -->|Transmet les hyperparamètres| C{Contrôle de connectivité API}
    C -->|Flux Nominal| D[core_processing.py : Requête Sentinel Hub API] -->|Extraction Matrice Image| F[Pipeline de Traitement & Alignement Pandas/NumPy]
    C -->|Flux Dégradé / Exception| E[core_processing.py : Fallback Mock Data Local] -->|Simulation Matrice| F
    F -->|Génération de la Couche Raster| G[Moteur Cartographique : Folium Object]
    G -->|Injection Dynamique| B
    B -->|Affichage Fluide| A
