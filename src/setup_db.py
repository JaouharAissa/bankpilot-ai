"""
Script de préparation de la base de données pour l'assistant Contrôleur de Gestion
Transforme les données Churn_Modelling.csv en données métier de contrôle de gestion
"""

import pandas as pd
import sqlite3
import os
import sys
from pathlib import Path

# Force UTF-8 pour Windows (évite erreurs charmap avec les emojis dans le print)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

def charger_et_transformer_donnees(chemin_csv):
    """
    Charge le fichier CSV et transforme les colonnes vers un vocabulaire métier
    
    Args:
        chemin_csv: Chemin vers le fichier Churn_Modelling.csv
        
    Returns:
        DataFrame transformé avec colonnes métier
    """
    print(f"📂 Chargement des données depuis {chemin_csv}...")
    
    # Vérifier que le fichier existe
    if not os.path.exists(chemin_csv):
        raise FileNotFoundError(f"Le fichier {chemin_csv} n'existe pas")
    
    # Charger les données
    df = pd.read_csv(chemin_csv)
    print(f"✓ {len(df)} lignes chargées")
    
    # Transformation vers vocabulaire métier de Contrôle de Gestion
    print("🔄 Transformation des données vers le vocabulaire métier...")
    
    # Créer une colonne de période simulée (répartition aléatoire sur 4 trimestres)
    import random
    random.seed(42)  # Pour reproductibilité
    periodes = ['T1-2024', 'T2-2024', 'T3-2024', 'T4-2024']
    df['periode_simulee'] = [random.choice(periodes) for _ in range(len(df))]
    
    df_transformed = pd.DataFrame({
        'client_id': df['CustomerId'],
        'segment': df['Geography'],
        'periode': df['periode_simulee'],  # Nouvelle colonne
        'age': df['Age'],
        'anciennete': df['Tenure'],
        'produit': df['NumOfProducts'],  # Nombre de produits détenus
        'solde': df['Balance'],
        # Simulation de PNB (2% du solde)
        'pnb_simule': (df['Balance'] * 0.02).round(2),
        # Simulation de coûts (0.8% du solde)
        'cout_simule': (df['Balance'] * 0.008).round(2),
        # Calcul de la rentabilité
        'rentabilite': ((df['Balance'] * 0.02) - (df['Balance'] * 0.008)).round(2),
        'est_actif': df['IsActiveMember'],
        'a_quitte': df['Exited']
    })
    
    print(f"✓ Transformation terminée - {len(df_transformed.columns)} colonnes métier créées")
    print(f"  Colonnes: {', '.join(df_transformed.columns)}")
    
    return df_transformed


def creer_base_donnees(df, chemin_db):
    """
    Crée la base SQLite et insère les données transformées
    
    Args:
        df: DataFrame transformé
        chemin_db: Chemin de la base de données SQLite à créer
    """
    print(f"💾 Création de la base de données {chemin_db}...")
    
    # Créer le dossier data s'il n'existe pas
    Path(chemin_db).parent.mkdir(parents=True, exist_ok=True)
    
    # Supprimer la base existante si elle existe
    if os.path.exists(chemin_db):
        os.remove(chemin_db)
        print("  (Ancienne base supprimée)")
    
    # Connexion et création de la table
    conn = sqlite3.connect(chemin_db)
    
    try:
        # Insérer les données dans la table pnb_analytique
        df.to_sql('pnb_analytique', conn, if_exists='replace', index=False)
        
        # Créer des index pour améliorer les performances
        cursor = conn.cursor()
        cursor.execute('CREATE INDEX idx_segment ON pnb_analytique(segment)')
        cursor.execute('CREATE INDEX idx_produit ON pnb_analytique(produit)')
        cursor.execute('CREATE INDEX idx_client ON pnb_analytique(client_id)')
        cursor.execute('CREATE INDEX idx_periode ON pnb_analytique(periode)')  # Nouvel index
        conn.commit()
        
        print(f"✓ Base de données créée avec succès")
        print(f"  Table: pnb_analytique ({len(df)} lignes)")
        
        # Afficher quelques statistiques
        cursor.execute('SELECT COUNT(*) FROM pnb_analytique')
        count = cursor.fetchone()[0]
        
        cursor.execute('SELECT DISTINCT segment FROM pnb_analytique')
        segments = [row[0] for row in cursor.fetchall()]
        
        cursor.execute('SELECT MIN(pnb_simule), MAX(pnb_simule), AVG(pnb_simule) FROM pnb_analytique')
        pnb_min, pnb_max, pnb_avg = cursor.fetchone()
        
        print(f"\n📊 Statistiques:")
        print(f"  Nombre total de clients: {count}")
        print(f"  Segments disponibles: {', '.join(segments)}")
        print(f"  PNB simulé - Min: {pnb_min:.2f}, Max: {pnb_max:.2f}, Moyenne: {pnb_avg:.2f}")
        
    except Exception as e:
        print(f"❌ Erreur lors de la création de la base: {e}")
        raise
    finally:
        conn.close()


def main():
    """
    Orchestre la préparation de la base.
    Priorité: export Power BI (data/powerbi_export/) puis CSV Churn_Modelling.
    """
    print("=" * 70)
    print("🚀 PRÉPARATION DE LA BASE DE DONNÉES - ASSISTANT CONTRÔLEUR DE GESTION")
    print("=" * 70)
    print()

    repertoire_base = Path(__file__).parent.parent
    chemin_db = repertoire_base / 'data' / 'cdg_test.db'

    try:
        # Preferer le sync unifié (Power BI export > CSV)
        try:
            from data_sync import reconstruire_base, EXPORT_DIR
            print(f"📂 Source prioritaire: exports Power BI dans {EXPORT_DIR}")
            result = reconstruire_base()
            if not result.get('succes'):
                raise RuntimeError(result.get('erreur', 'Sync échoué'))
            print(f"✅ Source: {result.get('origine')} — {result.get('nombre_lignes')} lignes")
            print(f"   Fichier: {result.get('source')}")
        except Exception as sync_err:
            print(f"⚠️ Sync Power BI indisponible ({sync_err}), fallback CSV...")
            chemin_csv = repertoire_base / 'data' / 'Churn_Modelling.csv'
            df_transformed = charger_et_transformer_donnees(chemin_csv)
            print("\n📋 Aperçu des données transformées:")
            print(df_transformed.head())
            print()
            creer_base_donnees(df_transformed, chemin_db)

        print()
        print("=" * 70)
        print("✅ PRÉPARATION TERMINÉE AVEC SUCCÈS")
        print("=" * 70)
        print(f"\n💡 Base prête: {chemin_db}")
        print("   Placez vos exports Power BI dans data/powerbi_export/ puis:")
        print("   python src/data_sync.py rebuild")
        print("   streamlit run src/app.py")

    except Exception as e:
        print()
        print("=" * 70)
        print(f"❌ ERREUR: {e}")
        print("=" * 70)
        raise


if __name__ == "__main__":
    main()
