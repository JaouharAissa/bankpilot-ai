"""
Module de génération d'alertes automatiques
Détecte et affiche les signaux faibles importants
"""

import logging
from typing import Dict, Any, List
from detection_tendances import detecter_signaux_faibles


# Configuration du logging
logger = logging.getLogger('alertes')


def generer_alertes(seuil: float = 15.0, periode_actuelle: str = "T4-2024", 
                    periode_precedente: str = "T3-2024") -> Dict[str, Any]:
    """
    Génère une liste d'alertes basée sur les signaux faibles détectés
    
    Args:
        seuil: Seuil de variation en % pour déclencher une alerte (défaut: 15%)
        periode_actuelle: Période actuelle
        periode_precedente: Période de référence
        
    Returns:
        Dictionnaire avec les alertes
    """
    try:
        # Détecter les signaux faibles
        signaux_result = detecter_signaux_faibles(
            seuil_pourcentage=seuil,
            periode_actuelle=periode_actuelle,
            periode_precedente=periode_precedente
        )
        
        if not signaux_result.get('donnees_trouvees'):
            return {
                "succes": False,
                "erreur": "Impossible de détecter les signaux"
            }
        
        signaux = signaux_result['signaux']
        
        # Trier par sévérité et amplitude
        signaux_critiques = [s for s in signaux if s['severite'] == 'forte']
        signaux_moyens = [s for s in signaux if s['severite'] == 'moyenne']
        
        # Créer les alertes
        alertes = []
        
        for signal in signaux_critiques:
            tendance_icon = "📈" if signal['tendance'] == 'hausse' else "📉"
            alertes.append({
                "niveau": "CRITIQUE",
                "icon": "🔴",
                "tendance_icon": tendance_icon,
                "message": f"{signal['dimension']} : {signal['variation_pourcentage']:+.1f}%",
                "detail": f"{signal['valeur_precedente']:,.0f}€ → {signal['valeur_actuelle']:,.0f}€",
                "type": signal['type'],
                "variation": signal['variation_pourcentage']
            })
        
        for signal in signaux_moyens:
            tendance_icon = "📈" if signal['tendance'] == 'hausse' else "📉"
            alertes.append({
                "niveau": "ATTENTION",
                "icon": "🟠",
                "tendance_icon": tendance_icon,
                "message": f"{signal['dimension']} : {signal['variation_pourcentage']:+.1f}%",
                "detail": f"{signal['valeur_precedente']:,.0f}€ → {signal['valeur_actuelle']:,.0f}€",
                "type": signal['type'],
                "variation": signal['variation_pourcentage']
            })
        
        logger.info(
            f"Alertes générées: {len(alertes)}",
            extra={'extra_data': {
                'nb_critiques': len(signaux_critiques),
                'nb_moyennes': len(signaux_moyens),
                'seuil': seuil
            }}
        )
        
        return {
            "succes": True,
            "nb_alertes": len(alertes),
            "nb_critiques": len(signaux_critiques),
            "nb_moyennes": len(signaux_moyens),
            "alertes": alertes,
            "periode": f"{periode_precedente} → {periode_actuelle}",
            "seuil_utilise": seuil
        }
        
    except Exception as e:
        logger.error(f"Erreur génération alertes: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


# Test rapide
if __name__ == "__main__":
    print("Test du module d'alertes...")
    result = generer_alertes(seuil=10.0)
    
    if result['succes']:
        print(f"✅ {result['nb_alertes']} alertes générées")
        print(f"   🔴 Critiques: {result['nb_critiques']}")
        print(f"   🟠 Attention: {result['nb_moyennes']}")
        
        if result['alertes']:
            print("\nPremières alertes:")
            for alerte in result['alertes'][:3]:
                print(f"  {alerte['icon']} {alerte['message']}")
    else:
        print(f"❌ Erreur: {result['erreur']}")
