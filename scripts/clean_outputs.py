"""
Script de nettoyage du dossier outputs/
Garde seulement les 3 fichiers les plus récents de chaque type
"""

from pathlib import Path
import sys

def clean_outputs(keep_last=3):
    """Nettoie outputs/ en gardant les N derniers fichiers"""
    base_dir = Path(__file__).parent.parent
    outputs_dir = base_dir / 'outputs'
    
    if not outputs_dir.exists():
        print("✅ Dossier outputs/ n'existe pas")
        return
    
    print("Nettoyage du dossier outputs/")
    print("=" * 60)
    
    fichiers_supprimes = 0
    espace_libere = 0
    
    # Nettoyer Word
    fichiers_word = sorted(
        outputs_dir.glob('rapport_*.docx'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(fichiers_word) > keep_last:
        print(f"Word: {len(fichiers_word)} trouves, suppression de {len(fichiers_word) - keep_last}")
        for f in fichiers_word[keep_last:]:
            espace_libere += f.stat().st_size
            f.unlink()
            fichiers_supprimes += 1
    else:
        print(f"Word: {len(fichiers_word)} (OK)")
    
    # Nettoyer PowerPoint
    fichiers_pptx = sorted(
        outputs_dir.glob('presentation_*.pptx'),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(fichiers_pptx) > keep_last:
        print(f"PowerPoint: {len(fichiers_pptx)} trouves, suppression de {len(fichiers_pptx) - keep_last}")
        for f in fichiers_pptx[keep_last:]:
            espace_libere += f.stat().st_size
            f.unlink()
            fichiers_supprimes += 1
    else:
        print(f"PowerPoint: {len(fichiers_pptx)} (OK)")
    
    # Supprimer temporaires
    fichiers_temp = list(outputs_dir.glob('~$*'))
    if fichiers_temp:
        print(f"Temporaires: {len(fichiers_temp)} supprimes")
        for f in fichiers_temp:
            espace_libere += f.stat().st_size
            f.unlink()
            fichiers_supprimes += 1
    
    print("=" * 60)
    print(f"OK {fichiers_supprimes} fichiers supprimes")
    print(f"Espace {espace_libere / 1024 / 1024:.1f} MB liberes")

if __name__ == "__main__":
    clean_outputs(keep_last=3)
