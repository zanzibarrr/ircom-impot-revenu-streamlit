from pathlib import Path

import streamlit as st

from sections import conclusions, deep_dives, intro, overview
from utils.io import DATASET_URL, load_data
from utils.lang import t, traduire
from utils.prep import INDICATEURS, agreger, make_tables
from utils.viz import fr

st.set_page_config(page_title="Impôt sur le revenu - IRCOM", layout="wide")

# périmètres (FR, EN)
PERIMETRES = {
    "Métropole": ("Métropole", "Mainland France"),
    "Outre-mer": ("Outre-mer", "Overseas"),
    "Non-résidents": ("Non-résidents", "Non-residents"),
}

# infos étudiant et cours
ETUDIANT = "Mickael LY"
EMAIL = "mickael.ly@efrei.net"
PROGRAMME = "Data Engineering"
ANNEE_SCOLAIRE = "2026-2027"
COURS = "Data Analysis & Visualization"
PROF = "Mano Joseph Mathew"
LINKEDIN_PROF = "https://www.linkedin.com/in/manomathew/"
LOGO = Path(__file__).parent / "assets" / "efrei_logo.png"


@st.cache_data(show_spinner="Chargement des données... / Loading data...")
def get_data():
    serie_brute, tranches_brutes = load_data()
    tables = make_tables(serie_brute, tranches_brutes)
    tables["serie_brute"] = serie_brute
    tables["tranches_brutes"] = tranches_brutes
    return tables


tables = get_data()
panel = tables["panel"]


# ---------------- Textes des listes ----------------
def nom_perimetre(perimetre):
    return traduire(PERIMETRES[perimetre])


def nom_indicateur(cle):
    label = traduire(INDICATEURS[cle]["label"])
    unite = traduire(INDICATEURS[cle]["unite"])
    return f"{label} ({unite})"


# ---------------- Changement de langue ----------------
# une clé par langue pour chaque liste, on recopie les choix au changement de langue
LISTES = ["perimetre", "indicateur", "departement"]


def changer_langue():
    if st.session_state["langue"] == "English":
        nouvelle = "en"
        ancienne = "fr"
    else:
        nouvelle = "fr"
        ancienne = "en"

    for nom in LISTES:
        ancienne_cle = f"{nom}_{ancienne}"
        nouvelle_cle = f"{nom}_{nouvelle}"
        if ancienne_cle in st.session_state:
            st.session_state[nouvelle_cle] = st.session_state[ancienne_cle]


# ---------------- Barre latérale ----------------
with st.sidebar:
    st.radio("Langue / Language", ["Français", "English"], key="langue", horizontal=True, on_change=changer_langue)
    st.markdown(f"**{ETUDIANT}**  \n{EMAIL}  \n"
                f"{t('Programme', 'Program')} : {PROGRAMME}  \n"
                f"{t('Année', 'Year')} : {ANNEE_SCOLAIRE}")
    st.divider()

    L = t("fr", "en")

    # valeurs par défaut (premier chargement)
    if f"perimetre_{L}" not in st.session_state:
        st.session_state[f"perimetre_{L}"] = ["Métropole", "Outre-mer"]
    if f"indicateur_{L}" not in st.session_state:
        st.session_state[f"indicateur_{L}"] = "part_imposes"
    if f"departement_{L}" not in st.session_state:
        st.session_state[f"departement_{L}"] = "toute"

    st.header(t("Filtres", "Filters"))

    annees = st.slider(t("Période (années de revenus)", "Period (income years)"), 1984, 2024, (2000, 2024),
                       key="annees")
    premiere_annee = annees[0]
    derniere_annee = annees[1]

    annee = st.select_slider(t("Année pour la carte et les KPI", "Year for the map and KPIs"),
                             options=list(range(premiere_annee, derniere_annee + 1)), value=derniere_annee,
                             key="annee")

    perimetre = st.multiselect(t("Périmètre", "Scope"), list(PERIMETRES.keys()), format_func=nom_perimetre,
                               key=f"perimetre_{L}", placeholder=t("Choisir", "Choose"),
                               help=t("Non-résidents = foyers gérés par la direction des non-résidents "
                                      "(à partir de 2006)",
                                      "Non-residents = households handled by the non-residents tax office "
                                      "(from 2006)"))
    if len(perimetre) == 0:
        perimetre = ["Métropole"]

    # régions du périmètre choisi
    lignes_perimetre = panel[panel["perimetre"].isin(perimetre)]
    liste_regions = sorted(lignes_perimetre["region"].dropna().unique())
    regions = st.multiselect(t("Régions (vide = toutes)", "Regions (empty = all)"), liste_regions,
                             key="regions", placeholder=t("Toutes les régions", "All regions"))

    indicateur = st.selectbox(t("Indicateur", "Indicator"), list(INDICATEURS.keys()), format_func=nom_indicateur,
                              key=f"indicateur_{L}")

    # départements du périmètre et des régions choisis
    deps = panel[panel["perimetre"].isin(perimetre)]
    if len(regions) > 0:
        deps = deps[deps["region"].isin(regions)]
    deps = deps.drop_duplicates("dep").sort_values("dep")

    noms_deps = {}
    for index, ligne in deps.iterrows():
        noms_deps[ligne["dep"]] = ligne["dep_name"]

    def nom_departement(code):
        if code == "toute":
            return t("Toute la sélection", "Whole selection")
        return f"{code} - {noms_deps[code]}"

    # département plus dans la sélection -> "toute"
    if st.session_state[f"departement_{L}"] not in noms_deps:
        st.session_state[f"departement_{L}"] = "toute"

    departement = st.selectbox(t("Département (pour les tranches et la simulation)",
                                 "Department (for the brackets and the simulation)"),
                               ["toute"] + list(noms_deps.keys()), format_func=nom_departement,
                               key=f"departement_{L}")

    st.caption(t("DGFiP, IRCOM (data.gouv.fr) - Licence Ouverte 2.0",
                 "DGFiP, IRCOM (data.gouv.fr) - Open Licence 2.0"))

    st.divider()
    st.markdown(f"**{t('Cours', 'Course')} :** {COURS}  \n"
                f"**Prof. :** {PROF}  \n[LinkedIn]({LINKEDIN_PROF})")
    if LOGO.exists():
        st.image(str(LOGO), width=160)

st.title(t("Qui paie l'impôt sur le revenu, et où ?", "Who pays income tax in France, and where?"))
st.caption(f"Source : [IRCOM - DGFiP, data.gouv.fr]({DATASET_URL}) - " + t("Licence Ouverte 2.0", "Open Licence 2.0"))

# ---------------- Application des filtres ----------------
masque = panel["perimetre"].isin(perimetre)
masque = masque & (panel["year"] >= premiere_annee) & (panel["year"] <= derniere_annee)
if len(regions) > 0:
    masque = masque & panel["region"].isin(regions)

tranches = tables["tranches"]
masque_tranches = tranches["perimetre"].isin(perimetre)
if len(regions) > 0:
    masque_tranches = masque_tranches & tranches["region"].isin(regions)

# nom de la sélection pour les titres
if len(regions) == 0:
    noms = []
    for p in perimetre:
        noms.append(nom_perimetre(p))
    nom_selection = " + ".join(noms)
elif len(regions) <= 3:
    nom_selection = ", ".join(regions)
else:
    nom_selection = f"{len(regions)} " + t("régions", "regions")

if departement == "toute":
    departement_choisi = None
else:
    departement_choisi = departement

filtres = {
    "panel": panel[masque],
    "tranches": tranches[masque_tranches],
    "annees": annees,
    "annee": annee,
    "indicateur": indicateur,
    "departement": departement_choisi,
    "nom_selection": nom_selection,
}

# ---------------- KPI ----------------
par_annee = agreger(filtres["panel"], ["year"]).set_index("year")

if annee in par_annee.index:
    actuelle = par_annee.loc[annee]
    if annee - 1 in par_annee.index:
        precedente = par_annee.loc[annee - 1]
    else:
        precedente = None

    def evolution(colonne):
        """Évolution en % vs l'année précédente."""
        if precedente is None:
            return None
        variation = 100 * (actuelle[colonne] / precedente[colonne] - 1)
        return f"{variation:+.1f} % vs {annee - 1}"

    if precedente is None:
        evolution_imposes = None
    else:
        ecart = actuelle["part_imposes"] - precedente["part_imposes"]
        evolution_imposes = f"{ecart:+.1f} pt"

    st.subheader(t("Chiffres clés", "Key figures") + f" {annee} ({nom_selection})")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t("Foyers fiscaux", "Tax households"), f"{fr(actuelle['nb_foyers'] / 1e6, 2)} M",
              evolution("nb_foyers"))
    c2.metric(t("Foyers imposés", "Taxed households"), f"{fr(actuelle['part_imposes'])} %", evolution_imposes)
    c3.metric(t("Impôt net émis", "Net tax issued"), f"{fr(actuelle['impot_net'] / 1e9)} " + t("Md€", "€ bn"),
              evolution("impot_net"))
    c4.metric(t("Impôt moyen par foyer imposé", "Average tax per taxed household"),
              f"{fr(actuelle['impot_par_impose'], 0)} €", evolution("impot_par_impose"))
else:
    st.warning(t("Pas de données pour cette sélection.", "No data for this selection."))

# ---------------- Onglets ----------------
onglet1, onglet2, onglet3, onglet4 = st.tabs([t("Introduction", "Introduction"), t("Vue d'ensemble", "Overview"),
                                              t("Analyses détaillées", "Deep dives"), t("Conclusions", "Conclusions")])
with onglet1:
    intro.render(tables, filtres)
with onglet2:
    overview.render(tables, filtres)
with onglet3:
    deep_dives.render(tables, filtres)
with onglet4:
    conclusions.render(tables, filtres)
