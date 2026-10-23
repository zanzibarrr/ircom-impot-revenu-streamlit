# Introduction : contexte, questions, données, précautions

import streamlit as st

from utils.lang import t
from utils.prep import agreger
from utils.viz import fr


def render(tables, filtres):
    panel = tables["panel"]
    tranches = tables["tranches"]

    # France entière, 2024
    panel_2024 = panel[panel["year"] == 2024]
    france = agreger(panel_2024, ["year"]).iloc[0]

    tranches_2024 = tranches[tranches["year"] == 2024]
    hauts_revenus = tranches_2024[tranches_2024["tranche"] == "> 100 k€"]
    part_haut = 100 * hauts_revenus["impot_net"].sum() / tranches_2024["impot_net"].sum()
    foyers_haut = 100 * hauts_revenus["nb_foyers"].sum() / tranches_2024["nb_foyers"].sum()

    st.header(t("Pourquoi ce sujet ?", "Why this topic?"))
    st.markdown(t(f"""
Je commence bientôt un stage à la DGFiP dans un service de **recouvrement de l'impôt**. Le travail de ce
service, c'est d'encaisser l'impôt qui a été émis et de relancer ceux qui ne paient pas. Avant d'y aller,
je voulais comprendre à quoi ressemble l'impôt sur le revenu en chiffres : qui le paie et où.

Premier constat qui m'a surpris : **en 2024, {fr(foyers_haut)} % des foyers (ceux qui déclarent plus de
100 000 € de revenu fiscal de référence) paient {fr(part_haut, 0)} % de l'impôt sur le revenu**, et moins
d'un foyer sur deux ({fr(france['part_imposes'])} %) est imposé.
""", f"""
I will soon start an internship at the DGFiP (the French public finance administration) in a **tax collection**
department. This department collects the tax that has been issued and follows up with people who do not pay.
Before starting, I wanted to understand what income tax looks like in numbers: who pays it, and where.

First thing that surprised me: **in 2024, {fr(foyers_haut)}% of households (those declaring more than
€100,000 of reference taxable income) paid {fr(part_haut, 0)}% of income tax**, and less than one household
in two ({fr(france['part_imposes'])}%) pays income tax at all.
"""))

    st.subheader(t("Questions auxquelles j'essaie de répondre", "Questions I try to answer"))
    st.markdown(t("""
1. Comment ont évolué l'impôt et le nombre de foyers imposés depuis 1984 ? *(Vue d'ensemble)*
2. Quels départements paient le plus, et où y a-t-il le moins de foyers imposés ? *(Analyses détaillées)*
3. Quelle part de l'impôt repose sur les hauts revenus ? *(Analyses détaillées)*
4. Pour un service de recouvrement : combien de dossiers faut-il traiter pour récupérer l'essentiel
   de l'argent ? *(petite simulation dans Analyses détaillées)*

Public visé : des agents d'un service de recouvrement (ou des étudiants comme moi qui découvrent le sujet).
""", """
1. How have income tax and the number of taxed households changed since 1984? *(Overview)*
2. Which departments pay the most, and where are there the fewest taxed households? *(Deep dives)*
3. How much of the tax relies on high incomes? *(Deep dives)*
4. For a tax collection department: how many files must be handled to recover most of the money?
   *(small simulation in Deep dives)*

Target audience: staff of a tax collection department (or students like me discovering the topic).
"""))

    st.subheader(t("Les données", "The data"))
    st.markdown(t("""
J'utilise le jeu de données **« L'impôt sur le revenu par collectivité territoriale » (IRCOM)** publié par la
DGFiP sur data.gouv.fr (Licence Ouverte 2.0). Il est publié en plusieurs fichiers :

- un fichier Excel avec une ligne par département et par année, de **1984 à 2020** ;
- un fichier zip par année, que j'utilise pour **2018 à 2024**, avec le détail par **tranche de revenu** (8 tranches).

Variables utilisées : nombre de foyers, revenu fiscal de référence (RFR), impôt net, nombre de foyers
imposés. Tous les montants sont en euros courants.
""", """
I use the dataset **"L'impôt sur le revenu par collectivité territoriale" (IRCOM — income tax by local
authority)** published by the DGFiP on data.gouv.fr (Open Licence 2.0). It is published as several files:

- one Excel file with one row per department and per year, from **1984 to 2020**;
- one zip file per year, which I use for **2018 to 2024**, with the detail by **income bracket** (8 brackets).

Variables used: number of households, reference taxable income (RFR), net tax, number of taxed households.
All amounts are in current euros (not adjusted for inflation).
"""))

    with st.expander(t("Précautions avant de lire les graphiques", "Caveats before reading the charts")):
        st.markdown(t("""
- Les données concernent l'impôt **émis**, pas l'impôt réellement **encaissé** : on ne voit pas les impayés.
- Avant 2000, le revenu publié est le revenu net imposable, pas le RFR : les niveaux ne sont pas comparables.
- En 2018 (« année blanche » avec le CIMR) et 2019 (prélèvement à la source), les chiffres sont à
  interpréter avec prudence.
- Les tranches de revenu ne sont pas indexées sur l'inflation.
- Le détail de la qualité des données (et ce que j'ai corrigé) est dans l'onglet **Conclusions**.
""", """
- The data is about tax **issued**, not tax actually **collected**: unpaid tax is not visible.
- Before 2000, the published income is net taxable income, not RFR: levels are not comparable.
- In 2018 ("blank year" with the CIMR tax credit) and 2019 (withholding tax), figures must be read with care.
- Income brackets are not indexed on inflation.
- Details on data quality (and what I corrected) are in the **Conclusions** tab.
"""))

    with st.expander(t("Petit lexique", "Glossary")):
        st.markdown(t("""
- **Foyer fiscal** : une déclaration de revenus (personne seule ou couple, avec ou sans enfants).
- **RFR** : revenu fiscal de référence.
- **Impôt net** : impôt après réductions et crédits d'impôt (il peut être négatif).
- **PAS** : prélèvement à la source (depuis 2019). **CIMR** : crédit d'impôt qui a « effacé » l'impôt
  sur les revenus courants de 2018.
- **SIP** : service des impôts des particuliers.
""", """
- **Tax household (foyer fiscal)**: one income tax return (single person or couple, with or without children).
- **RFR**: reference taxable income (revenu fiscal de référence).
- **Net tax**: tax after reductions and tax credits (it can be negative).
- **PAS**: withholding tax (since 2019). **CIMR**: tax credit that "erased" the tax on regular 2018 income.
- **SIP**: local tax office for individuals.
"""))
