# Dans pdf_generator.py

from fpdf import FPDF
from datetime import datetime
import os
from pathlib import Path
import matplotlib.pyplot as plt
import tempfile
import numpy as np # Assurez-vous d'importer numpy si ce n'est pas déjà fait

# ... (La classe PDF reste identique) ...
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
    Version autonome qui crée son propre graphique.
    """
    def __init__(self, data):
        self.data = data
        self.pdf = PDF()

    def generate(self, file_path):
        """
        Crée et sauvegarde le rapport PDF.
        Cette méthode orchestre la création de toutes les sections,
        y compris la génération de l'image du graphique.
        """
        graph_image_path = None
        try:
            self.pdf.add_page()
            self.pdf.set_font('Arial', '', 12)

            # 1. Titre et Résumé
            self._write_title()
            self._write_summary()

            # 2. Génération et insertion du graphique (logique maintenant interne)
            graph_image_path = self._create_temp_graph_image()
            if graph_image_path and os.path.exists(graph_image_path):
                self._insert_graph(graph_image_path)
                self.pdf.add_page()  # Nouvelle page après le graphique

            # 3. Tableaux détaillés
            self._write_expenses_table()
            self._write_category_table()

            # 4. Sauvegarde du fichier
            self.pdf.output(file_path)
            return True, f"Rapport PDF généré avec succès : {Path(file_path).name}"

        except Exception as e:
            # En cas d'erreur, on retourne un message clair
            return False, f"Erreur lors de la génération du PDF : {e}"

        finally:
            # 5. Nettoyage du fichier image temporaire (TRÈS IMPORTANT)
            if graph_image_path and os.path.exists(graph_image_path):
                os.unlink(graph_image_path)

    def _create_temp_graph_image(self) -> str | None:
        """
        Génère l'image du graphique et la sauvegarde dans un fichier temporaire.
        Cette logique a été déplacée depuis le contrôleur pour une meilleure architecture.
        """
        categories_data = self.data.get('categories_data', {})
        if not categories_data:
            return None

        cat_labels = list(categories_data.keys())
        cat_values = list(categories_data.values())

        try:
            fig, ax1 = plt.subplots(figsize=(8, 5))
            fig.suptitle('Répartition des Dépenses par Catégorie', fontsize=14, fontweight='bold')

            colors = plt.cm.Set3(np.linspace(0, 1, len(cat_labels)))

            wedges, texts, autotexts = ax1.pie(cat_values, autopct='%1.1f%%', startangle=90, colors=colors)

            ax1.legend(wedges, cat_labels,
                       title="Catégories",
                       loc="center left",
                       bbox_to_anchor=(1, 0, 0.5, 1))

            plt.setp(autotexts, size=8, weight="bold")
            ax1.set_title('')
            plt.tight_layout(rect=[0, 0, 0.75, 1])

            # Sauvegarder dans un fichier temporaire
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png', mode='w+b')
            plt.savefig(temp_file.name, dpi=150, bbox_inches='tight')
            plt.close(fig)
            temp_file.close() # Fermer le handle du fichier
            return temp_file.name

        except Exception as e:
            print(f"Erreur lors de la création du graphique temporaire : {e}")
            plt.close('all') # S'assurer que toutes les figures sont fermées
            return None

    # ... (Les autres méthodes _write_title, _write_summary, etc., restent identiques) ...
    # Assurez-vous qu'elles sont présentes dans votre classe.
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
            if "Restant" in label and value < 0:
                self.pdf.set_text_color(220, 50, 50)
            value_text = f'{value:,.2f} EUR'.replace(',', ' ')
            self.pdf.cell(0, 10, value_text)
            self.pdf.set_text_color(0, 0, 0)
            self.pdf.ln(8)
        self.pdf.ln(10)

    def _insert_graph(self, graph_image_path):
        self.pdf.set_font('Arial', 'B', 14)
        self.pdf.cell(0, 10, 'Analyse Visuelle', 0, 1, 'L')
        
        try:
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
        
        col_widths = [80, 40, 30, 35]
        headers = ['Nom', 'Categorie', 'Montant (EUR)', 'Statut']
        for i, header in enumerate(headers):
            self.pdf.cell(col_widths[i], 8, header, 1, 0, 'C', 1)
        self.pdf.ln()

        self.pdf.set_font('Arial', '', 9)
        self.pdf.set_fill_color(255, 255, 255)
        
        for depense in self.data['depenses']:
            statut = "Payee" if depense.effectue else "A Payer"
            if depense.emprunte:
                statut += " (E)"
            
            nom_clean = self._clean_text(depense.nom)
            categorie_clean = self._clean_text(depense.categorie)
            
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
        
        self.pdf.cell(80, 8, 'Categorie', 1, 0, 'C', 1)
        self.pdf.cell(50, 8, 'Total (EUR)', 1, 0, 'C', 1)
        self.pdf.ln()
        
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
            
        self.pdf.set_font('Arial', 'B', 10)
        self.pdf.cell(80, 8, 'Total', 1, 0, 'R', 1)
        total_text = f'{total_cat:,.2f}'.replace(',', ' ')
        self.pdf.cell(50, 8, total_text, 1, 1, 'R', 1)

    def _clean_text(self, text):
        # ... (le code de _clean_text reste le même)
        if not text:
            return ""
        
        replacements = {
            'é': 'e', 'è': 'e', 'ê': 'e', 'ë': 'e', '€': 'EUR', 'ç': 'c',
            # Ajoutez d'autres remplacements si nécessaire
        }
        
        cleaned = str(text)
        for old, new in replacements.items():
            cleaned = cleaned.replace(old, new)
        
        return ''.join(char for char in cleaned if ord(char) < 128)