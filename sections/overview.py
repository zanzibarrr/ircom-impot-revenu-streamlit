# Vue d'ensemble : tendances depuis 1984

import plotly.graph_objects as go
import streamlit as st

from utils.lang import t, traduire
from utils.prep import INDICATEURS, RUPTURES, agreger
from utils.viz import BLEU, GRIS_CLAIR, ajouter_ruptures, courbe, fr, mise_en_forme

# vues de la première courbe
VUES = {
    "tout": ("Toute la sélection", "Whole selection"),
    "region": ("Par région", "By region"),
    "deps": ("Comparer des départements", "Compare departments"),
}


def nom_vue(vue):
    return traduire(VUES[vue])


def render(tables, filtres):
    cle = filtres["indicateur"]
    indicateur = INDICATEURS[cle]
    label = traduire(indicateur["label"])
    unite = traduire(indicateur["unite"])
    aide = traduire(indicateur["aide"])

    nat = agreger(filtres["panel"], ["year"])
    if nat.empty:
        st.warning(t("Pas de données pour cette sélection.", "No data for this selection."))
        return

    debut = nat.iloc[0]
    fin = nat.iloc[-1]
    annee_debut = int(debut["year"])
    annee_fin = int(fin["year"])

    evol_impot = 100 * (fin["impot_net"] / debut["impot_net"] - 1)
    evol_foyers = 100 * (fin["nb_foyers"] / debut["nb_foyers"] - 1)

    st.header(t("Vue d'ensemble", "Overview"))
    st.markdown(t(f"**Entre {annee_debut} et {annee_fin}, l'impôt émis a augmenté de {fr(evol_impot, 0)} % "
                  f"alors que le nombre de foyers a augmenté de {fr(evol_foyers, 0)} %.**",
                  f"**Between {annee_debut} and {annee_fin}, the tax issued increased by {fr(evol_impot, 0)}% "
                  f"while the number of households increased by {fr(evol_foyers, 0)}%.**"))

    # --- 1. évolution de l'indicateur ---
    st.subheader(f"{label} ({unite})")
    vue = st.radio(t("Afficher", "Show"), list(VUES.keys()), format_func=nom_vue, horizontal=True, key="vue")
    titre_y = f"{label} ({unite})"

    if vue == "tout":
        fig = courbe(nat, "year", cle, titre_y, ruptures=RUPTURES)

    elif vue == "region":
        par_region = agreger(filtres["panel"], ["region", "year"])
        fig = courbe(par_region, "year", cle, titre_y, couleur="region", ruptures=RUPTURES)

    else:
        panel = filtres["panel"]
        noms = {}
        for index, ligne in panel.iterrows():
            noms[ligne["dep"]] = ligne["dep_name"]

        def nom_departement(code):
            return noms[code]

        # 75, 92, 93 par défaut
        defaut = []
        for code in ["75", "92", "93"]:
            if code in noms:
                defaut.append(code)

        choix = st.multiselect(t("Départements", "Departments"), list(noms.keys()), default=defaut,
                               format_func=nom_departement, key="deps_compares",
                               placeholder=t("Choisir des départements", "Choose departments"))
        lignes_choisies = panel[panel["dep"].isin(choix)]
        fig = courbe(lignes_choisies, "year", cle, titre_y, couleur="dep_name", ruptures=RUPTURES)

    st.plotly_chart(fig, width="stretch")
    st.caption(t(f"Description du graphique : évolution de « {label} » par année de revenus. "
                 f"Définition : {aide}. Les pointillés indiquent les ruptures de série.",
                 f"Chart description: change in \"{label}\" by income year. "
                 f"Definition: {aide}. Dotted lines show breaks in the series."))

    # --- 2. foyers imposés / non imposés ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(t("Foyers imposés et non imposés", "Taxed and non-taxed households"))
        imposes = nat["nb_imposes"] / 1e6
        non_imposes = (nat["nb_foyers"] - nat["nb_imposes"]) / 1e6

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=nat["year"], y=imposes, name=t("Imposés", "Taxed"), stackgroup="a",
                                 line_color=BLEU))
        fig.add_trace(go.Scatter(x=nat["year"], y=non_imposes, name=t("Non imposés", "Not taxed"), stackgroup="a",
                                 line_color=GRIS_CLAIR))
        fig.update_layout(xaxis_title=t("Année de revenus", "Income year"),
                          yaxis_title=t("Foyers (millions)", "Households (millions)"))
        ruptures_courtes = {2018: ("CIMR", "CIMR"), 2019: ("PAS", "Withholding")}
        ajouter_ruptures(fig, ruptures_courtes, annee_debut, annee_fin)
        st.plotly_chart(mise_en_forme(fig, 380), width="stretch")
        st.caption(t(f"Description : en {annee_fin}, {fr(fin['nb_imposes'] / 1e6)} millions de foyers imposés "
                     f"sur {fr(fin['nb_foyers'] / 1e6)} millions.",
                     f"Description: in {annee_fin}, {fr(fin['nb_imposes'] / 1e6)} million taxed households "
                     f"out of {fr(fin['nb_foyers'] / 1e6)} million."))

    with col2:
        st.subheader(t("Impôt moyen par foyer imposé", "Average tax per taxed household"))
        fig = courbe(nat, "year", "impot_par_impose", t("€ par foyer imposé", "€ per taxed household"))
        st.plotly_chart(mise_en_forme(fig, 380), width="stretch")
        st.caption(t(f"Description : {fr(debut['impot_par_impose'], 0)} € en {annee_debut}, "
                     f"{fr(fin['impot_par_impose'], 0)} € en {annee_fin}.",
                     f"Description: €{fr(debut['impot_par_impose'], 0)} in {annee_debut}, "
                     f"€{fr(fin['impot_par_impose'], 0)} in {annee_fin}."))

    st.info(t("Ce que j'en retiens : le nombre de foyers imposés bouge assez peu, mais l'impôt moyen d'un foyer "
              "imposé augmente beaucoup. Pour le recouvrement, chaque dossier représente donc plus d'argent.",
              "What I take from this: the number of taxed households changes little, but the average tax of a "
              "taxed household rises a lot. For tax collection, each file therefore represents more money."))

    with st.expander(t("Pourquoi 2018 et 2019 sont des années à part", "Why 2018 and 2019 are special years")):
        st.write(t("Avec le passage au prélèvement à la source en 2019, l'impôt sur les revenus courants de 2018 a été "
                   "annulé par le CIMR (crédit d'impôt modernisation du recouvrement) pour éviter de payer deux fois. "
                   "Le fichier donne l'impôt 2018 avant et après CIMR ; j'utilise la valeur avant CIMR pour pouvoir "
                   "comparer avec les autres années.",
                   "With the switch to withholding tax in 2019, the tax on regular 2018 income was cancelled by the "
                   "CIMR tax credit, so that people would not pay twice. The file gives the 2018 tax before and after "
                   "the CIMR; I use the value before the CIMR so it can be compared with the other years."))
