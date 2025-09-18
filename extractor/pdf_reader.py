# microflow_ai/extractor/pdf_reader.py
import fitz  # PyMuPDF
import os
import ollama
import requests
import json
import streamlit as st # Nécessaire pour accéder aux secrets

# --- Configuration ---
LLM_PROVIDER = "none" # Par défaut, aucun fournisseur n'est configuré

# On essaie de récupérer la clé API depuis les secrets de Streamlit.
# Cette partie ne fonctionnera que lorsque le code tourne sur Streamlit Cloud.
try:
    if "HUGGINGFACE_API_KEY" in st.secrets:
        HF_TOKEN = st.secrets["HUGGINGFACE_API_KEY"]
        LLM_PROVIDER = "huggingface"
        print("INFO: Clé API Hugging Face trouvée. L'application utilisera l'API en ligne.")
    else:
        LLM_PROVIDER = "ollama"
        print("INFO: Pas de clé API Hugging Face détectée. L'application utilisera Ollama en local.")
except (FileNotFoundError, KeyError):
    # Cette erreur se produit quand on lance le script en local (pas dans Streamlit)
    # et que 'st.secrets' n'existe pas. C'est normal.
    LLM_PROVIDER = "ollama"
    print("INFO: Lancement en local. L'application utilisera Ollama.")


# URL de l'API Hugging Face et nom du modèle Ollama
HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
OLLAMA_MODEL = "qwen3:8b" 

def extract_text_from_pdf(pdf_path):
    if not os.path.exists(pdf_path):
        print(f"ERREUR: Fichier non trouvé : {pdf_path}")
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

def structure_data_with_llm(text_content):
    print("INFO: Envoi du texte au LLM pour structuration...")
    prompt = f"""
    Tu es un assistant expert en extraction de données à partir de devis du BTP.
    Analyse le texte brut suivant. Ta mission est de retourner UNIQUEMENT un objet JSON.

    Le JSON doit contenir les clés suivantes :
    - "nom_client": Le nom de l'entreprise ou de la personne à qui le devis est adressé.
    - "date_devis": La date d'émission du devis.
    - "numero_devis": Le numéro d'identification unique du devis.
    - "total_ht": Le montant total Hors Taxes (doit être un nombre).
    - "total_ttc": Le montant total Toutes Taxes Comprises (doit être un nombre).
    - "lignes_articles": Une liste d'objets.

    Chaque objet dans la liste "lignes_articles" doit contenir :
    - "description": La description de l'article.
    - "quantite": La quantité (doit être un nombre).
    - "prix_unitaire_ht": Le prix unitaire HT (doit être un nombre).
    - "total_ligne_ht": Le prix total de la ligne HT (doit être un nombre).

    Règles importantes :
    1. Si une information n'est pas trouvée, utilise la valeur `null` (pas la chaîne "null").
    2. Extrais les nombres uniquement (ex: pour "8.50 €", extrais `8.50`).

    Voici le texte à analyser :
    ---
    {text_content}
    ---
    """
    # C'est ici que notre code devient "intelligent"
    if LLM_PROVIDER == "huggingface":
        print("INFO: Appel à l'API Hugging Face (mode en ligne)...")
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {"max_new_tokens": 1024, "temperature": 0.1, "return_full_text": False}
        }
        try:
            response = requests.post(HF_API_URL, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            generated_json_text = response.json()[0]['generated_text']
            print("SUCCÈS: Réponse reçue de Hugging Face.")
            return json.loads(generated_json_text)
        except Exception as e:
            print(f"ERREUR (Hugging Face): {e}")
            st.error(f"Erreur de communication avec le service IA en ligne. Détails : {e}")
            return None

    elif LLM_PROVIDER == "ollama":
        print("INFO: Appel à Ollama (mode local)...")
        try:
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                format="json"
            )
            print("SUCCÈS: Réponse reçue d'Ollama.")
            return json.loads(response['message']['content'])
        except Exception as e:
            print(f"ERREUR (Ollama): {e}")
            st.error(f"Erreur de communication avec l'IA locale. Ollama est-il bien lancé ? Détails : {e}")
            return None

    else:
        print("ERREUR: Aucun fournisseur LLM n'est configuré.")
        st.error("Le service d'intelligence artificielle n'est pas configuré.")
        return None