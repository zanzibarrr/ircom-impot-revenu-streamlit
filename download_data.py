# Télécharge les fichiers IRCOM sur data.gouv.fr et crée les CSV dans data/extracted
# Utilisation : python download_data.py   (ajouter --force pour tout retélécharger)
import sys

from utils.io import construire_csv

construire_csv(force="--force" in sys.argv)
print("Terminé, on peut lancer : streamlit run app.py")
