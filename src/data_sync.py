"""
Synchronisation des données pour l'Assistant CDG

Sources supportées (priorité):
1. data/powerbi_export/  → exports CSV/Excel depuis Power BI (source prioritaire)
2. data/Churn_Modelling.csv → fallback historique

Quand un export Power BI change, la base SQLite est reconstruite.
Le chatbot lit toujours SQLite → données à jour après chaque sync.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

# Répertoires projet
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
EXPORT_DIR = DATA_DIR / "powerbi_export"
DB_PATH = DATA_DIR / "cdg_test.db"
CSV_FALLBACK = DATA_DIR / "Churn_Modelling.csv"
META_PATH = DATA_DIR / "sync_meta.json"

# Colonnes attendues après normalisation
COLONNES_CIBLES = [
    "client_id", "segment", "periode", "age", "anciennete",
    "produit", "solde", "pnb_simule", "cout_simule", "rentabilite",
    "est_actif", "a_quitte"
]


def _ecrire_meta(info: Dict[str, Any]) -> None:
    META_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)


def lire_meta() -> Dict[str, Any]:
    if META_PATH.exists():
        try:
            with open(META_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def lister_exports_powerbi() -> List[Path]:
    """Liste les fichiers CSV/XLSX dans le dossier d'export Power BI"""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    fichiers = []
    for pattern in ("*.csv", "*.xlsx", "*.xls"):
        fichiers.extend(EXPORT_DIR.glob(pattern))
    # Ignorer fichiers temporaires Excel
    fichiers = [f for f in fichiers if not f.name.startswith("~$")]
    return sorted(fichiers, key=lambda p: p.stat().st_mtime, reverse=True)


def _trouver_colonne(df: pd.DataFrame, candidats: List[str]) -> Optional[str]:
    lower_map = {c.lower().strip(): c for c in df.columns}
    for cand in candidats:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    return None


def _normaliser_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalise un export Power BI ou un CSV churn vers le schéma pnb_analytique.
    Accepte soit le schéma métier déjà transformé, soit Churn_Modelling.
    """
    # Cas 1: schéma métier déjà présent
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
        return out[COLONNES_CIBLES]

    # Cas 2: format Churn_Modelling / export proche
    col_id = _trouver_colonne(df, ["CustomerId", "client_id", "ClientId", "ID"])
    col_geo = _trouver_colonne(df, ["Geography", "segment", "Segment", "Country"])
    col_age = _trouver_colonne(df, ["Age", "age"])
    col_tenure = _trouver_colonne(df, ["Tenure", "anciennete", "Anciennete"])
    col_prod = _trouver_colonne(df, ["NumOfProducts", "produit", "Produit", "NbProduits"])
    col_bal = _trouver_colonne(df, ["Balance", "solde", "Solde", "PNB", "pnb"])
    col_active = _trouver_colonne(df, ["IsActiveMember", "est_actif", "Actif"])
    col_exit = _trouver_colonne(df, ["Exited", "a_quitte", "Churn"])
    col_periode = _trouver_colonne(df, ["periode", "Periode", "Period", "Trimestre"])
    col_pnb = _trouver_colonne(df, ["pnb_simule", "PNB", "pnb"])
    col_cout = _trouver_colonne(df, ["cout_simule", "Cout", "cout", "Cost"])
    col_rent = _trouver_colonne(df, ["rentabilite", "Rentabilite", "Marge"])

    if not col_id or not col_geo:
        raise ValueError(
            "Export Power BI invalide: colonnes client_id/CustomerId et "
            "segment/Geography requises."
        )

    import random
    random.seed(42)
    periodes = ["T1-2024", "T2-2024", "T3-2024", "T4-2024"]

    solde = pd.to_numeric(df[col_bal], errors="coerce").fillna(0) if col_bal else pd.Series([0.0] * len(df))

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
        "client_id": df[col_id],
        "segment": df[col_geo],
        "periode": periode,
        "age": pd.to_numeric(df[col_age], errors="coerce").fillna(0).astype(int) if col_age else 0,
        "anciennete": pd.to_numeric(df[col_tenure], errors="coerce").fillna(0).astype(int) if col_tenure else 0,
        "produit": pd.to_numeric(df[col_prod], errors="coerce").fillna(1).astype(int) if col_prod else 1,
        "solde": solde.round(2),
        "pnb_simule": pnb.round(2),
        "cout_simule": cout.round(2),
        "rentabilite": rent.round(2),
        "est_actif": pd.to_numeric(df[col_active], errors="coerce").fillna(0).astype(int) if col_active else 0,
        "a_quitte": pd.to_numeric(df[col_exit], errors="coerce").fillna(0).astype(int) if col_exit else 0,
    })
    return out


def _charger_fichier(chemin: Path) -> pd.DataFrame:
    if chemin.suffix.lower() == ".csv":
        return pd.read_csv(chemin)
    if chemin.suffix.lower() in (".xlsx", ".xls"):
        return pd.read_excel(chemin)
    raise ValueError(f"Format non supporté: {chemin.suffix}")


def reconstruire_base(source: Optional[Path] = None) -> Dict[str, Any]:
    """
    Reconstruit cdg_test.db depuis Power BI export (prioritaire) ou CSV fallback.
    """
    from setup_db import creer_base_donnees

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    source_utilisee = source
    origine = "manuel"

    if source_utilisee is None:
        exports = lister_exports_powerbi()
        if exports:
            source_utilisee = exports[0]
            origine = "powerbi_export"
        elif CSV_FALLBACK.exists():
            source_utilisee = CSV_FALLBACK
            origine = "csv_fallback"
        else:
            return {
                "succes": False,
                "erreur": (
                    f"Aucune source trouvée. Placez un export dans "
                    f"{EXPORT_DIR} ou {CSV_FALLBACK}"
                )
            }

    try:
        df_brut = _charger_fichier(source_utilisee)
        df = _normaliser_dataframe(df_brut)
        creer_base_donnees(df, DB_PATH)

        meta = {
            "derniere_sync": datetime.now().isoformat(),
            "source": str(source_utilisee),
            "origine": origine,
            "nombre_lignes": len(df),
            "mtime_source": source_utilisee.stat().st_mtime,
        }
        _ecrire_meta(meta)

        return {
            "succes": True,
            "source": str(source_utilisee),
            "origine": origine,
            "nombre_lignes": len(df),
            "db": str(DB_PATH),
            "derniere_sync": meta["derniere_sync"],
        }
    except Exception as e:
        return {"succes": False, "erreur": str(e)}


def synchroniser_si_modifie() -> Dict[str, Any]:
    """
    Reconstruit la DB uniquement si l'export Power BI (ou CSV) a changé.
    """
    meta = lire_meta()
    exports = lister_exports_powerbi()

    if exports:
        source = exports[0]
        mtime = source.stat().st_mtime
        if meta.get("mtime_source") == mtime and meta.get("source") == str(source) and DB_PATH.exists():
            return {
                "succes": True,
                "action": "aucune",
                "message": "Données déjà à jour",
                "derniere_sync": meta.get("derniere_sync"),
                "source": str(source),
            }
        result = reconstruire_base(source)
        result["action"] = "rebuild"
        return result

    if CSV_FALLBACK.exists():
        mtime = CSV_FALLBACK.stat().st_mtime
        if meta.get("mtime_source") == mtime and DB_PATH.exists():
            return {
                "succes": True,
                "action": "aucune",
                "message": "Données déjà à jour (CSV)",
                "derniere_sync": meta.get("derniere_sync"),
            }
        result = reconstruire_base(CSV_FALLBACK)
        result["action"] = "rebuild"
        return result

    return {
        "succes": False,
        "erreur": "Aucune source Power BI ni CSV disponible"
    }


def statut_sync() -> Dict[str, Any]:
    """Statut pour l'UI Streamlit"""
    meta = lire_meta()
    exports = lister_exports_powerbi()
    return {
        "db_existe": DB_PATH.exists(),
        "db_mtime": datetime.fromtimestamp(DB_PATH.stat().st_mtime).isoformat() if DB_PATH.exists() else None,
        "derniere_sync": meta.get("derniere_sync"),
        "source": meta.get("source"),
        "origine": meta.get("origine"),
        "nombre_lignes": meta.get("nombre_lignes"),
        "exports_disponibles": [f.name for f in exports],
        "dossier_export": str(EXPORT_DIR),
    }


def surveiller_exports(intervalle_sec: int = 10) -> None:
    """Boucle de surveillance du dossier powerbi_export + CSV"""
    print("=" * 70)
    print("SURVEILLANCE DONNÉES → SQLITE (Power BI / CSV)")
    print("=" * 70)
    print(f"Dossier prioritaire: {EXPORT_DIR}")
    print(f"Fallback CSV: {CSV_FALLBACK}")
    print(f"Intervalle: {intervalle_sec}s — Ctrl+C pour arrêter")
    print("=" * 70)

    try:
        while True:
            result = synchroniser_si_modifie()
            ts = datetime.now().strftime("%H:%M:%S")
            if result.get("action") == "rebuild" and result.get("succes"):
                print(f"[{ts}] Sync OK — {result.get('nombre_lignes')} lignes depuis {result.get('origine')}")
            elif not result.get("succes"):
                print(f"[{ts}] Erreur: {result.get('erreur')}")
            time.sleep(intervalle_sec)
    except KeyboardInterrupt:
        print("\nSurveillance arrêtée.")


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("rebuild", "sync"):
        print(json.dumps(reconstruire_base(), indent=2, ensure_ascii=False))
    elif cmd == "watch":
        surveiller_exports()
    elif cmd == "check":
        print(json.dumps(synchroniser_si_modifie(), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(statut_sync(), indent=2, ensure_ascii=False))
