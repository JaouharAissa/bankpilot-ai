#!/usr/bin/env python3
"""
Script de vérification rapide avant tests complets
Vérifie que tous les composants sont opérationnels
"""

import sys
from pathlib import Path

def check_ollama():
    """Vérifie qu'Ollama est disponible"""
    try:
        import ollama
        models = ollama.list()
        print("✅ Ollama disponible")
        
        # Chercher llama3.1
        model_names = [m.get('name', m.get('model', '')) for m in models.get('models', [])]
        if any('llama3.1' in name.lower() for name in model_names):
            print("✅ Modèle llama3.1 trouvé")
            return True
        else:
            print("❌ Modèle llama3.1 non trouvé")
            print(f"   Modèles disponibles: {model_names}")
            return False
    except Exception as e:
        print(f"❌ Erreur Ollama: {e}")
        return False

def check_database():
    """Vérifie que la base de données existe"""
    db_path = Path("data/cdg_test.db")
    if db_path.exists():
        print(f"✅ Base de données trouvée: {db_path}")
        return True
    else:
        print(f"❌ Base de données manquante: {db_path}")
        return False

def check_model_ml():
    """Vérifie que le modèle de churn existe"""
    model_path = Path("models/churn_model.pkl")
    if model_path.exists():
        print(f"✅ Modèle ML trouvé: {model_path}")
        return True
    else:
        print(f"❌ Modèle ML manquant: {model_path}")
        return False

def check_imports():
    """Vérifie que tous les modules peuvent être importés"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        
        import assistant, outils_donnees, visualisations
        import prediction_churn, export, alertes
        print("✅ Tous les modules importés avec succès")
        return True
    except ImportError as e:
        print(f"❌ Erreur d'import: {e}")
        return False

def check_outputs_dir():
    """Vérifie que le dossier outputs existe"""
    outputs = Path("outputs")
    exports = Path("outputs/exports")
    
    if not outputs.exists():
        outputs.mkdir(exist_ok=True)
        print("✅ Dossier outputs créé")
    else:
        print("✅ Dossier outputs existe")
    
    if not exports.exists():
        exports.mkdir(exist_ok=True)
        print("✅ Dossier exports créé")
    else:
        print("✅ Dossier exports existe")
    
    return True

def main():
    """Exécute toutes les vérifications"""
    print("\n🔍 VÉRIFICATION RAPIDE DU SYSTÈME")
    print("=" * 50)
    
    checks = [
        ("Ollama", check_ollama),
        ("Base de données", check_database),
        ("Modèle ML", check_model_ml),
        ("Dossiers outputs", check_outputs_dir),
        ("Imports Python", check_imports),
    ]
    
    results = {}
    for name, check_func in checks:
        print(f"\n{name}:")
        results[name] = check_func()
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ:")
    
    all_ok = all(results.values())
    
    for name, status in results.items():
        status_icon = "✅" if status else "❌"
        print(f"{status_icon} {name}")
    
    print("=" * 50)
    
    if all_ok:
        print("\n✅ TOUT EST PRÊT ! Vous pouvez lancer l'application:")
        print("   streamlit run src/app.py")
        return 0
    else:
        print("\n⚠️  Certains éléments nécessitent votre attention")
        print("   Corrigez les problèmes ci-dessus avant de continuer")
        return 1

if __name__ == "__main__":
    sys.exit(main())
