# graph_view.py (Version avec fermeture sur 'Échap')

from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTabWidget, QWidget, QPushButton, QHBoxLayout
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

class GraphDialog(QDialog):
    """
    Fenêtre de dialogue pour afficher les graphiques financiers.
    """
    def __init__(self, graph_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Graphiques du Mois")
        self.setMinimumSize(800, 600)
        # effet plus fluide
        self.setWindowOpacity(0.95)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint)

        # On récupère les données fournies par le contrôleur
        self.labels_by_name, self.values_by_name, _, self.categories_data, self.monthly_data, self.first_word_data = graph_data
        
        # Le conteneur principal de la fenêtre
        main_layout = QVBoxLayout(self)
        
        # On utilise un système d'onglets pour afficher plusieurs graphiques
        tab_widget = QTabWidget()
        main_layout.addWidget(tab_widget)

        # Création et ajout des onglets
        tab_widget.addTab(self._create_pie_chart_tab(), "Dépenses par Catégorie")
        tab_widget.addTab(self._create_bar_chart_tab(), "Top 10 Dépenses (Barres)")
        tab_widget.addTab(self._create_top_expenses_pie_chart_tab(), "Top Dépenses (Camembert)")
        tab_widget.addTab(self._create_first_word_pie_chart_tab(), "Dépenses par Premier Mot")
        tab_widget.addTab(self._create_monthly_trends_tab(), "Tendances Mensuelles")

        button_layout = QHBoxLayout()
        close_button = QPushButton("Fermer")
        close_button.clicked.connect(self.reject)
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        main_layout.addLayout(button_layout)

    def _create_pie_chart_tab(self) -> QWidget:
        """Crée l'onglet contenant le graphique en camembert des catégories."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        fig = Figure(figsize=(5, 5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        ax = fig.add_subplot(111)
        
        cat_labels = list(self.categories_data.keys())
        cat_values = list(self.categories_data.values())

        ax.pie(cat_values, labels=cat_labels, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        ax.set_title("Répartition des Dépenses par Catégorie", pad=20)
        
        fig.tight_layout()
        
        return tab

    def _create_bar_chart_tab(self) -> QWidget:
        """Crée l'onglet contenant le graphique en barres des 10 plus grosses dépenses."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(5, 5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        ax = fig.add_subplot(111)

        expenses = sorted(zip(self.values_by_name, self.labels_by_name), reverse=True)
        top_10_expenses = expenses[:10]
        
        if top_10_expenses:
            top_values, top_labels = zip(*top_10_expenses)
            top_labels = list(reversed(top_labels))
            top_values = list(reversed(top_values))

            ax.barh(top_labels, top_values, color='skyblue')
            ax.set_xlabel('Montant (€)')
            ax.set_title('Top 10 des plus grosses Dépenses')
            
            fig.tight_layout()

        return tab

    def _create_top_expenses_pie_chart_tab(self) -> QWidget:
        """Crée l'onglet pour le camembert des 10 plus grosses dépenses + 'Autres'."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(5, 5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        ax = fig.add_subplot(111)

        expenses = sorted(zip(self.values_by_name, self.labels_by_name), reverse=True)
        
        chart_labels = []
        chart_values = []
        
        if len(expenses) > 10:
            top_10 = expenses[:10]
            others = expenses[10:]
            
            top_values, top_labels = zip(*top_10)
            chart_labels.extend(list(top_labels))
            chart_values.extend(list(top_values))
            
            sum_of_others = sum(value for value, label in others)
            
            if sum_of_others > 0:
                chart_labels.append("Autres Dépenses")
                chart_values.append(sum_of_others)
        else:
            if expenses:
                chart_values, chart_labels = zip(*expenses)

        if chart_values:
            wedges, _, autotexts = ax.pie(chart_values, autopct='%1.1f%%', startangle=90, textprops=dict(color="w"))
            
            total = sum(chart_values)
            legend_labels = [
                f"{label} ({value/total:.1%})" 
                for label, value in zip(chart_labels, chart_values)
            ]

            ax.legend(wedges, legend_labels,
                      title="Dépenses",
                      loc="center left",
                      bbox_to_anchor=(1, 0, 0.5, 1))

            ax.set_title("Répartition des 10 plus grosses dépenses", pad=20)
        
        fig.tight_layout()
        return tab

    def _create_first_word_pie_chart_tab(self) -> QWidget:
        """Crée un onglet pour le camembert des dépenses regroupées par premier mot du nom."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        fig = Figure(figsize=(5, 5))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)

        ax = fig.add_subplot(111)

        labels = list(self.first_word_data.keys())
        values = list(self.first_word_data.values())

        if values:
            wedges, texts, autotexts = ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, textprops=dict(color='w'))
            total = sum(values)
            legend_labels = [f"{label} ({value/total:.1%})" for label, value in zip(labels, values)]
            ax.legend(wedges, legend_labels,
                      title="Premier mot",
                      loc="center left",
                      bbox_to_anchor=(1, 0, 0.5, 1))
            ax.set_title("Répartition des Dépenses par Premier Mot du Nom", pad=20)
            ax.axis('equal')

        fig.tight_layout()
        return tab

    def _create_monthly_trends_tab(self) -> QWidget:
        """Crée un onglet avec un graphique montrant l'évolution mensuelle des revenus, dépenses et de l'épargne."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        fig = Figure(figsize=(8, 6))
        canvas = FigureCanvas(fig)
        layout.addWidget(canvas)
        
        ax = fig.add_subplot(111)

        # Les données sont un dictionnaire avec les clés 'mois', 'revenus' et 'depenses'
        months = [data['mois'] for data in self.monthly_data]
        revenues = [data['revenus'] for data in self.monthly_data]
        expenses = [data['depenses'] for data in self.monthly_data]
        net_balance = [rev - exp for rev, exp in zip(revenues, expenses)]

        x = range(len(months))
        width = 0.25

        ax.bar([i - width for i in x], revenues, width, label='Revenus', color='g', alpha=0.7)
        ax.bar(x, expenses, width, label='Dépenses', color='r', alpha=0.7)
        ax.bar([i + width for i in x], net_balance, width, label='Solde Net', color='b', alpha=0.7)

        ax.set_title("Tendances Financières Mensuelles", pad=20)
        ax.set_ylabel("Montant (€)")
        ax.set_xlabel("Mois")
        ax.set_xticks(x)
        ax.set_xticklabels(months, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', linestyle='--', alpha=0.6)
        
        fig.tight_layout()
        
        return tab
        
    def keyPressEvent(self, event: QKeyEvent):
        """Ferme la fenêtre si la touche 'Échap' est pressée."""
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
