# =======================================================
# microflow_ai/app.py
# Application principale de MicroFlow.AI - MVP.
# =======================================================

import streamlit as st
import os
import json
from datetime import datetime
import csv
import time
from extractor.pdf_reader import extract_text_from_pdf, structure_data_with_llm
from generator.pdf_generator import generate_pdf
import pandas as pd

# --- Fichiers de Données ---
LEADS_FILE = "beta_users.csv"

# --- Configuration de la Page ---
st.set_page_config(
    page_title="MicroFlow.AI - Assistant Devis",
    page_icon="🤖",
    layout="centered" 
)

# --- Initialisation de la Mémoire de Session (Session State) ---
def initialize_state():
    if 'access_granted' not in st.session_state:
        st.session_state.access_granted = False
    if 'email_provided' not in st.session_state:
        st.session_state.email_provided = False
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
def initialize_state():
    if 'access_granted' not in st.session_state:
        st.session_state.access_granted = False
    # ... (les autres variables de session sont utiles pour le workflow interne)
    if 'step' not in st.session_state: st.session_state.step = "upload"
    # ...

def update_or_create_lead(name, email, profession):
    """
    Crée un nouveau lead s'il n'existe pas, ou met à jour
    les informations (prénom, métier) si l'email existe déjà et que les
    nouveaux champs sont remplis.
    """
    # Noms des colonnes pour notre fichier CSV
    columns = ['prenom', 'email', 'metier', 'date_inscription']
    
    # On vérifie si le fichier existe et n'est pas vide
    if os.path.isfile(LEADS_FILE) and os.path.getsize(LEADS_FILE) > 0:
        # Si oui, on le lit avec Pandas
        df = pd.read_csv(LEADS_FILE)
    else:
        # Si non, on crée un DataFrame (tableau) vide avec les bonnes colonnes
        df = pd.DataFrame(columns=columns)

    # On cherche si l'email existe déjà dans le DataFrame
    if email in df['email'].values:
        print(f"UTILISATEUR EXISTANT : {email}. Vérification des mises à jour...")
        # On trouve l'index (le numéro de ligne) de cet utilisateur
        index = df[df['email'] == email].index[0]
        
        # On met à jour le prénom SEULEMENT si un nouveau prénom a été fourni
        if name:
            df.loc[index, 'prenom'] = name
            print(f"-> Prénom mis à jour pour {email}.")
            
        # On met à jour le métier SEULEMENT si un nouveau métier a été fourni
        if profession:
            df.loc[index, 'metier'] = profession
            print(f"-> Métier mis à jour pour {email}.")
    else:
        # Si l'email n'existe pas, on crée une nouvelle ligne
        print(f"NOUVEL INSCRIT : {email}")
        new_lead = pd.DataFrame([{
            'prenom': name,
            'email': email,
            'metier': profession,
            'date_inscription': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }])
        df = pd.concat([df, new_lead], ignore_index=True)
    
    # Enfin, on sauvegarde le DataFrame mis à jour dans le fichier CSV, en écrasant l'ancien.
    # index=False signifie qu'on ne veut pas écrire le numéro de ligne de Pandas dans le fichier.
    df.to_csv(LEADS_FILE, index=False, encoding='utf-8')

def restart_process():
    """Réinitialise tout le processus pour un nouveau devis."""
    st.session_state.step = "upload"
    st.session_state.raw_data = None
    st.session_state.final_quote_data = None
    st.session_state.processed_file_name = None
    # Pas besoin de st.rerun() ici, le bouton qui l'appelle le fera.

# =======================================================
# PORTE D'ENTRÉE "INTELLIGENTE" - VERSION CORRIGÉE
# =======================================================
if not st.session_state.access_granted:
    st.title("🤖 Bienvenue sur MicroFlow.AI")
    st.header("L'outil qui transforme vos devis fournisseurs en devis clients.")
    st.markdown("---")
    
    st.info("""
    **Déjà inscrit ?** Entrez simplement votre email pour accéder à l'outil.
    \n**Première visite ?** Remplissez les champs pour rejoindre la bêta gratuite !
    """)

    # On crée un conteneur vide que l'on pourra faire disparaître
    form_placeholder = st.empty()

    # On met le formulaire À L'INTÉRIEUR du conteneur
    with form_placeholder.container():
        with st.form("access_form"):
            user_email = st.text_input("Votre Adresse Email* (obligatoire)")
            st.markdown("---")
            st.write("Informations pour les nouveaux utilisateurs (optionnel et modifiable plus tard) :")
            user_name = st.text_input("Votre Prénom")
            user_profession = st.text_input("Votre Métier (ex: Plombier)")
            
            submitted = st.form_submit_button("Accéder à l'Outil Gratuitement")

    # La logique de soumission reste EN DEHORS du 'with form_placeholder.container()'
    if submitted:
        if user_email and "@" in user_email:
            update_or_create_lead(user_name, user_email, user_profession)
            st.session_state.access_granted = True
            
            # On vide le conteneur pour faire disparaître le formulaire
            form_placeholder.empty()
            
            with st.spinner('Accès autorisé. Préparation de votre espace...'):
                time.sleep(2)
            st.success("Bienvenue ! L'application se charge.")
            time.sleep(1)
            st.rerun()
        else:
            st.error("Veuillez entrer une adresse email valide.")

# =======================================================
# APPLICATION PRINCIPALE
# =======================================================
else:
    # --- Conteneur Principal ---
    main_placeholder = st.container()

    # --- On remplit le conteneur en fonction de l'étape ---
    # ==================== ÉTAPE 1 : UPLOAD ====================
    if st.session_state.step == "upload":
        with main_placeholder:
            st.title("🤖 MicroFlow.AI")
            st.header("1. Importez votre devis fournisseur")
            uploaded_file = st.file_uploader(
                "Choisissez un fichier PDF", 
                type="pdf", 
                label_visibility="collapsed",
                key="file_uploader" # On lui donne un nom unique
            )
        st.info("Importez un fichier PDF de devis fournisseur. L'IA va analyser et structurer les données automatiquement.")

        if uploaded_file is not None:
            with st.spinner("Analyse du PDF par l'IA... (cela peut prendre jusqu'à 30 secondes, merci de patienter)"):
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

    # ==================== ÉTAPE 2 : AJUSTEMENTS ====================
    elif st.session_state.step == "edit":
        with main_placeholder:
            st.title("🤖 MicroFlow.AI")
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
            
            submitted = st.form_submit_button("Calculer et Prévisualiser le Devis Final (cliquez 2 fois si besoin)")
        if st.button("Recommencer (importer un autre PDF ou repartir de zéro)"):
            restart_process()
            st.rerun()
            
        if submitted:
            with st.spinner("Application de vos ajustements et recalcul des totaux..."):
                time.sleep(2) # On attend 2 secondes pour l'effet
            # On applique la marge et ajoute la main d'œuvre
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

    # ==================== ÉTAPE 3 : APERÇU ET GÉNÉRATION ====================
    elif st.session_state.step == "preview":
        with main_placeholder:
            st.title("🤖 MicroFlow.AI")
            st.header("3. Aperçu et Génération du PDF")

        st.success("Votre devis est prêt ! Vérifiez les informations ci-dessous avant de générer le PDF.")

        # Affichage du tableau final pour vérification
        df_final = pd.DataFrame(st.session_state.final_quote_data.get('lignes_articles', []))
        st.table(df_final.style.format(na_rep="-", formatter={"prix_unitaire_ht": "{:.2f} €", "total_ligne_ht": "{:.2f} €"}))

        # Calcul et affichage des totaux
        total_ht = df_final['total_ligne_ht'].sum()
        total_ttc = total_ht * 1.20
        col_total1, col_total2 = st.columns(2)
        col_total1.metric("TOTAL HT", f"{total_ht:.2f} €")
        col_total2.metric("TOTAL TTC", f"{total_ttc:.2f} €")

        st.markdown("---")

        # --- ACTIONS POSSIBLES ---
        
        col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 3])

        with col_btn1:
            # Bouton pour revenir à l'étape d'édition
            if st.button("Modifier les Ajustements"):
                st.session_state.step = "edit"
                # ON UTILISE st.rerun() ICI, car on veut explicitement changer de page
                st.rerun()
                
        with col_btn2:
            # Bouton pour tout recommencer
            if st.button("Recommencer de Zéro"):
                restart_process()
                # ON UTILISE st.rerun() ICI, car on veut explicitement tout réinitialiser
                st.rerun()

        # Le bouton principal de génération. Il est en dehors des colonnes pour être plus visible.
        if st.button("✅ Générer et Télécharger le PDF", type="primary"):
            with st.spinner("Création de votre document..."):
                # On prépare les données finales (identique à avant)
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
                        # On affiche le bouton de téléchargement directement
                        st.download_button(
                            label="Cliquez ici pour télécharger",
                            data=pdf_file,
                            file_name=output_filename,
                            mime="application/pdf"
                        )
                else: 
                    st.error("Erreur lors de la création du PDF.")