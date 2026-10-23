# Téléchargement et lecture des fichiers IRCOM (data.gouv.fr)
# - Excel 1984-2020 : une ligne par département et par année (euros)
# - zips 2018-2024 : détail par tranche de revenu (milliers d'euros)
# Résultat : 2 CSV bruts dans data/extracted (nettoyage dans prep.py)

import io
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
EXTRACTED_DIR = ROOT / "data" / "extracted"
LONG_CSV = EXTRACTED_DIR / "ircom_departements_1984_2020.csv"
TRANCHES_CSV = EXTRACTED_DIR / "ircom_departements_tranches_2018_2024.csv"

DATASET_URL = "https://www.data.gouv.fr/datasets/limpot-sur-le-revenu-par-collectivite-territoriale-ircom/"
LICENCE = "DGFiP, IRCOM (data.gouv.fr) - Licence Ouverte 2.0"

BASE = "https://static.data.gouv.fr/resources/limpot-sur-le-revenu-par-collectivite-territoriale-ircom/"
BASE_ANCIENNE = "https://static.data.gouv.fr/resources/l-impot-sur-le-revenu-par-collectivite-territoriale/"

# série longue (Excel)
URL_SERIE_LONGUE = BASE + "20230228-115014/impotrevenudep-1984-2020.xlsx"

# un zip par année de revenus
URLS_TRANCHES = {
    2018: BASE_ANCIENNE + "20211227-171921/ircom-2019-revenus-2018.zip",
    2019: BASE_ANCIENNE + "20211227-172005/ircom-2020-revenus-2019.zip",
    2020: BASE + "20220621-110528/ircom-2021-revenus-2020.zip",
    2021: BASE + "20230608-145433/ircom-2022-revenus-2021.zip",
    2022: BASE + "20240610-082154/ircom-2023-revenus-2022.zip",
    2023: BASE + "20250919-135242/ircom-2024-revenus-2023.zip",
    2024: BASE + "20260526-131537/ircom-2025-revenus-2024.zip",
}

TRANCHES = ["0 à 10 000", "10 001 à 12 000", "12 001 à 15 000", "15 001 à 20 000", "20 001 à 30 000",
            "30 001 à 50 000", "50 001 à 100 000", "+ de 100 000", "Total"]

COLS_LONG = ["year", "dep_code", "dep_label", "nb_foyers", "revenu", "revenu_concept", "impot_net",
             "nb_imposes", "revenu_imposes", "nb_salaires", "mt_salaires", "nb_pensions", "mt_pensions",
             "impot_net_apres_cimr"]

COLS_TRANCHES = ["year", "dep_code", "dep_label", "tranche_rfr", "nb_foyers", "rfr_keur", "impot_net_keur",
                 "nb_imposes", "rfr_imposes_keur", "nb_salaires", "mt_salaires_keur", "nb_pensions",
                 "mt_pensions_keur"]


def telecharger(url, force=False):
    """Télécharge dans data/raw (sauf si déjà présent)."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    nom_fichier = url.split("/")[-1]
    chemin = RAW_DIR / nom_fichier

    if chemin.exists() and not force:
        return chemin

    print("  téléchargement de", nom_fichier)
    reponse = requests.get(url, timeout=180)
    reponse.raise_for_status()
    chemin.write_bytes(reponse.content)
    return chemin


def nettoyer_cellule(valeur):
    """Cellule vide -> None, texte sans espaces autour."""
    if valeur is None:
        return None
    if isinstance(valeur, float) and pd.isna(valeur):
        return None
    if isinstance(valeur, str):
        valeur = valeur.strip()
        if valeur == "":
            return None
    return valeur


def nettoyer_ligne(ligne):
    """nettoyer_cellule sur toute la ligne."""
    resultat = []
    for valeur in ligne:
        resultat.append(nettoyer_cellule(valeur))
    return resultat


def enlever_colonnes_vides(df):
    """Enlève les colonnes vides du début (feuilles qui commencent en colonne B)."""
    while df.shape[1] > 0 and df.iloc[:, 0].isna().all():
        df = df.iloc[:, 1:]
    df.columns = range(df.shape[1])
    return df


def valeur_ou_vide(ligne, position):
    """Cellule à cette position, ou None si la ligne est trop courte."""
    if len(ligne) > position:
        return ligne[position]
    return None


def lire_annee(valeur):
    """Année en entier, ou None."""
    try:
        annee = int(float(valeur))
    except (TypeError, ValueError):
        return None
    if annee < 1980 or annee > 2100:
        return None
    return annee


def lire_serie_longue(fichier):
    """Lit toutes les feuilles de données du fichier Excel."""
    feuilles = pd.read_excel(fichier, sheet_name=None, header=None, dtype=object)
    lignes = []

    for nom_feuille in feuilles:
        if nom_feuille.lower().startswith("notice"):
            continue

        df = enlever_colonnes_vides(feuilles[nom_feuille])

        for ligne_brute in df.itertuples(index=False):
            r = nettoyer_ligne(ligne_brute)
            if len(r) < 9 or r[0] is None:
                continue

            # ligne de données = année en 3e colonne
            annee = lire_annee(r[2])
            if annee is None:
                continue

            ligne = {}
            for colonne in COLS_LONG:
                ligne[colonne] = None
            ligne["year"] = annee
            ligne["dep_code"] = str(r[0]).upper()
            ligne["dep_label"] = r[1]
            ligne["nb_foyers"] = r[3]
            ligne["revenu"] = r[4]
            ligne["impot_net"] = r[5]

            if nom_feuille == "1984_1999":
                # avant 2000 : revenu net imposable (RNI) au lieu du RFR
                ligne["revenu_concept"] = "RNI"
                ligne["nb_imposes"] = r[6]
                ligne["revenu_imposes"] = r[7]
            elif nom_feuille == "2018":
                # 2018 : 2 colonnes CIMR en plus, on garde l'impôt avant CIMR
                ligne["revenu_concept"] = "RFR"
                ligne["impot_net_apres_cimr"] = r[6]
                ligne["nb_imposes"] = r[8]
                ligne["revenu_imposes"] = r[9]
                ligne["nb_salaires"] = r[10]
                ligne["mt_salaires"] = r[11]
                ligne["nb_pensions"] = r[12]
                ligne["mt_pensions"] = valeur_ou_vide(r, 13)
            else:
                ligne["revenu_concept"] = "RFR"
                ligne["nb_imposes"] = r[6]
                ligne["revenu_imposes"] = r[7]
                ligne["nb_salaires"] = r[8]
                ligne["mt_salaires"] = r[9]
                ligne["nb_pensions"] = r[10]
                ligne["mt_pensions"] = valeur_ou_vide(r, 11)

            lignes.append(ligne)

    serie = pd.DataFrame(lignes, columns=COLS_LONG)
    serie = serie.sort_values(["year", "dep_code"])
    serie = serie.reset_index(drop=True)
    return serie


def fichiers_departementaux(z, dans_zip_dep=False):
    """Liste des fichiers départementaux (nom, contenu) d'un zip IRCOM.
    Rangement : dep/ (2018), zip dans le zip (2019-2021), departemental/ (2022-2024)."""
    resultat = []
    for nom in z.namelist():
        nom_minuscule = nom.lower()

        if nom_minuscule.endswith(".zip") and "departement" in nom_minuscule:
            # zip dans le zip
            contenu_zip = io.BytesIO(z.read(nom))
            with zipfile.ZipFile(contenu_zip) as z2:
                resultat = resultat + fichiers_departementaux(z2, dans_zip_dep=True)

        elif nom_minuscule.endswith(".xls") or nom_minuscule.endswith(".xlsx"):
            if dans_zip_dep or "departemental/" in nom_minuscule or nom_minuscule.startswith("dep/"):
                resultat.append((nom, z.read(nom)))

    return resultat


def est_ligne_entete(ligne):
    """En-tête = "Dép." (ou "Depdir" pour les non-résidents)."""
    if len(ligne) == 0:
        return False
    if not isinstance(ligne[0], str):
        return False
    debut = ligne[0].lower().replace("é", "e")
    return debut.startswith("dep")


def lire_fichier_departement(contenu, annee, nom=""):
    """Garde les 9 lignes du département (8 tranches + Total), pas celles des communes."""
    df = pd.read_excel(io.BytesIO(contenu), header=None, dtype=object)
    df = enlever_colonnes_vides(df)

    lignes = []
    for ligne_brute in df.itertuples(index=False):
        lignes.append(nettoyer_ligne(ligne_brute))

    # ligne d'en-tête
    entete = None
    for ligne in lignes:
        if est_ligne_entete(ligne):
            entete = ligne
            break
    if entete is None:
        raise ValueError("en-tête introuvable dans " + nom)

    # 2018 : 2 colonnes CIMR en plus
    annee_cimr = False
    for cellule in entete:
        if isinstance(cellule, str) and "CIMR" in cellule:
            annee_cimr = True

    resultat = []
    for r in lignes:
        if len(r) < 13 or r[3] is None:
            continue
        tranche = str(r[3]).strip()
        if tranche not in TRANCHES:
            continue

        # ligne de commune -> ignorée
        if r[1] is not None and str(r[1]).strip() not in ("", "000"):
            continue

        if annee_cimr:
            # impôt avant CIMR, on saute les 2 colonnes CIMR
            valeurs = [r[4], r[5], r[6], r[9], r[10], r[11], r[12], r[13], valeur_ou_vide(r, 14)]
        else:
            valeurs = r[4:13]

        ligne = {
            "year": annee,
            "dep_code": str(r[0]).upper(),
            "dep_label": r[2],
            "tranche_rfr": tranche,
            "nb_foyers": valeurs[0],
            "rfr_keur": valeurs[1],
            "impot_net_keur": valeurs[2],
            "nb_imposes": valeurs[3],
            "rfr_imposes_keur": valeurs[4],
            "nb_salaires": valeurs[5],
            "mt_salaires_keur": valeurs[6],
            "nb_pensions": valeurs[7],
            "mt_pensions_keur": valeurs[8],
        }
        resultat.append(ligne)

    return resultat


def lire_zip_annee(fichier, annee):
    """Lit tous les départements du zip d'une année."""
    lignes = []
    with zipfile.ZipFile(fichier) as z:
        for nom, contenu in fichiers_departementaux(z):
            lignes = lignes + lire_fichier_departement(contenu, annee, nom)

    if len(lignes) == 0:
        raise ValueError(f"aucun fichier départemental trouvé pour {annee}")
    return pd.DataFrame(lignes, columns=COLS_TRANCHES)


def construire_csv(force=False):
    """Télécharge tout et écrit les 2 CSV."""
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)

    fichier_excel = telecharger(URL_SERIE_LONGUE, force)
    serie = lire_serie_longue(fichier_excel)
    serie.to_csv(LONG_CSV, index=False)
    print(f"  {len(serie)} lignes -> {LONG_CSV.name}")

    tableaux = []
    for annee in URLS_TRANCHES:
        fichier_zip = telecharger(URLS_TRANCHES[annee], force)
        tableaux.append(lire_zip_annee(fichier_zip, annee))
    tranches = pd.concat(tableaux)
    tranches.to_csv(TRANCHES_CSV, index=False)
    print(f"  {len(tranches)} lignes -> {TRANCHES_CSV.name}")


def load_data():
    """Charge les 2 CSV (les crée s'ils manquent)."""
    if not LONG_CSV.exists() or not TRANCHES_CSV.exists():
        construire_csv()

    serie = pd.read_csv(LONG_CSV, dtype={"dep_code": str})
    tranches = pd.read_csv(TRANCHES_CSV, dtype={"dep_code": str})
    return serie, tranches
