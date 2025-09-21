# microflow_ai/generator/pdf_generator.py
from fpdf import FPDF
import os
from datetime import date

class QuotePDF(FPDF):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
        try:
            self.add_font("DejaVu", "", os.path.join(font_path, "DejaVuSans.ttf"), uni=True)
            self.add_font("DejaVu", "B", os.path.join(font_path, "DejaVuSans-Bold.ttf"), uni=True)
            self.add_font("DejaVu", "I", os.path.join(font_path, "DejaVuSans-Oblique.ttf"), uni=True)
            self.add_font("DejaVu", "BI", os.path.join(font_path, "DejaVuSans-BoldOblique.ttf"), uni=True)
            self.set_font("DejaVu", "", 10)
        except Exception as e:
            print(f"AVERTISSEMENT: Polices DejaVu non trouvées. Erreur: {e}. Utilisation de Helvetica.")
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

    # **** NOUVELLE VERSION "SIMPLICITÉ RADICALE" DE LA FONCTION quote_table ****
    def quote_table(self, lines, total_ht, total_ttc):
        self.set_font(self.font_family, 'B', 10)
        col_widths = (100, 20, 35, 35)
        headers = ['Description', 'Qté', 'Prix U. HT', 'Total HT']
        
        # Dessiner les en-têtes
        for header, width in zip(headers, col_widths):
            self.cell(width, 8, header, 1, 0, 'C')
        self.ln()

        self.set_font(self.font_family, '', 9)
        if not lines:
            self.cell(sum(col_widths), 10, "Aucun article à afficher.", 1, 1, 'C')
        else:
            for item in lines:
                # --- NOUVELLE LOGIQUE D'AFFICHAGE LIGNE PAR LIGNE ---

                # On nettoie les données, comme avant.
                description = str(item.get('description', ''))
                try:
                    quantite = int(item.get('quantite', 0)) if float(item.get('quantite', 0)).is_integer() else float(item.get('quantite', 0))
                    quantite_str = str(quantite)
                except:
                    quantite_str = str(item.get('quantite', ''))

                try: prix_unitaire_str = f"{float(item.get('prix_unitaire_ht', 0)):.2f} EUR"
                except: prix_unitaire_str = "N/A"
                
                try: total_ligne_str = f"{float(item.get('total_ligne_ht', 0)):.2f} EUR"
                except: total_ligne_str = "N/A"

                # On dessine chaque cellule une par une sur la même ligne.
                # C'est moins flexible pour les descriptions très longues, mais 100x plus fiable.
                self.cell(col_widths[0], 6, description, 1, 0, 'L')
                self.cell(col_widths[1], 6, quantite_str, 1, 0, 'R')
                self.cell(col_widths[2], 6, prix_unitaire_str, 1, 0, 'R')
                self.cell(col_widths[3], 6, total_ligne_str, 1, 1, 'R') # Le '1' à la fin provoque un saut de ligne
        
        self.ln(5)
        self.set_font(self.font_family, 'B', 10)
        try:
            total_ht_val = float(total_ht or 0)
            total_ttc_val = float(total_ttc or 0)
            tva_amount = total_ttc_val - total_ht_val
        except (ValueError, TypeError):
            total_ht_val, total_ttc_val, tva_amount = 0, 0, 0

        self.cell(sum(col_widths[:3]), 8, 'TOTAL HT', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ht_val:.2f} EUR", 1, 1, 'R')
        self.cell(sum(col_widths[:3]), 8, 'TVA (Calculée)', 1, 0, 'R') # Libellé plus clair
        self.cell(col_widths[3], 8, f"{tva_amount:.2f} EUR", 1, 1, 'R')
        self.set_font(self.font_family, 'B', 11)
        self.cell(sum(col_widths[:3]), 8, 'TOTAL TTC', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ttc_val:.2f} EUR", 1, 1, 'R')

def generate_pdf(data, output_path):
    try:
        pdf = QuotePDF()
        pdf.add_page()
        pdf.customer_block(data.get('nom_client'))
        pdf.quote_details(data.get('date_devis'), data.get('numero_devis'))
        pdf.quote_table(data.get('lignes_articles'), data.get('total_ht'), data.get('total_ttc'))
        pdf.output(output_path)
        print(f"INFO: PDF généré avec succès à {output_path}")
        return True
    except Exception as e:
        print(f"ERREUR Critique lors de la génération PDF : {e}")
        return False