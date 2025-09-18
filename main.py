# microflow_ai/main.py
# Chef d'orchestre du workflow complet.

from extractor.pdf_reader import extract_text_from_pdf, structure_data_with_llm
from generator.pdf_generator import generate_pdf
import os
from datetime import datetime

# --- Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_FOLDER = os.path.join(PROJECT_ROOT, "data")
OUTPUT_FOLDER = os.path.join(PROJECT_ROOT, "output_devis")
PDF_FILENAME_TO_PROCESS = "devis_test_03.pdf" # Change ce nom pour tester d'autres PDF

# --- Exécution Principale ---
if __name__ == "__main__":
    print("--- Lancement du workflow complet de MicroFlow.AI V0.2 ---")

    # S'assurer que le dossier de sortie existe
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)

    input_pdf_path = os.path.join(DATA_FOLDER, PDF_FILENAME_TO_PROCESS)
    
    # --- ÉTAPE 1 : EXTRACTION ---
    print("\n[ÉTAPE 1/3] Extraction du texte brut du PDF...")
    raw_text = extract_text_from_pdf(input_pdf_path)

    if raw_text:
        # --- ÉTAPE 2 : STRUCTURATION PAR L'IA ---
        print("\n[ÉTAPE 2/3] Structuration des données avec l'IA...")
        structured_data = structure_data_with_llm(raw_text)
        
        if structured_data:
            # --- ÉTAPE 3 : GÉNÉRATION DU PDF CLIENT ---
            print("\n[ÉTAPE 3/3] Génération du devis client en PDF...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"devis_client_{os.path.splitext(PDF_FILENAME_TO_PROCESS)[0]}_{timestamp}.pdf"
            output_pdf_path = os.path.join(OUTPUT_FOLDER, output_filename)
            
            generate_pdf(structured_data, output_pdf_path)
            print(f"\nTerminé ! Le nouveau devis a été sauvegardé ici : {output_pdf_path}")
        else:
            print("\nÉCHEC DU WORKFLOW : L'IA n'a pas pu structurer les données.")
    else:
        print("\nÉCHEC DU WORKFLOW : Impossible d'extraire le texte du PDF initial.")

    print("\n--- Workflow terminé. ---")