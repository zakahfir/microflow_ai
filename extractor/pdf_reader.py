# microflow_ai/extractor/pdf_reader.py

import os
import json
import fitz
import streamlit as st

# On importe les deux clients, même si on n'en utilise qu'un à la fois.
from huggingface_hub import InferenceClient
import requests # CET IMPORT EST IMPORTANT POUR LA GESTION D'ERREURS

# --- Configuration ---
# ... (le reste du code de configuration est bon)
LLM_PROVIDER = "none"
HF_TOKEN = None

try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        LLM_PROVIDER = "huggingface"
        print("INFO: Clé API Hugging Face trouvée. Utilisation de l'API en ligne.")
    else:
        LLM_PROVIDER = "none"
        st.error("ERREUR DE CONFIGURATION : Clé API Hugging Face non trouvée.")
except (FileNotFoundError, KeyError):
    LLM_PROVIDER = "local_placeholder" 
    print("INFO: Lancement en local (simulation).")

# NOUVEL IDENTIFIANT DE MODÈLE : google/gemma-7b-it
HF_MODEL_ID = "google/gemma-7b-it"

# --- La Fonction d'Extraction de Texte (inchangée) ---
def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"ERREUR: Fichier PDF non trouvé : {pdf_path}")
        return None
    try:
        document = fitz.open(pdf_path)
        full_text = ""
        for page in document:
            full_text += page.get_text("text", sort=True)
        document.close()
        print("SUCCÈS: Texte brut extrait du PDF.")
        return full_text
    except Exception as e:
        print(f"ERREUR lors de la lecture du PDF : {e}")
        return None

# --- La Fonction de Structuration (Version "Anti-Crash") ---
def structure_data_with_llm(text_content):
    if LLM_PROVIDER != "huggingface":
        st.error(f"Le fournisseur d'IA configuré ({LLM_PROVIDER}) n'est pas supporté.")
        return None

    print(f"INFO: Appel à l'API Hugging Face (modèle: {HF_MODEL_ID})...")
    
    # On garde notre excellent prompt "One-Shot"
    prompt = f"""
    Tu es un assistant expert en extraction de données. Ta mission est d'analyser un texte de devis et de retourner un objet JSON valide et complet.

    RÈGLES STRICTES :
    1. Tu dois retourner UNIQUEMENT l'objet JSON. Pas de texte avant, pas de texte après, pas de ```json.
    2. Toutes les valeurs numériques (quantite, prix, total) doivent être des nombres (float ou int), pas des chaînes de caractères.
    3. Si une information est introuvable, sa valeur doit être `null`.

    EXEMPLE DE SORTIE ATTENDUE :
    {{
      "nom_client": "M. Jean Dupont", "date_devis": "25/08/2025", "numero_devis": "DEV-2025-042",
      "total_ht": 4122.00, "total_ttc": 4946.40,
      "lignes_articles": [
        {{"description": "Fourniture et pose chaudière Frisquet", "quantite": 1, "prix_unitaire_ht": 3500.00, "total_ligne_ht": 3500.00}}
      ]
    }}

    MAINTENANT, ANALYSE LE TEXTE SUIVANT ET PRODUIS LE JSON CORRESPONDANT :

    TEXTE À ANALYSER:
    ---
    {text_content}
    ---
    """
    
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {
        "inputs": prompt,
        "parameters": {"max_new_tokens": 4096, "temperature": 0.1, "return_full_text": False}
    }

    try:
        response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=60) # Timeout augmenté à 60s
        response.raise_for_status()

        response_data = response.json()
        
        # --- NOUVELLE LOGIQUE "ANTI-CRASH" ---
        # 1. On vérifie que la réponse n'est pas vide et est bien une liste
        if not response_data or not isinstance(response_data, list):
            print(f"ERREUR: Réponse inattendue de l'API (pas une liste ou vide): {response_data}")
            st.error("Le service IA a retourné une réponse vide ou mal formée.")
            return None

        # 2. On accède au premier élément en toute sécurité
        generated_text = response_data[0].get('generated_text', '')

        if not generated_text:
            print(f"ERREUR: L'IA n'a rien généré. Réponse complète : {response_data}")
            st.error("Le service IA n'a pas généré de texte.")
            return None

        # 3. On nettoie et on parse le JSON
        print("SUCCÈS: Réponse reçue de l'API.")
        if generated_text.strip().startswith("```json"):
            cleaned_text = generated_text.strip()[7:-4]
        elif generated_text.strip().startswith("{"):
            cleaned_text = generated_text.strip()
        else:
            start_index = generated_text.find('{')
            end_index = generated_text.rfind('}') + 1
            if start_index != -1 and end_index != -1:
                cleaned_text = generated_text[start_index:end_index]
            else:
                raise ValueError("Aucun JSON trouvé dans la réponse de l'IA.")
        
        return json.loads(cleaned_text)

    except requests.exceptions.RequestException as e:
        print(f"ERREUR (Hugging Face): {e}")
        st.error(f"Erreur de communication avec le service IA. Détails : {e}")
        return None
    except (ValueError, KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"ERREUR: La réponse de l'IA n'était pas un JSON valide. {e}")
        st.error("Le service IA a retourné une réponse inattendue. Veuillez réessayer.")
        print("Réponse brute de l'API:", response.text if 'response' in locals() else "Pas de réponse capturée")
        return None