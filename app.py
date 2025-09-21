# =======================================================
# microflow_ai/app.py
# VERSION 1.0 - MVP PROPRE ET FONCTIONNEL
# =======================================================

import streamlit as st
import os
import json
from datetime import datetime
from extractor.pdf_reader import extract_text_from_pdf, structure_data_with_llm
from generator.pdf_generator import generate_pdf
import pandas as pd

# --- Configuration de la Page ---
st.set_page_config(
    page_title="MicroFlow.AI - Assistant Devis",
    page_icon="🤖",
    layout="wide"
)

# --- Initialisation de la Mémoire de Session (Session State) ---
def initialize_state():
    if 'step' not in st.session_state:
        st.session_state.step = "upload"
    if 'raw_data' not in st.session_state:
        st.session_state.raw_data = None
    if 'final_quote_data' not in st.session_state:
        st.session_state.final_quote_data = None
    if 'processed_file_name' not in st.session_state:
        st.session_state.processed_file_name = None

initialize_state()

# --- Fonctions Utilitaires ---
def restart_process():
    """Réinitialise tout le processus pour un nouveau devis."""
    st.session_state.step = "upload"
    st.session_state.raw_data = None
    st.session_state.final_quote_data = None
    st.session_state.processed_file_name = None
    # Pas besoin de st.rerun() ici, le bouton qui l'appelle le fera.

# --- Interface Utilisateur ---
st.title("🤖 MicroFlow.AI")
st.subheader("Transformez vos devis fournisseurs en devis clients, simplement.")

# =======================================================
# ÉTAPE 1 : UPLOAD
# =======================================================
if st.session_state.step == "upload":
    st.header("1. Importez votre devis fournisseur")
    uploaded_file = st.file_uploader("Choisissez un fichier PDF", type="pdf", label_visibility="collapsed")

    if uploaded_file is not None:
        with st.spinner("Analyse du PDF par l'IA... (cela peut prendre jusqu'à 2 minutes, merci de patienter)"):
            temp_dir = "temp_data"; os.makedirs(temp_dir, exist_ok=True)
            temp_pdf_path = os.path.join(temp_dir, uploaded_file.name)
            with open(temp_pdf_path, "wb") as f: f.write(uploaded_file.getbuffer())
            
            raw_text = extract_text_from_pdf(temp_pdf_path)
            if raw_text:
                structured_data = structure_data_with_llm(raw_text)
                if structured_data:
                    st.session_state.raw_data = structured_data
                    st.session_state.step = "edit"
                    st.session_state.processed_file_name = uploaded_file.name
                    st.rerun()
                else: st.error("L'IA n'a pas pu structurer les données. Veuillez réessayer avec un autre document.")
            else: st.error("Impossible d'extraire le texte de ce PDF.")
            os.remove(temp_pdf_path)

# =======================================================
# ÉTAPE 2 : AJUSTEMENTS SIMPLES
# =======================================================
elif st.session_state.step == "edit":
    st.header("2. Appliquez vos ajustements")
    
    st.info("Voici les données extraites. Vous pouvez maintenant appliquer votre marge et ajouter votre main d'œuvre.")
    df_raw = pd.DataFrame(st.session_state.raw_data.get('lignes_articles', []))
    st.table(df_raw.style.format(na_rep="-", formatter={"prix_unitaire_ht": "{:.2f} €", "total_ligne_ht": "{:.2f} €"}))

    st.markdown("---")

    with st.form("adjustment_form"):
        st.subheader("Vos Ajustements")
        margin_percentage = st.number_input("Marge sur fournitures (%)", min_value=0, step=5, value=30)
        st.markdown("##### Ajoutez votre main d'œuvre")
        mo_desc = st.text_input("Description", "Main d'œuvre - Prestation Globale")
        mo_hours = st.number_input("Quantité (heures)", min_value=0.0, step=0.5, value=8.0)
        mo_rate = st.number_input("Taux horaire (€/h)", min_value=0.0, step=5.0, value=50.0)
        
        submitted = st.form_submit_button("Calculer et Prévisualiser le Devis Final")

    if submitted:
        final_lines = []
        for line in st.session_state.raw_data.get('lignes_articles', []):
            new_line = line.copy()
            try:
                original_price = float(line.get('prix_unitaire_ht', 0))
                new_price = original_price * (1 + margin_percentage / 100)
                new_line['prix_unitaire_ht'] = new_price
                new_line['total_ligne_ht'] = new_price * float(line.get('quantite', 1))
                final_lines.append(new_line)
            except:
                final_lines.append(line)
        
        if mo_desc and mo_hours > 0 and mo_rate > 0:
            mo_line = {"description": mo_desc, "quantite": mo_hours, "prix_unitaire_ht": mo_rate, "total_ligne_ht": mo_hours * mo_rate}
            final_lines.append(mo_line)

        st.session_state.final_quote_data = {
            "lignes_articles": final_lines,
            "nom_client": st.session_state.raw_data.get('nom_client'),
            "date_devis": st.session_state.raw_data.get('date_devis'),
            "numero_devis": st.session_state.raw_data.get('numero_devis'),
        }
        st.session_state.step = "preview"
        st.rerun()

    if st.button("Recommencer (importer un autre PDF)"):
        restart_process()
        st.rerun()

# =======================================================
# ÉTAPE 3 : APERÇU ET GÉNÉRATION
# =======================================================
elif st.session_state.step == "preview":
    st.header("3. Aperçu et Génération du PDF")
    st.success("Votre devis est prêt ! Vérifiez les informations ci-dessous avant de générer le PDF.")

    df_final = pd.DataFrame(st.session_state.final_quote_data.get('lignes_articles', []))
    st.table(df_final.style.format(na_rep="-", formatter={"prix_unitaire_ht": "{:.2f} €", "total_ligne_ht": "{:.2f} €"}))

    total_ht = df_final['total_ligne_ht'].sum()
    total_ttc = total_ht * 1.20
    col_total1, col_total2 = st.columns(2)
    col_total1.metric("TOTAL HT", f"{total_ht:.2f} €")
    col_total2.metric("TOTAL TTC", f"{total_ttc:.2f} €")

    # On regroupe les boutons d'action dans des colonnes
    col_btn1, col_btn2, col_btn3 = st.columns([1,1,2])
    
    with col_btn1:
        if st.button("Modifier les Ajustements"):
            st.session_state.step = "edit"
            st.rerun()
            
    with col_btn2:
        if st.button("Recommencer de Zéro"):
            restart_process()
            st.rerun()

    # Le bouton principal, pour générer le PDF
    if st.button("Générer et Télécharger le PDF", type="primary"):
        with st.spinner("Création du document..."):
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
                        label="Cliquez ici pour télécharger",
                        data=pdf_file,
                        file_name=output_filename,
                        mime="application/pdf"
                    )
            else: 
                st.error("Erreur lors de la création du PDF.")