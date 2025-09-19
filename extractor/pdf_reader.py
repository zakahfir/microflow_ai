# microflow_ai/extractor/pdf_reader.py

import os
import json
import fitz
import streamlit as st
from huggingface_hub import InferenceClient

# --- Configuration ---
LLM_PROVIDER = "none"
HF_TOKEN = None

# Logique de détection de l'environnement
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

# NOUVEL IDENTIFIANT DE MODÈLE : Qwen 3 Next 80B A3B Thinking
HF_MODEL_ID = "Qwen/Qwen3-Next-80B-A3B-Thinking"

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

# --- La Fonction de Structuration (avec InferenceClient et le bon modèle) ---
def structure_data_with_llm(text_content):
    if LLM_PROVIDER != "huggingface":
        st.error(f"Le fournisseur d'IA configuré ({LLM_PROVIDER}) n'est pas supporté pour le moment.")
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
    
    messages = [{"role": "user", "content": prompt}]

    try:
        client = InferenceClient(token=HF_TOKEN)

        full_response_text = ""
        for token in client.chat_completion(
            messages=messages,
            model=HF_MODEL_ID,
            max_tokens=4096, # On garde une grande fenêtre de réponse
            stream=True,
            temperature=0.1
        ):
            if token.choices[0].delta.content is not None:
                full_response_text += token.choices[0].delta.content
        
        print("SUCCÈS: Réponse complète reçue de l'API.")
        
        # Le nettoyage pour enlever les ```json ... ``` est toujours une bonne pratique
        if full_response_text.strip().startswith("```json"):
            cleaned_text = full_response_text.strip()[7:-4]
        elif full_response_text.strip().startswith("{"):
            cleaned_text = full_text
        else: # Si l'IA ajoute du texte avant le JSON
            start_index = full_response_text.find('{')
            end_index = full_response_text.rfind('}') + 1
            if start_index != -1 and end_index != -1:
                cleaned_text = full_response_text[start_index:end_index]
            else:
                cleaned_text = full_response_text
        
        return json.loads(cleaned_text)

    except Exception as e:
        print(f"ERREUR (Hugging Face): L'appel à l'API a échoué. {e}")
        st.error(f"Erreur de communication avec le service IA. Détails : {e}")
        print("Réponse brute de l'API (si disponible):", full_response_text if 'full_response_text' in locals() else "Pas de réponse capturée")
        return None