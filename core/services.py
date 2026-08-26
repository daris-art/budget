# core/services.py

import json
import openpyxl
import requests
import datetime
import logging
from pathlib import Path
from typing import List
from dataclasses import asdict
from openpyxl.worksheet.worksheet import Worksheet
from core.database import DatabaseManager
from core.data_models import Result, Depense, DatabaseError

logger = logging.getLogger(__name__)


class ImportCategoryClassifier:
    """Déduit une catégorie à partir du libellé d'une dépense."""

    KEYWORDS_BY_CATEGORY = {
        "Alimentation": [
            "carrefour", "auchan", "leclerc", "casino", "supermarche", "epicerie",
            "boulangerie", "magasin", "superette", "fruit", "legume", "lidl", 
            "bingo", "brkic", "konzum"
        ],
        "Logement": [
            "loyer", "copropriete", "assurance habitation", "eau", "gaz", "electricite",
            "energie", "chauffage", "immobilier", "apartement", "remboursement",
            "charges courantes", "pret habitat", "electricite", "assurence habitation"
        ],
        "Transport": [
            "sncf", "uber", "taxi", "essence", "station", "parking", "train", "bus",
            "carburant", "autoroute", "mobilite"
        ],
        "Factures": [
            "orange", "free", "edf", "engie", "internet", "telephone", "mobile", "facture",
            "abonnement", "box", "sfr", "canal+", "impot", "novotel", "google"
        ],
        "Shopping": [
            "amazon", "ikea", "zalando", "decathlon", "boutique", "vetement", "vêtement",
            "chaussure", "mode", "commerce"
        ],
        "Santé": [
            "pharmacie", "docteur", "clinique", "medecin", "dentiste", "optique", "sante",
            "hopital"
        ],
        "Loisirs": [
            "netflix", "spotify", "cinema", "restaurant", "bar", "festival", "loisir",
            "sortie", "theatre", "theater", "cafe"
        ],
        "Autres": []
    }

    @staticmethod
    def normalize_label(label: str) -> str:
        if not label:
            return ""
        normalized = str(label).lower()
        for accented, plain in {"é": "e", "è": "e", "à": "a", "ç": "c", "ù": "u"}.items():
            normalized = normalized.replace(accented, plain)
        normalized = ''.join(ch if ch.isalnum() or ch.isspace() else ' ' for ch in normalized)
        return ' '.join(normalized.split())

    @classmethod
    def infer_expense_category(cls, label: str) -> str:
        normalized = cls.normalize_label(label)
        if not normalized:
            return "Autres"

        best_category = "Autres"
        best_score = 0

        for category, keywords in cls.KEYWORDS_BY_CATEGORY.items():
            if not keywords:
                continue
            score = 0
            for keyword in keywords:
                normalized_keyword = cls.normalize_label(keyword)
                if normalized_keyword in normalized:
                    score += 2
            if score > best_score:
                best_score = score
                best_category = category

        return best_category


class BitcoinAPIService:
    """Service pour récupérer le prix du Bitcoin."""
    def get_price(self) -> Result:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": "bitcoin", "vs_currencies": "eur"}
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            price = data.get("bitcoin", {}).get("eur")
            
            if price is None:
                return Result.error("Format de réponse de l'API inattendu.")
            return Result.success(data=price)
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur réseau BTC: {e}")
            return Result.error("Erreur réseau. Vérifiez votre connexion.")
        except Exception as e:
            logger.error(f"Erreur API BTC: {e}")
            return Result.error("Une erreur inattendue est survenue.")


class ImportExportService:
    """Service pour l'import/export de fichiers."""
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def export_month_report_pdf(self, mois_id: int, filepath: Path) -> Result:
        """Crée un rapport PDF complet du mois avec résumé et liste des opérations."""
        try:
            mois = self.db_manager.get_mois_by_id(mois_id)
            if not mois:
                return Result.error("Mois non trouvé pour le rapport PDF.")

            depenses = self.db_manager.get_depenses_by_mois(mois_id)
            try:
                from reportlab.lib import colors
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import mm
                from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
            except ImportError:
                return Result.error("La dépendance 'reportlab' est requise pour générer un PDF. Installez-la avec : pip install reportlab")

            total_revenus = sum(d.montant for d in depenses if d.est_credit)
            total_depenses = sum(d.montant for d in depenses if not d.est_credit)
            total_effectue = sum(d.montant for d in depenses if d.effectue and not d.est_credit)
            total_non_effectue = total_depenses - total_effectue
            total_emprunte = sum(d.montant for d in depenses if d.emprunte)
            total_depenses_fixes = sum(d.montant for d in depenses if not d.est_credit and d.est_fixe)
            argent_restant = total_revenus - total_depenses

            doc = SimpleDocTemplate(str(filepath), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=12*mm, bottomMargin=12*mm)
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('Title', parent=styles['Title'], fontSize=18, leading=22, spaceAfter=10, textColor=colors.HexColor('#1f2937'))
            section_style = ParagraphStyle('Section', parent=styles['Heading2'], fontSize=12, leading=14, spaceAfter=6, textColor=colors.HexColor('#111827'))
            normal_style = ParagraphStyle('NormalBold', parent=styles['BodyText'], fontSize=9, leading=11)
            cell_style = ParagraphStyle(
                'CellBody',
                parent=styles['BodyText'],
                fontSize=7,
                leading=9,
                wordWrap='CJK',
                borderPadding=2,
                alignment=1
            )

            story = []
            story.append(Paragraph(f"Rapport du mois : {mois.nom}", title_style))
            story.append(Paragraph(f"Date de génération : {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}", normal_style))
            story.append(Spacer(1, 8))

            summary_data = [
                ["Total revenus", f"{total_revenus:.2f} €"],
                ["Total dépenses", f"{total_depenses:.2f} €"],
                ["Dépenses effectuées", f"{total_effectue:.2f} €"],
                ["Dépenses non effectuées", f"{total_non_effectue:.2f} €"],
                ["Dépenses fixes", f"{total_depenses_fixes:.2f} €"],
                ["Montant emprunté", f"{total_emprunte:.2f} €"],
                ["Argent restant", f"{argent_restant:.2f} €"],
            ]
            summary_table = Table(summary_data, colWidths=[90*mm, 55*mm])
            summary_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5e7eb')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#111827')),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9fafb')]),
            ]))
            story.append(Paragraph("Résumé", section_style))
            story.append(summary_table)
            story.append(Spacer(1, 12))

            story.append(Paragraph("Détails des opérations", section_style))
            if depenses:
                rows = [["Date", "Nom", "Catégorie", "Montant", "Type", "Payé", "Fixe"]]
                for d in sorted(depenses, key=lambda x: x.date_depense if x.date_depense else '', reverse=True):
                    montant_style = ParagraphStyle(
                        'AmountCell',
                        parent=cell_style,
                        textColor=colors.HexColor('#16a34a') if d.est_credit else colors.HexColor('#111827'),
                        fontName='Helvetica-Bold' if d.est_credit else 'Helvetica',
                        fontSize=7,
                        leading=9,
                        alignment=2,
                    )
                    rows.append([
                        Paragraph(d.date_depense, cell_style),
                        Paragraph(d.nom, cell_style),
                        Paragraph(d.categorie, cell_style),
                        Paragraph(f"{d.montant:.2f} €", montant_style),
                        Paragraph('Revenu' if d.est_credit else 'Dépense', cell_style),
                        Paragraph('Oui' if d.effectue else 'Non', cell_style),
                        Paragraph('Oui' if d.est_fixe else 'Non', cell_style),
                    ])
                detail_table = Table(
                    rows,
                    colWidths=[18*mm, 48*mm, 30*mm, 18*mm, 18*mm, 14*mm, 12*mm],
                    repeatRows=1
                )
                detail_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dbeafe')),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ALIGN', (3, 1), (3, -1), 'RIGHT'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
                    ('LEFTPADDING', (0, 0), (-1, -1), 3),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                ]))
                story.append(detail_table)
            else:
                story.append(Paragraph("Aucune opération enregistrée pour ce mois.", normal_style))

            doc.build(story)
            return Result.success(f"Rapport PDF généré : {filepath.name}")

        except Exception as e:
            logger.error(f"Erreur inattendue lors de la génération du rapport PDF: {e}")
            return Result.error(f"Une erreur inattendue est survenue lors de la génération du PDF: {e}")

    def export_to_json(self, mois_id: int, filepath: Path) -> Result:
        """Exporte les données d'un mois (salaire et dépenses) vers un fichier JSON."""
        try:
            mois_details = self.db_manager.get_mois_by_id(mois_id)
            if not mois_details:
                return Result.error("Mois non trouvé pour l'export.")
            
            depenses = self.db_manager.get_depenses_by_mois(mois_id)
            
            # --- CORRECTION ---
            # On utilise asdict(dep) pour les dataclasses au lieu de dep._asdict()
            depenses_data = [asdict(dep) for dep in depenses]
            
            # Structure des données pour le fichier JSON
            data_to_export = {
                "mois": {
                    "nom": mois_details.nom,
                    "salaire": mois_details.salaire
                },
                "depenses": depenses_data
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_export, f, indent=4, ensure_ascii=False)
            
            return Result.success(f"Export réussi vers {filepath.name}")

        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'export JSON: {e}")
            return Result.error(f"Une erreur inattendue est survenue: {e}")

    def import_from_json(self, filepath: Path, new_mois_name: str) -> Result:
        """Importe un fichier JSON pour créer un nouveau mois et ses dépenses."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if 'depenses' not in data:
                return Result.error("Structure JSON invalide : clé 'depenses' manquante.")

            salaire = data.get('mois', {}).get('salaire', 0.0)
            
            depenses_a_importer = []
            for dep_data in data['depenses']:
                depenses_a_importer.append(Depense(
                    nom=dep_data.get('nom', 'Dépense sans nom'),
                    montant=dep_data.get('montant', 0.0),
                    categorie=dep_data.get('categorie', 'Autres'),
                    date_depense=dep_data.get('date_depense', datetime.datetime.now().strftime('%d/%m/%Y')),
                    est_credit=dep_data.get('est_credit', False),
                    effectue=dep_data.get('effectue', False),
                    emprunte=dep_data.get('emprunte', False)
                ))
            
            # On appelle la méthode transactionnelle
            self.db_manager.import_new_mois(new_mois_name, salaire, depenses_a_importer)
            
            return Result.success(f"Import réussi: {len(depenses_a_importer)} dépenses ajoutées à '{new_mois_name}'.")

        except FileNotFoundError:
            return Result.error("Fichier non trouvé.")
        except json.JSONDecodeError as e:
            return Result.error(f"Erreur de décodage JSON : {e}")
        except DatabaseError as e:
            return Result.error(str(e)) # L'erreur de la DB remonte ici
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'import JSON: {e}")
            return Result.error(f"Une erreur inattendue est survenue: {e}")

    def import_from_excel(self, filepath: Path, new_mois_name: str, progress_callback=None) -> Result:
        """
        Lit un fichier Excel, crée un nouveau mois et y importe les opérations.
        Les crédits sont sommés et définissent le salaire initial du mois.
        """
        try:
            workbook = openpyxl.load_workbook(filepath, read_only=True)
            sheet: Worksheet = workbook.active
            
            header_row_index = -1
            col_indices = {}

            # Recherche de la ligne d'en-tête à partir de la ligne 10
            for i in range(1, sheet.max_row + 1): # On commence à la ligne 1 pour plus de flexibilité
                row_values = [str(cell.value).strip() if cell.value else "" for cell in sheet[i]]
                if "Libellé" in row_values and "Date" in row_values:
                    header_row_index = i
                    col_indices["nom"] = row_values.index("Libellé")
                    col_indices["date"] = row_values.index("Date")
                    if "Débit euros" in row_values:
                        col_indices["debit"] = row_values.index("Débit euros")
                    if "Crédit euros" in row_values:
                        col_indices["credit"] = row_values.index("Crédit euros")
                    break
            
            if header_row_index == -1:
                return Result.error("En-tête non trouvé. Vérifiez que les colonnes 'Libellé' et 'Date' existent.")

            # On lit d'abord toutes les lignes en mémoire pour connaître le total
            rows_to_process = list(sheet.iter_rows(min_row=header_row_index + 1))
            total_rows = len(rows_to_process)
            if total_rows == 0:
                return Result.error("Aucune donnée trouvée après l'en-tête.")

            operations_a_importer: List[Depense] = []

            # On parcourt les lignes pré-chargées
            for row_index, row in enumerate(rows_to_process):

                cells = [cell.value for cell in row]
                nom = cells[col_indices["nom"]]
                date_val = cells[col_indices["date"]]
                debit_val = cells[col_indices.get("debit", -1)] if "debit" in col_indices else None
                credit_val = cells[col_indices.get("credit", -1)] if "credit" in col_indices else None

                if not nom or not date_val:
                    continue

                date_depense_str = ""
                if isinstance(date_val, datetime.datetime):
                    date_depense_str = date_val.strftime('%d/%m/%Y')
                else:
                    date_depense_str = str(date_val)

                montant, est_credit = 0.0, False
                try:
                    if "credit" in col_indices and credit_val and float(credit_val) > 0:
                        montant, est_credit = float(credit_val), True
                        categorie = "Revenue"
                    elif "debit" in col_indices and debit_val and float(debit_val) > 0:
                        montant, est_credit = float(debit_val), False
                        categorie = ImportCategoryClassifier.infer_expense_category(str(nom))
                    else:
                        continue
                except (ValueError, TypeError):
                    logger.warning(f"Ligne {row_index + header_row_index + 2} ignorée: montant invalide.")
                    continue

                operations_a_importer.append(
                    Depense(
                        nom=str(nom).strip(),
                        montant=montant,
                        categorie=categorie,
                        date_depense=date_depense_str,
                        est_credit=est_credit,
                        effectue=True,
                        emprunte=False,
                        est_fixe=False
                    )
                )

            # 1. On calcule le total des crédits qui servira de salaire initial
            salaire_initial = sum(op.montant for op in operations_a_importer if op.est_credit)

            # 2. On appelle notre méthode transactionnelle unique
            self.db_manager.import_new_mois(new_mois_name, salaire_initial, operations_a_importer)

            return Result.success(f"{len(operations_a_importer)} opérations importées dans '{new_mois_name}'.")

        except FileNotFoundError:
            return Result.error("Fichier Excel non trouvé.")
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'import Excel: {e}")
            return Result.error(f"Une erreur inattendue est survenue: {e}")
