"""
Module d'export de résultats vers différents formats
Permet d'exporter les données vers CSV et Excel
"""

import logging
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
from datetime import datetime


# Configuration du logging
logger = logging.getLogger('export')

# Dossier de sortie
OUTPUT_DIR = Path(__file__).parent.parent / 'outputs' / 'exports'


def _creer_dossier():
    """Crée le dossier d'export s'il n'existe pas"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def exporter_resultats(donnees: Any, format: str = "csv", nom_fichier: str = None) -> Dict[str, Any]:
    """
    Exporte des données vers CSV ou Excel
    
    Args:
        donnees: Données à exporter (dict, list de dicts, ou DataFrame)
        format: Format d'export ("csv" ou "excel")
        nom_fichier: Nom personnalisé (optionnel)
        
    Returns:
        Dictionnaire avec le chemin du fichier exporté
    """
    try:
        _creer_dossier()
        
        # Convertir en DataFrame si nécessaire
        if isinstance(donnees, dict):
            # Si c'est un dict simple, le mettre dans une liste
            if all(not isinstance(v, (list, dict)) for v in donnees.values()):
                donnees = [donnees]
            else:
                # Si c'est un dict avec des listes, essayer de le convertir
                donnees = pd.DataFrame(donnees)
        
        if isinstance(donnees, list):
            df = pd.DataFrame(donnees)
        elif isinstance(donnees, pd.DataFrame):
            df = donnees
        else:
            return {
                "succes": False,
                "erreur": f"Type de données non supporté: {type(donnees)}"
            }
        
        # Générer le nom de fichier
        if nom_fichier is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nom_fichier = f"export_{timestamp}"
        
        # Export selon le format
        if format.lower() == "csv":
            filepath = OUTPUT_DIR / f"{nom_fichier}.csv"
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
        elif format.lower() in ["excel", "xlsx"]:
            filepath = OUTPUT_DIR / f"{nom_fichier}.xlsx"
            df.to_excel(filepath, index=False, engine='openpyxl')
        else:
            return {
                "succes": False,
                "erreur": f"Format non supporté: {format}"
            }
        
        logger.info(
            f"Données exportées: {format}",
            extra={'extra_data': {
                'format': format,
                'nb_lignes': len(df),
                'fichier': nom_fichier
            }}
        )
        
        return {
            "succes": True,
            "format": format,
            "fichier": f"{nom_fichier}.{format.lower().replace('excel', 'xlsx')}",
            "chemin_complet": str(filepath),
            "nb_lignes": len(df),
            "nb_colonnes": len(df.columns)
        }
        
    except Exception as e:
        logger.error(f"Erreur export: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


# Test rapide
if __name__ == "__main__":
    print("Test du module d'export...")
    
    # Données de test
    data_test = [
        {"segment": "France", "pnb": 1250, "clients": 5014},
        {"segment": "Germany", "pnb": 1180, "clients": 2509},
        {"segment": "Spain", "pnb": 1320, "clients": 2477}
    ]
    
    # Test CSV
    result_csv = exporter_resultats(data_test, "csv", "test_export")
    print(f"CSV: {'✅' if result_csv['succes'] else '❌'} {result_csv.get('fichier', result_csv.get('erreur'))}")
    
    # Test Excel
    result_excel = exporter_resultats(data_test, "excel", "test_export")
    print(f"Excel: {'✅' if result_excel['succes'] else '❌'} {result_excel.get('fichier', result_excel.get('erreur'))}")
