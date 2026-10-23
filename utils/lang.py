# Langue FR / EN (choisie dans la sidebar, gardée dans st.session_state["langue"])

import streamlit as st


def anglais():
    """True si l'anglais est choisi."""
    return st.session_state.get("langue") == "English"


def t(fr, en):
    """Texte dans la langue choisie."""
    if anglais():
        return en
    return fr


def traduire(couple):
    """t() avec un couple (fr, en)."""
    return t(couple[0], couple[1])
