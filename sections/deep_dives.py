# Analyses détaillées : départements, tranches de revenu, simulation

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from utils.lang import t, traduire
from utils.prep import INDICATEURS, agreger
from utils.viz import BLEU, GRIS, GRIS_CLAIR, ORANGE, barres_classement, carte, fr, mise_en_forme, nuage


def render(tables, filtres):
    st.header(t("Analyses détaillées", "Deep dives"))
    partie_departements(filtres)
    st.divider()

    # parties 2 et 3 seulement pour les années avec tranches (2018-2024)
    annees_tranches = sorted(filtres["tranches"]["year"].unique())

    if filtres["annee"] in annees_tranches:
        partie_tranches(filtres)
        st.divider()
        partie_simulation(filtres)
    else:
        debut = annees_tranches[0]
        fin = annees_tranches[-1]
        st.info(t(f"Les parties « Qui paie l'impôt ? » (détail par tranche de revenu) et « Simulation » sont "
                  f"disponibles pour les années {debut} à {fin} (j'ai chargé le détail par tranche uniquement pour "
                  f"ces années). Choisissez une de ces années dans la barre latérale.",
                  f"The parts \"Who pays the tax?\" (detail by income bracket) and \"Simulation\" are available "
                  f"for the years {debut} to {fin} (I only loaded the bracket detail for these years). "
                  f"Choose one of these years in the sidebar."))


# ------------------------------------------------------------------
# 1. Comparaison des départements
# ------------------------------------------------------------------
def partie_departements(filtres):
    cle = filtres["indicateur"]
    indicateur = INDICATEURS[cle]
    label = traduire(indicateur["label"])
    unite = traduire(indicateur["unite"])

    panel = filtres["panel"]
    d = panel[panel["year"] == filtres["annee"]]
    if d.empty:
        st.warning(t("Pas de données pour cette année.", "No data for this year."))
        return

    # valeur de la sélection, max et min
    reference = agreger(d, ["year"]).iloc[0][cle]
    haut = d.loc[d[cle].idxmax()]
    bas = d.loc[d[cle].idxmin()]

    # part du top 5
    top5 = d.nlargest(5, "impot_net")
    part_top5 = 100 * top5["impot_net"].sum() / d["impot_net"].sum()

    st.subheader(t("1. Comparaison des départements", "1. Comparing departments") + f" ({filtres['annee']})")
    st.markdown(t(f"**{label} : de {fr(bas[cle])} {unite} ({bas['dep_name']}) à {fr(haut[cle])} {unite} "
                  f"({haut['dep_name']}). Les 5 premiers départements paient {fr(part_top5, 0)} % de l'impôt.**",
                  f"**{label}: from {fr(bas[cle])} {unite} ({bas['dep_name']}) to {fr(haut[cle])} {unite} "
                  f"({haut['dep_name']}). The top 5 departments pay {fr(part_top5, 0)}% of the tax.**"))

    col1, col2 = st.columns([1.2, 1])

    with col1:
        if (d["perimetre"] == "Métropole").any():
            st.plotly_chart(carte(d, cle, f"{label} ({unite})"), width="stretch")
            st.caption(t(f"Description : carte de la métropole, plus le bleu est foncé plus « {label} » est "
                         "élevé. Les Outre-mer sont dans le classement à droite.",
                         f"Description: map of mainland France, the darker the blue the higher \"{label}\". "
                         "Overseas departments are in the ranking on the right."))

    with col2:
        n = st.slider(t("Nombre de départements en haut et en bas du classement",
                        "Number of departments at the top and bottom of the ranking"), 5, 20, 10, key="nb_classement")

        # n premiers et n derniers
        classement = pd.concat([d.nlargest(n, cle), d.nsmallest(n, cle)])
        classement = classement.drop_duplicates("dep")

        # outre-mer en orange
        outre_mer = classement[classement["perimetre"] == "Outre-mer"]
        a_colorer = list(outre_mer["dep_name"])

        fig = barres_classement(classement, cle, "dep_name", f"{label} ({unite})", reference, a_colorer)
        st.plotly_chart(fig, width="stretch")
        st.caption(t("Description : départements les plus hauts et les plus bas ; Outre-mer en orange ; "
                     "la ligne pointillée correspond à la valeur de toute la sélection.",
                     "Description: highest and lowest departments; overseas departments in orange; "
                     "the dashed line is the value for the whole selection."))

    st.markdown(t("**Revenu moyen et part de foyers imposés**", "**Average income and share of taxed households**"))
    fig = nuage(d, "revenu_moyen", "part_imposes", "impot_net", "region",
                t("Revenu moyen par foyer (€)", "Average income per household (€)"),
                t("Part de foyers imposés (%)", "Share of taxed households (%)"))
    st.plotly_chart(fig, width="stretch")

    correlation = d["revenu_moyen"].corr(d["part_imposes"])
    st.caption(t(f"Description : un point par département, taille = impôt payé. Corrélation : {fr(correlation, 2)}. "
                 "Attention, une corrélation ne veut pas dire qu'il y a une relation de cause à effet.",
                 f"Description: one dot per department, size = tax paid. Correlation: {fr(correlation, 2)}. "
                 "Careful, a correlation does not mean there is a cause-and-effect relationship."))

    with st.expander(t("Voir le tableau des départements", "See the department table")):
        colonnes = ["dep", "dep_name", "region", "nb_foyers", "part_imposes", "revenu_moyen", "impot_net"]
        tableau = d[colonnes]
        tableau = tableau.sort_values("impot_net", ascending=False)
        tableau = tableau.round(1)
        st.dataframe(tableau, hide_index=True, width="stretch")

        fichier_csv = tableau.to_csv(index=False).encode("utf-8")
        st.download_button(t("Télécharger en CSV", "Download as CSV"), fichier_csv,
                           f"departements_{filtres['annee']}.csv", "text/csv")


# ------------------------------------------------------------------
# 2. Tranches de revenu
# ------------------------------------------------------------------
def selection_tranches(filtres):
    """Tranches de l'année (et du département) choisis, année, nom affiché."""
    tranches = filtres["tranches"]
    annee = filtres["annee"]
    donnees = tranches[tranches["year"] == annee]
    nom = filtres["nom_selection"]

    if filtres["departement"] is not None:
        donnees = donnees[donnees["dep"] == filtres["departement"]]
        if len(donnees) > 0:
            nom = donnees["dep_name"].iloc[0]
        else:
            nom = filtres["departement"]

    return donnees, annee, nom


def part_hauts_revenus(groupe):
    """% de l'impôt payé par les > 100 k€."""
    hauts = groupe[groupe["tranche"] == "> 100 k€"]
    return 100 * hauts["impot_net"].sum() / groupe["impot_net"].sum()


def partie_tranches(filtres):
    if filtres["tranches"].empty:
        return

    donnees, annee, nom = selection_tranches(filtres)
    st.subheader(t("2. Qui paie l'impôt ? Détail par tranche de revenu",
                   "2. Who pays the tax? Detail by income bracket") + f" ({annee})")

    # parts par tranche
    g = donnees.groupby("tranche", observed=True)[["nb_foyers", "impot_net"]].sum()
    g = g.reset_index()
    g["part_foyers"] = 100 * g["nb_foyers"] / g["nb_foyers"].sum()
    g["part_impot"] = 100 * g["impot_net"] / g["impot_net"].sum()

    haut = g[g["tranche"] == "> 100 k€"].iloc[0]
    st.markdown(t(f"**{nom} : les foyers au-dessus de 100 000 € représentent {fr(haut['part_foyers'])} % des foyers "
                  f"mais paient {fr(haut['part_impot'], 0)} % de l'impôt.**",
                  f"**{nom}: households above €100,000 are {fr(haut['part_foyers'])}% of households "
                  f"but pay {fr(haut['part_impot'], 0)}% of the tax.**"))

    # étiquettes (vides sous 1 %)
    textes = []
    for valeur in g["part_impot"]:
        if valeur >= 1:
            textes.append(f"{valeur:.0f} %")
        else:
            textes.append("")

    noms_tranches = g["tranche"].astype(str)
    fig = go.Figure()
    fig.add_trace(go.Bar(x=noms_tranches, y=g["part_foyers"], name=t("Part des foyers", "Share of households"),
                         marker_color=GRIS_CLAIR))
    fig.add_trace(go.Bar(x=noms_tranches, y=g["part_impot"], name=t("Part de l'impôt", "Share of the tax"),
                         marker_color=BLEU, text=textes, textposition="outside"))
    fig.update_layout(barmode="group",
                      xaxis_title=t("Tranche de revenu fiscal de référence", "Reference taxable income bracket"),
                      yaxis_title=t("% du total", "% of total"))
    st.plotly_chart(mise_en_forme(fig), width="stretch")
    st.caption(t("Description : pour chaque tranche, part des foyers (gris) et part de l'impôt (bleu). "
                 "Sous 20 000 €, l'impôt net est un peu négatif à cause des crédits d'impôt remboursés.",
                 "Description: for each bracket, share of households (grey) and share of the tax (blue). "
                 "Below €20,000, net tax is slightly negative because of refunded tax credits."))

    # part des > 100 k€ par département
    tranches_annee = filtres["tranches"][filtres["tranches"]["year"] == annee]
    lignes = []
    for cle_groupe, groupe in tranches_annee.groupby(["dep", "dep_name", "region", "perimetre"]):
        lignes.append({
            "dep": cle_groupe[0],
            "dep_name": cle_groupe[1],
            "region": cle_groupe[2],
            "perimetre": cle_groupe[3],
            "part_haut": part_hauts_revenus(groupe),
        })
    par_dep = pd.DataFrame(lignes)

    titre_part = t("% de l'impôt payé par les > 100 k€", "% of tax paid by > €100k")
    col1, col2 = st.columns([1.2, 1])

    with col1:
        if (par_dep["perimetre"] == "Métropole").any():
            st.plotly_chart(carte(par_dep, "part_haut", titre_part), width="stretch")
            st.caption(t("Description : carte de la part de l'impôt payée par les foyers au-dessus de 100 000 €.",
                         "Description: map of the share of tax paid by households above €100,000."))

    with col2:
        # évolution par année
        evolution = filtres["tranches"]
        if filtres["departement"] is not None:
            evolution = evolution[evolution["dep"] == filtres["departement"]]

        annees = []
        parts = []
        for annee_evo, groupe in evolution.groupby("year"):
            annees.append(str(annee_evo))
            parts.append(part_hauts_revenus(groupe))

        textes = []
        for valeur in parts:
            textes.append(f"{fr(valeur)} %")

        fig = go.Figure(go.Bar(x=annees, y=parts, marker_color=BLEU, text=textes, textposition="outside"))
        fig.update_layout(xaxis_title=t("Année", "Year"), yaxis_title=titre_part,
                          yaxis_range=[0, max(parts) * 1.25])
        st.plotly_chart(mise_en_forme(fig, 400), width="stretch")
        st.caption(t(f"Description : évolution {annees[0]}-{annees[-1]}. Les tranches ne sont pas "
                     "corrigées de l'inflation, donc une partie de la hausse vient juste de la hausse générale des "
                     "revenus. En 2018 et 2019 les non-résidents ne sont pas dans les fichiers par tranche.",
                     f"Description: change {annees[0]}-{annees[-1]}. Brackets are not adjusted for "
                     "inflation, so part of the increase only comes from the general rise in incomes. "
                     "In 2018 and 2019 non-residents are not in the bracket files."))


# ------------------------------------------------------------------
# 3. Simulation pour le recouvrement
# ------------------------------------------------------------------

# groupe de revenus de chaque tranche
GROUPES = {
    "< 10 k€": "bas",
    "10-12 k€": "bas",
    "12-15 k€": "bas",
    "15-20 k€": "bas",
    "20-30 k€": "bas",
    "30-50 k€": "moyen",
    "50-100 k€": "moyen",
    "> 100 k€": "haut",
}


def simuler(donnees, taux, capacite):
    """Part de l'argent récupérée en traitant d'abord les plus gros dossiers (taux d'impayé = hypothèses)."""
    g = donnees.groupby("tranche", observed=True)[["nb_imposes", "impot_net"]].sum()
    g = g.reset_index()

    # sans les tranches à impôt négatif
    g = g[g["impot_net"] > 0].copy()

    # taux d'impayé par tranche
    taux_tranches = []
    for tranche in g["tranche"].astype(str):
        groupe = GROUPES[tranche]
        taux_tranches.append(taux[groupe] / 100)
    g["taux"] = taux_tranches

    g["dossiers"] = g["nb_imposes"].fillna(0) * g["taux"]
    g["montant"] = g["impot_net"] * g["taux"]
    g["montant_moyen"] = g["montant"] / g["dossiers"]

    # plus gros dossiers d'abord
    g = g.sort_values("montant_moyen", ascending=False)

    # % cumulés : dossiers (x), montant (y)
    x = [0]
    y = [0]
    dossiers_cumules = 0
    montant_cumule = 0
    for index, ligne in g.iterrows():
        dossiers_cumules = dossiers_cumules + ligne["dossiers"]
        montant_cumule = montant_cumule + ligne["montant"]
        x.append(100 * dossiers_cumules / g["dossiers"].sum())
        y.append(100 * montant_cumule / g["montant"].sum())

    # montant récupéré pour la capacité choisie
    couvert = float(np.interp(capacite, x, y))
    return g, x, y, couvert


def partie_simulation(filtres):
    if filtres["tranches"].empty:
        return

    donnees, annee, nom = selection_tranches(filtres)
    st.subheader(t("3. Simulation : quels dossiers traiter en priorité ?",
                   "3. Simulation: which files should be handled first?") + f" ({annee})")
    st.warning(t("Les données ne disent pas combien d'impôt n'est pas payé. Les taux ci-dessous sont des "
                 "**hypothèses que j'ai choisies** pour l'exemple, ce ne sont pas des chiffres officiels.",
                 "The data does not say how much tax is unpaid. The rates below are **assumptions I chose** "
                 "for the example, they are not official figures."))

    col1, col2 = st.columns([1, 1.6])

    with col1:
        st.markdown(t(f"**Hypothèses ({nom}, revenus {annee})**", f"**Assumptions ({nom}, {annee} income)**"))
        taux_bas = st.slider(t("Taux d'impayé, revenus < 30 k€ (%)", "Unpaid rate, income < €30k (%)"),
                             0.0, 10.0, 3.0, 0.5, key="taux_bas")
        taux_moyen = st.slider(t("Taux d'impayé, revenus 30-100 k€ (%)", "Unpaid rate, income €30-100k (%)"),
                               0.0, 10.0, 1.5, 0.5, key="taux_moyen")
        taux_haut = st.slider(t("Taux d'impayé, revenus > 100 k€ (%)", "Unpaid rate, income > €100k (%)"),
                              0.0, 10.0, 1.0, 0.5, key="taux_haut")
        capacite = st.slider(t("Part des dossiers que le service peut traiter (%)",
                               "Share of files the department can handle (%)"), 5, 100, 20, 5, key="capacite")

    taux = {"bas": taux_bas, "moyen": taux_moyen, "haut": taux_haut}
    if taux_bas + taux_moyen + taux_haut == 0:
        st.info(t("Tous les taux sont à 0 : rien à simuler.", "All rates are 0: nothing to simulate."))
        return

    g, x, y, couvert = simuler(donnees, taux, capacite)

    with col2:
        kpi1, kpi2, kpi3 = st.columns(3)
        kpi1.metric(t("Dossiers en retard (estimés)", "Late files (estimated)"), fr(g["dossiers"].sum(), 0))
        kpi2.metric(t("Montant concerné", "Amount concerned"),
                    f"{fr(g['montant'].sum() / 1e6, 0)} " + t("M€", "€ m"))
        kpi3.metric(t("Montant récupéré", "Amount recovered"), f"{fr(couvert, 0)} %",
                    f"{couvert - capacite:+.0f} pt " + t("vs au hasard", "vs random"))

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[0, 100], y=[0, 100], name=t("Dossiers pris au hasard", "Files taken at random"),
                                 line=dict(color=GRIS, dash="dash")))
        fig.add_trace(go.Scatter(x=x, y=y, name=t("Plus gros dossiers d'abord", "Biggest files first"),
                                 line=dict(color=BLEU, width=3), mode="lines+markers"))
        fig.add_trace(go.Scatter(x=[capacite], y=[couvert], name=t("Mon scénario", "My scenario"), mode="markers",
                                 marker=dict(color=ORANGE, size=12)))
        fig.update_layout(xaxis_title=t("% des dossiers traités", "% of files handled"),
                          yaxis_title=t("% du montant récupéré", "% of the amount recovered"),
                          xaxis_range=[0, 100], yaxis_range=[0, 102])
        st.plotly_chart(mise_en_forme(fig, 400), width="stretch")
        st.caption(t(f"Description : en traitant d'abord les plus gros dossiers, {capacite} % des dossiers "
                     f"représentent environ {fr(couvert, 0)} % du montant (contre {capacite} % au hasard).",
                     f"Description: by handling the biggest files first, {capacite}% of the files represent "
                     f"about {fr(couvert, 0)}% of the amount (versus {capacite}% at random)."))

    with st.expander(t("Comment j'ai fait le calcul", "How I did the calculation")):
        st.markdown(t("""
- dossiers en retard = foyers imposés de la tranche × taux d'impayé ;
- montant = impôt net de la tranche × taux d'impayé ;
- les tranches avec un impôt négatif sont enlevées ;
- je suppose que tous les dossiers d'une même tranche ont le même montant (en réalité c'est encore plus
  concentré).

Limite importante : depuis le prélèvement à la source, une grande partie de l'impôt est prélevée
directement sur le salaire, donc les vrais impayés concernent surtout les soldes et les acomptes.
""", """
- late files = taxed households in the bracket × unpaid rate;
- amount = net tax of the bracket × unpaid rate;
- brackets with a negative tax are removed;
- I assume all files in the same bracket have the same amount (in reality it is even more concentrated).

Important limit: since withholding tax, a large part of the tax is taken directly from salaries, so real
unpaid tax mostly concerns balances and instalments.
"""))
        st.dataframe(g[["tranche", "taux", "dossiers", "montant", "montant_moyen"]].round(2), hide_index=True)
