"""
Connecteur Power BI ↔ Ollama
Permet d'utiliser les outils AI directement depuis Power BI
"""

import sys
from pathlib import Path
import pandas as pd

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent))

from assistant import AssistantCDG
from outils_donnees import get_statistiques_globales, get_pnb_par_segment
from prediction_churn import predire_clients_a_risque
from detection_tendances import detecter_signaux_faibles
from powerbi_sync import get_statut_synchronisation, synchroniser_donnees_powerbi


def get_data_with_ai_insights():
    """
    Récupère les données enrichies avec insights AI
    Retourne un DataFrame pandas pour Power BI
    
    Returns:
        DataFrame avec: segment, nombre_clients, rentabilite_moyenne, clients_a_risque
    """
    # Récupérer statistiques globales
    stats = get_statistiques_globales()
    
    if not stats.get('donnees_trouvees'):
        return pd.DataFrame({'erreur': ['Aucune donnée disponible']})
    
    # Convertir en DataFrame
    segments_data = []
    for segment in stats['par_segment']:
        segments_data.append({
            'segment': segment['segment'],
            'nombre_clients': segment['nombre_clients'],
            'rentabilite_moyenne': segment['rentabilite_moyenne']
        })
    
    df_segments = pd.DataFrame(segments_data)
    
    # Ajouter prédictions churn (optionnel)
    try:
        clients_risque = predire_clients_a_risque(seuil=0.7)
        if clients_risque.get('succes'):
            df_segments['clients_a_risque'] = 0  # Initialiser
            
            # Compter les clients à risque par segment
            for client in clients_risque['clients']:
                segment = client['segment']
                mask = df_segments['segment'] == segment
                df_segments.loc[mask, 'clients_a_risque'] += 1
    except Exception as e:
        print(f"Avertissement: Prédiction churn non disponible - {e}")
        df_segments['clients_a_risque'] = 0
    
    return df_segments


def get_segments_with_details():
    """
    Récupère toutes les statistiques détaillées par segment
    
    Returns:
        DataFrame avec colonnes détaillées (PNB, coûts, rentabilité, etc.)
    """
    stats = get_statistiques_globales()
    
    if not stats.get('donnees_trouvees'):
        return pd.DataFrame({'erreur': ['Aucune donnée disponible']})
    
    # Récupérer détails pour chaque segment
    segments_details = []
    for segment_info in stats['par_segment']:
        segment_name = segment_info['segment']
        
        # Récupérer statistiques PNB
        from outils_donnees import get_pnb_par_segment, get_rentabilite_par_segment
        pnb_data = get_pnb_par_segment(segment_name)
        rent_data = get_rentabilite_par_segment(segment_name)
        
        if pnb_data.get('donnees_trouvees') and rent_data.get('donnees_trouvees'):
            segments_details.append({
                'segment': segment_name,
                'nombre_clients': pnb_data['nombre_clients'],
                'pnb_total': pnb_data['pnb_total'],
                'pnb_moyen': pnb_data['pnb_moyen'],
                'pnb_min': pnb_data['pnb_min'],
                'pnb_max': pnb_data['pnb_max'],
                'rentabilite_totale': rent_data['rentabilite_totale'],
                'rentabilite_moyenne': rent_data['rentabilite_moyenne'],
                'cout_moyen': rent_data['cout_moyen'],
                'marge_pourcent': rent_data['marge_pourcent']
            })
    
    return pd.DataFrame(segments_details)


def get_signaux_faibles_dataframe(seuil=15.0):
    """
    Récupère les signaux faibles sous forme de DataFrame
    
    Args:
        seuil: Seuil de variation en % (défaut: 15%)
        
    Returns:
        DataFrame avec les signaux faibles détectés
    """
    signaux = detecter_signaux_faibles(
        seuil_pourcentage=seuil,
        periode_actuelle="T4-2024",
        periode_precedente="T3-2024"
    )
    
    if not signaux.get('donnees_trouvees') or not signaux.get('signaux'):
        return pd.DataFrame({
            'message': ['Aucun signal faible détecté'],
            'seuil': [seuil]
        })
    
    # Convertir les signaux en DataFrame
    df = pd.DataFrame(signaux['signaux'])
    
    # Ajouter des colonnes calculées utiles pour Power BI
    df['variation_abs_formattee'] = df['variation_absolue'].apply(lambda x: f"{x:,.0f}€")
    df['variation_pct_formattee'] = df['variation_pourcentage'].apply(lambda x: f"{x:+.1f}%")
    df['alerte_niveau'] = df['severite'].apply(lambda x: 'CRITIQUE' if x == 'forte' else 'ATTENTION')
    
    return df


def get_clients_a_risque_dataframe(seuil=0.7):
    """
    Récupère la liste des clients à risque sous forme de DataFrame
    
    Args:
        seuil: Seuil de probabilité (0.0 à 1.0)
        
    Returns:
        DataFrame avec les clients à risque
    """
    clients = predire_clients_a_risque(seuil=seuil)
    
    if not clients.get('succes') or not clients.get('clients'):
        return pd.DataFrame({
            'message': ['Aucun client à risque ou modèle non disponible'],
            'seuil': [seuil]
        })
    
    df = pd.DataFrame(clients['clients'])
    
    # Formater les colonnes
    df['probabilite_pourcent'] = (df['probabilite_churn'] * 100).round(1)
    df['solde_formate'] = df['solde'].apply(lambda x: f"{x:,.0f}€")
    df['actif_text'] = df['actif'].apply(lambda x: 'Oui' if x else 'Non')
    
    return df


def get_ai_commentary(segment: str):
    """
    Génère un commentaire AI pour un segment
    
    Args:
        segment: Nom du segment (France, Germany, Spain)
        
    Returns:
        Commentaire généré par Ollama (texte)
    """
    try:
        assistant = AssistantCDG()
        question = f"Analyse-moi le segment {segment} en 2 phrases maximum, sans HTML"
        response = assistant.poser_question(question)
        return response.get('reponse', f"Analyse du segment {segment} non disponible")
    except Exception as e:
        return f"Erreur: {str(e)}"


# ===== POUR POWER BI: FONCTIONS PRINCIPALES =====


def pousser_vers_chatbot_sqlite(
    dataset_pbi=None,
    label_source: str = "Power BI (Push Python connector)"
):
    r"""
    Pousse UN DATASET POWER BI (DataFrame) DIRECTEMENT dans la SQLite du chatbot —
    SANS passer par un export CSV.

    ⚙️ MODE D'EMPLOI DANS POWER BI DESKTOP :
    1) Onglet « Accueil » → 🔄 « Transformer les données » (Power Query Editor)
    2) Dans Power Query : Onglet « Transformer » → bouton « Exécuter le script Python »
    3) Colle ce code (adapte le chemin du projet) :

        import sys
        sys.path.insert(0, r"C:\Users\LENOVO\Desktop\assistant ai\src")
        from powerbi_connector import pousser_vers_chatbot_sqlite
        # 'dataset' est la variable que Power BI fournit = ta table actuelle
        pousser_vers_chatbot_sqlite(dataset)

    4) Clique OK → tes données sont envoyées au chatbot instantanément.
    5) Reviens dans le chatbot → tu peux poser tes questions (sync auto inutile ici).

    Args:
        dataset_pbi: DataFrame Pandas envoyé par Power BI (le script Python
                     reçoit automatiquement une variable `dataset`).
        label_source: Nom affiché dans le statut de synchro.
    """
    import sys
    import os
    from datetime import datetime
    from pathlib import Path
    import pandas as pd
    import sqlite3

    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    DB_PATH = DATA_DIR / "cdg_test.db"
    EXPORT_DIR = DATA_DIR / "powerbi_export"

    if dataset_pbi is None:
        # Cas d'appel standalone : prend le dataset par défaut que Power BI
        # injecte dans le namespace quand le script est lancé depuis Power Query
        frame = sys._getframe(1)
        dataset_pbi = frame.f_locals.get("dataset")
        if dataset_pbi is None:
            dataset_pbi = frame.f_globals.get("dataset")

    if dataset_pbi is None or (
        isinstance(dataset_pbi, pd.DataFrame) and len(dataset_pbi) == 0
    ):
        return {
            "succes": False,
            "erreur": (
                "Aucun DataFrame fourni et variable 'dataset' introuvable. "
                "Lance cette fonction DANS Power Query → Exécuter le script Python."
            ),
        }

    df = dataset_pbi.copy()
    if not isinstance(df, pd.DataFrame):
        try:
            df = pd.DataFrame(df)
        except Exception:
            return {
                "succes": False,
                "erreur": f"Impossible de convertir l'entrée en DataFrame. Type: {type(df)}",
            }

    # ---- Normalisation (même moteur que data_sync.py) ----
    def _trouver_colonne(df_local, candidats):
        lower_map = {str(c).lower().strip(): c for c in df_local.columns}
        for cand in candidats:
            if cand.lower() in lower_map:
                return lower_map[cand.lower()]
        return None

    COLONNES_CIBLES = [
        "client_id", "segment", "periode", "age", "anciennete",
        "produit", "solde", "pnb_simule", "cout_simule", "rentabilite",
        "est_actif", "a_quitte",
    ]

    # Cas 1 : schéma métier déjà présent (poussé depuis une autre étape Power Query)
    if "client_id" in df.columns and "pnb_simule" in df.columns:
        out = df.copy()
        for col in COLONNES_CIBLES:
            if col not in out.columns:
                if col == "periode":
                    out[col] = "T4-2024"
                elif col in ("est_actif", "a_quitte"):
                    out[col] = 0
                else:
                    out[col] = 0
        out = out[COLONNES_CIBLES]
    else:
        import random
        random.seed(42)
        periodes = ["T1-2024", "T2-2024", "T3-2024", "T4-2024"]

        col_id = _trouver_colonne(df, ["CustomerId", "client_id", "ClientId", "ID", "Client"])
        col_geo = _trouver_colonne(df, ["Geography", "segment", "Segment", "Country", "Pays"])
        col_age = _trouver_colonne(df, ["Age", "age"])
        col_tenure = _trouver_colonne(df, ["Tenure", "anciennete", "Anciennete", "Ancienneté"])
        col_prod = _trouver_colonne(
            df, ["NumOfProducts", "produit", "Produit", "NbProduits", "Produits"]
        )
        col_bal = _trouver_colonne(
            df, ["Balance", "solde", "Solde", "PNB", "pnb", "Montant"]
        )
        col_active = _trouver_colonne(df, ["IsActiveMember", "est_actif", "Actif", "Active"])
        col_exit = _trouver_colonne(
            df, ["Exited", "a_quitte", "Churn", "Churned", "Quitte"]
        )
        col_periode = _trouver_colonne(
            df, ["periode", "Periode", "Période", "Period", "Trimestre", "Quarter"]
        )
        col_pnb = _trouver_colonne(df, ["pnb_simule", "PNB", "pnb"])
        col_cout = _trouver_colonne(df, ["cout_simule", "Cout", "cout", "Cost", "Coût"])
        col_rent = _trouver_colonne(df, ["rentabilite", "Rentabilite", "Rentabilité", "Marge"])

        if col_geo is None or col_bal is None:
            return {
                "succes": False,
                "erreur": (
                    "Colonnes requises introuvables : il faut une colonne Pays/segment ET "
                    "une colonne Montant/solde. Colonnes reçues : "
                    + ", ".join(map(str, list(df.columns)))
                ),
            }

        if col_id is None:
            df["__tmp_id"] = range(15600000, 15600000 + len(df))
            col_id = "__tmp_id"

        solde = pd.to_numeric(df[col_bal], errors="coerce").fillna(0.0)

        if col_pnb:
            pnb = pd.to_numeric(df[col_pnb], errors="coerce").fillna(0)
        else:
            pnb = (solde * 0.02).round(2)
        if col_cout:
            cout = pd.to_numeric(df[col_cout], errors="coerce").fillna(0)
        else:
            cout = (solde * 0.008).round(2)
        if col_rent:
            rent = pd.to_numeric(df[col_rent], errors="coerce").fillna(0)
        else:
            rent = (pnb - cout).round(2)

        if col_periode:
            periode = df[col_periode].astype(str)
        else:
            periode = [random.choice(periodes) for _ in range(len(df))]

        out = pd.DataFrame({
            "client_id": df[col_id].astype(str),
            "segment": df[col_geo].astype(str),
            "periode": periode,
            "age": (pd.to_numeric(df[col_age], errors="coerce").fillna(0).astype(int)
                   if col_age else 0),
            "anciennete": (
                pd.to_numeric(df[col_tenure], errors="coerce").fillna(0).astype(int)
                if col_tenure else 0
            ),
            "produit": (
                pd.to_numeric(df[col_prod], errors="coerce").fillna(1).astype(int)
                if col_prod else 1
            ),
            "solde": solde.round(2),
            "pnb_simule": pnb.round(2),
            "cout_simule": cout.round(2),
            "rentabilite": rent.round(2),
            "est_actif": (
                pd.to_numeric(df[col_active], errors="coerce").fillna(0).astype(int)
                if col_active else 0
            ),
            "a_quitte": (
                pd.to_numeric(df[col_exit], errors="coerce").fillna(0).astype(int)
                if col_exit else 0
            ),
        })

    # ---- Insertion dans la SQLite ----
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        out.to_sql("pnb_analytique", conn, if_exists="replace", index=False)
        cur = conn.cursor()
        for sql_idx in [
            "CREATE INDEX IF NOT EXISTS idx_segment ON pnb_analytique(segment)",
            "CREATE INDEX IF NOT EXISTS idx_produit ON pnb_analytique(produit)",
            "CREATE INDEX IF NOT EXISTS idx_client ON pnb_analytique(client_id)",
            "CREATE INDEX IF NOT EXISTS idx_periode ON pnb_analytique(periode)",
        ]:
            cur.execute(sql_idx)
        conn.commit()
    finally:
        conn.close()

    # ---- Ecrit un fichier témoin + sync_meta pour que l'auto-sync sache que
    #      les données sont déjà à jour (pas de rebuild 2 fois).
    try:
        import json
        meta_path = DATA_DIR / "sync_meta.json"
        meta = {
            "derniere_sync": datetime.now().isoformat(),
            "source": label_source,
            "origine": "powerbi_python_push",
            "nombre_lignes": len(out),
            "mtime_source": datetime.now().timestamp(),
        }
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)

        status_path = DATA_DIR / "sync_status.json"
        pnb_total = float(out["pnb_simule"].sum())
        rent_total = float(out["rentabilite"].sum())
        status = {
            "statut": "synchronisé",
            "source": label_source,
            "derniere_synchro": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "derniere_synchro_iso": datetime.now().isoformat(),
            "nombre_clients": len(out),
            "pnb_total": round(pnb_total, 2),
            "rentabilite_totale": round(rent_total, 2),
            "auto_sync_actif": True,
        }
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

    # Snapshot du push (pour debug / audit)
    try:
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        csv_backup = (
            EXPORT_DIR
            / f"pbi_push_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        out.to_csv(csv_backup, index=False, encoding="utf-8-sig")
    except Exception:
        pass

    return {
        "succes": True,
        "message": (
            f"✅ Push Power BI → SQLite OK : {len(out):,} lignes insérées "
            f"(source: {label_source}). Passe au chatbot !"
        ).replace(",", " "),
        "lignes": len(out),
        "segments": list(out["segment"].dropna().unique())[:10],
        "db": str(DB_PATH),
        "dataframe_pret": out,
    }


def tableau_bord_apres_push(resultat_push: dict) -> dict:
    """
    Fabrique plusieurs DataFrames que Power BI affiche automatiquement
    dans son tableau de bord après un script Python.
    Appelle ça à la FIN de ton script Power Query :
        globals().update(tableau_bord_apres_push(result))
    """
    import pandas as pd

    df = resultat_push.get("dataframe_pret")
    if df is None:
        return {}

    # 1) Données complètes (tout le dataset - Power BI en affichera 20 en préview
    #    mais l'étape suivante contient BIEN toutes les lignes)
    out_tables = {"dataset_complet": df.copy()}

    # 2) Tableau de bord : stats par segment
    try:
        seg = (
            df.groupby("segment", dropna=False)
            .agg(
                Clients=("client_id", "nunique"),
                PNB_Simule=("pnb_simule", "sum"),
                Cout_Simule=("cout_simule", "sum"),
                Rentabilite=("rentabilite", "sum"),
                Solde_Moyen=("solde", "mean"),
            )
            .reset_index()
            .sort_values("PNB_Simule", ascending=False)
        )
        for c in ["PNB_Simule", "Cout_Simule", "Rentabilite", "Solde_Moyen"]:
            if c in seg.columns:
                seg[c] = seg[c].round(2)
        out_tables["01_Dashboard_Par_Segment"] = seg
    except Exception:
        pass

    # 3) Tableau de bord : stats par produit
    try:
        prod = (
            df.groupby("produit", dropna=False)
            .agg(
                Clients=("client_id", "nunique"),
                PNB_Simule=("pnb_simule", "sum"),
                Rentabilite=("rentabilite", "sum"),
                Churn_Clients=("a_quitte", "sum"),
            )
            .reset_index()
            .sort_values("produit")
        )
        for c in ["PNB_Simule", "Rentabilite"]:
            if c in prod.columns:
                prod[c] = prod[c].round(2)
        out_tables["02_Dashboard_Par_Produit"] = prod
    except Exception:
        pass

    # 4) Tableau de bord : stats par période
    try:
        per = (
            df.groupby("periode", dropna=False)
            .agg(
                Clients=("client_id", "nunique"),
                PNB_Simule=("pnb_simule", "sum"),
                Rentabilite=("rentabilite", "sum"),
                Solde_Total=("solde", "sum"),
            )
            .reset_index()
            .sort_values("periode")
        )
        for c in ["PNB_Simule", "Rentabilite", "Solde_Total"]:
            if c in per.columns:
                per[c] = per[c].round(2)
        out_tables["03_Dashboard_Par_Periode"] = per
    except Exception:
        pass

    # 5) Stats globales (1 ligne)
    try:
        nb_clients = df["client_id"].nunique()
        total_pnb = float(df["pnb_simule"].sum())
        total_rent = float(df["rentabilite"].sum())
        total_solde = float(df["solde"].sum())
        churn = int(df["a_quitte"].sum())
        global_df = pd.DataFrame(
            {
                "Nombre_Lignes": [len(df)],
                "Clients_Uniques": [nb_clients],
                "PNB_Simule_Total": [round(total_pnb, 2)],
                "Cout_Simule_Total": [round(float(df["cout_simule"].sum()), 2)],
                "Rentabilite_Totale": [round(total_rent, 2)],
                "Solde_Total_Portefeuille": [round(total_solde, 2)],
                "Taux_Churn_Pct": [round(100.0 * churn / nb_clients, 2) if nb_clients else 0.0],
                "Date_Push": [pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")],
                "Source": [resultat_push.get("lignes") and "OK" or "Push"],
            }
        )
        out_tables["00_Verification_Statut_Push"] = global_df
    except Exception:
        pass

    return out_tables


def main_segments():
    """
    Fonction principale pour Power BI: Segments avec insights AI
    Utilisez cette fonction pour obtenir une vue d'ensemble
    """
    return get_data_with_ai_insights()


def main_segments_details():
    """
    Fonction pour Power BI: Détails complets par segment
    Utilisez pour analyses approfondies (PNB, rentabilité, marges)
    """
    return get_segments_with_details()


def main_signaux_faibles(seuil=15.0):
    """
    Fonction pour Power BI: Signaux faibles / Alertes
    Utilisez pour détecter les variations anormales
    """
    return get_signaux_faibles_dataframe(seuil)


def main_clients_risque(seuil=0.7):
    """
    Fonction pour Power BI: Clients à risque de churn
    Utilisez pour la prévention du départ clients
    """
    return get_clients_a_risque_dataframe(seuil)


# Test en ligne de commande
if __name__ == "__main__":
    print("=" * 70)
    print("TEST DU CONNECTEUR POWER BI")
    print("=" * 70)
    print()
    
    print("1. Segments avec insights AI:")
    df1 = main_segments()
    print(df1)
    print()
    
    print("2. Détails complets par segment:")
    df2 = main_segments_details()
    print(df2)
    print()
    
    print("3. Signaux faibles (seuil 15%):")
    df3 = main_signaux_faibles(15.0)
    print(df3.head() if len(df3) > 0 else "Aucun signal")
    print()
    
    print("4. Clients à risque (probabilité > 70%):")
    df4 = main_clients_risque(0.7)
    print(f"{len(df4)} clients à risque" if len(df4) > 0 else "Aucun client à risque")
    print()
    
    print("=" * 70)
    print("✅ Connecteur Power BI prêt!")
    print("=" * 70)
