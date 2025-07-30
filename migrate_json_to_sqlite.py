# migrate_json_to_sqlite.py
"""
Script de migration pour convertir les anciens fichiers JSON vers SQLite.
À utiliser une seule fois pour migrer vos données existantes.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
import sys

def migrate_json_to_sqlite():
    """Migre tous les fichiers JSON trouvés vers SQLite."""
    
    # Chemins
    data_dir = Path.home() / ".BudgetApp"
    db_path = data_dir / "budget.db"
    
    if not data_dir.exists():
        print("Dossier .BudgetApp non trouvé. Aucune migration nécessaire.")
        return
    
    # Trouver tous les fichiers JSON
    json_files = list(data_dir.glob("*.json"))
    config_files = [f for f in json_files if f.name == "config.json"]
    budget_files = [f for f in json_files if f.name != "config.json"]
    
    if not budget_files:
        print("Aucun fichier JSON de budget trouvé.")
        return
    
    print(f"Fichiers JSON trouvés : {[f.name for f in budget_files]}")
    
    # Initialiser la base de données
    init_database(db_path)
    
    # Migrer chaque fichier
    migrated_count = 0
    for json_file in budget_files:
        success = migrate_single_file(json_file, db_path)
        if success:
            migrated_count += 1
    
    print(f"\nMigration terminée : {migrated_count}/{len(budget_files)} fichiers migrés.")
    
    # Sauvegarder les anciens fichiers
    backup_dir = data_dir / "backup_json"
    backup_dir.mkdir(exist_ok=True)
    
    for json_file in budget_files + config_files:
        backup_path = backup_dir / json_file.name
        json_file.rename(backup_path)
        print(f"Fichier {json_file.name} sauvegardé dans backup_json/")

def init_database(db_path):
    """Initialise la base de données SQLite."""
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Création de la table mois
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS mois (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nom TEXT UNIQUE NOT NULL,
                salaire REAL NOT NULL DEFAULT 0.0,
                date_creation TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Création de la table depenses
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS depenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mois_id INTEGER NOT NULL,
                nom TEXT NOT NULL DEFAULT '',
                montant REAL NOT NULL DEFAULT 0.0,
                categorie TEXT NOT NULL DEFAULT 'Autres',
                effectue BOOLEAN NOT NULL DEFAULT 0,
                emprunte BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (mois_id) REFERENCES mois (id) ON DELETE CASCADE
            )
        ''')
        
        # Création de la table de configuration
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config (
                cle TEXT PRIMARY KEY,
                valeur TEXT NOT NULL
            )
        ''')
        
        conn.commit()

def migrate_single_file(json_file, db_path):
    """Migre un seul fichier JSON vers SQLite."""
    try:
        # Lire le fichier JSON
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extraire le nom du mois depuis le nom du fichier
        # Ex: "budget_data_Juin.json" -> "Juin"
        mois_name = json_file.stem.replace("budget_data_", "").replace("budget_", "")
        if not mois_name or mois_name == json_file.stem:
            # Si on n'arrive pas à extraire le nom, utiliser le nom complet
            mois_name = json_file.stem
        
        salaire = data.get('salaire', 0.0)
        depenses_data = data.get('depenses', [])
        
        print(f"\nMigration de {json_file.name} -> Mois: '{mois_name}', Salaire: {salaire}€, Dépenses: {len(depenses_data)}")
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Créer le mois
            try:
                cursor.execute(
                    'INSERT INTO mois (nom, salaire, date_creation) VALUES (?, ?, ?)',
                    (mois_name, salaire, datetime.now().isoformat())
                )
                mois_id = cursor.lastrowid
            except sqlite3.IntegrityError:
                # Le mois existe déjà, demander à l'utilisateur
                print(f"Le mois '{mois_name}' existe déjà.")
                response = input("Voulez-vous le remplacer ? (o/n): ").lower()
                if response == 'o':
                    cursor.execute('DELETE FROM mois WHERE nom = ?', (mois_name,))
                    cursor.execute(
                        'INSERT INTO mois (nom, salaire, date_creation) VALUES (?, ?, ?)',
                        (mois_name, salaire, datetime.now().isoformat())
                    )
                    mois_id = cursor.lastrowid
                else:
                    print(f"Migration de {json_file.name} ignorée.")
                    return False
            
            # Ajouter les dépenses
            for depense in depenses_data:
                cursor.execute('''
                    INSERT INTO depenses (mois_id, nom, montant, categorie, effectue, emprunte)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    mois_id,
                    depense.get('nom', ''),
                    depense.get('montant', 0.0),
                    depense.get('categorie', 'Autres'),
                    depense.get('effectue', False),
                    depense.get('emprunte', False)
                ))
            
            conn.commit()
            print(f"✓ Migration réussie : {len(depenses_data)} dépenses ajoutées.")
            return True
            
    except Exception as e:
        print(f"✗ Erreur lors de la migration de {json_file.name}: {e}")
        return False

def main():
    print("=== Migration JSON vers SQLite ===")
    print("Ce script va migrer vos fichiers JSON existants vers la nouvelle base SQLite.")
    print("Les anciens fichiers seront sauvegardés dans le dossier backup_json/")
    
    response = input("\nContinuer ? (o/n): ").lower()
    if response != 'o':
        print("Migration annulée.")
        return
    
    migrate_json_to_sqlite()
    print("\n=== Migration terminée ===")

if __name__ == "__main__":
    main()
