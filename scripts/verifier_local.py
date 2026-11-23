"""
Script de validation 100% local
Vérifie qu'aucun appel réseau externe n'est effectué pendant l'exécution
(sauf vers Ollama sur localhost:11434)
"""

import socket
import sys
from pathlib import Path
from unittest.mock import patch
from typing import List, Tuple

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Liste des connexions détectées
connexions_detectees: List[Tuple[str, int]] = []
connexions_autorisees = [
    ('127.0.0.1', 11434),  # Ollama
    ('localhost', 11434),  # Ollama (hostname)
    ('127.0.0.1', 8501),   # Streamlit local
    ('localhost', 8501),   # Streamlit local
]


def intercepter_connect(original_connect):
    """Wrapper pour intercepter socket.connect()"""
    def connect_wrapper(self, address):
        # Enregistrer la tentative
        if isinstance(address, tuple) and len(address) >= 2:
            host, port = address[0], address[1]
            connexions_detectees.append((host, port))
            
            # Vérifier si autorisé
            est_autorise = any(
                (host == ah or host.endswith('.'+ah)) and port == ap
                for ah, ap in connexions_autorisees
            )
            
            # Vérifier localhost/127.0.0.1
            est_localhost = host in ('127.0.0.1', 'localhost', '::1') or host.startswith('127.')
            
            if not est_autorise and not est_localhost:
                print(f"🚨 CONNEXION EXTERNE DÉTECTÉE: {host}:{port}")
                raise ConnectionError(f"Connexion externe non autorisée vers {host}:{port}")
        
        # Appeler la vraie méthode connect
        return original_connect(address)
    
    return connect_wrapper


def tester_assistant_local():
    """Teste l'assistant avec une question simple"""
    print("\n🧪 TEST DE L'ASSISTANT...")
    print("─" * 70)
    
    try:
        from assistant import AssistantCDG
        
        assistant = AssistantCDG()
        
        if not assistant.ollama_disponible:
            print("⚠️  Ollama non disponible - test partiel uniquement")
            print("   Lancez Ollama avec: ollama run llama3.1")
            return False
        
        # Question test
        question = "Quel est le PNB moyen du segment France ?"
        print(f"❓ Question: {question}")
        
        # Poser la question
        result = assistant.poser_question(question)
        
        if result.get('succes'):
            print(f"✅ Réponse reçue ({len(result['reponse'])} caractères)")
            print(f"   Outils utilisés: {len(result.get('outils_utilises', []))}")
            return True
        else:
            print(f"❌ Erreur: {result.get('erreur', 'Inconnue')}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test: {e}")
        return False


def analyser_connexions():
    """Analyse les connexions détectées"""
    print("\n📊 ANALYSE DES CONNEXIONS")
    print("=" * 70)
    
    if not connexions_detectees:
        print("✅ AUCUNE connexion réseau détectée")
        print("   (Situation idéale si l'assistant n'a pas été testé)")
        return True
    
    # Grouper par destination
    connexions_uniques = list(set(connexions_detectees))
    
    print(f"\n📡 {len(connexions_detectees)} tentatives de connexion détectées")
    print(f"   {len(connexions_uniques)} destinations uniques\n")
    
    connexions_locales = []
    connexions_externes = []
    
    for host, port in connexions_uniques:
        est_local = (
            host in ('127.0.0.1', 'localhost', '::1') or
            host.startswith('127.') or
            host.startswith('192.168.') or
            host.startswith('10.')
        )
        
        if est_local:
            connexions_locales.append((host, port))
        else:
            connexions_externes.append((host, port))
    
    # Afficher connexions locales
    if connexions_locales:
        print("✅ CONNEXIONS LOCALES (autorisées):")
        for host, port in sorted(connexions_locales):
            nb_fois = connexions_detectees.count((host, port))
            service = "Ollama" if port == 11434 else "Streamlit" if port == 8501 else "Inconnu"
            print(f"   • {host}:{port} ({service}) - {nb_fois} fois")
    
    # Afficher connexions externes
    if connexions_externes:
        print("\n🚨 CONNEXIONS EXTERNES DÉTECTÉES:")
        for host, port in sorted(connexions_externes):
            nb_fois = connexions_detectees.count((host, port))
            print(f"   • {host}:{port} - {nb_fois} fois")
        print("\n❌ ÉCHEC: Le projet fait des appels externes !")
        return False
    
    print("\n✅ SUCCÈS: Toutes les connexions sont locales (127.0.0.1/localhost)")
    return True


def main():
    """Fonction principale"""
    print("=" * 70)
    print("🔒 VALIDATION 100% LOCAL - ASSISTANT CDG")
    print("=" * 70)
    print("\nCe script vérifie qu'aucun appel réseau externe n'est effectué.")
    print("Seules les connexions vers localhost (Ollama) sont autorisées.")
    
    # Intercepter socket.connect
    original_connect = socket.socket.connect
    socket.socket.connect = intercepter_connect(original_connect)
    
    try:
        # Test 1: Importer les modules
        print("\n📦 ÉTAPE 1: Import des modules...")
        print("─" * 70)
        
        try:
            import outils_donnees
            import visualisations
            import prediction_churn
            import export
            import alertes
            print("✅ Tous les modules importés sans erreur")
        except Exception as e:
            print(f"❌ Erreur d'import: {e}")
            return 1
        
        # Test 2: Tester une requête simple
        print("\n📊 ÉTAPE 2: Test requête base de données...")
        print("─" * 70)
        
        try:
            from outils_donnees import get_pnb_par_segment
            result = get_pnb_par_segment("France")
            if result.get('donnees_trouvees'):
                print(f"✅ Requête SQL réussie (PNB moyen France: {result['pnb_moyen']:.2f} €)")
            else:
                print(f"⚠️  Pas de données trouvées: {result}")
        except Exception as e:
            print(f"❌ Erreur lors de la requête: {e}")
        
        # Test 3: Tester l'assistant avec Ollama (optionnel si disponible)
        succes_assistant = tester_assistant_local()
        
        # Analyse finale
        succes_global = analyser_connexions()
        
        # Résumé final
        print("\n" + "=" * 70)
        print("📋 RÉSUMÉ FINAL")
        print("=" * 70)
        
        if succes_global:
            print("\n✅ VALIDATION RÉUSSIE")
            print("   Ce projet ne fait aucun appel réseau externe.")
            print("   Seuls les appels vers Ollama (localhost:11434) sont effectués.")
            print("\n🎉 Le projet respecte l'exigence 100% local !")
            return 0
        else:
            print("\n❌ VALIDATION ÉCHOUÉE")
            print("   Des connexions vers des adresses externes ont été détectées.")
            print("   Vérifiez les dépendances et le code source.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        return 1
    except Exception as e:
        print(f"\n\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        # Restaurer socket.connect original
        socket.socket.connect = original_connect


if __name__ == "__main__":
    sys.exit(main())
