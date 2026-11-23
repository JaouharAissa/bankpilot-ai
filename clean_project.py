"""
Script de nettoyage du projet Assistant CDG
Nettoie les fichiers redondants, temporaires et obsolètes
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta


def nettoyer_outputs(keep_last=3):
    """
    Nettoie le dossier outputs/ en gardant seulement les N derniers fichiers
    
    Args:
        keep_last: Nombre de fichiers à garder par type (défaut: 3)
    """
    print("🧹 Nettoyage du dossier outputs/")
    print("=" * 60)
    
    outputs_dir = Path(__file__).parent / 'outputs'
    
    if not outputs_dir.exists():
        print("   ✅ Dossier outputs/ n'existe pas, rien à nettoyer")
        return
    
    # Fichiers Word
    fichiers_word = sorted(
        outputs_dir.glob('rapport_*.docx'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    fichiers_supprimes = 0
    
    if len(fichiers_word) > keep_last:
        print(f"   📄 Fichiers Word trouvés: {len(fichiers_word)}")
        print(f"   🗑️  Suppression de {len(fichiers_word) - keep_last} anciens rapports...")
        
        for fichier in fichiers_word[keep_last:]:
            try:
                fichier.unlink()
                fichiers_supprimes += 1
                print(f"      - Supprimé: {fichier.name}")
            except Exception as e:
                print(f"      ❌ Erreur: {fichier.name} - {e}")
    else:
        print(f"   ✅ Fichiers Word: {len(fichiers_word)} (OK, < {keep_last})")
    
    # Fichiers PowerPoint
    fichiers_pptx = sorted(
        outputs_dir.glob('presentation_*.pptx'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(fichiers_pptx) > keep_last:
        print(f"   📊 Fichiers PowerPoint trouvés: {len(fichiers_pptx)}")
        print(f"   🗑️  Suppression de {len(fichiers_pptx) - keep_last} anciennes présentations...")
        
        for fichier in fichiers_pptx[keep_last:]:
            try:
                fichier.unlink()
                fichiers_supprimes += 1
                print(f"      - Supprimé: {fichier.name}")
            except Exception as e:
                print(f"      ❌ Erreur: {fichier.name} - {e}")
    else:
        print(f"   ✅ Fichiers PowerPoint: {len(fichiers_pptx)} (OK, < {keep_last})")
    
    # Fichiers temporaires (~$)
    fichiers_temp = list(outputs_dir.glob('~$*'))
    
    if fichiers_temp:
        print(f"   🗑️  Suppression de {len(fichiers_temp)} fichiers temporaires...")
        for fichier in fichiers_temp:
            try:
                fichier.unlink()
                fichiers_supprimes += 1
                print(f"      - Supprimé: {fichier.name}")
            except Exception as e:
                print(f"      ❌ Erreur: {fichier.name} - {e}")
    else:
        print(f"   ✅ Aucun fichier temporaire trouvé")
    
    print()
    print(f"   ✅ Nettoyage terminé: {fichiers_supprimes} fichiers supprimés")
    print()


def nettoyer_cache():
    """Nettoie les fichiers cache Python"""
    print("🧹 Nettoyage des fichiers cache Python")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    
    dossiers_cache = [
        base_dir / 'src' / '__pycache__',
        base_dir / 'tests' / '__pycache__',
        base_dir / '.pytest_cache'
    ]
    
    dossiers_supprimes = 0
    
    for dossier in dossiers_cache:
        if dossier.exists():
            try:
                shutil.rmtree(dossier)
                dossiers_supprimes += 1
                print(f"   ✅ Supprimé: {dossier.relative_to(base_dir)}")
            except Exception as e:
                print(f"   ❌ Erreur: {dossier.relative_to(base_dir)} - {e}")
        else:
            print(f"   ⏭️  Ignoré (n'existe pas): {dossier.relative_to(base_dir)}")
    
    # Fichiers .pyc individuels
    fichiers_pyc = list(base_dir.rglob('*.pyc'))
    
    if fichiers_pyc:
        print(f"   🗑️  Suppression de {len(fichiers_pyc)} fichiers .pyc...")
        for fichier in fichiers_pyc:
            try:
                fichier.unlink()
                print(f"      - Supprimé: {fichier.relative_to(base_dir)}")
            except Exception as e:
                print(f"      ❌ Erreur: {fichier.relative_to(base_dir)} - {e}")
    
    print()
    print(f"   ✅ Nettoyage cache terminé: {dossiers_supprimes} dossiers supprimés")
    print()


def verifier_gitignore():
    """Vérifie et complète le .gitignore"""
    print("🧹 Vérification du .gitignore")
    print("=" * 60)
    
    gitignore_path = Path(__file__).parent / '.gitignore'
    
    if not gitignore_path.exists():
        print("   ❌ .gitignore n'existe pas!")
        return
    
    with open(gitignore_path, 'r', encoding='utf-8') as f:
        contenu = f.read()
    
    regles_manquantes = []
    
    regles_necessaires = [
        ('__pycache__/', 'Fichiers cache Python'),
        ('*.pyc', 'Bytecode Python'),
        ('*.pyo', 'Bytecode Python optimisé'),
        ('.pytest_cache/', 'Cache pytest'),
        ('outputs/*.docx', 'Rapports Word générés'),
        ('outputs/*.pptx', 'Présentations PowerPoint générées'),
        ('outputs/~$*', 'Fichiers temporaires Office'),
        ('.env', 'Fichier de configuration (clés API)'),
    ]
    
    for regle, description in regles_necessaires:
        if regle not in contenu:
            regles_manquantes.append((regle, description))
            print(f"   ⚠️  Manquant: {regle} ({description})")
    
    if regles_manquantes:
        print()
        print("   💡 Règles à ajouter au .gitignore:")
        print()
        for regle, description in regles_manquantes:
            print(f"   {regle}  # {description}")
        print()
        
        reponse = input("   ❓ Voulez-vous les ajouter automatiquement? (o/N): ")
        
        if reponse.lower() in ['o', 'oui', 'y', 'yes']:
            with open(gitignore_path, 'a', encoding='utf-8') as f:
                f.write("\n# Ajouté par clean_project.py\n")
                for regle, description in regles_manquantes:
                    f.write(f"{regle}  # {description}\n")
            print("   ✅ Règles ajoutées au .gitignore")
        else:
            print("   ⏭️  Ignoré")
    else:
        print("   ✅ .gitignore est complet")
    
    print()


def afficher_statistiques():
    """Affiche les statistiques du projet"""
    print("📊 Statistiques du projet")
    print("=" * 60)
    
    base_dir = Path(__file__).parent
    
    # Compter les fichiers Python
    fichiers_py = list(base_dir.rglob('*.py'))
    lignes_totales = 0
    
    for fichier in fichiers_py:
        if '__pycache__' not in str(fichier):
            try:
                with open(fichier, 'r', encoding='utf-8') as f:
                    lignes_totales += len(f.readlines())
            except:
                pass
    
    print(f"   📝 Fichiers Python: {len(fichiers_py)}")
    print(f"   📏 Lignes de code: {lignes_totales:,}")
    
    # Compter la documentation
    fichiers_md = list(base_dir.glob('*.md'))
    fichiers_txt = list(base_dir.glob('*.txt'))
    
    print(f"   📘 Fichiers Markdown: {len(fichiers_md)}")
    print(f"   📄 Fichiers texte: {len(fichiers_txt)}")
    
    # Taille du dossier outputs
    outputs_dir = base_dir / 'outputs'
    if outputs_dir.exists():
        fichiers_outputs = list(outputs_dir.glob('*.*'))
        taille_totale = sum(f.stat().st_size for f in fichiers_outputs if f.is_file())
        taille_mb = taille_totale / (1024 * 1024)
        
        print(f"   💾 Fichiers outputs: {len(fichiers_outputs)}")
        print(f"   📦 Taille outputs: {taille_mb:.1f} MB")
    
    # Taille de la base de données
    db_path = base_dir / 'data' / 'cdg_test.db'
    if db_path.exists():
        taille_db = db_path.stat().st_size / (1024 * 1024)
        print(f"   🗄️  Taille base de données: {taille_db:.1f} MB")
    
    print()


def main():
    """Fonction principale"""
    print()
    print("=" * 60)
    print("🧹 NETTOYAGE DU PROJET ASSISTANT CDG")
    print("=" * 60)
    print()
    
    # 1. Statistiques avant nettoyage
    afficher_statistiques()
    
    # 2. Nettoyer outputs
    nettoyer_outputs(keep_last=3)
    
    # 3. Nettoyer cache
    nettoyer_cache()
    
    # 4. Vérifier .gitignore
    verifier_gitignore()
    
    # 5. Statistiques après nettoyage
    print("📊 Statistiques après nettoyage")
    print("=" * 60)
    afficher_statistiques()
    
    print()
    print("=" * 60)
    print("✅ NETTOYAGE TERMINÉ")
    print("=" * 60)
    print()
    print("💡 Prochaines étapes recommandées:")
    print("   1. Vérifier que l'application fonctionne: streamlit run src/app.py")
    print("   2. Lancer les tests: pytest tests/")
    print("   3. Vérifier Power BI: python src/powerbi_connector.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  Nettoyage interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n\n❌ Erreur: {e}")
