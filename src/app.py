"""Point d'entrée de l'application Streamlit ANRAC.

Gère l'interface utilisateur, la configuration des paramètres spatiaux
et le rendu visuel des pipelines d'analyse géospatiale.
"""

import streamlit as st
import folium
from streamlit_folium import st_folium
import numpy as np
import cv2
import matplotlib.pyplot as plt
import traceback
from sentinelhub import SHConfig

# Importation du module métier
from core_processing import train_spectral_classifier, fetch_sentinel2_data, run_spatial_analysis_pipeline

# Configuration initiale de la page
st.set_page_config(page_title="ANRAC - SIG Haute Performance", layout="wide", page_icon="🛰️")
st.title("Plateforme SIG ANRAC - Détection Multi-Spectrale")
st.markdown("*Statut : Algorithmes calibrés pour la réduction du taux d'erreur (Ségrégation d'anomalies).*")
st.write("---")

if "coords_cibles" not in st.session_state:
    st.session_state.coords_cibles = None

# Chargement en cache du modèle IA
@st.cache_resource
def load_model():
    return train_spectral_classifier()

modele_ia = load_model()

# ==========================================
# CONFIGURATION DES PARAMÈTRES (SIDEBAR)
# ==========================================
st.sidebar.header("Paramètres de Sécurité SIG")
st.sidebar.write("---")
activer_filtrage = st.sidebar.checkbox("Activer le filtrage morphologique", value=True)
surface_minimale = st.sidebar.slider("Superficie minimale (Ha)", 0.05, 1.0, 0.10, step=0.05)
surface_maximale = st.sidebar.slider("Superficie maximale (Ha)", 1.0, 15.0, 6.0, step=0.5)

parametres_geometriques = {
    "filtrer": activer_filtrage, "surf_min": surface_minimale, "surf_max": surface_maximale
}
seuil_sensibilite_ia = st.sidebar.slider("Sensibilité du Modèle", min_value=0.20, max_value=0.85, value=0.55, step=0.05)

# ==========================================
# INTERFACE UTILISATEUR EN ONGLETS
# ==========================================
onglets = st.tabs(["Mode API (Sentinel Hub)", " Mode Local (Démo)"])

with onglets[0]:
    st.subheader("Centre de Diagnostic Visualisation - Cloud API")
    config = SHConfig()
    try:
        config.sh_client_id = st.secrets["sentinelhub"]["client_id"]
        config.sh_client_secret = st.secrets["sentinelhub"]["client_secret"]
        api_disponible = True
    except Exception:
        st.warning("Identifiants API absents (`.streamlit/secrets.toml`). Mode restreint.")
        api_disponible = False

    if api_disponible:
        st.sidebar.write("---")
        st.sidebar.subheader(" Coordonnées")
        input_lat = st.sidebar.number_input("Latitude :", value=34.9100, format="%.4f")
        input_lng = st.sidebar.number_input("Longitude :", value=-4.5700, format="%.4f")
        
        if st.sidebar.button(" Centrer la carte"):
            st.session_state.coords_cibles = {"lat": input_lat, "lng": input_lng}
            st.rerun()

        coordonnees_carte = [st.session_state.coords_cibles['lat'], st.session_state.coords_cibles['lng']] if st.session_state.coords_cibles else [34.9100, -4.5700]

        carte_interactive = folium.Map(location=coordonnees_carte, zoom_start=12)
        if st.session_state.coords_cibles:
            folium.Marker(coordonnees_carte, icon=folium.Icon(color="red", icon="satellite", prefix='fa')).add_to(carte_interactive)

        evenement_carte = st_folium(carte_interactive, width="100%", height=380, key="map_visuelle")
        if evenement_carte and evenement_carte.get("last_clicked"):
            clic = evenement_carte["last_clicked"]
            if not st.session_state.coords_cibles or (abs(st.session_state.coords_cibles['lat'] - clic['lat']) > 0.0001):
                st.session_state.coords_cibles = clic
                st.rerun()

        if st.session_state.coords_cibles:
            pt = st.session_state.coords_cibles
            rayon_action = 0.025 
            if st.button(" Lancer l'Analyse Cartographique", type="primary"):
                with st.spinner(" Extraction et traitement des cubes de données..."):
                    try:
                        ndvi_m, ndmi_m, rendvi_m = fetch_sentinel2_data(pt['lat'], pt['lng'], '2025-05-01', '2025-05-31', rayon_action, config)
                        ndvi_a, ndmi_a, rendvi_a = fetch_sentinel2_data(pt['lat'], pt['lng'], '2025-08-01', '2025-08-31', rayon_action, config)
                        cadre = [pt['lng'] - rayon_action, pt['lat'] - rayon_action, pt['lng'] + rayon_action, pt['lat'] + rayon_action]
                        
                        df, contours, masque, ra, ma, stats = run_spatial_analysis_pipeline(
                            ndvi_m, ndmi_m, rendvi_m, ndvi_a, ndmi_a, rendvi_a, cadre, modele_ia, seuil_sensibilite_ia, parametres_geometriques
                        )
                        
                        st.subheader("Tableau de bord d'Analyse Spatiale")
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Superficie Validée", f"{stats['surface_totale']:.2f} Ha")
                        c2.metric("Parcelles Identifiées", f"{stats['nb_parcelles']}")
                        c3.success(f"{stats['faux_positifs_elimines']} anomalies filtrées.")
                        
                        if not df.empty:
                            st.dataframe(df, use_container_width=True)
                        
                        fig, ax = plt.subplots(1, 3, figsize=(18, 5))
                        ax[0].imshow(ra, cmap='Greens', vmin=0.1, vmax=0.8); ax[0].set_title("RENDVI (Chlorophylle)")
                        ax[1].imshow(ma, cmap='YlGnBu', vmin=-0.1, vmax=0.6); ax[1].set_title("NDMI (Irrigation)")
                        fond = cv2.cvtColor(masque, cv2.COLOR_GRAY2RGB)
                        if contours: cv2.drawContours(fond, contours, -1, (255, 0, 0), 2)
                        ax[2].imshow(fond); ax[2].set_title("Vecteurs Extraits")
                        for a in ax: a.axis('off')
                        st.pyplot(fig)
                        plt.close(fig)
                    except Exception as e:
                        st.error("Erreur d'exécution du pipeline API.")
                        st.code(traceback.format_exc())

with onglets[1]:
    st.subheader(" Module d'Analyse Déconnectée")
    fichier_charge = st.file_uploader("Charger une matrice consolidée (.npz)", type=["npz"])
    st.write("---")
    
    if st.button("Lancer la Détection", type="primary"):
        with st.spinner(" Traitement matriciel en cours..."):
            try:
                shape = (500, 500)
                if fichier_charge is not None:
                    data = np.load(fichier_charge)
                    ndvi_m, ndmi_m, rendvi_m = data['ndvi_m'], data['ndmi_m'], data['rendvi_m']
                    ndvi_a, ndmi_a, rendvi_a = data['ndvi_a'], data['ndmi_a'], data['rendvi_a']
                else:
                    np.random.seed(42)
                    ndvi_m, ndmi_m, rendvi_m = np.random.uniform(0.15,0.25,shape), np.random.uniform(-0.20,-0.10,shape), np.random.uniform(0.05,0.15,shape)
                    ndvi_a, ndmi_a, rendvi_a = np.random.uniform(0.12,0.22,shape), np.random.uniform(-0.25,-0.15,shape), np.random.uniform(0.04,0.12,shape)
                    
                    # Simulation de signatures
                    cv2.rectangle(ndvi_m, (40, 40), (200, 200), 0.20, -1) # Faux positif (Maïs)
                    cv2.rectangle(ndvi_a, (40, 40), (200, 200), 0.76, -1)
                    cv2.rectangle(ndmi_a, (40, 40), (200, 200), 0.48, -1)
                    cv2.rectangle(rendvi_a, (40, 40), (200, 200), 0.35, -1)
                    cv2.circle(ndmi_a, (120, 380), 40, 0.65, -1) # Faux positif (Eau)
                    cv2.circle(ndvi_a, (120, 380), 40, 0.20, -1) 
                    cv2.rectangle(ndvi_m, (340, 340), (440, 440), 0.18, -1) # Cible valide
                    cv2.rectangle(ndvi_a, (340, 340), (440, 440), 0.81, -1)
                    cv2.rectangle(ndmi_a, (340, 340), (440, 440), 0.52, -1) 
                    cv2.rectangle(rendvi_a, (340, 340), (440, 440), 0.66, -1)

                bbox_fictive = [-4.5950, 34.8850, -4.5450, 34.9350]
                df_cadastre, contours, masque, ra, ma, stats = run_spatial_analysis_pipeline(
                    ndvi_m, ndmi_m, rendvi_m, ndvi_a, ndmi_a, rendvi_a, bbox_fictive, modele_ia, seuil_sensibilite_ia, parametres_geometriques
                )
                
                if not df_cadastre.empty:
                    st.success(" Extraction réussie. Cadastre mis à jour.")
                    st.dataframe(df_cadastre, use_container_width=True)
                    st.download_button("Exporter le registre (CSV)", data=df_cadastre.to_csv(index=False).encode('utf-8'), file_name="registre_anrac.csv", mime="text/csv")
                else:
                    st.warning("Aucune anomalie spatiale détectée.")

                fig, ax = plt.subplots(1, 3, figsize=(15, 4))
                ax[0].imshow(ra, cmap='Greens'); ax[0].set_title("RENDVI (Chlorophylle)")
                ax[1].imshow(ma, cmap='YlGnBu'); ax[1].set_title("NDMI (Irrigation)")
                fond = cv2.cvtColor(masque, cv2.COLOR_GRAY2RGB)
                if contours: cv2.drawContours(fond, contours, -1, (0, 255, 0), 2)
                ax[2].imshow(fond); ax[2].set_title("Topologie Validée")
                for a in ax: a.axis('off')
                st.pyplot(fig)
                plt.close(fig)
                
            except Exception as e:
                st.error("Erreur critique d'analyse locale.")
                st.code(traceback.format_exc())
