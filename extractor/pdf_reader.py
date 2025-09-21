# microflow_ai/extractor/pdf_reader.py
# Version "Réinitialisation Totale"

import os
import json
import fitz
import streamlit as st
import requests # IMPORTATION CRUCIALE

# --- Configuration ---
LLM_PROVIDER = "none"
HF_TOKEN = None
HF_MODEL_ID = "google/gemma-7b-it" # On utilise Gemma, stable et ouvert
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"

# Logique de détection
try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        LLM_PROVIDER = "huggingface"
        print("INFO: Clé API HF trouvée. Mode en ligne activé.")
    else:
        LLM_PROVIDER = "none"
except (FileNotFoundError, KeyError):
    LLM_PROVIDER = "local_placeholder"
    print("INFO: Lancement local (simulation).")

# --- Fonctions ---
def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"ERREUR: Fichier non trouvé : {pdf_path}")
        return None
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text("text", sort=True) for page in doc)
        doc.close()
        print("SUCCÈS: Texte brut extrait.")
        return text
    except Exception as e:
        print(f"ERREUR LECTURE PDF: {e}")
        return None

def structure_data_with_llm(text_content):
    if LLM_PROVIDER != "huggingface":
        st.error(f"Fournisseur IA non configuré ({LLM_PROVIDER}).")
        return None

    print(f"INFO: Appel API HF (Modèle: {HF_MODEL_ID})")
    
    prompt = f"""
    Tu es un expert en extraction de données de devis BTP. Analyse le texte suivant et retourne UNIQUEMENT un objet JSON valide.

    Règles:
    1. Le JSON doit contenir : "nom_client", "date_devis", "numero_devis", "total_ht", "total_ttc", "lignes_articles" (une liste d'objets).
    2. Chaque objet dans "lignes_articles" doit avoir : "description", "quantite" (nombre), "prix_unitaire_ht" (nombre), "total_ligne_ht" (nombre).
    3. Si une info est introuvable, utilise la valeur `null`.
    4. Extrais les nombres uniquement (ex: pour "8.50 €", extrais 8.50).

    TEXTE À ANALYSER:
    ---
    {text_content}
    ---
    """
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 2048, "temperature": 0.1, "return_full_text": False}
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        
        if not response_data or not isinstance(response_data, list):
            raise ValueError(f"Réponse API inattendue (pas une liste): {response_data}")

        generated_text = response_data[0].get('generated_text', '')
        if not generated_text:
            raise ValueError("L'IA a retourné un texte généré vide.")
        
        start_index = generated_text.find('{')
        end_index = generated_text.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            raise ValueError("Aucun JSON trouvé dans la réponse.")
            
        json_string = generated_text[start_index:end_index]
        print("SUCCÈS: Réponse JSON extraite.")
        return json.loads(json_string)

    except requests.exceptions.RequestException as e:
        print(f"ERREUR (Requests): {e}")
        st.error(f"Erreur de communication avec le service IA.")
        return None
    except (ValueError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"ERREUR (Parsing): {e}")
        st.error("La réponse de l'IA était mal formée.")
        print("Réponse brute:", response.text if 'response' in locals() else "N/A")
        return None