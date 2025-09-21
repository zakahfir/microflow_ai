# microflow_ai/extractor/pdf_reader.py
# VERSION FINALE CORRIGÉE - 26/08/2025

import os
import json
import fitz
import streamlit as st
import requests  # Importation essentielle

# --- Configuration ---
LLM_PROVIDER = "none"
HF_TOKEN = None

# On utilise un modèle léger et fiable pour nos tests de connexion
HF_MODEL_ID = "google/gemma-2b-it" 
HF_API_URL = f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}"

# Logique de détection pour récupérer la clé API
try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        LLM_PROVIDER = "huggingface"
        print("INFO: Clé API HF trouvée. Mode en ligne activé.")
    else:
        LLM_PROVIDER = "none"
        # On ne met pas d'erreur ici pour permettre au reste de l'app de se charger
except (FileNotFoundError, KeyError):
    LLM_PROVIDER = "local_placeholder"
    print("INFO: Lancement en local (simulation, le service IA ne sera pas appelé).")

# --- Fonctions ---

def extract_text_from_pdf(pdf_path):
    """Extrait le texte brut d'un fichier PDF."""
    if not os.path.exists(pdf_path):
        print(f"ERREUR: Fichier non trouvé : {pdf_path}")
        return None
    try:
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text("text", sort=True) for page in doc)
        doc.close()
        print("SUCCÈS: Texte brut extrait du PDF.")
        return text
    except Exception as e:
        print(f"ERREUR LECTURE PDF: {e}")
        return None

def structure_data_with_llm(text_content):
    """Appelle l'API Hugging Face pour structurer le texte en JSON."""
    if LLM_PROVIDER != "huggingface" or not HF_TOKEN:
        st.error("Le service IA n'est pas configuré. Veuillez ajouter la clé HUGGINGFACE_API_KEY dans les secrets Streamlit.")
        return None

    print(f"INFO: Appel API HF (Modèle: {HF_MODEL_ID})")
    
    # Prompt détaillé et robuste
    prompt = f"""
    Tu es un assistant expert en extraction de données. Ta mission est d'analyser un texte de devis et de retourner UNIQUEMENT un objet JSON valide et complet.

    RÈGLES STRICTES :
    1. Le JSON doit contenir : "nom_client", "date_devis", "numero_devis", "total_ht", "total_ttc", et "lignes_articles" (une liste d'objets).
    2. Chaque objet dans "lignes_articles" doit avoir : "description", "quantite" (nombre), "prix_unitaire_ht" (nombre), "total_ligne_ht" (nombre).
    3. Si une information est introuvable, utilise la valeur `null`.
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

    # Lignes de débogage pour vérifier les informations avant l'envoi
    print(f"DEBUG: Appel de l'URL : {HF_API_URL}")
    print(f"DEBUG: Clé API utilisée (derniers 4 caractères) : ...{HF_TOKEN[-4:]}")

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=90)
        response.raise_for_status() # Lèvera une erreur pour les statuts 4xx/5xx
        response_data = response.json()
        
        # Logique de parsing de la réponse robuste
        if not response_data or not isinstance(response_data, list):
            raise ValueError(f"Réponse API inattendue (pas une liste ou vide): {response_data}")

        generated_text = response_data[0].get('generated_text', '')
        if not generated_text:
            raise ValueError("L'IA a retourné un texte généré vide.")
        
        # Logique de nettoyage du JSON
        start_index = generated_text.find('{')
        end_index = generated_text.rfind('}') + 1
        if start_index == -1 or end_index == 0:
            raise ValueError("Aucun JSON trouvé dans la réponse de l'IA.")
            
        json_string = generated_text[start_index:end_index]
        print("SUCCÈS: Réponse JSON extraite de l'API.")
        return json.loads(json_string)

    except requests.exceptions.HTTPError as http_err:
        print(f"ERREUR HTTP: {http_err}")
        st.error(f"Erreur du serveur distant ({http_err.response.status_code}). Le modèle est peut-être en cours de chargement. Veuillez réessayer dans une minute.")
        print("Réponse du serveur:", http_err.response.text)
        return None
    except requests.exceptions.RequestException as e:
        print(f"ERREUR de Connexion: {e}")
        st.error("Erreur de communication avec le service IA. Vérifiez votre connexion ou l'état du service Hugging Face.")
        return None
    except (ValueError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"ERREUR de Parsing de la Réponse: {e}")
        st.error("La réponse de l'IA était inattendue ou mal formée. L'équipe technique analyse le problème.")
        # Pour notre débogage, on affiche la réponse brute
        print("Réponse brute de l'API:", response.text if 'response' in locals() else "Pas de réponse capturée")
        return None