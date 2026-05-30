"""Module de traitement géospatial et de classification spectrale.

Ce module contient les algorithmes de calcul d'indices biophysiques,
d'entraînement du modèle Random Forest et le pipeline de segmentation spatiale.
"""

import numpy as np
import cv2
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sentinelhub import SentinelHubRequest, DataCollection, BBox, CRS, MimeType

def train_spectral_classifier() -> RandomForestClassifier:
    """Génère un jeu de données synthétique et entraîne un classificateur.

    Les classes incluent la cible (cannabis), la forêt, les vergers et les sols nus,
    basées sur des signatures phénologiques multi-temporelles.

    Returns:
        RandomForestClassifier: Modèle entraîné et équilibré.
    """
    np.random.seed(42)
    taille_classe = 1200 
    
    # Signatures: [NDVI_Mai, NDMI_Mai, RENDVI_Mai, NDVI_Aout, NDMI_Aout, RENDVI_Aout]
    target_mai = np.random.normal(loc=[0.20, -0.15, 0.10], scale=0.03, size=(taille_classe, 3))
    target_aout = np.random.normal(loc=[0.78, 0.45, 0.65], scale=0.04, size=(taille_classe, 3))
    X_target = np.hstack((target_mai, target_aout))
    y_target = np.ones(taille_classe)
    
    foret_mai = np.random.normal(loc=[0.68, 0.35, 0.48], scale=0.04, size=(taille_classe, 3))
    foret_aout = np.random.normal(loc=[0.64, 0.12, 0.42], scale=0.04, size=(taille_classe, 3))
    X_foret = np.hstack((foret_mai, foret_aout))
    y_foret = np.zeros(taille_classe)
    
    verger_mai = np.random.normal(loc=[0.35, 0.10, 0.25], scale=0.04, size=(taille_classe, 3))
    verger_aout = np.random.normal(loc=[0.55, 0.28, 0.38], scale=0.04, size=(taille_classe, 3))
    X_verger = np.hstack((verger_mai, verger_aout))
    y_verger = np.zeros(taille_classe)
    
    sol_mai = np.random.normal(loc=[0.40, 0.15, 0.25], scale=0.06, size=(taille_classe, 3)) 
    sol_aout = np.random.normal(loc=[0.38, -0.10, 0.20], scale=0.05, size=(taille_classe, 3)) 
    X_sol = np.hstack((sol_mai, sol_aout))
    y_sol = np.zeros(taille_classe)
    
    X_train = np.vstack((X_target, X_foret, X_verger, X_sol))
    y_train = np.concatenate((y_target, y_foret, y_verger, y_sol))
    
    modele = RandomForestClassifier(n_estimators=500, max_depth=15, random_state=42, class_weight='balanced')
    modele.fit(X_train, y_train)
    return modele

def calculate_spectral_indices(b04: np.ndarray, b05: np.ndarray, b07: np.ndarray, b08: np.ndarray, b11: np.ndarray) -> tuple:
    """Calcule les indices NDVI, NDMI et RENDVI à partir des bandes Sentinel-2.

    Args:
        b04 (np.ndarray): Bande Rouge.
        b05 (np.ndarray): Bande Red-Edge 1.
        b07 (np.ndarray): Bande Red-Edge 3.
        b08 (np.ndarray): Bande Proche Infrarouge (NIR).
        b11 (np.ndarray): Bande Infrarouge à ondes courtes (SWIR).

    Returns:
        tuple: Matrices normalisées (ndvi, ndmi, rendvi).
    """
    def ratio_normalise(bande_a, bande_b):
        with np.errstate(divide='ignore', invalid='ignore'):
            denom = bande_a + bande_b
            ratio = (bande_a - bande_b) / denom
            ratio = np.nan_to_num(ratio, nan=0.0, posinf=1.0, neginf=-1.0)
            return np.clip(ratio, -1.0, 1.0)

    ndvi = ratio_normalise(b08, b04)   
    ndmi = ratio_normalise(b08, b11)   
    rendvi = ratio_normalise(b07, b05) 
    return ndvi, ndmi, rendvi

def fetch_sentinel2_data(lat: float, lon: float, d_start: str, d_end: str, delta: float, config) -> tuple:
    """Télécharge et traite les données satellitaires via l'API Sentinel Hub.

    Args:
        lat (float): Latitude centrale.
        lon (float): Longitude centrale.
        d_start (str): Date de début (YYYY-MM-DD).
        d_end (str): Date de fin (YYYY-MM-DD).
        delta (float): Rayon de la bounding box.
        config (SHConfig): Configuration d'authentification API.

    Returns:
        tuple: Matrices d'indices (ndvi, ndmi, rendvi).
    """
    bbox = BBox(bbox=[lon - delta, lat - delta, lon + delta, lat + delta], crs=CRS.WGS84)
    evalscript = """//VERSION=3
    function setup() { return { input: ["B04", "B05", "B07", "B08", "B11"], output: { id: "default", bands: 5, sampleType: "FLOAT32" } }; }
    function evaluatePixel(sample) { return [sample.B04, sample.B05, sample.B07, sample.B08, sample.B11]; }"""
    
    req = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[SentinelHubRequest.input_data(data_collection=DataCollection.SENTINEL2_L2A, time_interval=(d_start, d_end))],
        responses=[SentinelHubRequest.output_response('default', MimeType.TIFF)],
        bbox=bbox, size=[500, 500], config=config
    )
    cubes = req.get_data()[0]
    if len(cubes.shape) == 4: 
        cubes = cubes[0]
    return calculate_spectral_indices(cubes[:, :, 0], cubes[:, :, 1], cubes[:, :, 2], cubes[:, :, 3], cubes[:, :, 4])

def run_spatial_analysis_pipeline(ndvi_m, ndmi_m, rendvi_m, ndvi_a, ndmi_a, rendvi_a, bbox_wgs84, model, seuil_ia: float, config_geom: dict) -> tuple:
    """Exécute la segmentation spatiale et le filtrage phénologique des parcelles.

    Applique un clustering K-Means pour la macro-segmentation, suivi d'un 
    filtrage par Random Forest et d'une analyse morphologique OpenCV.

    Args:
        ndvi_m, ndmi_m, rendvi_m (np.ndarray): Matrices d'indices de la période initiale.
        ndvi_a, ndmi_a, rendvi_a (np.ndarray): Matrices d'indices de la période finale.
        bbox_wgs84 (list): Bounding box [min_lon, min_lat, max_lon, max_lat].
        model (RandomForestClassifier): Modèle de prédiction.
        seuil_ia (float): Seuil de probabilité pour la classification.
        config_geom (dict): Dictionnaire des paramètres de filtrage spatial.

    Returns:
        tuple: (df_resultats, contours_valides, masque_filtre, rendvi_a, ndmi_a, statistiques)
    """
    hauteur, largeur = ndvi_m.shape
    
    X_pixels = np.column_stack((
        ndvi_m.flatten(), ndmi_m.flatten(), rendvi_m.flatten(),
        ndvi_a.flatten(), ndmi_a.flatten(), rendvi_a.flatten()
    ))
    X_pixels = np.nan_to_num(X_pixels, nan=0.0, posinf=1.0, neginf=-1.0)
    
    # 1. Macro-segmentation par K-Means
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    labels = kmeans.fit_predict(X_pixels)
    
    centres = kmeans.cluster_centers_
    deltas_ndvi_clusters = centres[:, 3] - centres[:, 0] 
    idx_cluster_agricole = np.argmax(deltas_ndvi_clusters)
    masque_1d_kmeans = (labels == idx_cluster_agricole)
    
    carte_binaire_1d = np.zeros(X_pixels.shape[0], dtype=np.uint8)
    
    # 2. Prédiction par Random Forest sur les candidats
    if np.any(masque_1d_kmeans):
        pixels_candidats = X_pixels[masque_1d_kmeans]
        probabilites = model.predict_proba(pixels_candidats)[:, 1]
        predictions_ajustees = (probabilites >= seuil_ia).astype(np.uint8)
        carte_binaire_1d[masque_1d_kmeans] = predictions_ajustees * 255
        
    carte_binaire_2d = carte_binaire_1d.reshape((hauteur, largeur))
    
    # 3. Filtrage morphologique spatial
    noyau = cv2.getStructuringElement(cv2.MORPH_CROSS, (3,3))
    masque_filtre = cv2.morphologyEx(carte_binaire_2d, cv2.MORPH_OPEN, noyau)
    masque_filtre = cv2.morphologyEx(masque_filtre, cv2.MORPH_CLOSE, noyau)
    contours, _ = cv2.findContours(masque_filtre, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    resolution_pixel = 10 
    surface_totale_ha = 0
    registre_parcelles = []
    contours_valides = []

    # 4. Extraction et validation vectorielle
    for c in contours:
        surface_px = cv2.contourArea(c)
        perimetre_px = cv2.arcLength(c, True)
        surface_ha = (surface_px * resolution_pixel * resolution_pixel) / 10000
        
        if surface_px < 6 or perimetre_px == 0:
            continue
            
        circularite = (4 * np.pi * surface_px) / (perimetre_px ** 2)
        hull = cv2.convexHull(c)
        surface_hull = cv2.contourArea(hull)
        solidite = float(surface_px) / surface_hull if surface_hull > 0 else 0

        masque_parcelle = np.zeros((hauteur, largeur), dtype=np.uint8)
        cv2.drawContours(masque_parcelle, [c], -1, 255, -1)
        px_valides = (masque_parcelle == 255)
        
        moyen_ndvi_mai = np.mean(ndvi_m[px_valides])
        moyen_ndvi_aout = np.mean(ndvi_a[px_valides])
        moyen_ndmi_aout = np.mean(ndmi_a[px_valides])
        moyen_rendvi_aout = np.mean(rendvi_a[px_valides])
        delta_ndvi_reel = moyen_ndvi_aout - moyen_ndvi_mai

        verrou_phenologique = (delta_ndvi_reel >= 0.28) and (moyen_ndmi_aout >= 0.18) and (moyen_ndvi_mai <= 0.38) and (moyen_rendvi_aout >= 0.48)

        if config_geom["filtrer"]:
            validation = (config_geom["surf_min"] <= surface_ha <= config_geom["surf_max"]) and (circularite >= 0.12) and (solidite >= 0.55) and verrou_phenologique
        else:
            validation = verrou_phenologique

        if validation:
            surface_totale_ha += surface_ha
            contours_valides.append(c)
            score_ia = model.predict_proba(np.array([[moyen_ndvi_mai, 0.0, 0.0, moyen_ndvi_aout, moyen_ndmi_aout, moyen_rendvi_aout]]))[0][1]
            
            M = cv2.moments(c)
            if M["m00"] != 0 and bbox_wgs84 is not None:
                cX, cY = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                min_lon, min_lat, max_lon, max_lat = bbox_wgs84
                lon_gps = min_lon + (cX / largeur) * (max_lon - min_lon)
                lat_gps = max_lat - (cY / hauteur) * (max_lat - min_lat)
                
                registre_parcelles.append({
                    "ID Parcelle": f"ANRAC-{len(contours_valides):03d}",
                    "Latitude": round(lat_gps, 5), "Longitude": round(lon_gps, 5),
                    "Superficie (Ha)": round(surface_ha, 2), "Croissance (Delta NDVI)": round(delta_ndvi_reel, 2),
                    "Humidité (NDMI)": round(moyen_ndmi_aout, 2), "Signature Red-Edge": round(moyen_rendvi_aout, 2),
                    "Indice Confiance": f"{score_ia * 100:.1f}%"
                })

    df_resultat = pd.DataFrame(registre_parcelles)
    statistiques = {
        "surface_totale": surface_totale_ha,
        "nb_parcelles": len(contours_valides),
        "faux_positifs_elimines": len(contours) - len(contours_valides)
    }
    
    return df_resultat, contours_valides, masque_filtre, rendvi_a, ndmi_a, statistiques
