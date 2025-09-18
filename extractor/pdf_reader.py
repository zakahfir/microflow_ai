# microflow_ai/extractor/pdf_reader.py
import fitz  # PyMuPDF
import os
import ollama
import json

LLM_MODEL = "qwen3:8b"  # Modèle LLM à utiliser

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
    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{'role': 'user', 'content': prompt}],
            format="json"
        )
        print("SUCCÈS: Réponse structurée reçue du LLM.")
        return json.loads(response['message']['content'])
    except Exception as e:
        print(f"ERREUR: Problème de communication avec Ollama : {e}")
        return None