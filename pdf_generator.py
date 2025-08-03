# pdf_generator.py - Version sans fichiers TTF externes

from fpdf import FPDF
from datetime import datetime
import os
from pathlib import Path

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'Rapport Budgetaire Mensuel', 0, 1, 'C')
        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

class PDFReportGenerator:
    """
    Génère un rapport PDF complet des données financières du mois.
    Version simplifiée utilisant uniquement les polices intégrées à FPDF.
    """
    def __init__(self, data):
        self.data = data
        self.pdf = PDF()

    def generate(self, file_path, graph_image_path=None):
        """
        Crée et sauvegarde le rapport PDF.
        """
        try:
            self.pdf.add_page()
            
            # Utiliser uniquement Arial (police intégrée)
            self.pdf.set_font('Arial', '', 12)

            # Section Titre et Date
            self._write_title()

            # Section Résumé
            self._write_summary()

            # Section Graphique
            if graph_image_path and os.path.exists(graph_image_path):
                self._insert_graph(graph_image_path)
                self.pdf.add_page() # Nouvelle page après le graphique

            # Section Dépenses Détaillées
            self._write_expenses_table()

            # Section Dépenses par Catégorie
            self._write_category_table()

            # Sauvegarde du fichier
            self.pdf.output(file_path)
            return True, f"Rapport PDF genere avec succes: {Path(file_path).name}"
            
        except Exception as e:
            return False, f"Erreur lors de la generation du PDF: {e}"

    def _write_title(self):
        self.pdf.set_font('Arial', 'B', 16)
        title = self._clean_text(f"Rapport pour : {self.data['mois_nom']}")
        self.pdf.cell(0, 10, title, 0, 1, 'L')
        
        self.pdf.set_font('Arial', '', 10)
        self.pdf.cell(0, 8, f"Genere le : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", 0, 1, 'L')
        self.pdf.ln(10)

    def _write_summary(self):
        self.pdf.set_font('Arial', 'B', 14)
        self.pdf.cell(0, 10, 'Resume Financier', 0, 1, 'L')
        
        self.pdf.set_font('Arial', '', 12)
        summary_items = [
            ("Salaire", self.data['salaire']),
            ("Total des Depenses", self.data['total_depenses']),
            ("Argent Restant", self.data['argent_restant'])
        ]

        for label, value in summary_items:
            self.pdf.cell(60, 10, f'{label} :')
            # Mettre le restant en rouge si négatif
            if "Restant" in label and value < 0:
                self.pdf.set_text_color(220, 50, 50)
            value_text = f'{value:,.2f} EUR'.replace(',', ' ')
            self.pdf.cell(0, 10, value_text)
            self.pdf.set_text_color(0, 0, 0) # Réinitialiser la couleur
            self.pdf.ln(8)
        self.pdf.ln(10)

    def _insert_graph(self, graph_image_path):
        self.pdf.set_font('Arial', 'B', 14)
        self.pdf.cell(0, 10, 'Analyse Visuelle', 0, 1, 'L')
        
        try:
            # Insérer l'image du graphique
            self.pdf.image(graph_image_path, x=10, y=None, w=self.pdf.w - 20)
            self.pdf.ln(5)
        except Exception as e:
            print(f"Erreur lors de l'insertion de l'image: {e}")
            self.pdf.cell(0, 10, "Erreur: impossible d'inserer le graphique", 0, 1, 'L')

    def _write_expenses_table(self):
        self.pdf.set_font('Arial', 'B', 14)
        self.pdf.cell(0, 10, 'Detail des Depenses', 0, 1, 'L')
        
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_fill_color(224, 235, 255)
        
        # En-têtes du tableau
        col_widths = [80, 40, 30, 35]
        headers = ['Nom', 'Categorie', 'Montant (EUR)', 'Statut']
        for i, header in enumerate(headers):
            self.pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
        self.pdf.ln()

        # Contenu du tableau
        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_fill_color(255, 255, 255)
        
        for depense in self.data['depenses']:
            statut = "Payee" if depense.effectue else "A Payer"
            if depense.emprunte:
                statut += " (E)" # E pour Empruntée
            
            # Nettoyer le texte pour éviter les caractères problématiques
            nom_clean = self._clean_text(depense.nom)
            categorie_clean = self._clean_text(depense.categorie)
            
            # Limiter la longueur des textes
            nom_display = nom_clean[:28] + "..." if len(nom_clean) > 28 else nom_clean
            
            self.pdf.cell(col_widths[0], 7, nom_display, 1, 0, 'L', 1)
            self.pdf.cell(col_widths[1], 7, categorie_clean, 1, 0, 'L', 1)
            montant_text = f'{depense.montant:,.2f}'.replace(',', ' ')
            self.pdf.cell(col_widths[2], 7, montant_text, 1, 0, 'R', 1)
            self.pdf.cell(col_widths[3], 7, statut, 1, 1, 'C', 1)
        
        self.pdf.ln(10)
        
    def _write_category_table(self):
        if not self.data['categories_data']:
            return
            
        self.pdf.set_font('Arial', 'B', 14)
        self.pdf.cell(0, 10, 'Resume par Categorie', 0, 1, 'L')
        
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.set_fill_color(224, 235, 255)
        
        # En-têtes
        self.pdf.cell(80, 8, 'Categorie', 1, 0, 'C', 1)
        self.pdf.cell(50, 8, 'Total (EUR)', 1, 0, 'C', 1)
        self.pdf.ln()
        
        # Contenu
        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_fill_color(255, 255, 255)
        
        total_cat = 0
        sorted_categories = sorted(
            self.data['categories_data'].items(), 
            key=lambda item: item[1], 
            reverse=True
        )
        
        for categorie, montant in sorted_categories:
            categorie_clean = self._clean_text(categorie)
            montant_text = f'{montant:,.2f}'.replace(',', ' ')
            
            self.pdf.cell(80, 7, categorie_clean, 1, 0, 'L', 1)
            self.pdf.cell(50, 7, montant_text, 1, 1, 'R', 1)
            total_cat += montant
            
        # Ligne de total
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(80, 8, 'Total', 1, 0, 'R', 1)
        total_text = f'{total_cat:,.2f}'.replace(',', ' ')
        self.pdf.cell(50, 8, total_text, 1, 1, 'R', 1)

    def _clean_text(self, text):
        """
        Nettoie le texte en remplaçant les caractères accentués 
        par leurs équivalents non accentués.
        """
        if not text:
            return ""
        
        # Dictionnaire de remplacement pour les caractères accentués
        replacements = {
            # Caractères minuscules
            'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a',
            'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e',
            'ì': 'i', 'í': 'i', 'î': 'i', 'ï': 'i',
            'ò': 'o', 'ó': 'o', 'ô': 'o', 'õ': 'o', 'ö': 'o', 'ø': 'o',
            'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
            'ç': 'c', 'ñ': 'n', 'ý': 'y', 'ÿ': 'y',
            
            # Caractères majuscules
            'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A',
            'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E',
            'Ì': 'I', 'Í': 'I', 'Î': 'I', 'Ï': 'I',
            'Ò': 'O', 'Ó': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O', 'Ø': 'O',
            'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
            'Ç': 'C', 'Ñ': 'N', 'Ý': 'Y',
            
            # Autres caractères spéciaux
            '€': 'EUR', '£': 'GBP', '$': 'USD',
            '°': 'deg', '²': '2', '³': '3',
            '«': '"', '»': '"', ''': "'", ''': "'", '"': '"', '"': '"',
            '–': '-', '—': '-', '…': '...',
            'œ': 'oe', 'Œ': 'OE', 'æ': 'ae', 'Æ': 'AE'
        }
        
        cleaned = str(text)
        for old_char, new_char in replacements.items():
            cleaned = cleaned.replace(old_char, new_char)
        
        # Remplacer les caractères non-ASCII restants par un espace ou les supprimer
        cleaned = ''.join(char if ord(char) < 128 else ' ' for char in cleaned)
        
        # Nettoyer les espaces multiples
        while '  ' in cleaned:
            cleaned = cleaned.replace('  ', ' ')
        
        return cleaned.strip()


# Version encore plus simple si vous voulez juste un PDF basique
class SimplePDFGenerator:
    """Version ultra-simple pour générer un PDF sans fioritures."""
    
    def __init__(self, data):
        self.data = data
    
    def generate_simple(self, file_path):
        """Génère un PDF très simple."""
        try:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font('Arial', 'B', 16)
            
            # Titre
            pdf.cell(0, 10, 'Rapport Budget', 0, 1, 'C')
            pdf.ln(10)
            
            # Informations de base
            pdf.set_font('Arial', '', 12)
            pdf.cell(0, 8, f'Mois: {self._clean_simple(self.data["mois_nom"])}', 0, 1)
            pdf.cell(0, 8, f'Salaire: {self.data["salaire"]:.2f} EUR', 0, 1)
            pdf.cell(0, 8, f'Depenses: {self.data["total_depenses"]:.2f} EUR', 0, 1)
            pdf.cell(0, 8, f'Restant: {self.data["argent_restant"]:.2f} EUR', 0, 1)
            pdf.ln(10)
            
            # Liste simple des dépenses
            pdf.set_font('Arial', 'B', 12)
            pdf.cell(0, 8, 'Liste des depenses:', 0, 1)
            pdf.set_font('Arial', '', 10)
            
            for depense in self.data['depenses']:
                nom = self._clean_simple(depense.nom)[:40]
                montant = f'{depense.montant:.2f}'
                statut = 'Payee' if depense.effectue else 'A payer'
                pdf.cell(0, 6, f'- {nom}: {montant} EUR ({statut})', 0, 1)
            
            pdf.output(file_path)
            return True, f"PDF simple genere: {Path(file_path).name}"
            
        except Exception as e:
            return False, f"Erreur: {e}"
    
    def _clean_simple(self, text):
        """Nettoyage très simple du texte."""
        if not text:
            return ""
        
        # Remplacements basiques
        simple_replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e',
            'à': 'a', 'â': 'a', 'ä': 'a',
            'ù': 'u', 'û': 'u', 'ü': 'u',
            'ô': 'o', 'ö': 'o',
            'î': 'i', 'ï': 'i',
            'ç': 'c', '€': 'EUR'
        }
        
        cleaned = str(text)
        for old, new in simple_replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return cleaned