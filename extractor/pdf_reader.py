# microflow_ai/extractor/pdf_reader.py
# VERSION FINALE "CHAT COMPLETION" - LA BONNE MÉTHODE

import os
import json
import fitz
import streamlit as st
from huggingface_hub import InferenceClient

# --- Configuration ---
HF_TOKEN = None
MODEL_ID = "Qwen/Qwen3-Next-80B-A3B-Instruct"  # Modèle puissant pour les tâches de chat

try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        print("INFO: Clé API HF trouvée. Mode en ligne activé.")
    else:
        st.error("ERREUR DE CONFIGURATION : Clé API Hugging Face non trouvée.")
except (FileNotFoundError, KeyError):
    print("INFO: Lancement en local (le service IA en ligne ne fonctionnera pas).")

# --- Fonctions ---
def extract_text_from_pdf(pdf_path):
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
    if not HF_TOKEN:
        st.error("Le service IA n'est pas configuré (clé API manquante).")
        return None

    print(f"INFO: Appel API HF avec la tâche 'chat' (Modèle: {MODEL_ID})...")
    
    # Notre prompt est déjà bien formaté pour une conversation, mais on s'assure qu'il est propre.
    # On enlève les balises <|system|>, etc. que l'on avait mises pour text-generation.
    prompt = f"""
    Tu es un assistant expert en extraction de données. Analyse le texte de devis suivant et retourne UNIQUEMENT un objet JSON valide et complet.

    Règles:
    1. Le JSON doit contenir : "nom_client", "date_devis", "numero_devis", "total_ht", "total_ttc", "lignes_articles" (une liste d'objets).
    2. Chaque objet dans "lignes_articles" doit avoir : "description", "quantite" (nombre), "prix_unitaire_ht" (nombre), "total_ligne_ht" (nombre).
    3. Si une info est introuvable, utilise la valeur `null`.
    4. Extrais les nombres uniquement (ex: pour "8.50 €", extrais 8.50).

    TEXTE À ANALYSER:
    ---
    {text_content[:4000]} 
    ---
    """
    
    # On formate la requête pour la tâche 'chat_completion'
    messages = [{"role": "user", "content": prompt}]
    
    try:
        client = InferenceClient(token=HF_TOKEN, timeout=180) # Timeout plus long pour les gros modèles

        # ON UTILISE LA BONNE MÉTHODE : chat_completion
        response = client.chat_completion(
            messages=messages,
            model=MODEL_ID,
            max_tokens=2048,
            temperature=0.1,
            response_format={"type": "json_object"}, 
        )
        
        # Avec chat_completion, la réponse n'est pas un stream par défaut et est directement accessible
        generated_text = response.choices[0].message.content
        
        print("SUCCÈS: Réponse reçue de l'API via chat_completion.")
        
        # Le 'response_format' devrait nous garantir un JSON, mais on vérifie quand même.
        return json.loads(generated_text)

    except Exception as e:
        print(f"ERREUR (Hugging Face): {e}")
        st.error(f"Erreur de communication avec le service IA. Détails de l'erreur ci-dessous.")
        st.exception(e) # Affiche l'erreur complète dans l'interface Streamlit pour le débogage
        return None