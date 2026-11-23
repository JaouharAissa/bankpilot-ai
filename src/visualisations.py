"""
Module de génération de visualisations avec Plotly
Crée des graphiques interactifs pour l'analyse financière
"""

import logging
from typing import Dict, Any, Optional
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import pandas as pd

from outils_donnees import (
    get_pnb_par_segment,
    get_statistiques_globales,
    comparer_segments
)
from detection_tendances import detecter_evolution


# Configuration du logging
logger = logging.getLogger('visualisations')


def graphique_evolution_pnb(segment: str, periode_actuelle: str = "T4-2024", 
                            periode_precedente: str = "T3-2024") -> Dict[str, Any]:
    """
    Crée un graphique d'évolution du PNB pour un segment entre deux périodes
    
    Args:
        segment: Nom du segment (France, Germany, Spain)
        periode_actuelle: Période actuelle
        periode_precedente: Période précédente
        
    Returns:
        Dictionnaire avec description textuelle (pas l'objet Figure)
    """
    try:
        from detection_tendances import detecter_evolution
        
        # Récupérer les données d'évolution
        evolution = detecter_evolution(segment, periode_actuelle, periode_precedente)
        
        if not evolution.get('donnees_trouvees'):
            return {
                "succes": False,
                "erreur": evolution.get('erreur', 'Données non disponibles'),
                "donnees_trouvees": False
            }
        
        # Préparer les données pour le graphique
        periodes = [periode_precedente, periode_actuelle]
        pnb_total = [
            evolution['valeur_precedente']['pnb_total'],
            evolution['valeur_actuelle']['pnb_total']
        ]
        pnb_moyen = [
            evolution['valeur_precedente']['pnb_moyen'],
            evolution['valeur_actuelle']['pnb_moyen']
        ]
        
        # Créer le graphique
        fig = go.Figure()
        
        # Ligne PNB Total
        fig.add_trace(go.Scatter(
            x=periodes,
            y=pnb_total,
            mode='lines+markers+text',
            name='PNB Total',
            line=dict(color='#667eea', width=3),
            marker=dict(size=12),
            text=[f"{v:,.0f}€" for v in pnb_total],
            textposition="top center",
            textfont=dict(size=12, color='#667eea')
        ))
        
        # Ligne PNB Moyen
        fig.add_trace(go.Scatter(
            x=periodes,
            y=pnb_moyen,
            mode='lines+markers+text',
            name='PNB Moyen',
            line=dict(color='#764ba2', width=3, dash='dash'),
            marker=dict(size=10),
            text=[f"{v:,.0f}€" for v in pnb_moyen],
            textposition="bottom center",
            textfont=dict(size=12, color='#764ba2'),
            yaxis='y2'
        ))
        
        # Configuration du layout
        fig.update_layout(
            title=dict(
                text=f"Évolution du PNB - {segment}",
                font=dict(size=20, color='#2d3748', family='Inter')
            ),
            xaxis=dict(
                title="Période",
                showgrid=True,
                gridcolor='#e2e8f0'
            ),
            yaxis=dict(
                title="PNB Total (€)",
                showgrid=True,
                gridcolor='#e2e8f0',
                tickformat=",",
                side='left'
            ),
            yaxis2=dict(
                title="PNB Moyen (€)",
                overlaying='y',
                side='right',
                tickformat=",",
                showgrid=False
            ),
            hovermode='x unified',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter', size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500
        )
        
        logger.info(
            "Graphique d'évolution généré",
            extra={'extra_data': {
                'segment': segment,
                'periode_actuelle': periode_actuelle,
                'periode_precedente': periode_precedente
            }}
        )
        
        # Retourner SEULEMENT les données textuelles pour le LLM
        # L'objet Figure sera stocké et affiché par app.py
        return {
            "succes": True,
            "donnees_trouvees": True,
            "description": f"Graphique d'évolution du PNB - Segment {segment}",
            "pnb_total_t3": f"{pnb_total[0]:,.0f}€",
            "pnb_total_t4": f"{pnb_total[1]:,.0f}€",
            "pnb_moyen_t3": f"{pnb_moyen[0]:,.0f}€",
            "pnb_moyen_t4": f"{pnb_moyen[1]:,.0f}€",
            "variation": evolution.get('variation_pourcentage', 0),
            # Stocker la figure pour app.py (non envoyée au LLM)
            "_figure": fig,
            "type": "evolution_pnb"
        }
        
    except Exception as e:
        logger.error(f"Erreur génération graphique évolution: {e}")
        return {
            "succes": False,
            "donnees_trouvees": False,
            "erreur": f"Erreur lors de la génération: {str(e)}"
        }


def graphique_comparaison_segments() -> Dict[str, Any]:
    """
    Crée un graphique comparant les PNB de tous les segments
    
    Returns:
        Dictionnaire avec le graphique Plotly et les données
    """
    try:
        # Récupérer les statistiques de chaque segment individuellement pour avoir plus de détails
        from outils_donnees import get_pnb_par_segment, get_rentabilite_par_segment, _obtenir_segments_disponibles
        
        segments_list = _obtenir_segments_disponibles()
        
        segments_data = []
        for seg in segments_list:
            pnb_data = get_pnb_par_segment(seg)
            rent_data = get_rentabilite_par_segment(seg)
            
            if pnb_data.get('donnees_trouvees') and rent_data.get('donnees_trouvees'):
                segments_data.append({
                    'segment': seg,
                    'pnb_total': pnb_data['pnb_total'],
                    'pnb_moyen': pnb_data['pnb_moyen'],
                    'nombre_clients': pnb_data['nombre_clients'],
                    'rentabilite_moyenne': rent_data['rentabilite_moyenne']
                })
        
        if not segments_data:
            return {
                "succes": False,
                "erreur": "Impossible de récupérer les données des segments"
            }
        
        segments = [s['segment'] for s in segments_data]
        pnb_total = [s['pnb_total'] for s in segments_data]
        rentabilite = [s['rentabilite_moyenne'] for s in segments_data]
        nb_clients = [s['nombre_clients'] for s in segments_data]
        
        # Créer un graphique avec barres groupées
        fig = go.Figure()
        
        # Barres PNB Total
        fig.add_trace(go.Bar(
            name='PNB Total',
            x=segments,
            y=pnb_total,
            text=[f"{v:,.0f}€" for v in pnb_total],
            textposition='outside',
            marker=dict(
                color='#667eea',
                line=dict(color='#5568d3', width=2)
            )
        ))
        
        # Barres Rentabilité Moyenne
        fig.add_trace(go.Bar(
            name='Rentabilité Moyenne',
            x=segments,
            y=rentabilite,
            text=[f"{v:,.0f}€" for v in rentabilite],
            textposition='outside',
            marker=dict(
                color='#764ba2',
                line=dict(color='#5e3a82', width=2)
            ),
            yaxis='y2'
        ))
        
        # Configuration du layout
        fig.update_layout(
            title=dict(
                text="Comparaison des Segments Géographiques",
                font=dict(size=20, color='#2d3748', family='Inter')
            ),
            xaxis=dict(
                title="Segment",
                showgrid=False
            ),
            yaxis=dict(
                title="PNB Total (€)",
                showgrid=True,
                gridcolor='#e2e8f0',
                tickformat=","
            ),
            yaxis2=dict(
                title="Rentabilité Moyenne (€)",
                overlaying='y',
                side='right',
                tickformat=",",
                showgrid=False
            ),
            barmode='group',
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter', size=12),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            height=500
        )
        
        # Ajouter les nombres de clients comme annotation
        for i, (seg, nb) in enumerate(zip(segments, nb_clients)):
            fig.add_annotation(
                x=seg,
                y=0,
                text=f"{nb:,} clients",
                showarrow=False,
                yshift=-40,
                font=dict(size=10, color='#718096')
            )
        
        logger.info("Graphique de comparaison généré")
        
        # Retourner les données textuelles pour le LLM (pas l'objet Figure)
        return {
            "succes": True,
            "donnees_trouvees": True,
            "description": "Graphique de comparaison des segments géographiques",
            "segments": {
                seg['segment']: {
                    "pnb_total": f"{seg['pnb_total']:,.0f}€",
                    "rentabilite_moyenne": f"{seg['rentabilite_moyenne']:,.0f}€",
                    "nombre_clients": seg['nombre_clients']
                }
                for seg in segments_data
            },
            # Stocker la figure pour app.py
            "_figure": fig,
            "type": "comparaison_segments"
        }
        
    except Exception as e:
        logger.error(f"Erreur génération graphique comparaison: {e}")
        return {
            "succes": False,
            "erreur": f"Erreur lors de la génération: {str(e)}"
        }


def graphique_repartition_produits() -> Dict[str, Any]:
    """
    Crée un graphique de répartition des clients par nombre de produits
    
    Returns:
        Dictionnaire avec le graphique Plotly et les données
    """
    try:
        # Récupérer les statistiques de chaque produit individuellement
        from outils_donnees import get_rentabilite_par_produit
        
        produits_possibles = [1, 2, 3, 4]
        produits_data = []
        
        for nb_prod in produits_possibles:
            prod_data = get_rentabilite_par_produit(nb_prod)
            if prod_data.get('donnees_trouvees'):
                produits_data.append({
                    'nombre_produits': nb_prod,
                    'nombre_clients': prod_data['nombre_clients'],
                    'pnb_total': prod_data.get('pnb_total', 0),
                    'rentabilite_moyenne': prod_data['rentabilite_moyenne']
                })
        
        if not produits_data:
            return {
                "succes": False,
                "erreur": "Impossible de récupérer les données des produits"
            }
        
        labels = [f"{p['nombre_produits']} produit(s)" for p in produits_data]
        valeurs = [p['nombre_clients'] for p in produits_data]
        
        # Créer un graphique en camembert (pie chart)
        fig = go.Figure(data=[go.Pie(
            labels=labels,
            values=valeurs,
            hole=0.4,  # Donut chart
            marker=dict(
                colors=['#667eea', '#764ba2', '#f093fb', '#4facfe'],
                line=dict(color='white', width=3)
            ),
            textinfo='label+percent',
            textfont=dict(size=14, color='white', family='Inter'),
            hovertemplate='<b>%{label}</b><br>' +
                         'Clients: %{value:,}<br>' +
                         'Pourcentage: %{percent}<br>' +
                         '<extra></extra>'
        )])
        
        # Configuration du layout
        fig.update_layout(
            title=dict(
                text="Répartition des Clients par Nombre de Produits",
                font=dict(size=20, color='#2d3748', family='Inter')
            ),
            annotations=[dict(
                text=f'{sum(valeurs):,}<br>clients',
                x=0.5,
                y=0.5,
                font=dict(size=16, color='#2d3748', family='Inter'),
                showarrow=False
            )],
            plot_bgcolor='white',
            paper_bgcolor='white',
            font=dict(family='Inter', size=12),
            height=500,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="middle",
                y=0.5,
                xanchor="left",
                x=1.05
            )
        )
        
        logger.info("Graphique de répartition généré")
        
        # Retourner les données textuelles pour le LLM (pas l'objet Figure)
        return {
            "succes": True,
            "donnees_trouvees": True,
            "description": "Graphique de répartition des clients par nombre de produits",
            "repartition": {
                f"{p['nombre_produits']} produit(s)": {
                    "nombre_clients": p['nombre_clients'],
                    "pourcentage": f"{(p['nombre_clients']/sum(valeurs)*100):.1f}%"
                }
                for p in produits_data
            },
            "total_clients": sum(valeurs),
            # Stocker la figure pour app.py
            "_figure": fig,
            "type": "repartition_produits"
        }
        
    except Exception as e:
        logger.error(f"Erreur génération graphique répartition: {e}")
        return {
            "succes": False,
            "erreur": f"Erreur lors de la génération: {str(e)}"
        }


def sauvegarder_graphique_png(figure, nom_fichier: str) -> Optional[str]:
    """
    Sauvegarde un graphique Plotly en PNG pour l'inclure dans PowerPoint
    
    Args:
        figure: Figure Plotly
        nom_fichier: Nom du fichier (sans extension)
        
    Returns:
        Chemin du fichier PNG créé, ou None si erreur
    """
    try:
        output_dir = Path(__file__).parent.parent / 'outputs' / 'graphs'
        output_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = output_dir / f"{nom_fichier}.png"
        figure.write_image(str(filepath), width=1200, height=600)
        
        logger.info(f"Graphique sauvegardé: {filepath}")
        return str(filepath)
        
    except Exception as e:
        logger.error(f"Erreur sauvegarde graphique: {e}")
        return None


# Test rapide si exécuté directement
if __name__ == "__main__":
    print("=" * 70)
    print("TEST DU MODULE DE VISUALISATIONS")
    print("=" * 70)
    print()
    
    print("1. Test graphique d'évolution...")
    result1 = graphique_evolution_pnb("France", "T4-2024", "T3-2024")
    if result1['succes']:
        print("✅ Graphique d'évolution créé")
        result1['figure'].show()
    else:
        print(f"❌ Erreur: {result1['erreur']}")
    
    print("\n2. Test graphique de comparaison...")
    result2 = graphique_comparaison_segments()
    if result2['succes']:
        print("✅ Graphique de comparaison créé")
        result2['figure'].show()
    else:
        print(f"❌ Erreur: {result2['erreur']}")
    
    print("\n3. Test graphique de répartition...")
    result3 = graphique_repartition_produits()
    if result3['succes']:
        print("✅ Graphique de répartition créé")
        result3['figure'].show()
    else:
        print(f"❌ Erreur: {result3['erreur']}")
