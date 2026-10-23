# Nettoyage des données et calcul des indicateurs

import numpy as np
import pandas as pd

from utils.io import ROOT

# département -> nom, région
DEPS = pd.read_csv(ROOT / "data" / "departements.csv", dtype=str)
OUTRE_MER = ["971", "972", "973", "974", "976"]

# sous-directions d'avant 2010 -> leur département
SOUS_DIRECTIONS = {
    "131": "130",  # Bouches-du-Rhône
    "132": "130",
    "591": "590",  # Nord
    "592": "590",
    "754": "750",  # Paris
    "755": "750",
    "756": "750",
    "757": "750",
    "758": "750",
    "921": "920",  # Hauts-de-Seine
    "922": "920",
}

# ruptures de série (FR, EN)
RUPTURES = {
    2000: ("RNI → RFR", "Taxable income → RFR"),
    2006: ("Réforme du barème", "Tax scale reform"),
    2018: ("CIMR", "CIMR (blank year)"),
    2019: ("Prélèvement à la source", "Withholding tax"),
}

# noms courts des tranches
NOMS_TRANCHES = {
    "0 à 10 000": "< 10 k€",
    "10 001 à 12 000": "10-12 k€",
    "12 001 à 15 000": "12-15 k€",
    "15 001 à 20 000": "15-20 k€",
    "20 001 à 30 000": "20-30 k€",
    "30 001 à 50 000": "30-50 k€",
    "50 001 à 100 000": "50-100 k€",
    "+ de 100 000": "> 100 k€",
}

# indicateurs : num / den * x (den = None si pas un ratio)
# ratio toujours calculé sur des sommes, jamais en moyenne de ratios
INDICATEURS = {
    "part_imposes": {
        "num": "nb_imposes",
        "den": "nb_foyers",
        "x": 100,
        "label": ("Part de foyers imposés", "Share of taxed households"),
        "unite": ("%", "%"),
        "aide": ("Foyers dont l'impôt net est positif / ensemble des foyers",
                 "Households with a positive net tax / all households"),
    },
    "impot_md": {
        "num": "impot_net",
        "den": None,
        "x": 1e-9,
        "label": ("Impôt net émis", "Net tax issued"),
        "unite": ("Md€", "€ bn"),
        "aide": ("Impôt sur le revenu net émis par voie de rôle", "Net income tax issued (assessed)"),
    },
    "impot_par_impose": {
        "num": "impot_net",
        "den": "nb_imposes",
        "x": 1,
        "label": ("Impôt moyen par foyer imposé", "Average tax per taxed household"),
        "unite": ("€", "€"),
        "aide": ("Montant moyen d'un dossier imposé (impôt net / foyers imposés)",
                 "Average amount of a taxed file (net tax / taxed households)"),
    },
    "revenu_moyen": {
        "num": "revenu",
        "den": "nb_foyers",
        "x": 1,
        "label": ("Revenu moyen par foyer", "Average income per household"),
        "unite": ("€", "€"),
        "aide": ("RFR (revenu net imposable avant 2000) / nombre de foyers",
                 "Reference taxable income (net taxable income before 2000) / households"),
    },
    "taux_moyen": {
        "num": "impot_net",
        "den": "revenu",
        "x": 100,
        "label": ("Taux moyen d'imposition", "Average tax rate"),
        "unite": ("% du revenu", "% of income"),
        "aide": ("Impôt net / revenu", "Net tax / income"),
    },
    "foyers_m": {
        "num": "nb_foyers",
        "den": None,
        "x": 1e-6,
        "label": ("Nombre de foyers fiscaux", "Number of tax households"),
        "unite": ("millions", "millions"),
        "aide": ("Nombre de déclarations de revenus", "Number of income tax returns"),
    },
}

COLS_NUM = ["nb_foyers", "revenu", "impot_net", "nb_imposes", "revenu_imposes", "nb_salaires",
            "mt_salaires", "nb_pensions", "mt_pensions", "impot_net_apres_cimr"]

# colonnes additionnables
COLS_A_SOMMER = ["nb_foyers", "revenu", "impot_net", "nb_imposes", "revenu_imposes"]


def code_insee(code):
    """Code DGFiP -> INSEE ('010' -> '01', '2A0' -> '2A')."""
    code = str(code).strip().upper()
    if code in OUTRE_MER or code == "B31":
        return code
    if len(code) == 3 and code.endswith("0"):
        return code[:2]
    return code


def calculer_indicateurs(df):
    """Une colonne par indicateur."""
    for cle in INDICATEURS:
        indicateur = INDICATEURS[cle]
        numerateur = df[indicateur["num"]]

        if indicateur["den"] is None:
            df[cle] = numerateur * indicateur["x"]
        else:
            # 0 -> NaN (pas de division par zéro)
            denominateur = df[indicateur["den"]].replace(0, np.nan)
            df[cle] = numerateur / denominateur * indicateur["x"]
    return df


def agreger(df, par):
    """Somme par groupe puis indicateurs."""
    colonnes = []
    for colonne in COLS_A_SOMMER:
        if colonne in df.columns:
            colonnes.append(colonne)

    groupes = df.groupby(par, as_index=False, observed=True)
    resultat = groupes[colonnes].sum(min_count=1)
    return calculer_indicateurs(resultat)


def ajouter_noms(df):
    """Ajoute nom, région et périmètre."""
    noms = DEPS.rename(columns={"code": "dep", "nom": "dep_name"})
    df = df.merge(noms, on="dep", how="left")

    df["perimetre"] = "Métropole"
    df.loc[df["dep"].isin(OUTRE_MER), "perimetre"] = "Outre-mer"
    df.loc[df["dep"] == "B31", "perimetre"] = "Non-résidents"
    return df


def nettoyer_serie(brut):
    """Série 1984-2020 : nombres, sous-directions regroupées, doublon Paris 2009 enlevé."""
    df = brut.copy()
    df["dep_code"] = df["dep_code"].astype(str).str.strip().str.upper()
    for colonne in COLS_NUM:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    # département parent de chaque ligne
    df["parent"] = df["dep_code"].replace(SOUS_DIRECTIONS)
    df["est_sous_dir"] = df["dep_code"].isin(list(SOUS_DIRECTIONS.keys()))

    # couples (année, département) présents en ligne normale
    lignes_departement = set()
    for index, ligne in df.iterrows():
        if not ligne["est_sous_dir"]:
            lignes_departement.add((ligne["year"], ligne["dep_code"]))

    # sous-direction en double si son département existe la même année
    en_double = []
    for index, ligne in df.iterrows():
        if ligne["est_sous_dir"] and (ligne["year"], ligne["parent"]) in lignes_departement:
            en_double.append(True)
        else:
            en_double.append(False)
    df["doublon"] = en_double

    lignes_doublons = df[df["doublon"]]
    doublons = lignes_doublons.groupby(["year", "parent"]).agg(lignes=("dep_code", "count"),
                                                                foyers=("nb_foyers", "sum"))
    doublons = doublons.reset_index()

    infos = {
        "doublons": doublons,
        "nb_doublons": int(df["doublon"].sum()),
        "nb_sous_dir": int((df["est_sous_dir"] & ~df["doublon"]).sum()),
    }

    # sans doublons, sous-directions regroupées
    df = df[~df["doublon"]].copy()
    df["dep"] = df["parent"].map(code_insee)
    df = df.groupby(["year", "dep", "revenu_concept"], as_index=False)[COLS_NUM].sum(min_count=1)
    return df, infos


def nettoyer_tranches(brut):
    """Tranches 2018-2024 : n.c. -> vide, k€ -> €."""
    df = brut.copy()
    cols_keur = ["rfr_keur", "impot_net_keur", "rfr_imposes_keur", "mt_salaires_keur", "mt_pensions_keur"]
    cols_nb = ["nb_foyers", "nb_imposes", "nb_salaires", "nb_pensions"]

    # comptage des "n.c." (secret statistique)
    nc_total = 0
    nc_par_colonne = {}
    for colonne in cols_keur + cols_nb:
        texte = df[colonne].astype(str).str.strip().str.lower()
        nombre_nc = int((texte == "n.c.").sum())
        nc_total = nc_total + nombre_nc
        if nombre_nc > 0:
            nc_par_colonne[colonne] = nombre_nc
    infos = {"nc_total": nc_total, "nc_par_colonne": nc_par_colonne}

    for colonne in cols_keur + cols_nb:
        df[colonne] = pd.to_numeric(df[colonne], errors="coerce")

    # k€ -> €
    df["revenu"] = df["rfr_keur"] * 1000
    df["impot_net"] = df["impot_net_keur"] * 1000
    df["revenu_imposes"] = df["rfr_imposes_keur"] * 1000
    df["mt_salaires"] = df["mt_salaires_keur"] * 1000
    df["mt_pensions"] = df["mt_pensions_keur"] * 1000

    df["dep"] = df["dep_code"].astype(str).str.strip().str.upper().map(code_insee)
    df["tranche_rfr"] = df["tranche_rfr"].astype(str).str.strip()

    garder = ["year", "dep", "tranche_rfr", "nb_foyers", "revenu", "impot_net", "nb_imposes", "revenu_imposes",
              "nb_salaires", "mt_salaires", "nb_pensions", "mt_pensions"]
    return df[garder], infos


def controles_qualite(serie_brute, tranches_brutes, panel, tranches, infos_serie, infos_tr):
    """Tableau des contrôles qualité (FR et EN)."""
    lignes = []

    def ajout(nom_fr, nom_en, ok, detail_fr, detail_en):
        lignes.append({
            "nom_fr": nom_fr,
            "nom_en": nom_en,
            "ok": bool(ok),
            "detail_fr": detail_fr,
            "detail_en": detail_en,
        })

    # 1. doublons
    d1 = serie_brute.duplicated(["year", "dep_code"]).sum()
    d2 = tranches_brutes.duplicated(["year", "dep_code", "tranche_rfr"]).sum()
    ajout("Doublons", "Duplicates", d1 + d2 == 0,
          f"{d1} dans la série 1984-2020, {d2} dans les tranches 2018-2024",
          f"{d1} in the 1984-2020 series, {d2} in the 2018-2024 brackets")

    # 2. double comptage (Paris 2009)
    if infos_serie["doublons"].empty:
        ajout("Double comptage département / sous-directions", "Double counting department / sub-directions",
              True, "aucun", "none")
    else:
        r = infos_serie["doublons"].iloc[0]
        foyers = f"{int(r.foyers):,}"
        foyers_fr = foyers.replace(",", " ")
        ajout("Double comptage département / sous-directions", "Double counting department / sub-directions",
              False,
              f"{int(r.year)} (code {r.parent} : {int(r.lignes)} lignes, {foyers_fr} foyers) "
              "-> lignes en double supprimées",
              f"{int(r.year)} (code {r.parent}: {int(r.lignes)} rows, {foyers} households) -> duplicate rows removed")

    # 3. sous-directions
    n = infos_serie["nb_sous_dir"]
    ajout("Sous-directions regroupées", "Sub-directions merged", True,
          f"{n} lignes regroupées dans leur département", f"{n} rows merged into their department")

    # 4. secret statistique
    n = infos_tr["nc_total"]
    ajout("Secret statistique (n.c.)", "Statistical secrecy (n.c.)", n == 0,
          f"{n} cellules masquées, laissées vides (pas d'imputation)", f"{n} hidden cells, left empty (no imputation)")

    # 5. foyers imposés <= foyers
    n = int((panel["nb_imposes"] > panel["nb_foyers"]).sum())
    ajout("Foyers imposés <= foyers", "Taxed households <= households", n == 0,
          f"{n} ligne(s) incohérente(s)", f"{n} inconsistent row(s)")

    # 6. somme des tranches = Total
    lignes_total = tranches[tranches["tranche_rfr"] == "Total"].set_index(["year", "dep"])
    lignes_tranches = tranches[tranches["tranche_rfr"] != "Total"]
    somme = lignes_tranches.groupby(["year", "dep"])[["nb_foyers", "impot_net"]].sum()
    ecart = (somme["nb_foyers"] - lignes_total["nb_foyers"]).abs() / lignes_total["nb_foyers"]
    ecart_max = ecart.max()
    ajout("Somme des tranches = ligne Total", "Sum of brackets = Total row", ecart_max < 0.005,
          f"écart maximum : {ecart_max:.3%}", f"maximum gap: {ecart_max:.3%}")

    # 7. territoires par année
    nb_territoires = panel.groupby("year")["dep"].nunique()
    ajout("Couverture", "Coverage", True,
          f"entre {nb_territoires.min()} et {nb_territoires.max()} territoires selon l'année "
          "(non-résidents publiés à partir de 2006, Mayotte à partir de 2013)",
          f"between {nb_territoires.min()} and {nb_territoires.max()} territories depending on the year "
          "(non-residents published from 2006, Mayotte from 2013)")

    # 8. non-résidents (B31) absents des tranches
    annees_tranches = set(tranches["year"])
    annees_avec_b31 = set(tranches.loc[tranches["dep"] == "B31", "year"])
    annees_sans_b31 = sorted(annees_tranches - annees_avec_b31)
    if len(annees_sans_b31) > 0:
        textes = []
        for annee in annees_sans_b31:
            textes.append(str(annee))
        annees = ", ".join(textes)
        ajout("Non-résidents dans les tranches", "Non-residents in the brackets", False,
              f"absents des fichiers par tranche de {annees} (présents dans la série longue)",
              f"missing from the bracket files of {annees} (present in the long series)")

    # 9. ruptures : revenu métropole +/- 15 % sur un an
    metropole = panel[panel["perimetre"] == "Métropole"]
    evolution = metropole.groupby("year")["revenu"].sum().pct_change()
    sauts = evolution[evolution.abs() > 0.15]
    textes = []
    for annee, variation in sauts.items():
        textes.append(f"{annee} ({variation:+.0%})")
    liste = ", ".join(textes)
    if liste == "":
        ajout("Ruptures de série (revenu national +/- 15 %)", "Series breaks (national income +/- 15%)", True,
              "aucune", "none")
    else:
        ajout("Ruptures de série (revenu national +/- 15 %)", "Series breaks (national income +/- 15%)", False,
              liste, liste)

    return pd.DataFrame(lignes)


def make_tables(serie_brute, tranches_brutes):
    """Toutes les tables de l'app."""
    serie, infos_serie = nettoyer_serie(serie_brute)
    tranches, infos_tr = nettoyer_tranches(tranches_brutes)

    # panel = série longue + lignes Total des tranches après 2020
    est_total = tranches["tranche_rfr"] == "Total"
    annee_absente = ~tranches["year"].isin(serie["year"])
    recent = tranches[est_total & annee_absente].drop(columns="tranche_rfr")
    recent["revenu_concept"] = "RFR"
    recent["impot_net_apres_cimr"] = np.nan

    panel = pd.concat([serie, recent[serie.columns]], ignore_index=True)
    panel = ajouter_noms(panel)
    panel = calculer_indicateurs(panel)
    panel = panel.sort_values(["year", "dep"]).reset_index(drop=True)

    # détail par tranche, noms courts dans l'ordre
    detail = tranches[tranches["tranche_rfr"] != "Total"].copy()
    ordre_tranches = list(NOMS_TRANCHES.values())
    detail["tranche"] = pd.Categorical(detail["tranche_rfr"].map(NOMS_TRANCHES),
                                       categories=ordre_tranches, ordered=True)
    detail = ajouter_noms(detail)

    controles = controles_qualite(serie_brute, tranches_brutes, panel, tranches, infos_serie, infos_tr)

    return {
        "panel": panel,
        "tranches": detail,
        "controles": controles,
        "infos_serie": infos_serie,
        "infos_tranches": infos_tr,
    }
