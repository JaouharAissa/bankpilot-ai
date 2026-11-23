"""
Module de gestion de l'upload de données personnalisées
Permet aux utilisateurs de charger leurs propres fichiers CSV
"""

import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any
import pandas as pd


# Configuration du logging
logger = logging.getLogger('upload_donnees')

# Chemins
BASE_DIR = Path(__file__).parent.parent
UPLOAD_DB_PATH = BASE_DIR / 'data' / 'cdg_upload.db'


def valider_csv(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Valide qu'un CSV contient les colonnes minimales attendues
    
    Args:
        df: DataFrame pandas
        
    Returns:
        Dictionnaire avec le statut de validation
    """
    colonnes_requises_options = [
        ['segment', 'montant'],  # Minimal
        ['Geography', 'Balance'],  # Format Churn_Modelling
        ['client_id', 'pnb_simule'],  # Format pnb_analytique
    ]
    
    colonnes_df = set(df.columns.str.lower())
    
    for option in colonnes_requises_options:
        option_lower = [c.lower() for c in option]
        if all(c in colonnes_df for c in option_lower):
            return {
                "valide": True,
                "colonnes_trouvees": option,
                "message": f"Colonnes valides détectées: {', '.join(option)}"
            }
    
    return {
        "valide": False,
        "colonnes_trouvees": [],
        "message": f"Colonnes manquantes. Le CSV doit contenir au minimum: segment + montant (ou Geography + Balance, ou client_id + pnb_simule)"
    }


def creer_table_upload():
    """Crée la table pour les données uploadées"""
    conn = sqlite3.connect(UPLOAD_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS donnees_upload (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id TEXT,
            segment TEXT,
            montant REAL,
            date_upload TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()


def importer_csv_upload(df: pd.DataFrame, session_id: str = "default") -> Dict[str, Any]:
    """
    Importe un CSV uploadé dans la base de données séparée
    
    Args:
        df: DataFrame pandas
        session_id: Identifiant de session
        
    Returns:
        Dictionnaire avec le statut d'import
    """
    try:
        # Valider le CSV
        validation = valider_csv(df)
        if not validation['valide']:
            return {
                "succes": False,
                "erreur": validation['message']
            }
        
        # Créer la table si nécessaire
        creer_table_upload()
        
        # Normaliser les colonnes
        df_norm = pd.DataFrame()
        
        if 'Geography' in df.columns and 'Balance' in df.columns:
            # Format Churn_Modelling
            df_norm['segment'] = df['Geography']
            df_norm['montant'] = df['Balance']
            df_norm['client_id'] = df.get('CustomerId', range(len(df)))
        elif 'segment' in df.columns and 'montant' in df.columns:
            # Format minimal
            df_norm = df[['segment', 'montant']].copy()
            df_norm['client_id'] = range(len(df))
        else:
            # Essayer avec colonnes en minuscules
            df.columns = df.columns.str.lower()
            if 'segment' in df.columns:
                df_norm['segment'] = df['segment']
            if 'montant' in df.columns or 'balance' in df.columns:
                df_norm['montant'] = df.get('montant', df.get('balance'))
            df_norm['client_id'] = range(len(df))
        
        # Importer dans SQLite
        conn = sqlite3.connect(UPLOAD_DB_PATH)
        
        # Supprimer les anciennes données de cette session
        cursor = conn.cursor()
        cursor.execute('DELETE FROM donnees_upload')
        
        # Insérer les nouvelles données
        df_norm.to_sql('donnees_upload', conn, if_exists='append', index=False)
        
        nb_lignes = len(df_norm)
        conn.close()
        
        logger.info(
            f"Données importées: {nb_lignes} lignes",
            extra={'extra_data': {
                'nb_lignes': nb_lignes,
                'session_id': session_id
            }}
        )
        
        return {
            "succes": True,
            "nb_lignes_importees": nb_lignes,
            "colonnes": list(df_norm.columns),
            "message": f"{nb_lignes} lignes importées avec succès"
        }
        
    except Exception as e:
        logger.error(f"Erreur import CSV: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


def get_statistiques_upload() -> Dict[str, Any]:
    """
    Récupère les statistiques des données uploadées
    
    Returns:
        Dictionnaire avec les statistiques
    """
    try:
        if not UPLOAD_DB_PATH.exists():
            return {
                "succes": False,
                "erreur": "Aucune donnée uploadée"
            }
        
        conn = sqlite3.connect(UPLOAD_DB_PATH)
        cursor = conn.cursor()
        
        # Statistiques globales
        cursor.execute('SELECT COUNT(*), SUM(montant), AVG(montant) FROM donnees_upload')
        nb, total, moyenne = cursor.fetchone()
        
        # Par segment
        cursor.execute('''
            SELECT segment, COUNT(*), SUM(montant), AVG(montant)
            FROM donnees_upload
            GROUP BY segment
        ''')
        par_segment = []
        for row in cursor.fetchall():
            par_segment.append({
                'segment': row[0],
                'nombre': row[1],
                'total': row[2] or 0,
                'moyenne': row[3] or 0
            })
        
        conn.close()
        
        return {
            "succes": True,
            "nombre_total": nb or 0,
            "montant_total": total or 0,
            "montant_moyen": moyenne or 0,
            "par_segment": par_segment
        }
        
    except Exception as e:
        logger.error(f"Erreur statistiques upload: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }
