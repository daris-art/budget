"""Calculs mensuels : les crédits sont les revenus, l'épargne est un transfert."""
from collections import defaultdict
from decimal import Decimal


def analyze_budget(expenses, savings_goal=0):
    income = Decimal('0')
    savings_paid = Decimal('0')
    savings_planned = Decimal('0')
    categories = defaultdict(lambda: Decimal('0'))
    for expense in expenses:
        amount = Decimal(str(expense.montant))
        if expense.est_credit:
            income += amount
        elif expense.categorie == 'Épargne':
            if expense.effectue:
                savings_paid += amount
            else:
                savings_planned += amount
        else:
            categories[expense.categorie] += amount
    spending = sum(categories.values(), Decimal('0'))
    savings = savings_paid + savings_planned
    goal = Decimal(str(savings_goal))
    # Ne pas réserver une deuxième fois les versements déjà saisis.
    available = income - spending - max(goal, savings)
    return dict(income=income, spending=spending, categories=dict(categories),
                savings_paid=savings_paid, savings_planned=savings_planned,
                savings_missing=max(Decimal('0'), goal - savings),
                available=available)
