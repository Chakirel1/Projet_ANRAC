

Pour des raisons de sécurité imposées par Git, le fichier contenant les
clés privées d'accès aux services de télédétection satellite n'est pas
directement injecté dans le code source public.

Pour exécuter ce tableau de bord ANRAC en mode complet , veuillez suivre
ces deux étapes simples avant de lancer Streamlit :

Étape 1 : Créer le dossier des secrets
--------------------------------------
À la racine de votre projet (au même niveau que le fichier app.py),
créez un dossier masqué nommé :
.streamlit

Étape 2 : Créer le fichier des clés
------------------------------------
Dans ce dossier .streamlit, créez un fichier nommé :
secrets.toml

Ouvrez ce fichier et collez-y les identifiants officiels suivants :
###############################
[sentinelhub]

client_id = "ad97abc1-a7ef-4180-85fe-170060c9af55"

client_secret = "92uIYt4TtoCUcbQXjjMe3avcPXDzAmXo"

################################


Une fois ce fichier enregistré, vous pouvez relancer l'application :
> streamlit run app.py

Le système détectera automatiquement le fichier, désactivera le mode
restreint et initialisera les modules de surveillance par satellite.

