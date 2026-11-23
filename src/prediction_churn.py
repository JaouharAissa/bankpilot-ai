"""
Module de prédiction du churn (départ client) via Machine Learning
Utilise RandomForestClassifier pour prédire le risque de départ des clients
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, classification_report
import joblib


# Configuration du logging
logger = logging.getLogger('prediction_churn')

# Chemins
BASE_DIR = Path(__file__).parent.parent
DATA_PATH = BASE_DIR / 'data' / 'Churn_Modelling.csv'
MODEL_DIR = BASE_DIR / 'models'
MODEL_PATH = MODEL_DIR / 'churn_model.pkl'
METRICS_PATH = MODEL_DIR / 'model_metrics.txt'


def entrainer_modele_churn() -> Dict[str, Any]:
    """
    Entraîne un modèle RandomForest pour prédire le churn
    
    Returns:
        Dictionnaire avec les métriques du modèle
    """
    try:
        # Créer le dossier models s'il n'existe pas
        MODEL_DIR.mkdir(exist_ok=True)
        
        # Charger les données
        logger.info("Chargement des données...")
        df = pd.read_csv(DATA_PATH)
        
        # Sélectionner les features
        features = ['CreditScore', 'Age', 'Tenure', 'Balance', 'NumOfProducts', 'HasCrCard', 'IsActiveMember']
        
        # Encoder Geography (France, Germany, Spain)
        geography_dummies = pd.get_dummies(df['Geography'], prefix='Geo', drop_first=True)
        
        # Encoder Gender
        df['Gender_Male'] = (df['Gender'] == 'Male').astype(int)
        
        # Préparer X et y
        X = df[features].copy()
        X = pd.concat([X, geography_dummies, df[['Gender_Male']]], axis=1)
        y = df['Exited']
        
        # Split train/test (80/20)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        logger.info(f"Entraînement sur {len(X_train)} exemples...")
        
        # Entraîner le modèle
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        
        model.fit(X_train, y_train)
        
        # Prédictions
        y_pred = model.predict(X_test)
        y_pred_proba = model.predict_proba(X_test)[:, 1]
        
        # Calculer les métriques
        accuracy = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_pred_proba)
        
        # Rapport de classification
        report = classification_report(y_test, y_pred, output_dict=True)
        
        # Feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        # Sauvegarder le modèle
        joblib.dump({
            'model': model,
            'features': list(X.columns),
            'feature_names_original': features
        }, MODEL_PATH)
        
        logger.info(f"Modèle sauvegardé: {MODEL_PATH}")
        
        # Sauvegarder les métriques
        metrics_text = f"""=== MÉTRIQUES DU MODÈLE DE PRÉDICTION DE CHURN ===

Précision (Accuracy): {accuracy:.4f}
AUC-ROC: {auc:.4f}

Détails par classe:
- Classe 0 (Ne part pas):
  Precision: {report['0']['precision']:.4f}
  Recall: {report['0']['recall']:.4f}
  F1-Score: {report['0']['f1-score']:.4f}

- Classe 1 (Part):
  Precision: {report['1']['precision']:.4f}
  Recall: {report['1']['recall']:.4f}
  F1-Score: {report['1']['f1-score']:.4f}

Taille dataset:
- Train: {len(X_train)} exemples
- Test: {len(X_test)} exemples

Top 5 features importantes:
{feature_importance.head(5).to_string(index=False)}
"""
        
        with open(METRICS_PATH, 'w', encoding='utf-8') as f:
            f.write(metrics_text)
        
        logger.info("Métriques sauvegardées")
        
        return {
            "succes": True,
            "accuracy": float(accuracy),
            "auc": float(auc),
            "precision_churn": float(report['1']['precision']),
            "recall_churn": float(report['1']['recall']),
            "f1_churn": float(report['1']['f1-score']),
            "feature_importance": feature_importance.head(5).to_dict('records'),
            "model_path": str(MODEL_PATH)
        }
        
    except Exception as e:
        logger.error(f"Erreur entraînement modèle: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


def charger_modele() -> Dict[str, Any]:
    """
    Charge le modèle de prédiction de churn depuis le disque
    
    Returns:
        Dictionnaire avec le modèle et les métadonnées
    """
    try:
        if not MODEL_PATH.exists():
            # Entraîner le modèle s'il n'existe pas
            logger.info("Modèle non trouvé, entraînement en cours...")
            result = entrainer_modele_churn()
            if not result['succes']:
                return {"succes": False, "erreur": "Impossible d'entraîner le modèle"}
        
        model_data = joblib.load(MODEL_PATH)
        return {
            "succes": True,
            "model": model_data['model'],
            "features": model_data['features'],
            "feature_names_original": model_data['feature_names_original']
        }
        
    except Exception as e:
        logger.error(f"Erreur chargement modèle: {e}")
        return {"succes": False, "erreur": str(e)}


def predire_risque_churn(client_id: int) -> Dict[str, Any]:
    """
    Prédit le risque de churn pour un client spécifique
    
    Args:
        client_id: ID du client
        
    Returns:
        Dictionnaire avec la probabilité et les facteurs principaux
    """
    try:
        # Charger le modèle
        model_data = charger_modele()
        if not model_data['succes']:
            return model_data
        
        model = model_data['model']
        features_order = model_data['features']
        
        # Charger les données du client
        df = pd.read_csv(DATA_PATH)
        client = df[df['CustomerId'] == client_id]
        
        if len(client) == 0:
            return {
                "succes": False,
                "erreur": f"Client {client_id} non trouvé"
            }
        
        client = client.iloc[0]
        
        # Préparer les features
        X_client = pd.DataFrame({
            'CreditScore': [client['CreditScore']],
            'Age': [client['Age']],
            'Tenure': [client['Tenure']],
            'Balance': [client['Balance']],
            'NumOfProducts': [client['NumOfProducts']],
            'HasCrCard': [client['HasCrCard']],
            'IsActiveMember': [client['IsActiveMember']],
            'Geo_Germany': [1 if client['Geography'] == 'Germany' else 0],
            'Geo_Spain': [1 if client['Geography'] == 'Spain' else 0],
            'Gender_Male': [1 if client['Gender'] == 'Male' else 0]
        })
        
        # Réordonner selon l'ordre du modèle
        X_client = X_client[features_order]
        
        # Prédire
        proba_churn = model.predict_proba(X_client)[0][1]
        prediction = int(proba_churn >= 0.5)
        
        # Feature importance pour ce client
        feature_values = X_client.iloc[0].to_dict()
        
        # Identifier les facteurs de risque principaux
        facteurs_risque = []
        
        if client['Age'] > 50:
            facteurs_risque.append(f"Âge élevé ({client['Age']} ans)")
        if client['NumOfProducts'] == 1:
            facteurs_risque.append("Un seul produit")
        if client['IsActiveMember'] == 0:
            facteurs_risque.append("Client inactif")
        if client['Balance'] == 0:
            facteurs_risque.append("Solde nul")
        if client['Geography'] == 'Germany':
            facteurs_risque.append("Segment Germany (risque plus élevé)")
        
        logger.info(
            f"Prédiction churn pour client {client_id}",
            extra={'extra_data': {
                'client_id': client_id,
                'probabilite': float(proba_churn),
                'prediction': prediction
            }}
        )
        
        return {
            "succes": True,
            "client_id": int(client_id),
            "probabilite_churn": float(proba_churn),
            "prediction": "À risque de départ" if prediction == 1 else "Pas de risque immédiat",
            "niveau_risque": "ÉLEVÉ" if proba_churn >= 0.7 else ("MOYEN" if proba_churn >= 0.4 else "FAIBLE"),
            "facteurs_risque": facteurs_risque if facteurs_risque else ["Aucun facteur majeur identifié"],
            "informations_client": {
                "segment": client['Geography'],
                "age": int(client['Age']),
                "anciennete": int(client['Tenure']),
                "solde": float(client['Balance']),
                "nb_produits": int(client['NumOfProducts']),
                "actif": bool(client['IsActiveMember'])
            }
        }
        
    except Exception as e:
        logger.error(f"Erreur prédiction churn: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


def predire_clients_a_risque(seuil: float = 0.7) -> Dict[str, Any]:
    """
    Liste tous les clients dont la probabilité de churn dépasse le seuil
    
    Args:
        seuil: Seuil de probabilité (défaut: 0.7)
        
    Returns:
        Dictionnaire avec la liste des clients à risque
    """
    try:
        # Charger le modèle
        model_data = charger_modele()
        if not model_data['succes']:
            return model_data
        
        model = model_data['model']
        features_order = model_data['features']
        
        # Charger toutes les données
        df = pd.read_csv(DATA_PATH)
        
        # Préparer les features pour tous les clients
        geography_dummies = pd.get_dummies(df['Geography'], prefix='Geo', drop_first=True)
        df['Gender_Male'] = (df['Gender'] == 'Male').astype(int)
        
        features_base = ['CreditScore', 'Age', 'Tenure', 'Balance', 'NumOfProducts', 'HasCrCard', 'IsActiveMember']
        X = df[features_base].copy()
        X = pd.concat([X, geography_dummies, df[['Gender_Male']]], axis=1)
        X = X[features_order]
        
        # Prédire pour tous
        probas = model.predict_proba(X)[:, 1]
        
        # Filtrer ceux au-dessus du seuil
        indices_risque = probas >= seuil
        clients_risque = df[indices_risque].copy()
        clients_risque['probabilite_churn'] = probas[indices_risque]
        
        # Trier par probabilité décroissante
        clients_risque = clients_risque.sort_values('probabilite_churn', ascending=False)
        
        # Préparer le résultat
        liste_clients = []
        for _, client in clients_risque.head(50).iterrows():  # Limiter à 50
            liste_clients.append({
                "client_id": int(client['CustomerId']),
                "probabilite_churn": float(client['probabilite_churn']),
                "segment": client['Geography'],
                "age": int(client['Age']),
                "solde": float(client['Balance']),
                "nb_produits": int(client['NumOfProducts']),
                "actif": bool(client['IsActiveMember'])
            })
        
        logger.info(
            f"Clients à risque identifiés: {len(liste_clients)}",
            extra={'extra_data': {
                'seuil': seuil,
                'nombre_total': int(indices_risque.sum())
            }}
        )
        
        return {
            "succes": True,
            "seuil_utilise": float(seuil),
            "nombre_total_clients_risque": int(indices_risque.sum()),
            "clients_affiches": len(liste_clients),
            "clients": liste_clients
        }
        
    except Exception as e:
        logger.error(f"Erreur détection clients à risque: {e}")
        return {
            "succes": False,
            "erreur": str(e)
        }


# Test et entraînement si exécuté directement
if __name__ == "__main__":
    print("=" * 70)
    print("ENTRAÎNEMENT DU MODÈLE DE PRÉDICTION DE CHURN")
    print("=" * 70)
    print()
    
    result = entrainer_modele_churn()
    
    if result['succes']:
        print("✅ Modèle entraîné avec succès!\n")
        print(f"Accuracy: {result['accuracy']:.4f}")
        print(f"AUC-ROC: {result['auc']:.4f}")
        print(f"Précision (churn): {result['precision_churn']:.4f}")
        print(f"Recall (churn): {result['recall_churn']:.4f}")
        print(f"F1-Score (churn): {result['f1_churn']:.4f}")
        print(f"\nModèle sauvegardé: {result['model_path']}")
        
        print("\n" + "=" * 70)
        print("TEST DE PRÉDICTION")
        print("=" * 70)
        
        # Tester sur un client
        test_result = predire_risque_churn(15634602)
        if test_result['succes']:
            print(f"\nClient {test_result['client_id']}:")
            print(f"  Probabilité de churn: {test_result['probabilite_churn']:.2%}")
            print(f"  Prédiction: {test_result['prediction']}")
            print(f"  Niveau de risque: {test_result['niveau_risque']}")
        
        # Lister clients à risque
        risque_result = predire_clients_a_risque(0.7)
        if risque_result['succes']:
            print(f"\n{risque_result['nombre_total_clients_risque']} clients à risque élevé (seuil={risque_result['seuil_utilise']})")
            print(f"Top 3:")
            for i, c in enumerate(risque_result['clients'][:3], 1):
                print(f"  {i}. Client {c['client_id']}: {c['probabilite_churn']:.2%} - {c['segment']}")
    else:
        print(f"❌ Erreur: {result['erreur']}")
