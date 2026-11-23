"""
Module de détection de tendances et signaux faibles
Analyse purement statistique (pas de LLM) sur les données de la base SQLite
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Any


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
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(requete_sql, parametres)
        resultats = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return resultats
    except sqlite3.Error as e:
        raise Exception(f"Erreur lors de l'exécution de la requête: {e}")


def detecter_evolution(segment: str, periode_actuelle: str, periode_precedente: str) -> Dict[str, Any]:
    """
    Calcule le % de variation du PNB entre deux périodes pour un segment donné
    
    Args:
        segment: Nom du segment (France, Germany, Spain)
        periode_actuelle: Période actuelle (ex: "T4-2024")
        periode_precedente: Période précédente (ex: "T3-2024")
        
    Returns:
        Dictionnaire structuré avec l'évolution détaillée
    """
    # Validation des paramètres
    if not all([segment, periode_actuelle, periode_precedente]):
        return {
            "erreur": "Tous les paramètres sont requis",
            "donnees_trouvees": False
        }
    
    # Requête pour la période actuelle
    requete_actuelle = """
        SELECT 
            segment,
            periode,
            COUNT(*) as nombre_clients,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen
        FROM pnb_analytique
        WHERE segment = ? AND periode = ?
        GROUP BY segment, periode
    """
    
    # Requête pour la période précédente
    requete_precedente = """
        SELECT 
            segment,
            periode,
            COUNT(*) as nombre_clients,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen
        FROM pnb_analytique
        WHERE segment = ? AND periode = ?
        GROUP BY segment, periode
    """
    
    try:
        resultats_actuels = _executer_requete(requete_actuelle, (segment, periode_actuelle))
        resultats_precedents = _executer_requete(requete_precedente, (segment, periode_precedente))
        
        if not resultats_actuels or not resultats_precedents:
            return {
                "erreur": f"Données manquantes pour {segment} sur les périodes demandées",
                "donnees_trouvees": False,
                "periode_actuelle_trouvee": len(resultats_actuels) > 0,
                "periode_precedente_trouvee": len(resultats_precedents) > 0
            }
        
        donnees_actuelles = resultats_actuels[0]
        donnees_precedentes = resultats_precedents[0]
        
        # Calcul des variations
        variation_pnb_total = donnees_actuelles['pnb_total'] - donnees_precedentes['pnb_total']
        variation_pnb_moyen = donnees_actuelles['pnb_moyen'] - donnees_precedentes['pnb_moyen']
        
        # Calcul des pourcentages (éviter division par zéro)
        pct_variation_total = 0
        pct_variation_moyen = 0
        
        if donnees_precedentes['pnb_total'] > 0:
            pct_variation_total = round((variation_pnb_total / donnees_precedentes['pnb_total']) * 100, 2)
        
        if donnees_precedentes['pnb_moyen'] > 0:
            pct_variation_moyen = round((variation_pnb_moyen / donnees_precedentes['pnb_moyen']) * 100, 2)
        
        return {
            "donnees_trouvees": True,
            "indicateur": f"Evolution PNB - {segment}",
            "segment": segment,
            "periode_actuelle": periode_actuelle,
            "periode_precedente": periode_precedente,
            "valeur_actuelle": {
                "pnb_total": donnees_actuelles['pnb_total'],
                "pnb_moyen": donnees_actuelles['pnb_moyen'],
                "nombre_clients": donnees_actuelles['nombre_clients']
            },
            "valeur_precedente": {
                "pnb_total": donnees_precedentes['pnb_total'],
                "pnb_moyen": donnees_precedentes['pnb_moyen'],
                "nombre_clients": donnees_precedentes['nombre_clients']
            },
            "variation_absolue": {
                "pnb_total": round(variation_pnb_total, 2),
                "pnb_moyen": round(variation_pnb_moyen, 2)
            },
            "variation_pourcentage": {
                "pnb_total": pct_variation_total,
                "pnb_moyen": pct_variation_moyen
            }
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors du calcul de l'évolution: {str(e)}",
            "donnees_trouvees": False
        }


def detecter_signaux_faibles(seuil_pourcentage: float = 10.0, periode_actuelle: str = "T4-2024", 
                             periode_precedente: str = "T3-2024") -> Dict[str, Any]:
    """
    Détecte tous les segments/produits dont la variation dépasse le seuil (positif ou négatif)
    
    Args:
        seuil_pourcentage: Seuil de variation en % (défaut: 10%)
        periode_actuelle: Période actuelle (défaut: "T4-2024")
        periode_precedente: Période précédente (défaut: "T3-2024")
        
    Returns:
        Dictionnaire avec tous les signaux faibles détectés
    """
    # Requête pour analyser les segments
    requete_segments = """
        SELECT 
            segment,
            periode,
            COUNT(*) as nombre_clients,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne
        FROM pnb_analytique
        WHERE periode IN (?, ?)
        GROUP BY segment, periode
        ORDER BY segment, periode
    """
    
    # Requête pour analyser les produits
    requete_produits = """
        SELECT 
            produit,
            periode,
            COUNT(*) as nombre_clients,
            ROUND(SUM(pnb_simule), 2) as pnb_total,
            ROUND(AVG(pnb_simule), 2) as pnb_moyen,
            ROUND(AVG(rentabilite), 2) as rentabilite_moyenne
        FROM pnb_analytique
        WHERE periode IN (?, ?)
        GROUP BY produit, periode
        ORDER BY produit, periode
    """
    
    try:
        resultats_segments = _executer_requete(requete_segments, (periode_precedente, periode_actuelle))
        resultats_produits = _executer_requete(requete_produits, (periode_precedente, periode_actuelle))
        
        signaux = []
        
        # Analyser les segments
        segments_data = {}
        for row in resultats_segments:
            key = row['segment']
            if key not in segments_data:
                segments_data[key] = {}
            segments_data[key][row['periode']] = row
        
        for segment, periodes in segments_data.items():
            if periode_actuelle in periodes and periode_precedente in periodes:
                actuel = periodes[periode_actuelle]
                precedent = periodes[periode_precedente]
                
                if precedent['pnb_total'] > 0:
                    variation_pct = round(
                        ((actuel['pnb_total'] - precedent['pnb_total']) / precedent['pnb_total']) * 100, 
                        2
                    )
                    
                    if abs(variation_pct) >= seuil_pourcentage:
                        signaux.append({
                            "type": "segment",
                            "dimension": segment,
                            "indicateur": "PNB Total",
                            "valeur_actuelle": actuel['pnb_total'],
                            "valeur_precedente": precedent['pnb_total'],
                            "variation_absolue": round(actuel['pnb_total'] - precedent['pnb_total'], 2),
                            "variation_pourcentage": variation_pct,
                            "signal_faible": True,
                            "tendance": "hausse" if variation_pct > 0 else "baisse",
                            "severite": "forte" if abs(variation_pct) >= 20 else "moyenne",
                            "periode_actuelle": periode_actuelle,
                            "periode_precedente": periode_precedente,
                            "nombre_clients_actuel": actuel['nombre_clients']
                        })
        
        # Analyser les produits
        produits_data = {}
        for row in resultats_produits:
            key = row['produit']
            if key not in produits_data:
                produits_data[key] = {}
            produits_data[key][row['periode']] = row
        
        for produit, periodes in produits_data.items():
            if periode_actuelle in periodes and periode_precedente in periodes:
                actuel = periodes[periode_actuelle]
                precedent = periodes[periode_precedente]
                
                if precedent['pnb_total'] > 0:
                    variation_pct = round(
                        ((actuel['pnb_total'] - precedent['pnb_total']) / precedent['pnb_total']) * 100,
                        2
                    )
                    
                    if abs(variation_pct) >= seuil_pourcentage:
                        signaux.append({
                            "type": "produit",
                            "dimension": f"{produit} produit(s)",
                            "indicateur": "PNB Total",
                            "valeur_actuelle": actuel['pnb_total'],
                            "valeur_precedente": precedent['pnb_total'],
                            "variation_absolue": round(actuel['pnb_total'] - precedent['pnb_total'], 2),
                            "variation_pourcentage": variation_pct,
                            "signal_faible": True,
                            "tendance": "hausse" if variation_pct > 0 else "baisse",
                            "severite": "forte" if abs(variation_pct) >= 20 else "moyenne",
                            "periode_actuelle": periode_actuelle,
                            "periode_precedente": periode_precedente,
                            "nombre_clients_actuel": actuel['nombre_clients']
                        })
        
        # Trier par abs(variation) décroissant
        signaux.sort(key=lambda x: abs(x['variation_pourcentage']), reverse=True)
        
        return {
            "donnees_trouvees": True,
            "seuil_utilise": seuil_pourcentage,
            "periode_actuelle": periode_actuelle,
            "periode_precedente": periode_precedente,
            "nombre_signaux": len(signaux),
            "signaux": signaux
        }
        
    except Exception as e:
        return {
            "erreur": f"Erreur lors de la détection des signaux: {str(e)}",
            "donnees_trouvees": False
        }


# Test rapide si exécuté directement
if __name__ == "__main__":
    print("=" * 70)
    print("TEST DU MODULE DE DÉTECTION DE TENDANCES")
    print("=" * 70)
    print()
    
    print("1. Test d'évolution pour un segment:")
    evolution = detecter_evolution("France", "T4-2024", "T3-2024")
    print(evolution)
    print("\n" + "=" * 70 + "\n")
    
    print("2. Test de détection de signaux faibles:")
    signaux = detecter_signaux_faibles(seuil_pourcentage=10)
    print(f"Nombre de signaux détectés: {signaux.get('nombre_signaux', 0)}")
    if signaux.get('signaux'):
        for signal in signaux['signaux'][:3]:  # Afficher les 3 premiers
            print(f"  - {signal['dimension']}: {signal['variation_pourcentage']}%")
