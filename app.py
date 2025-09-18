# =======================================================
# microflow_ai/app.py
# Objectif : MVP V1.2 - Interface "Simplicité Radicale"
# =======================================================

import streamlit as st
import os
import json
from datetime import datetime
from extractor.pdf_reader import extract_text_from_pdf, structure_data_with_llm
from generator.pdf_generator import generate_pdf
import pandas as pd

# --- Configuration de la Page ---
st.set_page_config(page_title="MicroFlow.AI", page_icon="🤖", layout="centered")

# --- Initialisation de la Mémoire de Session (Session State) ---
def initialize_state():
    if 'step' not in st.session_state:
        st.session_state.step = "upload" # 'upload', 'edit', 'preview'
    if 'raw_data' not in st.session_state:
        st.session_state.raw_data = None
    if 'final_quote_data' not in st.session_state:
        st.session_state.final_quote_data = None

initialize_state()

# --- Fonctions Utilitaires ---
def restart_process():
    """Réinitialise tout le processus."""
    st.session_state.step = "upload"
    st.session_state.raw_data = None
    st.session_state.final_quote_data = None

# --- Interface Utilisateur ---
st.title("🤖 MicroFlow.AI")
st.subheader("Transformez un devis fournisseur en devis client.")

# =======================================================
# ÉTAPE 1 : UPLOAD
# =======================================================
if st.session_state.step == "upload":
    st.header("1. Importez votre devis fournisseur")
    uploaded_file = st.file_uploader("Choisissez un fichier PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file is not None:
        with st.spinner("Analyse du PDF par l'IA... (cela peut prendre jusqu'à 2 minutes et 30 secondes ! Merci de patienter ...)"):
            # ... (logique de sauvegarde et d'extraction du PDF) ...
            temp_dir = "temp_data"; os.makedirs(temp_dir, exist_ok=True)
            temp_pdf_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_pdf_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            raw_text = extract_text_from_pdf(temp_pdf_path)
            if raw_text:
                structured_data = structure_data_with_llm(raw_text)
                if structured_data:
                    st.session_state.raw_data = structured_data
                    st.session_state.step = "edit" # On passe à l'étape suivante
                    st.rerun() # On force le rechargement de la page pour afficher l'étape 2
                else: st.error("L'IA n'a pas pu structurer les données.")
            else: st.error("Impossible d'extraire le texte du PDF.")
            os.remove(temp_pdf_path)

# =======================================================
# ÉTAPE 2 : AJUSTEMENTS SIMPLES
# =======================================================
elif st.session_state.step == "edit":
    st.header("2. Appliquez vos ajustements")
    
    st.info("Voici les données brutes extraites par l'IA.")
    # On affiche un tableau simple, NON-ÉDITABLE.
    df_raw = pd.DataFrame(st.session_state.raw_data.get('lignes_articles', []))
    st.table(df_raw.style.format({"prix_unitaire_ht": "{:.2f} €", "total_ligne_ht": "{:.2f} €"}))

    st.markdown("---")

    # On utilise un formulaire pour regrouper les inputs et n'avoir qu'un seul bouton
    with st.form("adjustment_form"):
        st.subheader("Ajustements")
        
        margin_percentage = st.number_input("Marge sur fournitures (%)", min_value=0, step=5, value=30)
        
        st.markdown("##### Ajoutez votre main d'œuvre")
        mo_desc = st.text_input("Description", "Main d'œuvre - Prestation Globale")
        mo_hours = st.number_input("Quantité (heures)", min_value=0.0, step=0.5, value=8.0)
        mo_rate = st.number_input("Taux horaire (€/h)", min_value=0.0, step=5.0, value=50.0)
        
        # Le seul bouton pour valider les ajustements
        submitted = st.form_submit_button("Calculer le Devis Final")

    if submitted:
        # On calcule les nouvelles données
        final_lines = []
        # 1. On applique la marge sur les lignes originales
        for line in st.session_state.raw_data.get('lignes_articles', []):
            new_line = line.copy()
            try:
                original_price = float(line.get('prix_unitaire_ht', 0))
                new_price = original_price * (1 + margin_percentage / 100)
                new_line['prix_unitaire_ht'] = new_price
                new_line['total_ligne_ht'] = new_price * float(line.get('quantite', 1))
                final_lines.append(new_line)
            except:
                final_lines.append(line) # En cas d'erreur, on garde la ligne originale
        
        # 2. On ajoute la ligne de main d'œuvre
        if mo_desc and mo_hours > 0 and mo_rate > 0:
            mo_line = {
                "description": mo_desc,
                "quantite": mo_hours,
                "prix_unitaire_ht": mo_rate,
                "total_ligne_ht": mo_hours * mo_rate
            }
            final_lines.append(mo_line)

        # On sauvegarde le résultat final dans la mémoire de session
        st.session_state.final_quote_data = {
            "lignes_articles": final_lines,
            "nom_client": st.session_state.raw_data.get('nom_client'),
            "date_devis": st.session_state.raw_data.get('date_devis'),
            "numero_devis": st.session_state.raw_data.get('numero_devis'),
        }
        st.session_state.step = "preview" # On passe à l'étape finale
        st.rerun()

    # Bouton pour tout recommencer
    if st.button("Recommencer (importer un autre PDF et tout refaire)"):
        restart_process()
        st.rerun()

# =======================================================
# ÉTAPE 3 : APERÇU ET GÉNÉRATION
# =======================================================
elif st.session_state.step == "preview":
    st.header("3. Aperçu et Génération")

    st.success("Votre devis est prêt à être généré !")

    # Affichage du tableau final pour vérification
    df_final = pd.DataFrame(st.session_state.final_quote_data.get('lignes_articles', []))
    st.table(df_final.style.format({"prix_unitaire_ht": "{:.2f} €", "total_ligne_ht": "{:.2f} €"}))

    # Calcul et affichage des totaux
    total_ht = df_final['total_ligne_ht'].sum()
    total_ttc = total_ht * 1.20
    col_total1, col_total2 = st.columns(2)
    col_total1.metric("TOTAL HT", f"{total_ht:.2f} €")
    col_total2.metric("TOTAL TTC", f"{total_ttc:.2f} €")

    # Bouton de génération
    if st.button("Générer et Télécharger le PDF", type="primary"):
        with st.spinner("Création du document..."):
            # On complète les données avec les totaux calculés
            data_to_generate = st.session_state.final_quote_data.copy()
            data_to_generate['total_ht'] = total_ht
            data_to_generate['total_ttc'] = total_ttc
            
            output_dir = "output_devis"; os.makedirs(output_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"Devis_Client_{timestamp}.pdf"
            output_pdf_path = os.path.join(output_dir, output_filename)

            success = generate_pdf(data_to_generate, output_pdf_path)

            if success:
                st.success("Devis généré !")
                with open(output_pdf_path, "rb") as pdf_file:
                    st.download_button(
                        label="Télécharger le PDF",
                        data=pdf_file,
                        file_name=output_filename,
                        mime="application/pdf"
                    )
            else: st.error("Erreur lors de la création du PDF.")
            
    # Bouton pour recommencer
    if st.button("Faire un autre devis (cela recommence tout)"):
        restart_process()
        st.rerun()