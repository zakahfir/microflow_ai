# microflow_ai/generator/pdf_generator.py

from fpdf import FPDF
import os
from datetime import date

class QuotePDF(FPDF):
    # La partie __init__ avec la gestion des polices est bonne, on la garde.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        font_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets')
        try:
            self.add_font("DejaVu", "", os.path.join(font_path, "DejaVuSans.ttf"), uni=True)
            self.add_font("DejaVu", "B", os.path.join(font_path, "DejaVuSans-Bold.ttf"), uni=True)
            # On définit la police par défaut, qui sera utilisée si on ne spécifie rien.
            self.set_font("DejaVu", "", 10)
        except Exception:
            print("AVERTISSEMENT: Polices DejaVu non trouvées. Utilisation de Helvetica.")
            self.set_font("Helvetica", "", 10)

    def header(self):
        self.set_font(self.font_family, 'B', 20)
        self.cell(0, 15, 'DEVIS CLIENT', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_family, 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    # ... (les fonctions customer_block et quote_details sont probablement bonnes, on ne touche pas)
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


    # **** C'EST ICI QUE LE PROBLÈME SE SITUE PROBABLEMENT ****
    def quote_table(self, lines, total_ht, total_ttc):
        self.set_font(self.font_family, 'B', 10)
        col_widths = (100, 20, 35, 35)
        headers = ['Description', 'Qté', 'Prix U. HT', 'Total HT']
        
        for header, width in zip(headers, col_widths):
            self.cell(width, 8, header, 1, 0, 'C')
        self.ln() # Saut de ligne après l'en-tête

        self.set_font(self.font_family, '', 9)
        if lines:
            for item in lines:
                # --- DÉBOGAGE ET ROBUSTESSE ---
                # On utilise .get(key, default_value) pour éviter les erreurs si une clé manque.
                # On convertit explicitement en string pour la fonction cell.
                description = str(item.get('description', ''))
                quantite = str(item.get('quantite', ''))
                
                # Pour les prix, on essaie de les formater, sinon on met une chaîne vide.
                try:
                    prix_unitaire = f"{float(item.get('prix_unitaire_ht', 0)):.2f} EUR"
                except (ValueError, TypeError):
                    prix_unitaire = "N/A"
                    
                try:
                    total_ligne = f"{float(item.get('total_ligne_ht', 0)):.2f} EUR"
                except (ValueError, TypeError):
                    total_ligne = "N/A"

                # On utilise la même logique multi-ligne qu'avant pour la description
                y_before = self.get_y()
                self.multi_cell(col_widths[0], 6, description, 1, 'L')
                y_after = self.get_y()
                line_height = y_after - y_before
                self.set_xy(self.get_x() + col_widths[0], y_before)
                
                self.cell(col_widths[1], line_height, quantite, 1, 0, 'R')
                self.cell(col_widths[2], line_height, prix_unitaire, 1, 0, 'R')
                self.cell(col_widths[3], line_height, total_ligne, 1, 1, 'R')
        
        # ... (La partie des totaux reste la même)
        self.ln(5)
        self.set_font(self.font_family, 'B', 10)
        self.cell(sum(col_widths[:3]), 8, 'TOTAL HT', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ht or 0:.2f} EUR", 1, 1, 'R')
        tva_amount = (total_ttc or 0) - (total_ht or 0)
        self.cell(sum(col_widths[:3]), 8, 'TVA (20%)', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{tva_amount:.2f} EUR", 1, 1, 'R')
        self.set_font(self.font_family, 'B', 11)
        self.cell(sum(col_widths[:3]), 8, 'TOTAL TTC', 1, 0, 'R')
        self.cell(col_widths[3], 8, f"{total_ttc or 0:.2f} EUR", 1, 1, 'R')


# La fonction generate_pdf reste inchangée, elle appelle simplement la classe.
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