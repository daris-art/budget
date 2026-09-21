"""Fenêtre de pilotage des dépenses et de l'épargne du mois sélectionné."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QDoubleSpinBox, QFormLayout,
    QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QMessageBox,
)
from core.budget_planning import analyze_budget


class BudgetPlanningDialog(QDialog):
    def __init__(self, month_name, expenses, categories, plan, save_plan, parent=None):
        super().__init__(parent)
        self.expenses = expenses
        self.save_plan = save_plan
        self.setWindowTitle(f'Dépenses et épargne — {month_name}')
        self.resize(850, 620)
        layout = QVBoxLayout(self)
        explanation = QLabel(
            'Bilan du mois entier, sans les filtres de recherche. Les montants incluent '
            'les opérations effectuées et prévues. Seules les opérations saisies sont prises en compte. '
            'Les débits « Épargne » sont des versements, séparés des dépenses courantes.')
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        form = QFormLayout()
        self.goal = self.amount_input(plan.get('savings_goal', 0))
        form.addRow("Objectif d'épargne du mois :", self.goal)
        layout.addLayout(form)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        layout.addWidget(QLabel('Plafonds du mois par catégorie (0 = aucun plafond)'))
        actual_categories = {d.categorie for d in expenses if not d.est_credit}
        spending_by_category = analyze_budget(expenses)['categories']
        self.categories = sorted(
            (set(categories) | actual_categories) - {'Revenue', 'Épargne'},
            key=lambda category: (-spending_by_category.get(category, 0), category.casefold()),
        )
        self.table = QTableWidget(len(self.categories), 4)
        self.table.setHorizontalHeaderLabels(['Catégorie', 'Dépenses saisies', 'Plafond', 'Situation'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.limits = {}
        for row, category in enumerate(self.categories):
            self.table.setItem(row, 0, QTableWidgetItem(category))
            limit = self.amount_input(plan.get('limits', {}).get(category, 0))
            self.limits[category] = limit
            self.table.setCellWidget(row, 2, limit)
            limit.valueChanged.connect(self.refresh)
        layout.addWidget(self.table)
        self.save_button = QPushButton('Enregistrer les objectifs de ce mois')
        self.save_button.clicked.connect(self.save)
        layout.addWidget(self.save_button)
        self.close_button = QPushButton('Fermer')
        self.close_button.clicked.connect(self.reject)
        layout.addWidget(self.close_button)
        self.goal.valueChanged.connect(self.refresh)
        self.refresh()

    @staticmethod
    def amount_input(value):
        widget = QDoubleSpinBox()
        widget.setRange(0, 999999999.99)
        widget.setDecimals(2)
        widget.setSuffix(' €')
        widget.setValue(float(value))
        return widget

    def refresh(self):
        result = analyze_budget(self.expenses, self.goal.value())
        available = result['available']
        balance = (f'Marge après réservation de l’épargne : {available:.2f} €'
                   if available >= 0 else f'Budget à rééquilibrer : {-available:.2f} € manquants')
        self.summary.setText(
            f"Revenus saisis : {result['income']:.2f} €  |  Dépenses courantes : {result['spending']:.2f} €\n"
            f"Épargne effectuée : {result['savings_paid']:.2f} €  |  Prévue : {result['savings_planned']:.2f} €\n"
            f"Versements restant à prévoir pour l’objectif : {result['savings_missing']:.2f} €\n"
            f'{balance}\nCette marge est un bilan prévisionnel, pas le solde bancaire disponible.')
        for row, category in enumerate(self.categories):
            spent = result['categories'].get(category, 0)
            limit = self.limits[category].value()
            remaining = round(limit - float(spent), 2)
            status = 'Sans plafond'
            if limit > 0:
                status = (f'Dépassement : {-remaining:.2f} €' if remaining < 0
                          else f'Reste : {remaining:.2f} €')
            self.table.setItem(row, 1, QTableWidgetItem(f'{spent:.2f} €'))
            self.table.setItem(row, 3, QTableWidgetItem(status))
        self.save_button.setText('Enregistrer les objectifs de ce mois')

    def save(self):
        plan = {'savings_goal': self.goal.value(),
                'limits': {category: widget.value() for category, widget in self.limits.items()}}
        try:
            self.save_plan(plan)
        except Exception as exc:
            QMessageBox.warning(self, 'Enregistrement impossible', str(exc))
            return
        self.save_button.setText('Objectifs enregistrés')
