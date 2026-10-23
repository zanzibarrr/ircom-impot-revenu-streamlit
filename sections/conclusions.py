# Conclusions : qualité des données, limites, enseignements

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.lang import anglais, t
from utils.prep import COLS_NUM, agreger
from utils.viz import BLEU, ORANGE, fr, mise_en_forme


def render(tables, filtres):
    qualite(tables)
    st.divider()
    enseignements(tables)


def qualite(tables):
    st.header(t("Qualité des données et limites", "Data quality and limitations"))
    st.markdown(t("Avant de faire les graphiques, j'ai vérifié les données. Voici les contrôles faits "
                  "automatiquement à chaque chargement :",
                  "Before making the charts, I checked the data. Here are the checks run automatically "
                  "every time the data is loaded:"))
    controles = tables["controles"]
    if anglais():
        resultats = controles["ok"].map({True: "OK", False: "Problem fixed / flagged"})
        tableau = pd.DataFrame({"Check": controles["nom_en"], "Result": resultats, "Detail": controles["detail_en"]})
        tableau = tableau.set_index("Check")
    else:
        resultats = controles["ok"].map({True: "OK", False: "Problème corrigé / signalé"})
        tableau = pd.DataFrame({"Contrôle": controles["nom_fr"], "Résultat": resultats,
                                "Détail": controles["detail_fr"]})
        tableau = tableau.set_index("Contrôle")
    st.table(tableau)

    # avant / après nettoyage
    brut = tables["serie_brute"].copy()
    brut["nb_foyers"] = pd.to_numeric(brut["nb_foyers"], errors="coerce")
    avant_serie = brut.groupby("year")["nb_foyers"].sum()

    tranches_brutes = tables["tranches_brutes"]
    est_total = tranches_brutes["tranche_rfr"] == "Total"
    annee_absente = ~tranches_brutes["year"].isin(brut["year"])
    totaux = tranches_brutes[est_total & annee_absente].copy()
    totaux["nb_foyers"] = pd.to_numeric(totaux["nb_foyers"], errors="coerce")
    avant_tranches = totaux.groupby("year")["nb_foyers"].sum()

    avant = pd.concat([avant_serie, avant_tranches])
    apres = tables["panel"].groupby("year")["nb_foyers"].sum()

    st.subheader(t("Exemple de correction : Paris compté deux fois en 2009",
                   "Example of a correction: Paris counted twice in 2009"))
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=avant.index, y=avant.values / 1e6, name=t("Avant nettoyage", "Before cleaning"),
                             line=dict(color=ORANGE, dash="dot")))
    fig.add_trace(go.Scatter(x=apres.index, y=apres.values / 1e6, name=t("Après nettoyage", "After cleaning"),
                             line=dict(color=BLEU)))
    fig.update_layout(xaxis_title=t("Année de revenus", "Income year"),
                      yaxis_title=t("Foyers fiscaux (millions)", "Tax households (millions)"))
    st.plotly_chart(mise_en_forme(fig, 350), width="stretch")
    st.caption(t("Description : nombre total de foyers avant et après nettoyage. En 2009, le fichier contient la ligne "
                 "« Paris » et aussi les 5 sous-directions de Paris, donc Paris était compté deux fois.",
                 "Description: total number of households before and after cleaning. In 2009, the file contains the "
                 "\"Paris\" row and also the 5 Paris sub-directions, so Paris was counted twice."))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(t("**Valeurs manquantes (série 1984-2020)**", "**Missing values (1984-2020 series)**"))
        pourcentages = {}
        for colonne in COLS_NUM:
            valeurs = pd.to_numeric(brut[colonne], errors="coerce")
            pourcentages[colonne] = round(valeurs.isna().mean() * 100, 1)
        manquants = pd.Series(pourcentages, name=t("% manquant", "% missing"))
        st.dataframe(manquants, width="stretch")
        st.caption(t("Salaires et pensions ne sont publiés qu'à partir de 2000, et l'impôt après CIMR "
                     "seulement en 2018 : ces manques sont normaux.",
                     "Salaries and pensions are only published from 2000, and the tax after CIMR only in 2018: "
                     "these gaps are expected."))
    with col2:
        st.markdown(t("**Ce que j'ai fait pour nettoyer**", "**What I did to clean the data**"))
        st.markdown(t("""
1. Conversion des codes DGFiP (`010`, `2A0`, `750`) en codes département (`01`, `2A`, `75`).
2. Regroupement des sous-directions d'avant 2010 (Paris-Centre, Nord-Lille...) dans leur département.
3. Suppression des lignes en double de Paris en 2009.
4. Conversion des milliers d'euros (fichiers par tranche) en euros.
5. Les 3 formats de fichiers par tranche (2018, 2019-2021, 2022-2024) sont lus par la même fonction ;
   en 2018 j'utilise l'impôt avant CIMR (2 colonnes en plus dans le fichier).
6. Les cellules « n.c. » (secret statistique) restent vides, je ne les remplace pas.
7. Ajout du nom et de la région de chaque département.
""", """
1. Conversion of DGFiP codes (`010`, `2A0`, `750`) into department codes (`01`, `2A`, `75`).
2. Pre-2010 sub-directions (Paris-Centre, Nord-Lille...) merged into their department.
3. Removal of the duplicate Paris rows in 2009.
4. Conversion of thousands of euros (bracket files) into euros.
5. The 3 bracket file formats (2018, 2019-2021, 2022-2024) are read by the same function;
   for 2018 I use the tax before CIMR (2 extra columns in the file).
6. "n.c." cells (statistical secrecy) stay empty, I do not replace them.
7. Name and region added for each department.
"""))

    with st.expander(t("Limites et éthique", "Limitations and ethics")):
        st.markdown(t("""
- Impôt **émis** et pas **encaissé** : la simulation repose sur des hypothèses.
- Euros courants (pas corrigés de l'inflation) et tranches non indexées.
- Le champ est l'impôt sur le revenu « par voie de rôle » : les revenus du capital au prélèvement
  forfaitaire unique ne sont pas dedans.
- Niveau département seulement : on ne voit pas les différences entre communes.
- Les données sont agrégées par la DGFiP et protégées par le secret statistique : aucune donnée
  personnelle n'est utilisée.
""", """
- Tax **issued**, not **collected**: the simulation relies on assumptions.
- Current euros (not adjusted for inflation) and non-indexed brackets.
- The scope is income tax "assessed by roll": capital income under the flat tax (PFU) is not included.
- Department level only: differences between municipalities are not visible.
- The data is aggregated by the DGFiP and protected by statistical secrecy: no personal data is used.
"""))


def enseignements(tables):
    panel = tables["panel"]
    tranches = tables["tranches"]

    # France entière, 2024
    p = panel[panel["year"] == 2024]
    france = agreger(p, ["year"]).iloc[0]

    tranches_2024 = tranches[tranches["year"] == 2024]
    hauts_revenus = tranches_2024[tranches_2024["tranche"] == "> 100 k€"]
    part_haut = 100 * hauts_revenus["impot_net"].sum() / tranches_2024["impot_net"].sum()

    idf = p[p["region"] == "Île-de-France"]
    idf_impot = 100 * idf["impot_net"].sum() / p["impot_net"].sum()
    idf_foyers = 100 * idf["nb_foyers"].sum() / p["nb_foyers"].sum()

    # nb de départements pour atteindre 50 % de l'impôt
    tri = p.sort_values("impot_net", ascending=False)
    total_impot = tri["impot_net"].sum()
    cumul = 0
    n_moitie = 0
    for montant in tri["impot_net"]:
        cumul = cumul + montant
        n_moitie = n_moitie + 1
        if cumul / total_impot >= 0.5:
            break

    st.header(t("Ce que je retiens", "Key insights"))
    st.success(t(f"""
- **L'impôt est très concentré sur les hauts revenus** : en 2024, les foyers au-dessus de 100 000 € paient
  {fr(part_haut, 0)} % de l'impôt, alors que {fr(100 - france['part_imposes'], 0)} % des foyers ne sont pas imposés.
- **Il est aussi concentré géographiquement** : {n_moitie} départements sur {len(p)} paient la moitié de l'impôt,
  et l'Île-de-France représente {fr(idf_foyers, 0)} % des foyers mais {fr(idf_impot, 0)} % de l'impôt.
- **Chaque dossier pèse plus lourd** : l'impôt moyen par foyer imposé est de {fr(france['impot_par_impose'], 0)} € en 2024.
""", f"""
- **Income tax is very concentrated on high incomes**: in 2024, households above €100,000 pay
  {fr(part_haut, 0)}% of the tax, while {fr(100 - france['part_imposes'], 0)}% of households pay no income tax.
- **It is also concentrated geographically**: {n_moitie} departments out of {len(p)} pay half of the tax,
  and Île-de-France has {fr(idf_foyers, 0)}% of households but {fr(idf_impot, 0)}% of the tax.
- **Each file weighs more**: the average tax per taxed household is €{fr(france['impot_par_impose'], 0)} in 2024.
"""))
    st.markdown(t("""
**Ce que ça veut dire pour un service de recouvrement (mon avis) :**
- suivre de près les gros dossiers, qui représentent la plus grande partie de l'argent ;
- automatiser les relances pour les petits montants, qui sont très nombreux ;
- les moyens nécessaires ne sont pas les mêmes selon les départements.

**Pour aller plus loin :**
1. Trouver des données sur l'impôt réellement encaissé (taux de recouvrement) pour remplacer mes hypothèses.
2. Descendre au niveau des communes (les fichiers IRCOM le permettent).
3. Ajouter les impôts locaux pour avoir une vue complète.
4. Corriger les montants de l'inflation.
""", """
**What this means for a tax collection department (my opinion):**
- closely follow the big files, which represent most of the money;
- automate reminders for small amounts, which are very numerous;
- the resources needed are not the same in every department.

**Next steps:**
1. Find data on tax actually collected (collection rates) to replace my assumptions.
2. Go down to municipality level (the IRCOM files allow it).
3. Add local taxes for a complete picture.
4. Adjust amounts for inflation.
"""))
