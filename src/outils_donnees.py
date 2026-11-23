"""
Outils de requêtage sécurisé des données pour l'assistant Contrôleur de Gestion
Toutes les fonctions utilisent des requêtes SQL paramétrées (jamais de concaténation)
Mode lecture seule strict avec gestion d'erreurs
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Any


# Chemin de la base de données
DB_PATH = Path(__file__).parent.parent / 'data' / 'cdg_test.db'


def _executer_requete(requete_sql: str, parametres: tuple = ()) -> List[Dict[str, Any]]:
    """
    Fonction utilitaire pour exécuter une requête SQL de manière sécurisée
    
    Args:
        requete_sql: Requête SQL avec placeholders (?)
        parametres: Tuple des paramètres à injecter de manière sécurisée
        
    Returns:
        Liste de dictionnaires représentant les résultats
        
    Raises:
        Exception: Si erreur de connexion ou d'exécution
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Pour obtenir des résultats sous forme de dictionnaires
        cursor = conn.cursor()
        
        # Exécution de la requête paramétrée (protection contre SQL injection)
        cursor.execute(requete_sql, parametres)
        
        # Récupération des résultats
        resultats = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        return resultats
        
    except sqlite3.Error as e:
        raise Exception(f"Erreur lors de l'exécution de la requête: {e}")


def get_pnb_par_segment(segment: str) -> Dict[str, Any]:
    """
    Récupère les statistiques de PNB pour un segment géographique donné
    
    Args:
        segment: Nom du segment (ex: 'France', 'Germany', 'Spain')
        
    Returns:
        Dictionnaire avec statistiques du segment ou message d'erreur
    """
    # Validation du paramètre
    if not segment or not isinstance(segment, str):
        return {
            "erreur": "Le paramètre 'segment' doit être une chaîne non vide",
            "donnees_trouvees": False
        }
    
    # Requête SQL paramétrée (le ? est remplacé de manière sécurisée)
    requete = """
        SELECT 
            segment,
            COUNT(*) as nombre_clients,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(MIN(pnb_simule), 2) as pnb_min,
            ROUND(MAX(pnb_simule), 2) as pnb_max
        FROM pnb_analytique
        WHERE segment = ?
        GROUP BY segment
    """
    
    try:
        resultats = _executer_requete(requete, (segment,))
        
        if not resultats:
            return {
                "erreur": f"Aucune donnée trouvée pour le segment '{segment}'",
                "segments_disponibles": _obtenir_segments_disponibles(),
                "donnees_trouvees": False
            }
        
        return {
            "donnees_trouvees": True,
            "segment": resultats[0]['segment'],
            "nombre_clients": resultats[0]['nombre_clients'],
            "pnb_moyen": resultats[0]['pnb_moyen'],
            "pnb_total": resultats[0]['pnb_total'],
            "pnb_min": resultats[0]['pnb_min'],
            "pnb_max": resultats[0]['pnb_max']
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la récupération des données: {str(e)}",
            "donnees_trouvees": False
        }


def get_rentabilite_par_produit(nb_produits: int) -> Dict[str, Any]:
    """
    Récupère les statistiques de rentabilité pour un nombre de produits donné
    
    Args:
        nb_produits: Nombre de produits détenus par les clients (1, 2, 3, 4)
        
    Returns:
        Dictionnaire avec statistiques de rentabilité ou message d'erreur
    """
    # Validation du paramètre
    if not isinstance(nb_produits, int) or nb_produits < 1:
        return {
            "erreur": "Le paramètre 'nb_produits' doit être un entier positif",
            "donnees_trouvees": False
        }
    
    requete = """
        SELECT 
            produit,
            COUNT(*) as nombre_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(AVG(cout_simule), 2) as cout_moyen
        FROM pnb_analytique
        WHERE produit = ?
        GROUP BY produit
    """
    
    try:
        resultats = _executer_requete(requete, (nb_produits,))
        
        if not resultats:
            return {
                "erreur": f"Aucune donnée trouvée pour {nb_produits} produit(s)",
                "donnees_trouvees": False
            }
        
        return {
            "donnees_trouvees": True,
            "nombre_produits": resultats[0]['produit'],
            "nombre_clients": resultats[0]['nombre_clients'],
            "rentabilite_moyenne": resultats[0]['rentabilite_moyenne'],
            "rentabilite_totale": resultats[0]['rentabilite_totale'],
            "pnb_moyen": resultats[0]['pnb_moyen'],
            "cout_moyen": resultats[0]['cout_moyen']
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la récupération des données: {str(e)}",
            "donnees_trouvees": False
        }


def get_rentabilite_par_segment(segment: str) -> Dict[str, Any]:
    """
    Récupère les statistiques de rentabilité pour un segment géographique donné
    
    Args:
        segment: Nom du segment (ex: 'France', 'Germany', 'Spain')
        
    Returns:
        Dictionnaire avec statistiques de rentabilité ou message d'erreur
    """
    if not segment or not isinstance(segment, str):
        return {
            "erreur": "Le paramètre 'segment' doit être une chaîne non vide",
            "donnees_trouvees": False
        }
    
    requete = """
        SELECT 
            segment,
            COUNT(*) as nombre_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(AVG(cout_simule), 2) as cout_moyen,
            ROUND(AVG(rentabilite) / AVG(pnb_simule) * 100, 2) as marge_pourcent
        FROM pnb_analytique
        WHERE segment = ?
        GROUP BY segment
    """
    
    try:
        resultats = _executer_requete(requete, (segment,))
        
        if not resultats:
            return {
                "erreur": f"Aucune donnée trouvée pour le segment '{segment}'",
                "segments_disponibles": _obtenir_segments_disponibles(),
                "donnees_trouvees": False
            }
        
        return {
            "donnees_trouvees": True,
            "segment": resultats[0]['segment'],
            "nombre_clients": resultats[0]['nombre_clients'],
            "rentabilite_moyenne": resultats[0]['rentabilite_moyenne'],
            "rentabilite_totale": resultats[0]['rentabilite_totale'],
            "pnb_moyen": resultats[0]['pnb_moyen'],
            "cout_moyen": resultats[0]['cout_moyen'],
            "marge_pourcent": resultats[0]['marge_pourcent']
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la récupération des données: {str(e)}",
            "donnees_trouvees": False
        }


def comparer_segments(segment_a: str, segment_b: str) -> Dict[str, Any]:
    """
    Compare les performances de deux segments géographiques
    
    Args:
        segment_a: Nom du premier segment
        segment_b: Nom du second segment
        
    Returns:
        Dictionnaire avec comparaison des deux segments ou message d'erreur
    """
    if not segment_a or not segment_b:
        return {
            "erreur": "Les deux paramètres 'segment_a' et 'segment_b' doivent être fournis",
            "donnees_trouvees": False
        }
    
    requete = """
        SELECT 
            segment,
            COUNT(*) as nombre_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(AVG(cout_simule), 2) as cout_moyen
        FROM pnb_analytique
        WHERE segment IN (?, ?)
        GROUP BY segment
        ORDER BY segment
    """
    
    try:
        resultats = _executer_requete(requete, (segment_a, segment_b))
        
        if len(resultats) < 2:
            segments_trouves = [r['segment'] for r in resultats]
            segments_manquants = []
            if segment_a not in segments_trouves:
                segments_manquants.append(segment_a)
            if segment_b not in segments_trouves:
                segments_manquants.append(segment_b)
            
            return {
                "erreur": f"Segments non trouvés: {', '.join(segments_manquants)}",
                "segments_disponibles": _obtenir_segments_disponibles(),
                "donnees_trouvees": False
            }
        
        # Organiser les résultats par segment
        comparaison = {}
        for resultat in resultats:
            comparaison[resultat['segment']] = {
                "nombre_clients": resultat['nombre_clients'],
                "rentabilite_moyenne": resultat['rentabilite_moyenne'],
                "rentabilite_totale": resultat['rentabilite_totale'],
                "pnb_moyen": resultat['pnb_moyen'],
                "cout_moyen": resultat['cout_moyen']
            }
        
        # Calculer les différences
        seg_a_data = comparaison[resultats[0]['segment']]
        seg_b_data = comparaison[resultats[1]['segment']]
        
        return {
            "donnees_trouvees": True,
            "segment_a": {
                "nom": resultats[0]['segment'],
                **seg_a_data
            },
            "segment_b": {
                "nom": resultats[1]['segment'],
                **seg_b_data
            },
            "differences": {
                "rentabilite_moyenne": round(seg_a_data['rentabilite_moyenne'] - seg_b_data['rentabilite_moyenne'], 2),
                "pnb_moyen": round(seg_a_data['pnb_moyen'] - seg_b_data['pnb_moyen'], 2),
                "nombre_clients": seg_a_data['nombre_clients'] - seg_b_data['nombre_clients']
            }
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la comparaison: {str(e)}",
            "donnees_trouvees": False
        }


def get_statistiques_globales() -> Dict[str, Any]:
    """
    Récupère les statistiques globales du portefeuille client
    
    Returns:
        Dictionnaire avec statistiques globales ou message d'erreur
    """
    requete_globale = """
        SELECT 
            COUNT(*) as nombre_total_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(AVG(cout_simule), 2) as cout_moyen,
            ROUND(SUM(cout_simule), 2) as cout_total,
            ROUND(AVG(anciennete), 2) as anciennete_moyenne
        FROM pnb_analytique
    """
    
    requete_par_segment = """
        SELECT 
            segment,
            COUNT(*) as nombre_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(SUM(pnb_simule), 2) as pnb_total
        FROM pnb_analytique
        GROUP BY segment
        ORDER BY rentabilite_moyenne DESC
    """
    
    requete_par_produit = """
        SELECT 
            produit,
            COUNT(*) as nombre_clients,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne,
            ROUND(SUM(rentabilite), 2) as rentabilite_totale,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(SUM(pnb_simule), 2) as pnb_total
        FROM pnb_analytique
        GROUP BY produit
        ORDER BY produit
    """
    
    try:
        stats_globales = _executer_requete(requete_globale)
        stats_segments = _executer_requete(requete_par_segment)
        stats_produits = _executer_requete(requete_par_produit)
        
        if not stats_globales:
            return {
                "erreur": "Aucune donnée disponible dans la base",
                "donnees_trouvees": False
            }
        
        g = dict(stats_globales[0])
        g['nombre_clients_total'] = g.get('nombre_total_clients', 10000)
        g['nombre_total_clients'] = g.get('nombre_total_clients', 10000)
        
        return {
            "donnees_trouvees": True,
            "global": g,
            "statistiques_generales": g,
            "par_segment": stats_segments,
            "par_produit": stats_produits
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la récupération des statistiques: {str(e)}",
            "donnees_trouvees": False
        }


def _obtenir_segments_disponibles() -> List[str]:
    """
    Fonction utilitaire pour lister les segments disponibles
    
    Returns:
        Liste des noms de segments
    """
    try:
        requete = "SELECT DISTINCT segment FROM pnb_analytique ORDER BY segment"
        resultats = _executer_requete(requete)
        return [r['segment'] for r in resultats]
    except:
        return []


# Test rapide des fonctions si exécuté directement
if __name__ == "__main__":
    print("Test des outils de données...\n")
    
    print("1. Statistiques globales:")
    print(get_statistiques_globales())
    print("\n" + "="*70 + "\n")
    
    print("2. PNB par segment (France):")
    print(get_pnb_par_segment("France"))
    print("\n" + "="*70 + "\n")
    
    print("3. Rentabilité par produit (2 produits):")
    print(get_rentabilite_par_produit(2))
    print("\n" + "="*70 + "\n")
    
    print("4. Comparaison France vs Germany:")
    print(comparer_segments("France", "Germany"))
