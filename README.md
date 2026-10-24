# Qui paie l'impôt sur le revenu, et où ?

Projet individuel Streamlit - #EFREIDataStories2026

- Étudiant : Mickael LY (mickael.ly@efrei.net) - Data Engineering (DE2), 2026-2027
- Cours : Data Analysis & Visualization - Prof. Mano Joseph Mathew

## Le sujet

Je vais faire un stage à la DGFiP dans un service de recouvrement de l'impôt. J'ai donc choisi un jeu de
données sur l'impôt sur le revenu pour comprendre qui le paie et où, et ce que ça implique pour un service
qui doit récupérer l'argent.

Questions :
1. Comment ont évolué l'impôt et le nombre de foyers imposés depuis 1984 ?
2. Quels départements paient le plus, et où y a-t-il le moins de foyers imposés ?
3. Quelle part de l'impôt repose sur les hauts revenus ?
4. Pour un service de recouvrement, combien de dossiers faut-il traiter pour récupérer l'essentiel ? (simulation)

Principaux résultats (2024) : 3,4 % des foyers (revenu fiscal de référence > 100 000 €) paient 53 % de l'impôt,
47 % des foyers sont imposés, et 13 départements sur 102 paient la moitié de l'impôt.

## Données

- Jeu de données : **L'impôt sur le revenu par collectivité territoriale (IRCOM)** - DGFiP
- Lien : https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom/
- Licence : Licence Ouverte 2.0 (Etalab)
- Fichiers utilisés (même jeu de données, années différentes) :
  - `impotrevenudep-1984-2020.xlsx` : une ligne par département et par année (1984-2020)
  - `ircom-2019-revenus-2018.zip` à `ircom-2025-revenus-2024.zip` (7 fichiers) : détail par tranche de revenu (2018-2024)
- Fond de carte : contours des départements de [france-geojson](https://github.com/gregoiredavid/france-geojson)
  (`assets/departements.geojson`)

La DGFiP publie ces données en Excel et en zips de fichiers `.xls` (pas en CSV). Le script `download_data.py`
télécharge les fichiers d'origine dans `data/raw/` puis recopie les tableaux, sans les modifier, dans deux CSV
(`data/extracted/`). Les deux CSV sont fournis avec le projet (environ 1 Mo) ; les fichiers bruts (environ 125 Mo)
ne le sont pas. Les liens exacts sont dans `data/SOURCE.txt`. Le nettoyage est fait ensuite dans `utils/prep.py`.

## Lancer le projet

Python 3.11 ou plus récent.

```
python -m venv .venv
.venv\Scripts\activate          (Mac/Linux : source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```

Pour tout reconstruire depuis data.gouv.fr : `python download_data.py --force` (2-3 minutes).
Si les CSV n'existent pas, l'application lance le téléchargement toute seule au premier démarrage.

## Langue

L'application est disponible en français et en anglais : le choix se fait en haut de la barre latérale.
Tous les textes sont écrits dans les deux langues avec la fonction `t("texte français", "english text")`
(dans `utils/lang.py`).

## Organisation du code

J'ai suivi la structure proposée dans la consigne :

```
app.py                 page principale : choix de la langue, filtres, KPI, onglets
sections/
  intro.py             contexte, objectifs, présentation des données et précautions
  overview.py          tendances depuis 1984
  deep_dives.py        comparaison des départements, tranches de revenu, simulation
  conclusions.py       qualité des données, limites, enseignements
utils/
  io.py                téléchargement et lecture des fichiers IRCOM
  prep.py              nettoyage, indicateurs, contrôles qualité
  viz.py               fonctions de graphiques (Plotly)
  lang.py              petite fonction t() pour afficher l'app en français ou en anglais
data/
  departements.csv     correspondance code département -> nom -> région
  SOURCE.txt           liens des fichiers
  extracted/           les 2 CSV créés par download_data.py
  raw/                 fichiers bruts téléchargés (pas fournis)
assets/
  departements.geojson contours pour la carte
  efrei_logo.png       logo de l'école
download_data.py       script de téléchargement
```

Le chargement et le nettoyage sont mis en cache avec `st.cache_data`. Il n'y a pas d'échantillonnage aléatoire
dans le projet, donc pas besoin de graine (seed) : les résultats sont toujours les mêmes.

## Nettoyage des données

Problèmes trouvés dans les fichiers et ce que j'ai fait :

- **Paris compté deux fois en 2009** : le fichier contient la ligne « Paris » et aussi ses 5 sous-directions
  (1 444 130 foyers en double). J'ai supprimé les sous-directions pour cette année.
- **Sous-directions avant 2010** (Paris-Centre, Nord-Lille, Bouches-du-Rhône-Aix...) : 150 lignes regroupées
  dans leur département.
- **Secret statistique** : 56 cellules « n.c. », laissées vides.
- **Unités différentes** : milliers d'euros dans les fichiers par tranche, convertis en euros.
- **3 formats de fichiers par tranche** : dossier `dep/` (2018), zip dans le zip (2019-2021), dossier
  `departemental/` (2022-2024). En 2018 il y a 2 colonnes en plus pour le CIMR (j'utilise l'impôt avant CIMR).
  Les non-résidents sont absents des fichiers par tranche de 2018 et 2019.
- **Codes** : codes DGFiP (`010`, `2A0`, `750`) convertis en codes département (`01`, `2A`, `75`).
- **Ruptures de série** : 2000 (RNI remplacé par le RFR), 2006 (réforme du barème, +30 % de revenu),
  2018 (CIMR, j'utilise l'impôt avant CIMR), 2019 (prélèvement à la source). Elles sont indiquées sur les courbes.

Les contrôles sont affichés dans l'onglet Conclusions (doublons, cohérence, somme des tranches = total, etc.).

## Limites

- Les données donnent l'impôt **émis**, pas l'impôt **encaissé** : la simulation de recouvrement utilise des
  taux d'impayé que j'ai choisis moi-même (hypothèses, pas des chiffres officiels).
- Montants en euros courants, tranches de revenu non corrigées de l'inflation.
- Niveau département uniquement.
- Une corrélation n'est pas une causalité.
- Données agrégées par la DGFiP avec secret statistique : pas de données personnelles.

## Accessibilité

Couleurs lisibles par les daltoniens, axes et unités indiqués, infobulles au survol, et une description en
texte sous chaque graphique.

## Livrables

- Application en ligne (Streamlit Community Cloud) : https://ircom-impot-revenu-app.streamlit.app
- Code (GitHub) : https://github.com/zanzibarrr/ircom-impot-revenu-streamlit
- Vidéo de démonstration : `demo_IRCOM_Mickael_LY.mp4`
- Rapport (en anglais) : `report.pdf`
- Storyboard : `storyboard.md`
