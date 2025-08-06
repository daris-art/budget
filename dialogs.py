# dialogs.py - Boîtes de dialogue personnalisées pour l'application

import tkinter as tk
from tkinter import ttk
from datetime import datetime
from typing import List, Optional

from utils import Mois

class Tooltip:
    """Classe utilitaire pour les infobulles"""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event):
        try:
            x, y, cx, cy = self.widget.bbox("insert")
            x += self.widget.winfo_rootx() + 20
            y += self.widget.winfo_rooty() + 20
            self.tooltip = tk.Toplevel(self.widget)
            self.tooltip.wm_overrideredirect(True)
            label = tk.Label(self.tooltip, text=self.text, bg="lightyellow", 
                           relief=tk.SOLID, borderwidth=1)
            label.pack()
            self.tooltip.wm_geometry("+%d+%d" % (x, y))
        except tk.TclError:
            pass

    def hide(self, event):
        if self.tooltip:
            try:
                self.tooltip.destroy()
                self.tooltip = None
            except tk.TclError:
                pass

class MoisSelectionDialog:
    """Boîte de dialogue pour la sélection d'un mois"""
    
    def __init__(self, parent, mois_list: List[Mois], title: str, prompt: str):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("500x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (400 // 2)
        self.dialog.geometry(f"500x400+{x}+{y}")
        
        tk.Label(self.dialog, text=prompt, pady=10, font=("Arial", 12)).pack()
        
        self.listbox = tk.Listbox(self.dialog, selectmode=tk.SINGLE, font=("Arial", 10))
        for mois in mois_list:
            display_text = f"{mois.nom} (Salaire: {mois.salaire:.2f}€)"
            if mois.date_creation:
                try:
                    date_obj = datetime.fromisoformat(mois.date_creation.split(' ')[0])
                    date_str = date_obj.strftime("%d/%m/%Y")
                    display_text += f" - Créé le {date_str}"
                except (ValueError, IndexError):
                    pass
            self.listbox.insert('end', display_text)
        
        self.listbox.pack(fill='both', expand=True, padx=10, pady=5)
        
        button_frame = ttk.Frame(self.dialog)
        button_frame.pack(pady=10)
        
        ttk.Button(button_frame, text="Sélectionner", command=self._on_select).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Annuler", command=self._on_cancel).pack(side='left', padx=5)
        
        self.listbox.bind('<Double-Button-1>', lambda e: self._on_select())
        
        self.listbox.focus_set()
        if mois_list:
            self.listbox.selection_set(0)
        
        self.mois_list = mois_list
        self.dialog.wait_window()
    
    def _on_select(self):
        selection = self.listbox.curselection()
        if selection:
            self.result = self.mois_list[selection[0]]
        self.dialog.destroy()
    
    def _on_cancel(self):
        self.dialog.destroy()
