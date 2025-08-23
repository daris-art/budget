# view.py (Version avec fermeture sur 'Échap')

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import qdarktheme

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox, QScrollArea, QMessageBox,
    QInputDialog, QFileDialog, QGroupBox, QFrame, QProgressBar, QDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QLocale
from PyQt6.QtGui import QFont, QDoubleValidator, QKeyEvent, QWheelEvent
import logging
from ui.custom_widgets import NoScrollComboBox

logger = logging.getLogger(__name__)

# --- NOUVELLE CLASSE POUR GÉRER LA NAVIGATION ---
class ExpenseScrollArea(QScrollArea):
    """
    QScrollArea personnalisée qui prend le contrôle des touches fléchées Haut/Bas
    pour naviguer entre les lignes de dépenses au lieu de faire défiler.
    """
    def __init__(self, view_instance, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.view = view_instance # Garde une référence à la fenêtre principale

    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()

        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            focused_widget = QApplication.focusWidget()
            if not focused_widget:
                super().keyPressEvent(event)
                return

            current_row = self.view._find_parent_row(focused_widget)
            if not current_row:
                super().keyPressEvent(event)
                return
            
            try:
                current_index = self.view.expense_rows.index(current_row)
                current_layout = current_row.layout()
                current_col = -1

                # 1. On trouve la colonne du widget qui a le focus
                for i in range(current_layout.count()):
                    if current_layout.itemAt(i).widget() == focused_widget:
                        _, current_col, _, _ = current_layout.getItemPosition(i)
                        break

                if current_col == -1: # Si on n'a pas trouvé, on abandonne
                    super().keyPressEvent(event)
                    return
                
                next_index = -1
                if key == Qt.Key.Key_Down and current_index < len(self.view.expense_rows) - 1:
                    next_index = current_index + 1
                elif key == Qt.Key.Key_Up and current_index > 0:
                    next_index = current_index - 1
                
                if next_index != -1:
                    target_row = self.view.expense_rows[next_index]
                    target_layout = target_row.layout()
                    
                    # 2. On cible le widget dans la MÊME colonne sur la nouvelle ligne
                    target_item = target_layout.itemAtPosition(0, current_col)
                    if target_item and target_item.widget():
                        target_widget = target_item.widget()
                        target_widget.setFocus()
                        if isinstance(target_widget, QLineEdit):
                            target_widget.selectAll()
                        
                        self.ensureWidgetVisible(target_widget, yMargin=10)
                    
                    event.accept()
                    return

            except (ValueError, IndexError) as e:
                logger.warning(f"Erreur de navigation clavier: {e}")
        
        super().keyPressEvent(event)

class BudgetView(QMainWindow):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.expense_rows: List[QWidget] = []
        self.summary_labels: Dict[str, QLabel] = {}
        self._scroll_on_range_change = False

        self.amount_validator = QDoubleValidator(0.00, 999999999.99, 2)
        self.amount_validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.amount_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        self._init_ui()

    # Dans view.py

    def _init_ui(self):
        self.setWindowTitle("Application de Budget (PyQt6)")
        screen = QApplication.primaryScreen()
        available_geometry = screen.availableGeometry()
        self.setGeometry(100, 100, 950, available_geometry.height())

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        main_layout.addWidget(self._create_file_management_section())
        main_layout.addWidget(self._create_salary_section())
        main_layout.addWidget(self._create_expenses_section())
        main_layout.addWidget(self._create_summary_section())
        self._create_status_bar()

    def _create_file_management_section(self) -> QGroupBox:
        group_box = QGroupBox("Gestion du Mois")
        group_box.setObjectName("MonthActionsGroup")
    
        layout = QHBoxLayout()

        layout.addWidget(QLabel("Mois :"))
        self.mois_selector_combo = QComboBox()
        self.mois_selector_combo.setToolTip("Sélectionner un mois à charger")
        self.mois_selector_combo.currentIndexChanged.connect(self.controller.handle_load_mois_from_combo)
        layout.addWidget(self.mois_selector_combo, 1)

        btn_nouveau = QPushButton("➕ Nouveau")
        btn_nouveau.clicked.connect(self.controller.handle_create_mois)
        layout.addWidget(btn_nouveau)
        
        btn_renommer = QPushButton("✏️ Renommer")
        btn_renommer.clicked.connect(self.controller.handle_rename_mois)
        layout.addWidget(btn_renommer)
        
        btn_dupliquer = QPushButton("📋 Dupliquer")
        btn_dupliquer.setToolTip("Dupliquer le mois actuel avec toutes ses opérations")
        btn_dupliquer.clicked.connect(self.controller.handle_duplicate_mois)
        layout.addWidget(btn_dupliquer)

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
    
    # --- NOUVELLE MÉTHODE POUR RAFRAÎCHIR LA LISTE ---
    def refresh_expense_list(self, expenses_to_display: List[Any]):
        """Vide et repeuple la liste des dépenses avec les données fournies."""
        self.clear_all_expenses()
        for i, depense in enumerate(expenses_to_display):
            self.add_expense_widget(depense, i)
        
        # S'assure que l'UI est fluide même avec beaucoup d'éléments
        QApplication.processEvents()

    # --- MODIFICATION DE update_complete_display ---
    def update_complete_display(self, display_data: Any):
        self.update_salary_display(display_data.salaire)
        
        # On utilise maintenant la nouvelle méthode pour afficher les dépenses
        self.refresh_expense_list(display_data.depenses)
        
        summary = {
            "nombre_depenses": display_data.nombre_depenses,
            "total_depenses": display_data.total_depenses,
            "argent_restant": display_data.argent_restant,
            "total_effectue": display_data.total_effectue,
            "total_non_effectue": display_data.total_non_effectue,
            "total_emprunte": display_data.total_emprunte,
            "total_revenus": display_data.total_revenus,
            "total_depenses_fixes": display_data.total_depenses_fixes
        }
        self.update_summary_display(summary)


    def _create_salary_section(self) -> QGroupBox:
        group_box = QGroupBox("Salaire et Actions")
        group_box.setObjectName("SalaryActionsGroup")
        layout = QHBoxLayout()
        
        layout.addWidget(QLabel("Salaire Mensuel (€):"))
        self.salaire_input = QLineEdit("0.0")
        self.salaire_input.setToolTip("Entrez le salaire ou revenu total du mois")
        self.salaire_input.setFixedWidth(150)
        self.salaire_input.setValidator(self.amount_validator)
        self.salaire_input.editingFinished.connect(self.controller.handle_set_salaire)
        self.salaire_input.textChanged.connect(self.controller.handle_live_update)
        layout.addWidget(self.salaire_input)


        # --- AJOUT DU CHAMP DE RECHERCHE ---
        layout.addWidget(QLabel("Rechercher :"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrer par nom...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(180)
        # On connecte le signal de changement de texte au contrôleur
        self.search_input.textChanged.connect(self.controller.handle_search_expenses)
        layout.addWidget(self.search_input)
        
        layout.addStretch()
        
        layout.addWidget(QLabel("Trier par :"))
        self.sort_combo = QComboBox()
        self.sort_options = {
            "Date (plus récentes d'abord)": "date_desc",
            "Date (plus anciennes d'abord)": "date_asc",
            "Montant (plus élevé d'abord)": "montant_desc",
            "Montant (plus bas d'abord)": "montant_asc",
            "Nom (A-Z)": "nom_asc",
            "Nom (Z-A)": "nom_desc",
            "Payé d'abord": "effectue_desc",
            "Non payé d'abord": "effectue_asc",
            "Dépenses fixes d'abord": "est_fixe_desc",
            "Type (revenus puis dépenses)": "type"
        }
        self.sort_combo.addItems(self.sort_options.keys())
        self.sort_combo.activated.connect(self.controller.handle_sort_expenses)
        layout.addWidget(self.sort_combo)
        
        group_box.setLayout(layout)
        return group_box

    def _create_expenses_section(self) -> QGroupBox:
        group_box = QGroupBox("Dépenses")
        main_layout = QVBoxLayout()

        header_layout = QGridLayout()
        headers = ["Type", "Nom", "Montant (€)", "Date", "Catégorie", "Payé", "Prêt", "Fixe", "Actions"]
        for i, header in enumerate(headers):
            label = QLabel(f"<b>{header}</b>")
            
            if header in ("Nom", "Type"):
                label.setIndent(10)
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            elif header == "Actions":
                alignment = Qt.AlignmentFlag.AlignCenter
            elif header in ("Payé", "Prêt"):
                alignment = Qt.AlignmentFlag.AlignLeft
            else:
                alignment = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            
            header_layout.addWidget(label, 0, i, alignment)
        
        header_layout.setColumnStretch(0, 0)  # Type
        header_layout.setColumnStretch(1, 6)  # Nom
        header_layout.setColumnStretch(2, 2)  # Montant
        header_layout.setColumnStretch(3, 2)  # Date
        header_layout.setColumnStretch(4, 2)  # Catégorie (réduit de 3 à 2)
        header_layout.setColumnStretch(5, 1)  # Payé
        header_layout.setColumnStretch(6, 1)  # Prêt
        header_layout.setColumnStretch(7, 1)  # Fixe (nouveau)
        header_layout.setColumnStretch(8, 1)  # Actions (index décalé)
        main_layout.addLayout(header_layout)

        self.scroll_area = ExpenseScrollArea(self) # On passe 'self' (la vue) en référence
        self.scroll_area.setWidgetResizable(True)
        
        self.expenses_container = QWidget()
        self.expenses_layout = QVBoxLayout(self.expenses_container)
        self.expenses_layout.setSpacing(2) 
        self.expenses_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.expenses_container)
        main_layout.addWidget(self.scroll_area)
        
        self.btn_add_expense = QPushButton("➕ Ajouter une dépense")
        self.btn_add_expense.clicked.connect(self.controller.handle_add_expense)
        main_layout.addWidget(self.btn_add_expense, 0, Qt.AlignmentFlag.AlignRight)

        group_box.setLayout(main_layout)
        return group_box

    def add_expense_widget(self, depense: Any, index: int):
        row_widget = QWidget()
        row_widget.depense_id = depense.id
        row_layout = QGridLayout(row_widget)
        row_layout.setContentsMargins(5, 2, 5, 2)

        emoji_label = QLabel("🟢" if depense.est_credit else "🔴")
        emoji_label.setToolTip("Revenu" if depense.est_credit else "Dépense")

        nom_input = QLineEdit(depense.nom)
        nom_input.setCursorPosition(0)
        
        montant_text = "" if depense.montant == 0.0 else str(depense.montant)
        montant_input = QLineEdit(montant_text)
        montant_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        montant_input.setValidator(self.amount_validator)
        
        date_input = QLineEdit(depense.date_depense)
        date_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_input.setInputMask("00/00/0000")
        
        if not depense.date_depense:
            QTimer.singleShot(0, date_input.clear)
            
        cat_combo = NoScrollComboBox() 
        cat_combo.addItems(self.controller.model.categories)
        cat_combo.setCurrentText(depense.categorie)
        effectue_check = QCheckBox()
        effectue_check.setChecked(depense.effectue)
        emprunte_check = QCheckBox()
        emprunte_check.setChecked(depense.emprunte)
        # --- AJOUT : Création de la CheckBox "Fixe" ---
        fixe_check = QCheckBox()
        fixe_check.setChecked(depense.est_fixe)
        btn_supprimer_depense = QPushButton("➖")
        btn_supprimer_depense.setObjectName("RedButton")

        row_layout.addWidget(emoji_label, 0, 0, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(nom_input, 0, 1)
        row_layout.addWidget(montant_input, 0, 2)
        row_layout.addWidget(date_input, 0, 3)
        row_layout.addWidget(cat_combo, 0, 4)
        row_layout.addWidget(effectue_check, 0, 5, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(emprunte_check, 0, 6, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(fixe_check, 0, 7, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(btn_supprimer_depense, 0, 8)

        row_layout.setColumnStretch(0, 0)
        row_layout.setColumnStretch(1, 6)
        row_layout.setColumnStretch(2, 2)
        row_layout.setColumnStretch(3, 2)
        row_layout.setColumnStretch(4, 2) # (réduit de 3 à 2)
        row_layout.setColumnStretch(5, 1)
        row_layout.setColumnStretch(6, 1)
        row_layout.setColumnStretch(7, 1) # (nouveau)
        row_layout.setColumnStretch(8, 1) # (décalé)

        nom_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        montant_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        date_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        cat_combo.currentIndexChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        effectue_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        emprunte_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        fixe_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        btn_supprimer_depense.clicked.connect(lambda checked=False, d_id=depense.id: self.controller.handle_remove_expense_by_id(d_id))
        montant_input.textChanged.connect(self.controller.handle_live_update)
        effectue_check.stateChanged.connect(self.controller.handle_live_update)
        emprunte_check.stateChanged.connect(self.controller.handle_live_update)

        self.expenses_layout.addWidget(row_widget)
        self.expense_rows.append(row_widget)

    def _find_parent_row(self, widget: QWidget) -> Optional[QWidget]:
        """
        Remonte la hiérarchie d'un widget pour trouver la ligne de dépense
        (row_widget) qui le contient.
        """
        current_widget = widget
        while current_widget is not None:
            if current_widget in self.expense_rows:
                return current_widget
            current_widget = current_widget.parent()
        return None

    # --- MODIFICATION DE LA GESTION DES ÉVÉNEMENTS CLAVIER ---

    def keyPressEvent(self, event: QKeyEvent):
        """
        Gère les pressions sur les touches du clavier pour la fenêtre principale.
        La logique de navigation a été déplacée dans ExpenseScrollArea.
        """
        if event.key() == Qt.Key.Key_Escape:
            self.close()
        else:
            super().keyPressEvent(event)

    def focus_on_last_expense_name(self):
        if not self.expense_rows:
            return
        last_row_widget = self.expense_rows[-1]
        name_input_widget = last_row_widget.layout().itemAtPosition(0, 1).widget()
        if isinstance(name_input_widget, QLineEdit):
            name_input_widget.setFocus()

    def scroll_expenses_to_top(self):
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(0))
        
    def scroll_expenses_to_bottom(self):
        QApplication.processEvents()
        QTimer.singleShot(10, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))
    
    def get_sort_key(self) -> str:
        current_text = self.sort_combo.currentText()
        return self.sort_options.get(current_text, "date_desc")
    
    def set_month_actions_enabled(self, enabled: bool):
        # Cible le premier groupe (Gestion du Mois) par son nom
        month_group = self.findChild(QGroupBox, "MonthActionsGroup")
        if month_group:
            month_group.setEnabled(enabled)

        # Cible le second groupe (Salaire et Actions) par son nouveau nom
        salary_group = self.findChild(QGroupBox, "SalaryActionsGroup")
        if salary_group:
            salary_group.setEnabled(enabled)
    
        # Désactiver/Réactiver la ComboBox de sélection du mois
        if month_group:
            self.mois_selector_combo.setEnabled(enabled)

        # Bouton "Ajouter une dépense"
        if hasattr(self, 'btn_add_expense'):
            self.btn_add_expense.setEnabled(enabled)
        
        # Bouton "Voir Graphiques"
        if hasattr(self, 'btn_voir_graphiques'):
            self.btn_voir_graphiques.setEnabled(enabled)

        # On désactive le conteneur de la liste des dépenses, ce qui désactive
        # TOUS ses enfants 
        if hasattr(self, 'expenses_container'):
            self.expenses_container.setEnabled(enabled)


    def get_expense_data(self, index: int) -> Dict[str, Any]:
        if 0 <= index < len(self.expense_rows):
            layout = self.expense_rows[index].layout()
            return {
                "nom": layout.itemAtPosition(0, 1).widget().text(),
                "montant_str": layout.itemAtPosition(0, 2).widget().text(),
                "date_depense": layout.itemAtPosition(0, 3).widget().text(),
                "categorie": layout.itemAtPosition(0, 4).widget().currentText(),
                "effectue": layout.itemAtPosition(0, 5).widget().isChecked(),
                "emprunte": layout.itemAtPosition(0, 6).widget().isChecked(),
                "est_fixe": layout.itemAtPosition(0, 7).widget().isChecked(), # <-- AJOUT
            }
        return {}

    def _create_summary_section(self) -> QGroupBox:
        group_box = QGroupBox("Récapitulatif")
        main_layout = QHBoxLayout()

        # --- Conteneur pour toute la partie gauche (Tout sauf le Bitcoin) ---
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)

        # Création des colonnes de totaux principaux
        left_form_layout = QFormLayout()
        right_form_layout = QFormLayout()
        
        # --- MODIFICATION : On déplace "total_revenus" ici ---
        summary_items = {
            "total_revenus": "Total des Revenus:",
            "total_depenses": "Total des Dépenses:",
            "argent_restant": "Argent Restant:",
            "total_effectue": "Dépenses Réglées:",
            "total_non_effectue": "Dépenses Prévues:",
            "total_emprunte": "Total des Prêts:"
        }
        items = list(summary_items.items())
        mid_point = (len(items) + 1) // 2
        for key, text in items[:mid_point]:
            label = QLabel(text)
            # La condition pour "nombre_depenses" n'est plus utile ici
            value_label = QLabel("0.00 €")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.summary_labels[key] = value_label
            left_form_layout.addRow(label, value_label)
        for key, text in items[mid_point:]:
            label = QLabel(text)
            value_label = QLabel("0.00 €")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.summary_labels[key] = value_label
            right_form_layout.addRow(label, value_label)

        left_layout.addLayout(left_form_layout)
        separator1 = QFrame(); separator1.setFrameShape(QFrame.Shape.VLine); separator1.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator1)
        left_layout.addLayout(right_form_layout)

        # --- Section pour les totaux supplémentaires ---
        separator2 = QFrame(); separator2.setFrameShape(QFrame.Shape.VLine); separator2.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator2)

        extra_summary_layout = QFormLayout()
        # --- MODIFICATION : On déplace "nombre_depenses" ici ---
        extra_items = {
            "nombre_depenses": "Nombre de Lignes:",
            "total_depenses_fixes": "Total Dépenses Fixes:"
        }
        for key, text in extra_items.items():
            label = QLabel(text)
            # --- MODIFICATION : On déplace la condition pour le formatage sans décimales ici ---
            value_label = QLabel("0" if key == "nombre_depenses" else "0.00 €")
            value_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            self.summary_labels[key] = value_label
            extra_summary_layout.addRow(label, value_label)
        
        left_layout.addLayout(extra_summary_layout)

        # --- Le reste de la fonction est inchangé ---
        separator3 = QFrame(); separator3.setFrameShape(QFrame.Shape.VLine); separator3.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator3)

        self.btn_voir_graphiques = QPushButton("📊 Voir Graphiques")
        self.btn_voir_graphiques.setToolTip("Afficher les graphiques financiers pour le mois actuel")
        self.btn_voir_graphiques.clicked.connect(self.controller.handle_show_graphs)
        left_layout.addWidget(self.btn_voir_graphiques, 0, Qt.AlignmentFlag.AlignCenter)
        
        main_layout.addWidget(left_container)
        main_layout.addStretch()

        separator_btc = QFrame(); separator_btc.setFrameShape(QFrame.Shape.VLine); separator_btc.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator_btc)
        
        btc_container = QWidget()
        btc_layout = QVBoxLayout(btc_container)
        btc_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        btc_title_label = QLabel("<b>Cours du Bitcoin</b>")
        btc_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btc_price_label = QLabel("N/A")
        self.btc_price_label.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        self.btc_price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_refresh_btc = QPushButton("🔄")
        self.btn_refresh_btc.setToolTip("Mettre à jour le cours du Bitcoin")
        self.btn_refresh_btc.setFixedSize(65, 24)
        font = self.btn_refresh_btc.font()
        font.setPointSize(16)
        self.btn_refresh_btc.setFont(font)
        btc_layout.addWidget(btc_title_label)
        btc_layout.addWidget(self.btc_price_label)
        btc_layout.addWidget(self.btn_refresh_btc, 0, Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(btc_container)

        group_box.setLayout(main_layout)
        return group_box
    
    # Ajoutez cette nouvelle méthode à la classe BudgetView
    def update_bitcoin_price(self, price_text: str, tooltip_text: str):
        """Met à jour le label affichant le prix du Bitcoin."""
        self.btc_price_label.setText(price_text)
        self.btc_price_label.setToolTip(tooltip_text)


    def _create_status_bar(self):
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Prêt.")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.progress_bar.hide()

    def apply_theme(self, theme: str):
        if not hasattr(self, 'btn_toggle_theme'): return
        self.btn_toggle_theme.setText("☀️" if theme == 'dark' else "🌙")
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
        else:
            custom_styles = """
                QPushButton#RedButton { background-color: #ffdddd; border: 1px solid #ff9999; }
                QPushButton#RedButton:hover { background-color: #ffbbbb; }
                QPushButton#GreenButton { background-color: #ddffdd; border: 1px solid #99ff99; }
                QPushButton#GreenButton:hover { background-color: #bbffbb; }
                QLabel[cssClass="summaryValue"] { color: #000000; }
                QLabel[cssClass="summaryValueNegative"] { color: #DC2626; }
                QLabel[cssClass="summaryValuePositive"] { color: #16A34A; }
            """
        custom_styles += """QLabel[cssClass="shiftedHeader"] { padding-right: 25px; }"""
        final_stylesheet = qdarktheme.load_stylesheet(theme) + custom_styles
        app = QApplication.instance()
        if app:
            app.setStyleSheet(final_stylesheet)
        
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

    def update_summary_display(self, summary_data: Dict[str, float]):
        for key, value in summary_data.items():
            if key in self.summary_labels:
                label = self.summary_labels[key]
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
            if i % 15 == 0:
                QApplication.processEvents()
        summary = {
            "nombre_depenses": display_data.nombre_depenses,
            "total_depenses": display_data.total_depenses,
            "argent_restant": display_data.argent_restant,
            "total_effectue": display_data.total_effectue,
            "total_non_effectue": display_data.total_non_effectue,
            "total_emprunte": display_data.total_emprunte,
            "total_revenus": display_data.total_revenus,
            "total_depenses_fixes": display_data.total_depenses_fixes
        }
        self.update_summary_display(summary)

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

    def show_progress_bar(self, indeterminate: bool = False):
        if indeterminate:
            self.progress_bar.setRange(0, 0)
        else:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        self.progress_bar.show()

    def hide_progress_bar(self):
        self.progress_bar.hide()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
    
    def update_progress_bar(self, value: int):
        self.progress_bar.setValue(value)

    def clear_for_loading(self, message: str = "Chargement..."):
        self.clear_all_expenses()
        self.update_status_bar(message, duration=0)
        QApplication.processEvents()

    def get_excel_import_filepath(self) -> Optional[Path]:
        filepath, _ = QFileDialog.getOpenFileName(self, "Importer depuis Excel", "", "Fichiers Excel (*.xlsx);;Tous les fichiers (*.*)")
        return Path(filepath) if filepath else None

    def get_import_filepath(self) -> Optional[Path]:
        filepath, _ = QFileDialog.getOpenFileName(self, "Importer depuis JSON", "", "Fichiers JSON (*.json);;Tous les fichiers (*.*)")
        return Path(filepath) if filepath else None

    def get_export_filepath(self) -> Optional[Path]:
        filepath, _ = QFileDialog.getSaveFileName(self, "Exporter vers JSON", "", "Fichiers JSON (*.json);;Tous les fichiers (*.*)")
        return Path(filepath) if filepath else None
    
    