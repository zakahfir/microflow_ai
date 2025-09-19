# microflow_ai/extractor/pdf_reader.py

import os
import json
import fitz
import streamlit as st

# On importe le client officiel, plus fiable
from huggingface_hub import InferenceClient

# --- Configuration ---
LLM_PROVIDER = "none"
HF_TOKEN = None

# Logique de détection de l'environnement (Cloud vs Local)
try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        LLM_PROVIDER = "huggingface"
        print("INFO: Clé API Hugging Face trouvée. L'application utilisera l'API en ligne.")
    else:
        # Si on est dans Streamlit mais sans secret, on ne peut rien faire.
        LLM_PROVIDER = "none"
        st.error("ERREUR DE CONFIGURATION : Clé API Hugging Face non trouvée dans les secrets Streamlit.")
except (FileNotFoundError, KeyError):
    # Si 'st.secrets' n'existe pas, on est en local. On utilisera Ollama.
    LLM_PROVIDER = "ollama"
    print("INFO: Lancement en local. L'application utilisera Ollama (à implémenter).")

# Modèle cible sur l'API Hugging Face
HF_MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"

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

# --- La Fonction de Structuration (Version finale avec InferenceClient) ---
def structure_data_with_llm(text_content):
    if LLM_PROVIDER != "huggingface":
        # Pour l'instant, on se concentre sur la version en ligne qui était notre problème.
        # On pourrait rajouter la logique Ollama ici plus tard si besoin.
        st.error(f"Le fournisseur d'IA configuré ({LLM_PROVIDER}) n'est pas supporté pour le moment.")
        return None

    print(f"INFO: Appel à l'API Hugging Face (modèle: {HF_MODEL_ID})...")
    
    # Le nouveau prompt amélioré
    prompt = f"""
Tu es un assistant expert en extraction de données. Ta mission est d'analyser un texte de devis et de retourner un objet JSON valide et complet.

RÈGLES STRICTES :
1. Tu dois retourner UNIQUEMENT l'objet JSON. Pas de texte avant, pas de texte après, pas de ```json.
2. Toutes les valeurs numériques (quantite, prix, total) doivent être des nombres (float ou int), pas des chaînes de caractères.
3. Si une information est introuvable, sa valeur doit être `null`.

EXEMPLE DE SORTIE ATTENDUE :
{{
  "nom_client": "M. Jean Dupont",
  "date_devis": "25/08/2025",
  "numero_devis": "DEV-2025-042",
  "total_ht": 4122.00,
  "total_ttc": 4946.40,
  "lignes_articles": [
    {{
      "description": "Fourniture et pose chaudière Frisquet",
      "quantite": 1,
      "prix_unitaire_ht": 3500.00,
      "total_ligne_ht": 3500.00
    }},
    {{
      "description": "Tube cuivre diam. 14 (mètre)",
      "quantite": 12,
      "prix_unitaire_ht": 8.50,
      "total_ligne_ht": 102.00
    }}
  ]
}}

MAINTENANT, ANALYSE LE TEXTE SUIVANT ET PRODUIS LE JSON CORRESPONDANT :
    TEXTE À ANALYSER:
    ---
    {text_content}
    ---
    """
    final_prompt = prompt_template.format(text_content=text_content)
    
    messages = [{"role": "user", "content": final_prompt}]

    try:
        # On initialise le client avec notre token sécurisé
        client = InferenceClient(token=HF_TOKEN)

        # On utilise la méthode 'chat_completion' qui est la bonne pour ce modèle
        full_response_text = ""
        for token in client.chat_completion(
            messages=messages,
            model=HF_MODEL_ID,
            max_tokens=4096, # Assez de place pour un JSON complexe
            stream=True,
            temperature=0.1,
            "return_full_text": False
        ):
            if token.choices[0].delta.content is not None:
                full_response_text += token.choices[0].delta.content
        
        print("SUCCÈS: Réponse complète reçue de l'API.")
        # Le LLM peut parfois ajouter des ```json ... ``` autour de sa réponse.
        # On nettoie ça pour être sûr d'avoir un JSON pur.
        if full_response_text.strip().startswith("```json"):
            full_response_text = full_response_text.strip()[7:-4]

        return json.loads(full_response_text)

    except Exception as e:
        print(f"ERREUR (Hugging Face): L'appel à l'API a échoué. {e}")
        st.error(f"Erreur de communication avec le service IA. Détails : {e}")
        return None