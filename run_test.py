# microflow_ai/run_test.py
# Objectif : Script de test manuel pour le workflow back-end.
# C'est notre "laboratoire". L'application finale pour l'utilisateur est app.py.

from extractor.pdf_reader import extract_text_from_pdf, structure_data_with_llm
from generator.pdf_generator import generate_pdf
import os
from datetime import datetime

# --- Configuration du Test ---
# MODIFIE CETTE LIGNE POUR TESTER DIFFÉRENTS PDFS DE TON DOSSIER 'data'
PDF_FILENAME_TO_TEST = "devis_test_01.pdf" 

if __name__ == "__main__":
    print(f"--- Lancement d'un test sur le fichier : {PDF_FILENAME_TO_TEST} ---")

    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    DATA_FOLDER = os.path.join(PROJECT_ROOT, "data")
    OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "output_devis")
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    input_pdf_path = os.path.join(DATA_FOLDER, PDF_FILENAME_TO_TEST)
    
    # --- Workflow de Test ---
    raw_text = extract_text_from_pdf(input_pdf_path)
    if raw_text:
        structured_data = structure_data_with_llm(raw_text)
        if structured_data:
            # Pour la génération, on utilise les données structurées
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"test_output_{timestamp}.pdf"
            output_pdf_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            generate_pdf(structured_data, output_pdf_path)
    
    print("\n--- Test terminé. ---")