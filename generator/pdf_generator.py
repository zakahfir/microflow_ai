# microflow_ai/generator/pdf_generator.py
from fpdf import FPDF
import os
from datetime import date

class QuotePDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On définit le chemin vers notre dossier de polices
        font_path = os.path.join(os.path.dirname(__file__), '..', 'assets')

        # On ajoute les 4 styles de notre police Unicode en pointant vers les fichiers locaux
        self.add_font("DejaVu", "", os.path.join(font_path, "DejaVuSans.ttf"), uni=True)
        self.add_font("DejaVu", "B", os.path.join(font_path, "DejaVuSans-Bold.ttf"), uni=True)
        self.add_font("DejaVu", "I", os.path.join(font_path, "DejaVuSans-Oblique.ttf"), uni=True)
        self.add_font("DejaVu", "BI", os.path.join(font_path, "DejaVuSans-BoldOblique.ttf"), uni=True)

        # On définit la police par défaut
        self.set_font("DejaVu", "", 10)

    def header(self):
        self.set_font('DejaVu', 'B', 15)
        self.cell(0, 10, 'DEVIS CLIENT', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('DejaVu', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def customer_block(self, client_name):
        self.set_font('DejaVu', 'B', 12)
        self.cell(0, 10, 'Informations du Client :', 0, 1)
        self.set_font('DejaVu', '', 12)
        self.cell(0, 6, f"Nom: {client_name or 'Non spécifié'}", 0, 1)
        self.ln(10)

    def quote_details(self, quote_date, quote_number):
        self.set_font('DejaVu', '', 12)
        today = date.today().strftime("%d/%m/%Y")
        self.cell(0, 6, f"Date du devis: {quote_date or today}", 0, 1)
        self.cell(0, 6, f"Numéro de devis: {quote_number or 'N/A'}", 0, 1)
        self.ln(10)

    def quote_table(self, lines, total_ht, total_ttc):
        self.set_font('DejaVu', 'B', 11)
        # Largeurs des colonnes
        col_widths = (100, 20, 30, 30)
        # En-têtes
        self.cell(col_widths[0], 7, 'Description', 1, 0, 'C')
        self.cell(col_widths[1], 7, 'Qté', 1, 0, 'C')
        self.cell(col_widths[2], 7, 'Prix U. HT', 1, 0, 'C')
        self.cell(col_widths[3], 7, 'Total HT', 1, 1, 'C')

        self.set_font('DejaVu', '', 10)
        if lines:
            for item in lines:
                self.cell(col_widths[0], 6, item.get('description', ''), 1, 0)
                self.cell(col_widths[1], 6, str(item.get('quantite', '')), 1, 0, 'R')
                self.cell(col_widths[2], 6, f"{item.get('prix_unitaire_ht', 0):.2f} EUR", 1, 0, 'R')
                self.cell(col_widths[3], 6, f"{item.get('total_ligne_ht', 0):.2f} EUR", 1, 1, 'R')
        
        # Lignes pour les totaux
        self.set_font('DejaVu', 'B', 11)
        self.cell(sum(col_widths[:3]), 7, 'TOTAL HT', 1, 0, 'R')
        self.cell(col_widths[3], 7, f"{total_ht or 0:.2f} EUR", 1, 1, 'R')
        self.cell(sum(col_widths[:3]), 7, 'TOTAL TTC', 1, 0, 'R')
        self.cell(col_widths[3], 7, f"{total_ttc or 0:.2f} EUR", 1, 1, 'R')

def generate_pdf(data, output_path):
    print(f"INFO: Génération du PDF vers : {output_path}")
    try:
        pdf = QuotePDF()
        pdf.add_page()
        pdf.customer_block(data.get('nom_client'))
        pdf.quote_details(data.get('date_devis'), data.get('numero_devis'))
        pdf.quote_table(data.get('lignes_articles'), data.get('total_ht'), data.get('total_ttc'))
        
        pdf.output(output_path)
        print("SUCCÈS: Le fichier PDF a été généré.")
        return True
    except Exception as e:
        print(f"ERREUR: Une erreur est survenue lors de la génération du PDF : {e}")
        return False