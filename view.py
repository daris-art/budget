# view.py (Version PyQt6 - Complète et Corrigée)

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# On importe les bibliothèques nécessaires
import qdarktheme
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox, QScrollArea, QMessageBox,
    QInputDialog, QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

import logging

logger = logging.getLogger(__name__)

class BudgetView(QMainWindow):
    """
    Vue de l'application Budget en utilisant PyQt6.
    """
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.expense_rows: List[QWidget] = []
        # Dictionnaire pour stocker les labels du résumé
        self.summary_labels: Dict[str, QLabel] = {}
        self._init_ui()

    def _init_ui(self):
        """Initialise l'ensemble de l'interface utilisateur."""
        self.setWindowTitle("Application de Budget (PyQt6)")
        self.setGeometry(100, 100, 950, 750)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Création et ajout des différentes sections
        main_layout.addWidget(self._create_file_management_section())
        main_layout.addWidget(self._create_salary_section())
        main_layout.addWidget(self._create_expenses_section())
        main_layout.addWidget(self._create_summary_section())
        self._create_status_bar()

    def _create_file_management_section(self) -> QGroupBox:
        """Crée la section de gestion des mois et des actions globales."""
        group_box = QGroupBox("Gestion du Mois")
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Mois :"))
        self.mois_selector_combo = QComboBox()
        self.mois_selector_combo.setToolTip("Sélectionner un mois à charger")
        self.mois_selector_combo.currentIndexChanged.connect(self.controller.handle_load_mois_from_combo)
        layout.addWidget(self.mois_selector_combo, 1)

        btn_nouveau = QPushButton("➕ Nouveau")
        btn_nouveau.clicked.connect(self.controller.handle_create_mois)
        layout.addWidget(btn_nouveau)

        btn_import_json = QPushButton("📥 Importer JSON")
        btn_import_json.clicked.connect(self.controller.handle_import_from_json)
        layout.addWidget(btn_import_json)

        btn_export_json = QPushButton("📤 Exporter JSON")
        btn_export_json.clicked.connect(self.controller.handle_export_to_json)
        layout.addWidget(btn_export_json)

        btn_importer_excel = QPushButton("📥 Importer Excel")
        btn_importer_excel.setObjectName("GreenButton")
        btn_importer_excel.clicked.connect(self.controller.handle_import_from_excel)
        layout.addWidget(btn_importer_excel)
        
        btn_renommer = QPushButton("✏️ Renommer")
        btn_renommer.clicked.connect(self.controller.handle_rename_mois)
        layout.addWidget(btn_renommer)
        
        btn_supprimer = QPushButton("🗑️ Supprimer")
        btn_supprimer.setObjectName("RedButton")
        btn_supprimer.clicked.connect(self.controller.handle_delete_mois)
        layout.addWidget(btn_supprimer)
        
        layout.addStretch()

        self.btn_toggle_theme = QPushButton("🌙")
        self.btn_toggle_theme.setToolTip("Changer le thème (Clair/Sombre)")
        self.btn_toggle_theme.setFixedSize(32, 32)
        self.btn_toggle_theme.clicked.connect(self.controller.handle_toggle_theme)
        layout.addWidget(self.btn_toggle_theme)

        group_box.setLayout(layout)
        return group_box

    def _create_salary_section(self) -> QGroupBox:
        """Crée la section pour afficher et modifier le salaire."""
        group_box = QGroupBox("Revenus")
        layout = QFormLayout()
        
        self.salaire_input = QLineEdit("0.0")
        self.salaire_input.setToolTip("Entrez le salaire ou revenu total du mois")
        self.salaire_input.editingFinished.connect(self.controller.handle_set_salaire)
        self.salaire_input.textChanged.connect(self.controller.handle_live_update)
        
        layout.addRow("Salaire Mensuel (€):", self.salaire_input)
        
        group_box.setLayout(layout)
        return group_box

    def _create_expenses_section(self) -> QGroupBox:
        """Crée la section des dépenses avec la liste scrollable."""
        group_box = QGroupBox("Dépenses")
        main_layout = QVBoxLayout()

        header_layout = QGridLayout()
        headers = ["Nom", "Montant (€)", "Catégorie", "Payé", "Prêt", "Actions"]
        for i, header in enumerate(headers):
            label = QLabel(f"<b>{header}</b>")
            if header == "Nom":
                # Ajoute une marge intérieure de 5 pixels à gauche du texte.
                label.setIndent(15)
                # On le garde aligné à gauche
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            elif header in ("Payé", "Prêt"):
                label.setProperty("cssClass", "shiftedHeader")
                alignment = Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignVCenter
            else:
                # Pour tous les autres titres, on garde l'alignement à gauche
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            header_layout.addWidget(label, 0, i, alignment)

        # On définit les proportions des colonnes pour l'en-tête.
        # La colonne "Nom" (0) prendra plus de place.
        header_layout.setColumnStretch(0, 4)  # Nom
        header_layout.setColumnStretch(1, 2)  # Montant
        header_layout.setColumnStretch(2, 3)  # Catégorie
        header_layout.setColumnStretch(3, 1)  # Payé
        header_layout.setColumnStretch(4, 1)  # Prêt
        header_layout.setColumnStretch(5, 1)  # Actions

        main_layout.addLayout(header_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.expenses_container = QWidget()
        self.expenses_layout = QVBoxLayout(self.expenses_container)
        self.expenses_layout.setSpacing(2) 
        self.expenses_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll_area.setWidget(self.expenses_container)
        main_layout.addWidget(scroll_area)
        
        btn_add_expense = QPushButton("➕ Ajouter une dépense")
        btn_add_expense.clicked.connect(self.controller.handle_add_expense)
        main_layout.addWidget(btn_add_expense, 0, Qt.AlignmentFlag.AlignRight)

        group_box.setLayout(main_layout)
        return group_box

    def _create_summary_section(self) -> QGroupBox:
        """Crée la section récapitulative des totaux."""
        group_box = QGroupBox("Récapitulatif")
        layout = QGridLayout()

        # --- MODIFICATION ---
        # On ajoute "nombre_depenses" à la liste des éléments à afficher
        summary_items = {
            "nombre_depenses": "Nombre de Dépenses:",
            "total_depenses": "Total des Dépenses:",
            "argent_restant": "Argent Restant:",
            "total_effectue": "Dépenses Réglées:",
            "total_non_effectue": "Dépenses Prévues:",
            "total_emprunte": "Total des Prêts:"
        }

        for i, (key, text) in enumerate(summary_items.items()):
            label = QLabel(text)
            value_label = QLabel("0") # Valeur par défaut pour le nombre
            if key != "nombre_depenses":
                value_label.setText("0.00 €") # Valeur pour les montants

            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.summary_labels[key] = value_label
            layout.addWidget(label, i, 0)
            layout.addWidget(value_label, i, 1)

        group_box.setLayout(layout)
        return group_box
    
    def _create_status_bar(self):
        """Crée la barre de statut."""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Prêt.")

    def apply_theme(self, theme: str):
        """Applique un thème à l'ensemble de l'application."""
        if not hasattr(self, 'btn_toggle_theme'): return
        self.btn_toggle_theme.setText("☀️" if theme == 'dark' else "🌙")

        # Couleurs personnalisées pour les boutons, adaptées au thème
        custom_styles = ""
        
        if theme == 'dark':
            custom_styles = """
                QPushButton#RedButton { background-color: #582A2A; border: 1px solid #8B4545; }
                QPushButton#RedButton:hover { background-color: #6E3636; }
                QPushButton#GreenButton { background-color: #2A582A; border: 1px solid #458B45; }
                QPushButton#GreenButton:hover { background-color: #366E36; }
                QLabel[cssClass="summaryValue"] { color: #E0E0E0; }
                QLabel[cssClass="summaryValueNegative"] { color: #F87171; }
                QLabel[cssClass="summaryValuePositive"] { color: #4ADE80; }
            """
        else: # Thème clair
            custom_styles = """
                QPushButton#RedButton { background-color: #ffdddd; border: 1px solid #ff9999; }
                QPushButton#RedButton:hover { background-color: #ffbbbb; }
                QPushButton#GreenButton { background-color: #ddffdd; border: 1px solid #99ff99; }
                QPushButton#GreenButton:hover { background-color: #bbffbb; }
                QLabel[cssClass="summaryValue"] { color: #000000; }
                QLabel[cssClass="summaryValueNegative"] { color: #DC2626; }
                QLabel[cssClass="summaryValuePositive"] { color: #16A34A; }
            """

        # On ajoute la règle de style pour nos en-têtes décalés
        # Cette règle est indépendante du thème clair/sombre
        custom_styles += """
            QLabel[cssClass="shiftedHeader"] {
                padding-right: 25px; /* Pousse le texte de 15px vers la gauche */
            }
        """
        
        final_stylesheet = qdarktheme.load_stylesheet(theme) + custom_styles
        app = QApplication.instance()
        if app:
            app.setStyleSheet(final_stylesheet)
    

    def add_expense_widget(self, depense: Any, index: int):
        """Ajoute une ligne de dépense à l'interface."""
        row_widget = QWidget()
        row_widget.depense_id = depense.id

        row_layout = QGridLayout(row_widget)
        row_layout.setContentsMargins(5, 2, 5, 2)

        nom_input = QLineEdit(depense.nom)
        montant_input = QLineEdit(str(depense.montant))
        cat_combo = QComboBox()
        cat_combo.addItems(self.controller.model.categories)
        cat_combo.setCurrentText(depense.categorie)
        effectue_check = QCheckBox()
        effectue_check.setChecked(depense.effectue)
        emprunte_check = QCheckBox()
        emprunte_check.setChecked(depense.emprunte)
        btn_supprimer_depense = QPushButton("➖")
        btn_supprimer_depense.setObjectName("RedButton")

        row_layout.addWidget(nom_input, 0, 0)
        row_layout.addWidget(montant_input, 0, 1)
        row_layout.addWidget(cat_combo, 0, 2)
        row_layout.addWidget(effectue_check, 0, 3, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(emprunte_check, 0, 4, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(btn_supprimer_depense, 0, 5)

        # --- MODIFICATION ---
        # On applique EXACTEMENT les mêmes proportions aux colonnes de la ligne
        row_layout.setColumnStretch(0, 4)
        row_layout.setColumnStretch(1, 2)
        row_layout.setColumnStretch(2, 3)
        row_layout.setColumnStretch(3, 1)
        row_layout.setColumnStretch(4, 1)
        row_layout.setColumnStretch(5, 1)

        # Connexions (inchangées)
        nom_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        montant_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        cat_combo.currentIndexChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        effectue_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        emprunte_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        btn_supprimer_depense.clicked.connect(lambda checked=False, d_id=depense.id: self.controller.handle_remove_expense_by_id(d_id))

        montant_input.textChanged.connect(self.controller.handle_live_update)
        effectue_check.stateChanged.connect(self.controller.handle_live_update)
        emprunte_check.stateChanged.connect(self.controller.handle_live_update)

        self.expenses_layout.addWidget(row_widget)
        self.expense_rows.append(row_widget)

    def get_expense_data(self, index: int) -> Dict[str, Any]:
        """Récupère les données d'une ligne de dépense de l'UI."""
        if 0 <= index < len(self.expense_rows):
            row_widget = self.expense_rows[index]
            layout = row_widget.layout()
            return {
                "nom": layout.itemAt(0).widget().text(),
                "montant_str": layout.itemAt(1).widget().text(),
                "categorie": layout.itemAt(2).widget().currentText(),
                "effectue": layout.itemAt(3).widget().isChecked(),
                "emprunte": layout.itemAt(4).widget().isChecked(),
            }
        return {}

    def update_mois_list(self, mois_list: List[str], selected_mois: str):
        self.mois_selector_combo.blockSignals(True)
        self.mois_selector_combo.clear()
        if mois_list:
            self.mois_selector_combo.addItems(mois_list)
            if selected_mois in mois_list:
                self.mois_selector_combo.setCurrentText(selected_mois)
        self.mois_selector_combo.blockSignals(False)

    def update_salary_display(self, salaire: float):
        self.salaire_input.setText(f"{salaire:.2f}")

    # Dans view.py, remplacez cette méthode

    def update_summary_display(self, summary_data: Dict[str, float]):
        """Met à jour les labels du récapitulatif."""
        for key, value in summary_data.items():
            if key in self.summary_labels:
                label = self.summary_labels[key]
                
                # On formate différemment si c'est le nombre de dépenses
                if key == "nombre_depenses":
                    label.setText(str(int(value)))
                else:
                    label.setText(f"{value:,.2f} €".replace(",", " "))
                
                label.setProperty("cssClass", "summaryValue")
                if key == 'argent_restant':
                    label.setProperty("cssClass", "summaryValueNegative" if value < 0 else "summaryValuePositive")
                
                label.style().polish(label)

    def remove_expense_widget(self, index: int):
        if 0 <= index < len(self.expense_rows):
            row_to_remove = self.expense_rows.pop(index)
            row_to_remove.deleteLater()

    def clear_all_expenses(self):
        while self.expense_rows:
            row = self.expense_rows.pop()
            row.deleteLater()

    def update_complete_display(self, display_data: Any):
        self.update_salary_display(display_data.salaire)
        self.clear_all_expenses()
        for i, depense in enumerate(display_data.depenses):
            self.add_expense_widget(depense, i)
        summary = {
            "nombre_depenses": display_data.nombre_depenses,
            "total_depenses": display_data.total_depenses,
            "argent_restant": display_data.argent_restant,
            "total_effectue": display_data.total_effectue,
            "total_non_effectue": display_data.total_non_effectue,
            "total_emprunte": display_data.total_emprunte,
        }
        self.update_summary_display(summary)

    # --- Méthodes de dialogue ---
    def get_new_mois_input(self) -> Optional[Dict[str, str]]:
        nom, ok = QInputDialog.getText(self, "Nouveau Mois", "Entrez le nom du nouveau mois:")
        if ok and nom:
            salaire, ok = QInputDialog.getText(self, "Nouveau Mois", f"Entrez le salaire pour {nom}:", text="0.0")
            if ok:
                return {"nom": nom, "salaire": salaire}
        return None

    def ask_for_string(self, title: str, prompt: str, default_value: str = "") -> Optional[str]:
        text, ok = QInputDialog.getText(self, title, prompt, text=default_value)
        return text if ok else None

    def show_error_message(self, message: str):
        QMessageBox.critical(self, "Erreur", message)

    def show_warning_message(self, message: str):
        QMessageBox.warning(self, "Attention", message)

    def show_info_message(self, message: str):
        QMessageBox.information(self, "Information", message)

    def ask_confirmation(self, title: str, message: str) -> bool:
        reply = QMessageBox.question(self, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)
        return reply == QMessageBox.StandardButton.Yes
    
    def update_status_bar(self, text: str, is_error: bool = False, duration: int = 5000):
        style = "color: red;" if is_error else ""
        self.status_bar.setStyleSheet(style)
        self.status_bar.showMessage(text, duration)

    def clear_for_loading(self, message: str = "Chargement..."):
        self.clear_all_expenses()
        self.update_status_bar(message, duration=0)
        QApplication.processEvents()

    def get_excel_import_filepath(self) -> Optional[Path]:
        """Ouvre une boîte de dialogue pour sélectionner un fichier Excel (.xlsx)."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer depuis Excel",
            "",
            "Fichiers Excel (*.xlsx);;Tous les fichiers (*.*)"
        )
        return Path(filepath) if filepath else None

    def get_import_filepath(self) -> Optional[Path]:
        """Ouvre une boîte de dialogue pour sélectionner un fichier JSON à importer."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Importer depuis JSON",
            "",
            "Fichiers JSON (*.json);;Tous les fichiers (*.*)"
        )
        return Path(filepath) if filepath else None

    def get_export_filepath(self) -> Optional[Path]:
        """Ouvre une boîte dedialogue pour sauvegarder un fichier JSON."""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter vers JSON",
            "",
            "Fichiers JSON (*.json);;Tous les fichiers (*.*)"
        )
        return Path(filepath) if filepath else None