# view.py (Version avec fermeture sur 'Échap')
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
import qdarktheme

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QPushButton, QLineEdit, QComboBox, QCheckBox, QScrollArea, QMessageBox,
    QInputDialog, QFileDialog, QGroupBox, QFrame, QProgressBar, QDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, QTimer, QLocale, QEvent, QObject
from PyQt6.QtGui import QFont, QDoubleValidator, QKeyEvent, QCursor, QShortcut, QKeySequence
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
        self.selected_row_indices: List[int] = []
        self.last_selected_index: Optional[int] = None
        self.selected_rows_total_label: Optional[QLabel] = None
        self._scroll_on_range_change = False

        self.amount_validator = QDoubleValidator(0.00, 999999999.99, 2)
        self.amount_validator.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.amount_validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        
        self._init_ui()

    # Dans view.py

    def _init_ui(self):
        self.setWindowTitle("Application de Budget (PyQt6)")
        self.setMinimumWidth(1280) # Définit la largeur minimale à 1200 pixels
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
        self._refresh_expense_line_numbers()
        # S'assure que l'UI est fluide même avec beaucoup d'éléments
        QApplication.processEvents()

   
    def update_complete_display(self, display_data: Any):
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
            "total_depenses_fixes": display_data.total_depenses_fixes,
            "count_depenses": display_data.count_depenses,
            "count_revenus": display_data.count_revenus,
            "reste_apres_fixes": display_data.reste_apres_fixes
        }
        self.update_summary_display(summary)


    def _create_salary_section(self) -> QGroupBox:
        group_box = QGroupBox("Recherche et Trie")
        group_box.setObjectName("SalaryActionsGroup")
        layout = QHBoxLayout()
        
        """ layout.addWidget(QLabel("Salaire Mensuel (€):"))
        self.salaire_input = QLineEdit("0.0")
        self.salaire_input.setToolTip("Entrez le salaire ou revenu total du mois")
        self.salaire_input.setFixedWidth(150)
        self.salaire_input.setValidator(self.amount_validator)
        self.salaire_input.editingFinished.connect(self.controller.handle_set_salaire)
        self.salaire_input.textChanged.connect(self.controller.handle_live_update)
        layout.addWidget(self.salaire_input) """


        # --- AJOUT DU CHAMP DE RECHERCHE ---
        layout.addWidget(QLabel("Rechercher :"))
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Filtrer par nom...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setFixedWidth(180)
        # On connecte le signal de changement de texte au contrôleur
        self.search_input.textChanged.connect(self.controller.handle_search_input_changed)
        layout.addWidget(self.search_input)

        layout.addWidget(QLabel("Date min :"))
        self.search_date_min_input = QLineEdit()
        self.search_date_min_input.setPlaceholderText("JJ/MM/AAAA")
        self.search_date_min_input.setInputMask("00/00/0000")
        self.search_date_min_input.setClearButtonEnabled(True)
        self.search_date_min_input.setFixedWidth(120)
        self.search_date_min_input.textChanged.connect(self.controller.handle_search_input_changed)
        layout.addWidget(self.search_date_min_input)

        layout.addWidget(QLabel("Date max :"))
        self.search_date_max_input = QLineEdit()
        self.search_date_max_input.setPlaceholderText("JJ/MM/AAAA")
        self.search_date_max_input.setInputMask("00/00/0000")
        self.search_date_max_input.setClearButtonEnabled(True)
        self.search_date_max_input.setFixedWidth(120)
        self.search_date_max_input.textChanged.connect(self.controller.handle_search_input_changed)
        layout.addWidget(self.search_date_max_input)

        # --- NOUVEAU: CHAMPS DE RECHERCHE PAR MONTANT MIN/MAX ---
        layout.addWidget(QLabel("Montant Min (€) :"))
        self.search_amount_min_input = QLineEdit()
        self.search_amount_min_input.setPlaceholderText("Min...")
        self.search_amount_min_input.setClearButtonEnabled(True)
        self.search_amount_min_input.setValidator(self.amount_validator)
        self.search_amount_min_input.setFixedWidth(80)
        self.search_amount_min_input.textChanged.connect(self.controller.handle_search_input_changed)
        layout.addWidget(self.search_amount_min_input)

        layout.addWidget(QLabel("Max (€) :"))
        self.search_amount_max_input = QLineEdit()
        self.search_amount_max_input.setPlaceholderText("Max...")
        self.search_amount_max_input.setClearButtonEnabled(True)
        self.search_amount_max_input.setValidator(self.amount_validator)
        self.search_amount_max_input.setFixedWidth(80)
        self.search_amount_max_input.textChanged.connect(self.controller.handle_search_input_changed)
        layout.addWidget(self.search_amount_max_input)
        
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
        group_box = QGroupBox("Opérations")
        main_layout = QVBoxLayout()

        header_layout = QGridLayout()
        headers = ["N°", "Type", "Nom", "Montant (€)", "Date", "Catégorie", "Payé", "Prêt", "Fixe", "Actions"]
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
        
        header_layout.setColumnStretch(0, 0)  # Numéro de ligne
        header_layout.setColumnStretch(1, 0)  # Type
        header_layout.setColumnStretch(2, 6)  # Nom
        header_layout.setColumnStretch(3, 2)  # Montant
        header_layout.setColumnStretch(4, 2)  # Date
        header_layout.setColumnStretch(5, 2)  # Catégorie (réduit de 3 à 2)
        header_layout.setColumnStretch(6, 1)  # Payé
        header_layout.setColumnStretch(7, 1)  # Prêt
        header_layout.setColumnStretch(8, 1)  # Fixe
        header_layout.setColumnStretch(9, 1)  # Actions
        main_layout.addLayout(header_layout)

        self.scroll_area = ExpenseScrollArea(self) # On passe 'self' (la vue) en référence
        self.scroll_area.setWidgetResizable(True)
        
        self.expenses_container = QWidget()
        self.expenses_layout = QVBoxLayout(self.expenses_container)
        self.expenses_layout.setSpacing(2) 
        self.expenses_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scroll_area.setWidget(self.expenses_container)
        main_layout.addWidget(self.scroll_area)
        
        info_layout = QHBoxLayout()
        delete_info_label = QLabel("Supprimer une opération : Ctrl + S")
        delete_info_label.setStyleSheet("font-size: 13px;")
        info_layout.addWidget(delete_info_label)
        info_layout.addStretch()
        self.btn_add_expense = QPushButton("➕ Ajouter une opération (Ctrl + O)")
        self.btn_add_expense.clicked.connect(self.controller.handle_add_expense)
        info_layout.addWidget(self.btn_add_expense)
        main_layout.addLayout(info_layout)
        
        # --- NOUVEAU : Raccourcis clavier ---
        self.shortcut_add_expense = QShortcut(QKeySequence("Ctrl+O"), self)
        self.shortcut_add_expense.activated.connect(self.btn_add_expense.click)
        self.shortcut_delete_expense = QShortcut(QKeySequence("Ctrl+S"), self)
        self.shortcut_delete_expense.activated.connect(self.delete_focused_expense)
        # Note : On simule un clic sur le bouton ou un raccourci, ce qui appellera proprement
        # le handler du contrôleur.

        group_box.setLayout(main_layout)
        return group_box

    # view.py

    def add_expense_widget(self, depense: Any, index: int):
        row_widget = QWidget()
        row_widget.depense_id = depense.id
        row_widget.est_credit = depense.est_credit
        row_layout = QGridLayout(row_widget)
        row_layout.setContentsMargins(5, 2, 5, 2)

        type_button = QPushButton("🟢" if depense.est_credit else "🔴")
        type_button.setToolTip("Cliquer pour basculer Revenu/Dépense")
        type_button.setFlat(True) # Enlève l'arrière-plan du bouton
        type_button.setStyleSheet("QPushButton { border: none; padding-left: 5px; }") # Enlève la bordure
        type_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor)) # Montre une main au survol
        # Connexion au nouveau handler du contrôleur
        type_button.clicked.connect(lambda _, i=index: self.controller.handle_toggle_expense_type(i))
        
        nom_input = QLineEdit(depense.nom)
        nom_input.setCursorPosition(0)
        nom_input.setStyleSheet("font-size: 14px;")
        
        montant_text = "" if depense.montant == 0.0 else str(depense.montant)
        montant_input = QLineEdit(montant_text)
        montant_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        montant_input.setValidator(self.amount_validator)
        # --- NOUVEAU : Style conditionnel pour les revenus (🟢) ---
        if depense.est_credit:
            # Applique la couleur verte et le texte en gras via une feuille de style CSS/Qt
            montant_input.setStyleSheet("font-size: 14px; color: #4ADE80;")            # Note : #4ADE80 est le vert clair que vous utilisez déjà pour votre thème sombre.
            # Si vous préférez un vert plus standard, vous pouvez mettre "color: green;"
        else:
            # On remet le style par défaut pour les dépenses normales
            montant_input.setStyleSheet("font-size: 14px;")

        date_input = QLineEdit(depense.date_depense)
        date_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_input.setInputMask("00/00/0000")
        #: Augmenter la taille de la police pour la date ---
        date_input.setStyleSheet("font-size: 14px;")
        
        if not depense.date_depense:
            QTimer.singleShot(0, date_input.clear)
            
        cat_combo = NoScrollComboBox() 
        cat_combo.addItems(self.controller.model.categories)
        cat_combo.setCurrentText(depense.categorie)
        cat_combo.setStyleSheet("font-size: 14px;")

        # Style commun pour agrandir l'indicateur des cases à cocher
        checkbox_style = """
            QCheckBox::indicator {
                width: 22px;
                height: 22px;
            }
        """

        effectue_check = QCheckBox()
        effectue_check.setChecked(depense.effectue)
        effectue_check.setStyleSheet(checkbox_style) # <-- AJOUT

        emprunte_check = QCheckBox()
        emprunte_check.setChecked(depense.emprunte)
        emprunte_check.setStyleSheet(checkbox_style) # <-- AJOUT

        fixe_check = QCheckBox()
        fixe_check.setChecked(depense.est_fixe)
        fixe_check.setStyleSheet(checkbox_style) # <-- AJOUT
        btn_supprimer_depense = QPushButton("➖")
        btn_supprimer_depense.setObjectName("RedButton")

        line_number_label = QLabel(f"{index + 1:>3}")
        line_number_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        line_number_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; font-family: 'Courier New', monospace;"
        )
        line_number_label.setMinimumWidth(36)

        row_layout.addWidget(line_number_label, 0, 0, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(type_button, 0, 1, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(nom_input, 0, 2)
        row_layout.addWidget(montant_input, 0, 3)
        row_layout.addWidget(date_input, 0, 4)
        row_layout.addWidget(cat_combo, 0, 5)
        row_layout.addWidget(effectue_check, 0, 6, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(emprunte_check, 0, 7, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(fixe_check, 0, 8, Qt.AlignmentFlag.AlignCenter)
        row_layout.addWidget(btn_supprimer_depense, 0, 9)

        row_layout.setColumnStretch(0, 0)
        row_layout.setColumnStretch(1, 0)
        row_layout.setColumnStretch(2, 6)
        row_layout.setColumnStretch(3, 2)
        row_layout.setColumnStretch(4, 2)
        row_layout.setColumnStretch(5, 2)
        row_layout.setColumnStretch(6, 1)
        row_layout.setColumnStretch(7, 1)
        row_layout.setColumnStretch(8, 1)
        row_layout.setColumnStretch(9, 1)

        # CONNEXIONS OPTIMISÉES:
        # Sauvegarde uniquement à la fin de l'édition
        nom_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        montant_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        date_input.editingFinished.connect(lambda i=index: self.controller.handle_update_expense(i))
        cat_combo.currentIndexChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        
        # MODIFICATION: Les checkboxes ne déclenchent QUE la sauvegarde
        # La mise à jour live sera gérée par handle_update_expense
        effectue_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        emprunte_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        fixe_check.stateChanged.connect(lambda _, i=index: self.controller.handle_update_expense(i))
        
        # MODIFICATION: Seul le montant déclenche une mise à jour live pendant la frappe
        montant_input.textChanged.connect(self.controller.handle_live_update)
        
        btn_supprimer_depense.clicked.connect(lambda checked=False, d_id=depense.id: self.controller.handle_remove_expense_by_id(d_id))

        self._install_row_event_filters(row_widget)
        self.expenses_layout.addWidget(row_widget)
        self.expense_rows.append(row_widget)

    # --- AJOUT : Nouvelle méthode pour mettre à jour une ligne spécifique ---
    def update_expense_row_display(self, index: int, new_data: dict):
        """Met à jour l'affichage d'une seule ligne de dépense, par exemple l'émoji."""
        if not (0 <= index < len(self.expense_rows)):
            return

        row_widget = self.expense_rows[index]
        layout = row_widget.layout()

        # Met à jour l'émoji si l'information est présente
        if 'est_credit' in new_data:
            type_button = layout.itemAtPosition(0, 1).widget()
            if isinstance(type_button, QPushButton):
                new_char = "🟢" if new_data['est_credit'] else "🔴"
                type_button.setText(new_char)
            # Met à jour la propriété interne pour les calculs en direct
            row_widget.est_credit = new_data['est_credit']
            # --- NOUVEAU : Dynamiser la couleur du montant lors du clic sur l'émoji ---
            montant_input = layout.itemAtPosition(0, 3).widget()
            if isinstance(montant_input, QLineEdit):
                if new_data['est_credit']:
                    montant_input.setStyleSheet("font-size: 14px; color: #4ADE80;")
                else:
                    montant_input.setStyleSheet("font-size: 14px;") # Réinitialise pour les dépenses
        if 'categorie' in new_data:
            # Le QComboBox est à la 6ème colonne (index 5)
            cat_combo = layout.itemAtPosition(0, 5).widget()
            if isinstance(cat_combo, QComboBox):
                cat_combo.setCurrentText(new_data['categorie'])
        

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

    def delete_focused_expense(self):
        focused_widget = QApplication.focusWidget()
        if not focused_widget:
            return
        current_row = self._find_parent_row(focused_widget)
        if current_row is None:
            return
        current_index = self.expense_rows.index(current_row)
        line_number_widget = current_row.layout().itemAtPosition(0, 0).widget()
        depense_id = getattr(current_row, 'depense_id', None)
        if depense_id is None:
            return
        self.controller.handle_remove_expense_by_id(depense_id)

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
        name_input_widget = last_row_widget.layout().itemAtPosition(0, 2).widget()
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

        if hasattr(self, 'btn_refresh_btc'):
            self.btn_refresh_btc.setEnabled(enabled)


    def get_expense_data(self, index: int) -> Dict[str, Any]:
        if 0 <= index < len(self.expense_rows):
            row_widget = self.expense_rows[index]
            layout = row_widget.layout()
            return {
                "nom": layout.itemAtPosition(0, 2).widget().text(),
                "montant_str": layout.itemAtPosition(0, 3).widget().text(),
                "date_depense": layout.itemAtPosition(0, 4).widget().text(),
                "categorie": layout.itemAtPosition(0, 5).widget().currentText(),
                "effectue": layout.itemAtPosition(0, 6).widget().isChecked(),
                "emprunte": layout.itemAtPosition(0, 7).widget().isChecked(),
                "est_fixe": layout.itemAtPosition(0, 8).widget().isChecked(),
                "est_credit": row_widget.est_credit,
            }
        return {}

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.MouseButtonPress:
            parent_row = self._find_parent_row(watched)
            if parent_row in self.expense_rows:
                modifiers = event.modifiers() if hasattr(event, "modifiers") else QApplication.keyboardModifiers()
                if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                    index = self.expense_rows.index(parent_row)
                    self._handle_row_selection(index, modifiers)
        return super().eventFilter(watched, event)

    def _install_row_event_filters(self, row_widget: QWidget):
        row_widget.installEventFilter(self)
        for child in row_widget.findChildren(QWidget):
            child.installEventFilter(self)

    def _handle_row_selection(self, index: int, modifiers: Qt.KeyboardModifier):
        if modifiers & Qt.KeyboardModifier.ShiftModifier and self.last_selected_index is not None:
            start = min(self.last_selected_index, index)
            end = max(self.last_selected_index, index)
            if not (modifiers & Qt.KeyboardModifier.ControlModifier):
                self.clear_expense_selection()
            for i in range(start, end + 1):
                self._select_row(i, True)
            self.selected_row_indices = list(range(start, end + 1))
        elif modifiers & Qt.KeyboardModifier.ControlModifier:
            currently_selected = index in self.selected_row_indices
            self._select_row(index, not currently_selected)
            if currently_selected:
                self.selected_row_indices.remove(index)
            else:
                self.selected_row_indices.append(index)
        else:
            if self.selected_row_indices != [index]:
                self.clear_expense_selection()
                self._select_row(index, True)
                self.selected_row_indices = [index]
        self.last_selected_index = index
        self._update_selected_rows_total()

    def _select_row(self, index: int, selected: bool):
        if 0 <= index < len(self.expense_rows):
            row_widget = self.expense_rows[index]
            if selected:
                row_widget.setStyleSheet(
                    "background-color: rgba(120, 120, 140, 0.08);"
                    "border-left: 3px solid rgba(100, 100, 120, 0.35);"
                    "border-top-right-radius: 4px;"
                    "border-bottom-right-radius: 4px;"
                )
            else:
                row_widget.setStyleSheet("")

    def clear_expense_selection(self):
        for row_widget in self.expense_rows:
            row_widget.setStyleSheet("")
        self.selected_row_indices = []
        self.last_selected_index = None
        self._update_selected_rows_total()

    def _update_selected_rows_total(self):
        if not self.selected_rows_total_label:
            return

        total = 0.0
        for index in self.selected_row_indices:
            if not (0 <= index < len(self.expense_rows)):
                continue

            row_widget = self.expense_rows[index]
            layout = row_widget.layout()
            amount_widget = layout.itemAtPosition(0, 3).widget()
            if not isinstance(amount_widget, QLineEdit):
                continue

            amount_text = amount_widget.text().strip()
            if not amount_text:
                continue

            normalized = amount_text.replace(" ", "")
            if "," in normalized and "." in normalized:
                normalized = normalized.replace(".", "").replace(",", ".")
            elif "," in normalized:
                normalized = normalized.replace(",", ".")

            try:
                total += float(normalized)
            except ValueError:
                continue

        count_text = f"({len(self.selected_row_indices)})" if self.selected_row_indices else "(0)"
        self.selected_rows_total_label.setText(f"{count_text} {total:,.2f} €".replace(",", " "))

    def _create_summary_section(self) -> QGroupBox:
        group_box = QGroupBox("Récapitulatif")
        main_layout = QHBoxLayout()

        # --- Conteneur pour toute la partie gauche (Tout sauf le Bitcoin) ---
        left_container = QWidget()
        left_layout = QHBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)

        # Création des colonnes de totaux principaux
        left_form_layout = QFormLayout()
        right_form_layout = QFormLayout()

        # --- MODIFICATION 1 : Empêcher le FormLayout de compresser les libellés ---
        for form in (left_form_layout, right_form_layout):
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.DontWrapRows)

        summary_items = {
            "total_revenus": "Total des Revenus",
            "total_depenses": "Total des Dépenses",
            "argent_restant": "Argent Restant",
            "total_effectue": "Dépenses Payées",
            "total_non_effectue": "Dépenses Prévues",
            "total_emprunte": "Total des Prêts"
        }
        
        def add_summary_row(form_layout: QFormLayout, key: str, text: str, default_val: str = "0.00 €"):
            label = QLabel(text)
            # --- MODIFICATION 2 : Garantir une taille minimale pour le texte du label ---
            label.setMinimumWidth(130) 
            
            value_label = QLabel(default_val)
            value_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            value_label.setMinimumWidth(110)
            value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            
            self.summary_labels[key] = value_label
            form_layout.addRow(label, value_label)

        items = list(summary_items.items())
        mid_point = (len(items) + 1) // 2
        
        for key, text in items[:mid_point]:
            add_summary_row(left_form_layout, key, text)
            
        for key, text in items[mid_point:]:
            add_summary_row(right_form_layout, key, text)

        left_layout.addLayout(left_form_layout)
        left_layout.addSpacing(20)
        
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.VLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator1)
        left_layout.addSpacing(20)
        
        left_layout.addLayout(right_form_layout)
        left_layout.addSpacing(20)
        
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.VLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator2)
        left_layout.addSpacing(20)

        extra_summary_layout = QFormLayout()
        extra_summary_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        extra_items = {
            "nombre_depenses": "Nombre de Lignes:",
            "total_depenses_fixes": "Total Dépenses Fixes:",
            "reste_apres_fixes": "Reste après Fixes:"
        }
        for key, text in extra_items.items():
            val = "0" if key == "nombre_depenses" else "0.00 €"
            add_summary_row(extra_summary_layout, key, text, val)
        
        left_layout.addLayout(extra_summary_layout)
        left_layout.addSpacing(20)
        
        separator3 = QFrame()
        separator3.setFrameShape(QFrame.Shape.VLine)
        separator3.setFrameShadow(QFrame.Shadow.Sunken)
        left_layout.addWidget(separator3)
        left_layout.addSpacing(10)

        # Regrouper les boutons dans une colonne verticale
        buttons_layout = QVBoxLayout()

        selection_row_layout = QHBoxLayout()
        selection_label = QLabel("Total selection")
        selection_label.setMinimumWidth(100)
        selection_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        selection_row_layout.addWidget(selection_label)

        self.selected_rows_total_label = QLabel("0.00 €")
        self.selected_rows_total_label.setMinimumHeight(24)
        self.selected_rows_total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.selected_rows_total_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.selected_rows_total_label.setStyleSheet("color: #16A34A;")
        selection_row_layout.addWidget(self.selected_rows_total_label)

        buttons_layout.addLayout(selection_row_layout)

        self.btn_voir_graphiques = QPushButton("📊 Voir Graphiques")
        self.btn_voir_graphiques.setToolTip("Afficher les graphiques financiers pour le mois actuel")
        self.btn_voir_graphiques.clicked.connect(self.controller.handle_show_graphs)
        buttons_layout.addWidget(self.btn_voir_graphiques, 0, Qt.AlignmentFlag.AlignCenter)

        self.btn_import_alsace_excel = QPushButton("📥 Importer Excel (Alsace)")
        self.btn_import_alsace_excel.clicked.connect(self.controller.handle_import_from_alsace_excel)
        buttons_layout.addWidget(self.btn_import_alsace_excel, 0, Qt.AlignmentFlag.AlignCenter)

        # Forcer les 2 boutons à avoir la même largeur
        max_width = max(self.btn_voir_graphiques.sizeHint().width(),
                        self.btn_import_alsace_excel.sizeHint().width())
        self.btn_voir_graphiques.setMinimumWidth(max_width)
        self.btn_import_alsace_excel.setMinimumWidth(max_width)

        left_layout.addLayout(buttons_layout)
        
        # --- MODIFICATION 3 : Donner un stretch à left_container au lieu d'un main_layout.addStretch() direct ---
        main_layout.addWidget(left_container, 1)
        
        separator_btc = QFrame()
        separator_btc.setFrameShape(QFrame.Shape.VLine)
        separator_btc.setFrameShadow(QFrame.Shadow.Sunken)
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
        
        main_layout.addWidget(btc_container, 0)

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
                QLabel[cssClass="summaryValueWarning"] { color: #FBBF24; } /* Jaune/Orange */
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
                QLabel[cssClass="summaryValueWarning"] { color: #D97706; } /* Ambre/Orange foncé */
            """
        custom_styles += """QLabel[cssClass="shiftedHeader"] { padding-right: 25px; }
                QLabel[cssClass="summaryValueBlue"] { color: #3B82F6; }"""
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

    def update_summary_display(self, summary_data: Dict[str, float]):
        for key, value in summary_data.items():
            if key in self.summary_labels:
                label = self.summary_labels[key]
                
                # La logique pour formater le texte reste la même
                text_to_display = ""
                if key == "total_depenses":
                    count = summary_data.get("count_depenses", 0)
                    text_to_display = f"( {int(count)} ) {value:,.2f} €".replace(",", " ")
                elif key == "total_revenus":
                    count = summary_data.get("count_revenus", 0)
                    text_to_display = f"( {int(count)} ) {value:,.2f} €".replace(",", " ")
                elif key == "nombre_depenses":
                    text_to_display = str(int(value))
                elif isinstance(value, (int, float)):
                     text_to_display = f"{value:,.2f} €".replace(",", " ")
                else:
                    text_to_display = str(value)
                label.setText(text_to_display)

                # --- NOUVELLE LOGIQUE D'APPLICATION DES COULEURS ---
                css_class = "summaryValue"  # Classe par défaut (couleur normale)
                
                if key == 'total_revenus':
                    css_class = "summaryValuePositive"  # Vert
                    
                elif key in ['total_depenses', 'total_effectue', 'total_depenses_fixes']:
                    css_class = "summaryValueNegative"  # Rouge
                    
                elif key in ['total_non_effectue', 'total_emprunte']:
                    css_class = "summaryValueWarning"  # Orange/Jaune
                    
                elif key == 'argent_restant':
                    css_class = "summaryValueBlue"  # Bleu
                elif key == 'reste_apres_fixes':
                    if value >= 0:
                        css_class = "summaryValuePositive"  # Vert
                    else:
                        css_class = "summaryValueNegative"  # Rouge
                
                label.setProperty("cssClass", css_class)
                label.style().polish(label)

    def remove_expense_widget(self, index: int):
        if 0 <= index < len(self.expense_rows):
            row_to_remove = self.expense_rows.pop(index)
            row_to_remove.deleteLater()
            self._refresh_expense_line_numbers()

    def _refresh_expense_line_numbers(self):
        for i, row_widget in enumerate(self.expense_rows):
            layout = row_widget.layout()
            line_number_widget = layout.itemAtPosition(0, 0).widget()
            if isinstance(line_number_widget, QLabel):
                line_number_widget.setText(f"{i + 1:>3}")

    def clear_all_expenses(self):
        self.clear_expense_selection()
        while self.expense_rows:
            row = self.expense_rows.pop()
            row.deleteLater()

    def get_new_mois_input(self) -> Optional[Dict[str, str]]:
        nom, ok = QInputDialog.getText(self, "Nouveau Mois", "Entrez le nom du nouveau mois:")
        if ok and nom:
            return {"nom": nom}
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
    
    