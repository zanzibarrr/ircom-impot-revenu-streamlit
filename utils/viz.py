# Graphiques Plotly avec un style commun

import json

import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import sample_colorscale

from utils.io import ROOT
from utils.lang import anglais, t

BLEU = "#0B5CAD"
ORANGE = "#D55E00"
GRIS = "#9AA0A6"
GRIS_CLAIR = "#D0D4D9"


def fr(x, dec=1):
    """1 234,5 (FR) ou 1,234.5 (EN)."""
    texte = f"{x:,.{dec}f}"
    if anglais():
        return texte
    texte = texte.replace(",", " ")
    texte = texte.replace(".", ",")
    return texte


def mise_en_forme(fig, hauteur=420):
    """Style commun."""
    if anglais():
        separateurs = ".,"
    else:
        separateurs = ", "

    fig.update_layout(
        template="plotly_white",
        height=hauteur,
        margin=dict(l=10, r=10, t=40, b=10),
        separators=separateurs,
        legend=dict(orientation="h", y=1.08, x=0, title_text=""),
        font=dict(size=13),
    )
    return fig


def ajouter_ruptures(fig, ruptures, annee_min, annee_max):
    """Ligne pointillée + texte pour chaque rupture {année: (fr, en)}."""
    for annee in ruptures:
        texte_fr = ruptures[annee][0]
        texte_en = ruptures[annee][1]

        if annee < annee_min or annee > annee_max:
            continue

        fig.add_vline(x=annee, line_dash="dot", line_color=GRIS)
        fig.add_annotation(x=annee, y=1, yref="paper", text=t(texte_fr, texte_en), showarrow=False,
                           textangle=-90, xanchor="right", yanchor="top", font=dict(size=10, color="gray"))
    return fig


def courbe(df, x, y, titre_y, couleur=None, ruptures=None):
    """Courbe d'évolution (une par groupe si couleur)."""
    etiquettes = {x: t("Année de revenus", "Income year"), y: titre_y}

    if couleur is None:
        fig = px.line(df, x=x, y=y, markers=True, labels=etiquettes, color_discrete_sequence=[BLEU])
    else:
        fig = px.line(df, x=x, y=y, color=couleur, markers=False, labels=etiquettes,
                      color_discrete_sequence=px.colors.qualitative.Dark24)

    if ruptures is not None and len(ruptures) > 0 and not df.empty:
        ajouter_ruptures(fig, ruptures, int(df[x].min()), int(df[x].max()))
    return mise_en_forme(fig)


def barres_classement(df, valeur, nom, titre_x, reference=None, a_colorer=()):
    """Barres triées, a_colorer en orange."""
    df = df.sort_values(valeur)

    couleurs = []
    for nom_barre in df[nom]:
        if nom_barre in a_colorer:
            couleurs.append(ORANGE)
        else:
            couleurs.append(BLEU)

    barres = go.Bar(x=df[valeur], y=df[nom], orientation="h", marker_color=couleurs,
                    hovertemplate="%{y} : %{x:.1f}<extra></extra>")
    fig = go.Figure(barres)

    # valeur de la sélection
    if reference is not None:
        fig.add_vline(x=reference, line_dash="dash", line_color="black",
                      annotation_text=t("Sélection", "Selection") + f" : {fr(reference)}",
                      annotation_position="top")

    fig.update_xaxes(title=titre_x)
    hauteur = 22 * len(df) + 80
    if hauteur < 350:
        hauteur = 350
    return mise_en_forme(fig, hauteur=hauteur)


def lire_contours():
    """{code département: (xs, ys)} depuis le geojson."""
    with open(ROOT / "assets" / "departements.geojson", encoding="utf-8") as f:
        geo = json.load(f)

    contours = {}
    for departement in geo["features"]:
        geometrie = departement["geometry"]
        if geometrie["type"] == "MultiPolygon":
            polygones = geometrie["coordinates"]
        else:
            polygones = [geometrie["coordinates"]]

        xs = []
        ys = []
        for polygone in polygones:
            # contour extérieur
            for point in polygone[0]:
                xs.append(point[0])
                ys.append(point[1])
            # None = séparation entre deux morceaux
            xs.append(None)
            ys.append(None)

        code = departement["properties"]["code"]
        contours[code] = (xs, ys)
    return contours


def carte(df, valeur, titre):
    """Carte de la métropole, départements dessinés avec go.Scatter (pas de fond de carte)."""
    contours = lire_contours()

    d = df[df["perimetre"] == "Métropole"]
    d = d[d["dep"].isin(list(contours.keys()))]
    d = d.dropna(subset=[valeur])

    # valeur ramenée entre 0,15 et 1 sur l'échelle Blues
    vmin = d[valeur].min()
    vmax = d[valeur].max()
    positions = []
    for v in d[valeur]:
        positions.append((v - vmin) / (vmax - vmin) * 0.85 + 0.15)
    couleurs = sample_colorscale("Blues", positions)

    fig = go.Figure()
    numero = 0
    for index, ligne in d.iterrows():
        xs, ys = contours[ligne["dep"]]
        texte = f"{ligne['dep_name']} ({ligne['region']})<br>{titre} : {fr(ligne[valeur])}"
        fig.add_trace(go.Scatter(x=xs, y=ys, fill="toself", fillcolor=couleurs[numero], mode="lines",
                                 line=dict(color="white", width=0.6), hoveron="fills", hoverinfo="text",
                                 text=texte, showlegend=False))
        numero = numero + 1

    # trace invisible pour la légende de couleur
    fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers", showlegend=False, hoverinfo="skip",
                             marker=dict(colorscale="Blues", cmin=vmin, cmax=vmax, color=[vmin], showscale=True,
                                         colorbar=dict(title=titre, thickness=12))))

    fig.update_xaxes(visible=False)
    # proportions de la carte
    fig.update_yaxes(visible=False, scaleanchor="x", scaleratio=1.45)
    fig = mise_en_forme(fig, hauteur=550)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), plot_bgcolor="white")
    return fig


def nuage(df, x, y, taille, couleur, titre_x, titre_y):
    """Un point par département."""
    etiquettes = {x: titre_x, y: titre_y, couleur: ""}
    fig = px.scatter(df, x=x, y=y, size=taille, color=couleur, hover_name="dep_name", size_max=40,
                     labels=etiquettes, color_discrete_sequence=px.colors.qualitative.Safe)
    return mise_en_forme(fig, hauteur=480)
