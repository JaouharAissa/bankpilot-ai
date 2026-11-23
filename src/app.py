"""
Interface utilisateur Streamlit pour l'Assistant Contrôleur de Gestion
Interface unifiée avec AI Assistant intelligent - Une seule page pour tout
Version 2.0 - AI-First Design
"""

import streamlit as st
from datetime import datetime
from pathlib import Path
import sys
import pandas as pd
import json
import plotly.graph_objects as go

# Ajouter le répertoire src au path pour les imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from assistant import AssistantCDG
    from reporting_complet import generer_reporting_complet
    from detection_tendances import detecter_signaux_faibles, detecter_evolution
    from outils_donnees import get_statistiques_globales
    from alertes import generer_alertes
    from export import exporter_resultats
    from data_sync import statut_sync, synchroniser_si_modifie, reconstruire_base, EXPORT_DIR
except ImportError as e:
    st.error(f"Erreur d'import: {e}")
    st.stop()


# Configuration de la page
st.set_page_config(
    page_title="Assistant CDG - Contrôleur de Gestion",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# CSS Professionnel basé sur design_tokens.md
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    
    /* === COULEURS ET VARIABLES === */
    :root {
        --marine-deep: #1e3a5f;
        --copper-accent: #d4835e;
        --white: #ffffff;
        --grey-light: #f8f9fa;
        --grey-medium: #6c757d;
        --grey-dark: #2c3e50;
        --success: #28a745;
        --danger: #c0392b;
        --warning: #ffc107;
    }
    
    /* === FOND ET CONTENEURS PRINCIPAUX === */
    .main {
        background-color: var(--white);
        padding: 2rem 3rem;
    }
    
    .stApp {
        background-color: var(--grey-light);
    }
    
    /* === EN-TÊTE PROFESSIONNEL === */
    .app-header {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: var(--white);
        padding: 2.5rem 3rem;
        border-radius: 12px;
        margin-bottom: 2.5rem;
        box-shadow: 0 4px 20px rgba(30, 58, 95, 0.2);
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .app-header h1 {
        font-size: 2.25rem;
        font-weight: 700;
        margin: 0 0 0.75rem 0;
        color: var(--white);
        letter-spacing: -0.5px;
    }
    
    .app-header p {
        font-size: 1.05rem;
        margin: 0;
        opacity: 0.95;
        color: var(--white);
        font-weight: 400;
        line-height: 1.6;
    }
    
    /* === MESSAGES DE CHAT === */
    .chat-container {
        max-width: 950px;
        margin: 0 auto;
        padding: 1.5rem 0;
    }
    
    .user-message {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: var(--white);
        padding: 1.25rem 1.75rem;
        border-radius: 16px 16px 4px 16px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 12px rgba(30, 58, 95, 0.15);
        font-size: 1rem;
        line-height: 1.7;
    }
    
    .assistant-message {
        background: linear-gradient(to bottom, #ffffff 0%, #f8f9fa 100%);
        color: var(--grey-dark);
        padding: 1.75rem 2rem;
        border-radius: 4px 16px 16px 16px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border-left: 4px solid var(--copper-accent);
        font-size: 1rem;
        line-height: 1.8;
    }
    
    .message-time {
        font-size: 0.8rem;
        color: var(--grey-medium);
        margin-top: 0.75rem;
        opacity: 0.6;
        font-weight: 500;
    }
    
    /* === BADGES D'OUTILS === */
    .tools-used {
        margin-top: 1.25rem;
        padding-top: 1.25rem;
        border-top: 2px dashed rgba(108, 117, 125, 0.15);
    }
    
    .tool-badge {
        display: inline-block;
        background: linear-gradient(135deg, #e8eef3 0%, #f0f4f8 100%);
        color: var(--marine-deep);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        margin: 0.35rem 0.4rem 0.35rem 0;
        font-weight: 600;
        border: 1px solid rgba(30, 58, 95, 0.1);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .tool-badge-assistant {
        display: inline-block;
        background: linear-gradient(135deg, #e8eef3 0%, #f0f4f8 100%);
        color: var(--marine-deep);
        padding: 0.5rem 1rem;
        border-radius: 8px;
        font-size: 0.85rem;
        margin: 0.35rem 0.4rem 0.35rem 0;
        font-weight: 600;
        border: 1px solid rgba(30, 58, 95, 0.1);
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    /* === BOUTONS === */
    .stButton > button {
        background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
        color: var(--white);
        border: none;
        border-radius: 8px;
        padding: 0.85rem 1.75rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(30, 58, 95, 0.2);
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2c5282 0%, #3d6aa6 100%);
        box-shadow: 0 6px 20px rgba(30, 58, 95, 0.35);
        transform: translateY(-2px);
    }
    
    .stDownloadButton > button {
        background: linear-gradient(135deg, #d4835e 0%, #c67450 100%);
        color: var(--white);
        border: none;
        border-radius: 8px;
        padding: 0.85rem 1.75rem;
        font-weight: 600;
        font-size: 0.95rem;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(212, 131, 94, 0.2);
    }
    
    .stDownloadButton > button:hover {
        background: linear-gradient(135deg, #c67450 0%, #b86542 100%);
        box-shadow: 0 6px 20px rgba(212, 131, 94, 0.4);
        transform: translateY(-2px);
    }
    
    /* === SIDEBAR === */
    [data-testid="stSidebar"] {
        background-color: var(--white);
        border-right: 1px solid rgba(108, 117, 125, 0.15);
    }

    [data-testid="stSidebar"] > div {
        background-color: var(--white);
        padding: 1.5rem 1rem;
    }

    .sidebar .sidebar-content {
        background-color: var(--white);
    }
    
    /* === INPUTS === */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #e8eef3;
        border-radius: 8px;
        padding: 0.9rem 1.2rem;
        font-size: 1rem;
        transition: all 0.3s ease;
        background: var(--white);
    }
    
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: var(--marine-deep);
        box-shadow: 0 0 0 4px rgba(30, 58, 95, 0.12);
        background: var(--white);
    }
    
    /* === CARTES DE STATISTIQUES === */
    .stat-card {
        background: var(--white);
        border: 1px solid var(--grey-light);
        border-radius: 8px;
        padding: 1.5rem;
        margin: 0.5rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    
    .stat-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--copper-accent);
        margin: 0.5rem 0;
    }
    
    .stat-label {
        font-size: 0.9rem;
        color: var(--grey-medium);
        font-weight: 500;
    }
    
    /* === ALERTES === */
    .alert-card {
        background: var(--white);
        border-left: 4px solid var(--danger);
        padding: 1rem 1.5rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
    }
    
    .alert-card.warning {
        border-left-color: var(--warning);
    }
    
    .alert-card.success {
        border-left-color: var(--success);
    }
    
    /* === ESPACEMENT GÉNÉRAL === */
    .block-container {
        padding: 2rem 1rem;
        max-width: 1200px;
    }
    
    /* === TITRES === */
    h1, h2, h3 {
        color: var(--marine-deep);
        font-weight: 600;
    }
    
    h1 {
        font-size: 2rem;
        margin-bottom: 1rem;
    }
    
    h2 {
        font-size: 1.5rem;
        margin: 1.5rem 0 1rem 0;
    }
    
    h3 {
        font-size: 1.25rem;
        margin: 1rem 0 0.75rem 0;
    }
    
    /* === GRAPHIQUES === */
    .plotly-graph-div {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06);
        margin: 1.5rem 0;
    }
    
    /* === BOÎTES D'INFORMATION === */
    .info-box {
        background: linear-gradient(135deg, #e3f2fd 0%, #f0f8ff 100%);
        border-left: 4px solid var(--marine-deep);
        padding: 2rem 2.25rem;
        border-radius: 12px;
        margin: 2rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border: 1px solid rgba(30, 58, 95, 0.1);
    }
    
    .warning-box {
        background: linear-gradient(135deg, #fff3e0 0%, #fffbf0 100%);
        border-left: 4px solid var(--warning);
        padding: 2rem 2.25rem;
        border-radius: 12px;
        margin: 2rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.08);
        border: 1px solid rgba(255, 193, 7, 0.2);
    }
    
    .tool-badge-assistant {
        display: inline-block;
        background: var(--grey-light);
        color: var(--grey-dark);
        padding: 0.4rem 0.8rem;
        border-radius: 6px;
        font-size: 0.8rem;
        margin: 0.25rem 0.25rem 0.25rem 0;
        font-weight: 500;
    }
    
    .message-header {
        font-weight: 600;
        margin-bottom: 0.9rem;
        font-size: 0.95rem;
        opacity: 0.95;
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }
    
    .message-content {
        line-height: 1.8;
        font-size: 1rem;
    }
    
    /* === SUPPRESSION DES ÉLÉMENTS STREAMLIT PAR DÉFAUT === */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Supprimer l'espace vide en haut */
    .main > div:first-child {
        padding-top: 0 !important;
    }
    
    /* Réduire le padding du bloc principal */
    .block-container {
        padding-top: 1rem !important;
    }
    
    /* === ANIMATIONS SUBTILES === */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .assistant-message, .user-message {
        animation: fadeIn 0.3s ease;
    }
    </style>
""", unsafe_allow_html=True)


def initialiser_session():
    """Initialise les variables de session Streamlit"""
    if 'assistant' not in st.session_state:
        try:
            st.session_state.assistant = AssistantCDG()
            st.session_state.assistant_pret = True
        except (ConnectionError, Exception) as e:
            st.session_state.assistant_pret = False
            st.session_state.erreur_init = str(e)
    
    if 'messages_chat' not in st.session_state:
        st.session_state.messages_chat = []
    
    if 'stats_chargees' not in st.session_state:
        st.session_state.stats_chargees = False
    
    if 'alertes' not in st.session_state:
        st.session_state.alertes = None
    
    if 'dernier_graphique' not in st.session_state:
        st.session_state.dernier_graphique = None
    
    if 'graphiques_en_attente' not in st.session_state:
        st.session_state.graphiques_en_attente = []


def afficher_message(role: str, contenu: str, outils: list = None, timestamp=None):
    """Affiche un message dans l'interface avec style moderne - SANS HTML dans le texte"""
    
    import html
    import re
    
    time_str = timestamp.strftime("%H:%M") if timestamp else datetime.now().strftime("%H:%M")
    
    if role == "user":
        # Message utilisateur simple
        st.markdown(f"""
            <div class="user-message">
                <div class="message-header">
                    <span>👤 Vous</span>
                </div>
                <div class="message-content">{html.escape(contenu)}</div>
                <div class="message-time">{time_str}</div>
            </div>
        """, unsafe_allow_html=True)
    else:
        # NETTOYER COMPLÈTEMENT le HTML du contenu
        contenu_clean = re.sub(r'<div[^>]*>.*?</div>', '', contenu, flags=re.DOTALL | re.IGNORECASE)
        contenu_clean = re.sub(r'<span[^>]*>.*?</span>', '', contenu_clean, flags=re.DOTALL | re.IGNORECASE)
        contenu_clean = re.sub(r'<[^>]+>', '', contenu_clean)
        contenu_clean = re.sub(r'\s+', ' ', contenu_clean).strip()
        
        # Afficher SEULEMENT le texte propre
        st.markdown(f"""
            <div class="assistant-message">
                <div class="message-header">
                    <span>🤖 Assistant IA</span>
                </div>
                <div class="message-content">{html.escape(contenu_clean).replace(chr(10), '<br>')}</div>
                <div class="message-time">{time_str}</div>
            </div>
        """, unsafe_allow_html=True)
        
        # Afficher les badges d'outils SÉPARÉMENT en dessous
        if outils and len(outils) > 0:
            badges_html = ''.join([
                f'<span class="tool-badge-assistant">🔧 {html.escape(outil["nom"])}</span>'
                for outil in outils
            ])
            st.markdown(f"""
                <div class="tools-used">
                    <div style="font-size: 0.85rem; opacity: 0.7; margin-bottom: 0.5rem;">Outils utilisés:</div>
                    {badges_html}
                </div>
            """, unsafe_allow_html=True)


def afficher_statistiques_quick():
    """Affiche un aperçu rapide des statistiques dans la sidebar"""
    try:
        stats = get_statistiques_globales()

        if stats.get('donnees_trouvees'):
            gen = stats.get('global') or stats.get('statistiques_generales') or {}

            st.markdown("### 📊 Vue d'Ensemble Rapide")

            col1, col2 = st.columns(2)

            with col1:
                n_clients = gen.get('nombre_total_clients', gen.get('nombre_clients_total', 0))
                st.metric("👥 Clients", f"{n_clients:,}")
                pnb = gen.get('pnb_total', 0) or 0
                st.metric("💰 PNB Total", f"{pnb/1000000:.1f}M€")

            with col2:
                rent = gen.get('rentabilite_totale', 0) or 0
                st.metric("📈 Rentabilité", f"{rent/1000000:.1f}M€")
                pnb_moy = gen.get('pnb_moyen', 0) or 0
                st.metric("💵 PNB Moyen", f"{pnb_moy:,.0f}€")

            st.session_state.stats_chargees = True
    except Exception:
        pass


def afficher_sync_powerbi():
    """Panneau de synchronisation Power BI → Chatbot"""
    st.markdown("### 🔄 Données Power BI")
    try:
        statut = statut_sync()
        origine = statut.get("origine") or "non synchronisé"
        derniere = statut.get("derniere_sync") or "jamais"
        st.caption(f"Source: **{origine}**")
        st.caption(f"Dernière sync: {derniere}")
        exports = statut.get("exports_disponibles") or []
        if exports:
            st.caption(f"Exports: {', '.join(exports[:3])}")
        else:
            st.info(
                f"Placez un CSV/Excel exporté depuis Power BI dans:\n`{statut.get('dossier_export')}`"
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("↻ Actualiser", key="sync_check", use_container_width=True):
                result = synchroniser_si_modifie()
                if result.get("succes"):
                    if result.get("action") == "rebuild":
                        st.success(f"DB mise à jour ({result.get('nombre_lignes')} lignes)")
                        st.session_state.alertes = None
                        st.session_state.stats_chargees = False
                    else:
                        st.info(result.get("message", "Déjà à jour"))
                else:
                    st.error(result.get("erreur", "Échec sync"))
                st.rerun()
        with col_b:
            if st.button("⚡ Rebuild", key="sync_force", use_container_width=True):
                result = reconstruire_base()
                if result.get("succes"):
                    st.success(f"Rebuild OK — {result.get('nombre_lignes')} lignes")
                    st.session_state.alertes = None
                    st.session_state.stats_chargees = False
                else:
                    st.error(result.get("erreur", "Échec"))
                st.rerun()
    except Exception as e:
        st.warning(f"Sync indisponible: {e}")


def main():
    """Fonction principale - Interface AI-First unifiée"""
    
    # Initialisation
    initialiser_session()
    
    # Header Professionnel
    st.markdown("""
        <div class="app-header">
            <h1>🤖 Assistant IA Contrôleur de Gestion</h1>
            <p>Votre expert financier intelligent • Posez n'importe quelle question • Générez des rapports • Détectez des signaux</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Vérifier si Ollama est disponible
    if not st.session_state.assistant_pret:
        st.markdown(f"""
            <div class="warning-box">
                <h3 style="margin-top:0;">⚠️ Ollama Non Disponible</h3>
                <p><strong>Erreur:</strong> {st.session_state.erreur_init}</p>
                <p><strong>Solution:</strong></p>
                <ol>
                    <li>Téléchargez Ollama sur <a href="https://ollama.com" target="_blank">ollama.com</a></li>
                    <li>Installez et lancez Ollama</li>
                    <li>Exécutez: <code>ollama pull llama3.1</code></li>
                    <li>Relancez cette application</li>
                </ol>
            </div>
        """, unsafe_allow_html=True)
        st.stop()
    
    # === PANEL D'ALERTES EN HAUT - DÉSACTIVÉ ===
    # Si vous voulez réactiver les alertes, décommentez le bloc ci-dessous
    
    # try:
    #     if st.session_state.alertes is None:
    #         alertes_result = generer_alertes(seuil=15.0)
    #         if alertes_result.get('succes'):
    #             st.session_state.alertes = alertes_result
    #     
    #     if st.session_state.alertes and st.session_state.alertes.get('nb_alertes', 0) > 0:
    #         alertes = st.session_state.alertes
    #         st.markdown(f"""
    #             <div class="warning-box">
    #                 <h3 style="margin-top:0;">⚠️ Alertes Détectées ({alertes['nb_alertes']})</h3>
    #                 <p style="font-size: 0.9rem; opacity: 0.8;">Période: {alertes.get('periode', 'T3-2024 → T4-2024')}</p>
    #             </div>
    #         """, unsafe_allow_html=True)
    #         
    #         if alertes['nb_critiques'] > 0:
    #             col1, col2 = st.columns([1, 4])
    #             with col1:
    #                 st.metric("🔴 Critiques", alertes['nb_critiques'])
    #             with col2:
    #                 critiques = [a for a in alertes['alertes'] if a['niveau'] == 'CRITIQUE'][:3]
    #                 for alerte in critiques:
    #                     st.warning(f"{alerte['icon']} {alerte['tendance_icon']} **{alerte['message']}** - {alerte['detail']}")
    #         
    #         if alertes['nb_moyennes'] > 0:
    #             col1, col2 = st.columns([1, 4])
    #             with col1:
    #                 st.metric("🟠 Attention", alertes['nb_moyennes'])
    #             with col2:
    #                 moyennes = [a for a in alertes['alertes'] if a['niveau'] == 'ATTENTION'][:2]
    #                 for alerte in moyennes:
    #                     st.info(f"{alerte['icon']} {alerte['tendance_icon']} **{alerte['message']}** - {alerte['detail']}")
    #         
    #         st.divider()
    # except Exception as e:
    #     pass
    
    # Sidebar avec statistiques et actions rapides
    with st.sidebar:
        st.markdown("## 🎯 Actions Rapides")
        
        # Section Génération de Documents avec choix
        with st.expander("📄 Générer des Documents", expanded=False):
            st.markdown("**Choisissez le format:**")
            
            if st.button("📄 Rapport Word", key="quick_word", use_container_width=True):
                st.session_state.question_selectionnee = "Génère-moi un rapport Word complet du trimestre T4-2024"
                st.rerun()
            
            if st.button("📊 Présentation PowerPoint", key="quick_ppt", use_container_width=True):
                st.session_state.question_selectionnee = "Génère-moi une présentation PowerPoint du trimestre T4-2024"
                st.rerun()
            
            if st.button("📦 Word + PowerPoint", key="quick_both", use_container_width=True):
                st.session_state.question_selectionnee = "Génère un reporting complet avec Word et PowerPoint du T4-2024"
                st.rerun()
        
        # Quick actions
        quick_actions = [
            ("📊 Statistiques globales", "Donne-moi les statistiques globales du portefeuille"),
            ("📈 Comparer segments", "Compare la rentabilité entre France et Germany"),
            ("🔍 Signaux faibles T4", "Détecte les signaux faibles de T4-2024 vs T3-2024"),
            ("🇫🇷 Analyse France", "Quelle est l'évolution du segment France entre T3 et T4 2024?"),
            ("🎁 Clients 2 produits", "Quelle est la rentabilité des clients ayant 2 produits?"),
            ("🚨 Clients à risque", "Quels clients sont à risque de départ?"),
            ("📊 Graphique segments", "Montre-moi un graphique comparant tous les segments"),
        ]
        
        for label, question in quick_actions:
            if st.button(label, key=f"quick_{hash(label)}", use_container_width=True):
                st.session_state.question_selectionnee = question
                st.rerun()
        
        st.divider()

        # Sync Power BI → SQLite → Chatbot
        afficher_sync_powerbi()
        
        st.divider()
        
        # Statistiques rapides
        afficher_statistiques_quick()
        
        st.divider()
        
        # Actions de gestion
        st.markdown("### ⚙️ Gestion")
        
        if st.button("🗑️ Effacer la conversation", use_container_width=True):
            st.session_state.messages_chat = []
            st.rerun()
        
        if st.session_state.messages_chat:
            nb_questions = len([m for m in st.session_state.messages_chat if m['role'] == 'user'])
            st.metric("Questions posées", nb_questions)
            
            # Export conversation
            conversation_text = ""
            for m in st.session_state.messages_chat:
                role = "Vous" if m['role'] == 'user' else "Assistant"
                conversation_text += f"{role}: {m['contenu']}\n\n"
            
            st.download_button(
                label="💾 Exporter conversation",
                data=conversation_text,
                file_name=f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    # Zone principale de conversation
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Message de bienvenue si première utilisation
    if not st.session_state.messages_chat:
        st.markdown("""
            <div class="info-box">
                <h3 style="margin-top:0;">👋 Bienvenue ! Je suis votre assistant intelligent</h3>
                <p style="font-size: 1.05rem; line-height: 1.7;">
                    Je peux répondre à <strong>toutes vos questions</strong> sur les données financières, 
                    <strong>générer des rapports automatiquement</strong>, <strong>détecter des signaux faibles</strong>, 
                    et bien plus encore !
                </p>
                <p style="margin-bottom: 0;">
                    💡 <strong>Essayez les actions rapides</strong> dans la barre latérale ou posez votre question ci-dessous.
                </p>
            </div>
        """, unsafe_allow_html=True)
    
    # Afficher l'historique de conversation
    for idx, message in enumerate(st.session_state.messages_chat):
        afficher_message(
            message['role'],
            message['contenu'],
            message.get('outils'),
            message.get('timestamp')
        )
        
        # AFFICHER LES GRAPHIQUES STOCKÉS dans session_state
        if message['role'] == 'assistant' and message.get('outils'):
            outils_visu = ['graphique_evolution_pnb', 'graphique_comparaison_segments', 'graphique_repartition_produits']
            
            for outil_info in message.get('outils', []):
                if outil_info['nom'] in outils_visu:
                    # Chercher le graphique dans session_state.graphiques_en_attente
                    if 'graphiques_en_attente' in st.session_state and st.session_state.graphiques_en_attente:
                        for graph_data in st.session_state.graphiques_en_attente:
                            if graph_data['outil'] == outil_info['nom']:
                                try:
                                    st.plotly_chart(graph_data['figure'], use_container_width=True, key=f"graph_{idx}_{outil_info['nom']}")
                                except Exception as e:
                                    st.error(f"Erreur affichage graphique: {e}")
                                break
        
        # BOUTONS DE TÉLÉCHARGEMENT pour rapports/présentations
        if message['role'] == 'assistant' and message.get('outils'):
            outils_documents = ['generer_rapport_word', 'generer_presentation_pptx', 'generer_reporting_complet']
            
            for outil_info in message.get('outils', []):
                if outil_info['nom'] in outils_documents:
                    # Chercher les fichiers récemment créés dans outputs/
                    from pathlib import Path
                    import time
                    
                    outputs_dir = Path("outputs")
                    if outputs_dir.exists():
                        # Fichiers créés dans les 2 dernières minutes
                        recent_files = []
                        current_time = time.time()
                        
                        for pattern in ['rapport_*.docx', 'presentation_*.pptx']:
                            for file_path in outputs_dir.glob(pattern):
                                if current_time - file_path.stat().st_mtime < 120:  # 2 minutes
                                    recent_files.append(file_path)
                        
                        # Afficher UNIQUEMENT les boutons de téléchargement si fichiers trouvés
                        if recent_files:
                            # Séparer Word et PowerPoint
                            word_files = [f for f in recent_files if f.suffix == '.docx']
                            ppt_files = [f for f in recent_files if f.suffix == '.pptx']
                            
                            cols = []
                            if word_files:
                                cols.append(('word', word_files[0]))
                            if ppt_files:
                                cols.append(('ppt', ppt_files[0]))
                            
                            if len(cols) > 0:
                                columns = st.columns(len(cols))
                                
                                for i, (file_type, file_path) in enumerate(cols):
                                    try:
                                        with open(file_path, 'rb') as f:
                                            file_data = f.read()
                                        
                                        with columns[i]:
                                            if file_type == 'word':
                                                st.download_button(
                                                    label="📄 Télécharger Word",
                                                    data=file_data,
                                                    file_name=file_path.name,
                                                    mime='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                                    key=f"download_word_{idx}",
                                                    use_container_width=True
                                                )
                                            else:
                                                st.download_button(
                                                    label="📊 Télécharger PowerPoint",
                                                    data=file_data,
                                                    file_name=file_path.name,
                                                    mime='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                                                    key=f"download_ppt_{idx}",
                                                    use_container_width=True
                                                )
                                    except Exception as e:
                                        st.error(f"Erreur: {e}")
                    break
        
        # Si c'est une réponse avec des données tabulaires, proposer l'export
        if message['role'] == 'assistant' and message.get('outils'):
            # Vérifier si des outils de données ont été utilisés
            outils_avec_donnees = [
                'get_pnb_par_segment',
                'get_statistiques_globales',
                'comparer_segments',
                'predire_clients_a_risque'
            ]
            
            for outil in message.get('outils', []):
                if outil['nom'] in outils_avec_donnees:
                    col1, col2, col3 = st.columns([1, 1, 3])
                    with col1:
                        if st.button("📥 Export CSV", key=f"export_csv_{idx}"):
                            st.info("💡 Utilisez la question: 'Exporte ces résultats en CSV'")
                    with col2:
                        if st.button("📊 Export Excel", key=f"export_excel_{idx}"):
                            st.info("💡 Utilisez la question: 'Exporte ces résultats en Excel'")
                    break
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Zone de saisie fixe en bas
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Fonction callback pour gérer l'envoi
    def handle_submit():
        question = st.session_state.input_question
        if question and question.strip():
            # Éviter les doublons - ne traiter que si pas déjà en cours
            if not st.session_state.get('question_to_process'):
                st.session_state.question_to_process = question.strip()
                st.session_state.input_question = ""  # Vider le champ
    
    # Gérer question présélectionnée (depuis sidebar) AVANT d'afficher l'input
    if 'question_selectionnee' in st.session_state:
        st.session_state.question_to_process = st.session_state.question_selectionnee
        del st.session_state.question_selectionnee
    
    col1, col2 = st.columns([6, 1])
    
    with col1:
        question = st.text_input(
            "💭 Posez votre question...",
            key="input_question",
            placeholder="Ex: Compare France et Germany, génère un rapport, détecte les signaux faibles...",
            label_visibility="collapsed",
            on_change=handle_submit
        )
    
    with col2:
        bouton_envoyer = st.button("🚀 Envoyer", use_container_width=True, type="primary")
    
    # Si le bouton est cliqué, appeler handle_submit
    if bouton_envoyer:
        handle_submit()
    
    # Traiter la question si elle existe
    if st.session_state.get('question_to_process'):
        question_a_traiter = st.session_state.question_to_process
        del st.session_state.question_to_process
        
        # Vérifier si cette question n'est pas déjà la dernière dans l'historique (éviter doublons)
        derniere_question = None
        if st.session_state.messages_chat:
            messages_users = [m for m in st.session_state.messages_chat if m['role'] == 'user']
            if messages_users:
                derniere_question = messages_users[-1]['contenu']
        
        # Ajouter la question à l'historique seulement si pas déjà présente
        if question_a_traiter != derniere_question:
            st.session_state.messages_chat.append({
                'role': 'user',
                'contenu': question_a_traiter,
                'timestamp': datetime.now()
            })
        
        # Afficher un spinner pendant le traitement (seulement si question a été ajoutée)
        if question_a_traiter != derniere_question:
            with st.spinner("🤔 Analyse en cours..."):
                # Appeler l'assistant
                resultat = st.session_state.assistant.poser_question(question_a_traiter)
                
                # Vérifier si des outils de visualisation ont été utilisés
                outils_visu = [
                    'graphique_evolution_pnb',
                    'graphique_comparaison_segments',
                    'graphique_repartition_produits'
                ]
                
                graphiques_generes = []
                if resultat.get('succes') and resultat.get('outils_utilises'):
                    for outil in resultat['outils_utilises']:
                        if outil['nom'] in outils_visu:
                            graphiques_generes.append(outil['nom'])
                
                # Ajouter la réponse à l'historique
                if resultat['succes']:
                    st.session_state.messages_chat.append({
                        'role': 'assistant',
                        'contenu': resultat['reponse'],
                        'outils': resultat.get('outils_utilises', []),
                        'graphiques': graphiques_generes,
                        'timestamp': datetime.now()
                    })
                else:
                    st.session_state.messages_chat.append({
                        'role': 'assistant',
                        'contenu': f"❌ Désolé, une erreur s'est produite: {resultat['reponse']}",
                        'timestamp': datetime.now()
                    })
            
            # Rafraîchir la page
            st.rerun()
    
    # Footer avec informations
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: center; color: #718096; font-size: 0.85rem; padding: 2rem 0;">
            <p style="margin: 0;">
                💼 Assistant CDG v2.0 • 
                🤖 Propulsé par Llama 3.1 (Ollama) • 
                🔒 100% Local et Privé • 
                ⚡ 19 Outils Disponibles
            </p>
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
