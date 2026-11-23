"""
Script de synchronisation automatique Power BI ↔ SQLite

Flux recommandé (données à jour pour le chatbot):
1. Exporter depuis Power BI vers data/powerbi_export/ (CSV ou Excel)
2. python sync_powerbi.py rebuild   (ou watch)
3. Le chatbot lit SQLite → informations fraîches

Sens inverse: SQLite → Power BI via ODBC (Actualiser dans PBI Desktop).
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))


def rebuild_database():
    """Reconstruit SQLite depuis Power BI export (prioritaire) ou CSV"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔄 Reconstruction de la base de données...")
    try:
        from data_sync import reconstruire_base
        result = reconstruire_base()
        if result.get("succes"):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ DB à jour")
            print(f"                     Source: {result.get('origine')} — {result.get('nombre_lignes')} lignes")
            print(f"                     Fichier: {result.get('source')}")
            print(f"                     Actualisez Power BI (ODBC) si besoin")
            return True
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur: {result.get('erreur')}")
        return False
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur: {e}")
        return False


def watch_csv_file():
    """Surveille data/powerbi_export/ + CSV et reconstruit si changement"""
    from data_sync import surveiller_exports
    surveiller_exports(intervalle_sec=10)


def watch_csv_with_watchdog():
    """Surveillance immédiate (watchdog) du dossier export + data/"""
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        print("❌ Module 'watchdog' non installé — mode simple (10s)")
        print("💡 pip install watchdog\n")
        watch_csv_file()
        return

    data_dir = Path(__file__).parent / "data"
    export_dir = data_dir / "powerbi_export"
    export_dir.mkdir(parents=True, exist_ok=True)

    class ChangeHandler(FileSystemEventHandler):
        def __init__(self):
            self._last = 0

        def on_modified(self, event):
            if event.is_directory:
                return
            name = Path(event.src_path).name.lower()
            if name.startswith("~$"):
                return
            if not (name.endswith(".csv") or name.endswith(".xlsx") or name.endswith(".xls")):
                return
            now = time.time()
            if now - self._last < 2:
                return
            self._last = now
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 📝 Fichier modifié: {name}")
            rebuild_database()
            print()

    print("=" * 70)
    print("🔄 SURVEILLANCE POWER BI EXPORT → SQLITE")
    print("=" * 70)
    print(f"📂 Dossiers: {export_dir} et {data_dir}")
    print("⚡ Réaction immédiate — Ctrl+C pour arrêter")
    print("=" * 70)

    handler = ChangeHandler()
    observer = Observer()
    observer.schedule(handler, str(export_dir), recursive=False)
    observer.schedule(handler, str(data_dir), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⏹️  Surveillance arrêtée")
    observer.join()


def manual_rebuild():
    """
    Reconstruction manuelle de la base de données
    """
    print("=" * 70)
    print("🔧 RECONSTRUCTION MANUELLE DE LA BASE DE DONNÉES")
    print("=" * 70)
    print()
    
    rebuild_database()
    
    print()
    print("=" * 70)
    print("✅ Terminé!")
    print("💡 Conseil: Actualisez Power BI pour voir les changements")
    print("=" * 70)


if __name__ == "__main__":
    import sys
    
    # Vérifier les arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "rebuild" or sys.argv[1] == "--rebuild":
            # Reconstruction manuelle
            manual_rebuild()
        elif sys.argv[1] == "watch" or sys.argv[1] == "--watch":
            # Surveillance avec watchdog si disponible
            watch_csv_with_watchdog()
        elif sys.argv[1] == "watch-simple" or sys.argv[1] == "--watch-simple":
            # Surveillance simple sans watchdog
            watch_csv_file()
        elif sys.argv[1] == "help" or sys.argv[1] == "--help":
            print("=" * 70)
            print("SYNCHRONISATION POWER BI ↔ SQLITE")
            print("=" * 70)
            print()
            print("Usage:")
            print("  python sync_powerbi.py [commande]")
            print()
            print("Commandes disponibles:")
            print("  rebuild         Reconstruit SQLite (Power BI export prioritaire)")
            print("  watch           Surveille data/powerbi_export/ (watchdog)")
            print("  watch-simple    Surveillance toutes les 10s")
            print("  help            Affiche cette aide")
            print()
            print("Workflow Power BI → Chatbot:")
            print("  1. Exportez depuis Power BI vers data/powerbi_export/")
            print("  2. python sync_powerbi.py rebuild   (ou watch)")
            print("  3. Le chatbot lit automatiquement la DB à jour")
            print()
            print("=" * 70)
        else:
            print(f"❌ Commande inconnue: {sys.argv[1]}")
            print("💡 Utilisez: python sync_powerbi.py help")
    else:
        # Par défaut: surveillance avec watchdog
        watch_csv_with_watchdog()
