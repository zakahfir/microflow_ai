# microflow_ai/generator/pdf_generator.py

from fpdf import FPDF
import os
from datetime import date

class QuotePDF(FPDF):
    """
    Classe personnalisée pour générer nos devis PDF.
    Hérite de FPDF pour en utiliser les fonctionnalités de base.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # On déclare ici le chemin vers nos polices pour que le PDF soit autonome
        font_path = os.path.join(os.path.dirname(__file__), '..', 'assets')
        
        # On ajoute les différentes variantes de la police DejaVu. C'est crucial pour les caractères spéciaux (é, €, œ...).
        try:
            self.add_font("DejaVu", "", os.path.join(font_path, "DejaVuSans.ttf"), uni=True)
            self.add_font("DejaVu", "B", os.path.join(font_path, "DejaVuSans-Bold.ttf"), uni=True)
            self.add_font("DejaVu", "I", os.path.join(font_path, "DejaVuSans-Oblique.ttf"), uni=True)
            self.add_font("DejaVu", "BI", os.path.join(font_path, "DejaVuSans-BoldOblique.ttf"), uni=True)
            self.set_font("DejaVu", "", 10)
        except RuntimeError:
            print("AVERTISSEMENT: Polices DejaVu non trouvées. Le PDF pourrait avoir des problèmes d'encodage.")
            # Si les polices ne sont pas trouvées, on se rabat sur une police de base.
            self.set_font("Helvetica", "", 10)

    def header(self):
        self.set_font(self.font_family, 'B', 20)
        self.cell(0, 15, 'DEVIS CLIENT', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def customer_block(self, client_name):
        self.set_font(self.font_family, 'B', 11)
        self.cell(0, 7, 'Informations du Client :', 0, 1)
        self.set_font(self.font_family, '', 11)
        self.multi_cell(0, 7, f"Nom: {client_name or 'Non spécifié'}")
        self.ln(10)

    def quote_details(self, quote_date, quote_number):
        self.set_font(self.font_family, '', 11)
        today = date.today().strftime("%d/%m/%Y")
        self.cell(0, 7, f"Date du devis: {quote_date or today}", 0, 1)
        self.cell(0, 7, f"Numéro de devis: {quote_number or 'N/A'}", 0, 1)
        self.ln(10)

    def quote_table(self, lines, total_ht, total_ttc):
        self.set_font(self.font_family, 'B', 10)
        col_widths = (100, 20, 35, 35) # Ajustement des largeurs
        # En-têtes
        self.cell(col_widths[0], 8, 'Description', 1, 0, 'C')
        self.cell(col_widths[1], 8, 'Qté', 1, 0, 'C')
        self.cell(col_widths[2], 8, 'Prix U. HT', 1, 0, 'C')
        self.cell(col_widths[3], 8, 'Total HT', 1, 1, 'C')
        
        self.set_font(self.font_family, '', 9)
        if lines:
            for item in lines:
                # Utiliser multi_cell pour la description pour gérer les textes longs
                y_before = self.get_y()
                self.multi_cell(col_widths[0], 6, str(item.get('description', '')), 1, 'L')
                y_after = self.get_y()
                # On se replace sur la même ligne pour les autres cellules
                self.set_xy(self.get_x() + col_widths[0], y_before)
                
                self.cell(col_widths[1], (y_after - y_before), str(item.get('quantite', '')), 1, 0, 'R')
                self.cell(col_widths[2], (y_after - y_before), f"{item.get('prix_unitaire_ht', 0):.2f} EUR", 1, 0, 'R')
                self.cell(col_widths[3], (y_after - y_before), f"{item.get('total_ligne_ht', 0):.2f} EUR", 1, 1, 'R')
        
        # Lignes pour les totaux
        self.ln(5)
        self.set_font(self.font_family, 'B', 10)
        self.cell(sum(col_widths[:3]), 8, 'TOTAL HT', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ht or 0:.2f} EUR", 1, 1, 'R')
        # On pourrait ajouter la TVA ici
        tva_amount = (total_ttc or 0) - (total_ht or 0)
        self.cell(sum(col_widths[:3]), 8, 'TVA (20%)', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{tva_amount:.2f} EUR", 1, 1, 'R')

        self.set_font(self.font_family, 'B', 11)
        self.cell(sum(col_widths[:3]), 8, 'TOTAL TTC', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ttc or 0:.2f} EUR", 1, 1, 'R')

def generate_pdf(data, output_path):
    pdf = QuotePDF()
    pdf.add_page()
    pdf.customer_block(data.get('nom_client'))
    pdf.quote_details(data.get('date_devis'), data.get('numero_devis'))
    pdf.quote_table(data.get('lignes_articles'), data.get('total_ht'), data.get('total_ttc'))
    pdf.output(output_path)
    print(f"INFO: Le fichier PDF a été généré avec succès à l'emplacement : {output_path}")
    return True