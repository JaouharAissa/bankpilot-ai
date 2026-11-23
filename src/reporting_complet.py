"""
Module de génération de reporting complet (workflow Python, 1 seul outil chat)
Chaîne: détection → synthèse Ollama → commentaires Ollama → docs enrichis
PERSONNALISÉ: segment, produit, audience, objectif, titre, question originale
"""

import hashlib
import time
from typing import Dict, Any, List, Optional
from detection_tendances import detecter_signaux_faibles
from generation_analyse import generer_commentaire_gestion, generer_synthese_points_cles
from generation_documents import generer_rapport_word, generer_presentation_pptx
from outils_donnees import get_statistiques_globales


def _temperature_dynamique(base: float, question: str = "", variation_max: float = 0.25) -> float:
    """
    Génère une température LLM légèrement variable pour éviter des rapports
    identiques entre deux appels avec les mêmes données.
    Plage : [base, base + variation_max]
    """
    try:
        seed = int(hashlib.md5(
            (question + str(time.time_ns())).encode("utf-8")
        ).hexdigest(), 16)
        delta = (seed % 10_000) / 10_000 * variation_max
        return round(min(base + delta, base + variation_max), 3)
    except Exception:
        return base


def _filtrer_signaux(
    signaux: List[Dict[str, Any]],
    segment: Optional[str] = None,
    produit: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Filtre les signaux faibles détectés selon segment / produit ciblés.
    Si aucun filtre → signaux inchangés.
    """
    if not signaux:
        return signaux
    filtres = []
    if segment:
        seg_norm = str(segment).lower().strip()
        filtres.append(lambda s: (
            str(s.get("dimension", "")).lower() == seg_norm
            or str(s.get("segment", "")).lower() == seg_norm
            or seg_norm in str(s.get("nom", "")).lower()
        ))
    if produit:
        produit_norm = str(produit)
        filtres.append(lambda s: (
            str(s.get("produit", "")) == produit_norm
            or f"produit {produit_norm}" in str(s.get("dimension", "")).lower()
            or produit in s.get("produits", [])
        ))
    if not filtres:
        return signaux
    res = [s for s in signaux if all(f(s) for f in filtres)]
    return res if res else signaux


def _construire_contexte_enrichi(
    periode_actuelle: str,
    periode_precedente: str,
    signaux: List[Dict[str, Any]],
    segment: Optional[str] = None,
    produit: Optional[int] = None,
    audience: str = "direction",
    objectif: Optional[str] = None,
    question_originale: str = "",
    titre_personnalise: Optional[str] = None,
) -> Dict[str, Any]:
    """Agrège stats, churn et alertes pour documents détaillés + personnalisation"""
    contexte: Dict[str, Any] = {
        "periode_actuelle": periode_actuelle,
        "periode_precedente": periode_precedente,
        "signaux": signaux,
        "filtres": {
            "segment": segment,
            "produit": produit,
        },
        "audience": audience,
        "objectif": objectif,
        "question_originale": question_originale,
        "titre_personnalise": titre_personnalise,
    }

    try:
        stats = get_statistiques_globales()
        if stats.get("donnees_trouvees"):
            g = stats.get("global", {})
            contexte["stats_globales"] = g
            segs = stats.get("par_segment", [])
            prods = stats.get("par_produit", [])
            if segment:
                seg_norm = str(segment).lower()
                segs = [s for s in segs if str(s.get("segment", "")).lower() == seg_norm]
            if produit:
                prods = [p for p in prods if int(p.get("produit", 0)) == int(produit)]
            contexte["par_segment"] = segs
            contexte["par_produit"] = prods
    except Exception:
        pass

    try:
        from outils_donnees import get_pnb_par_segment, get_rentabilite_par_segment
        details_segments = []
        for seg in contexte.get("par_segment", []):
            nom = seg.get("segment")
            if not nom:
                continue
            pnb = get_pnb_par_segment(nom)
            rent = get_rentabilite_par_segment(nom)
            details_segments.append({
                "segment": nom,
                "nombre_clients": pnb.get("nombre_clients", seg.get("nombre_clients")),
                "pnb_total": pnb.get("pnb_total"),
                "pnb_moyen": pnb.get("pnb_moyen"),
                "rentabilite_totale": rent.get("rentabilite_totale"),
                "rentabilite_moyenne": rent.get("rentabilite_moyenne"),
                "cout_moyen": rent.get("cout_moyen"),
                "marge_pourcent": rent.get("marge_pourcent"),
            })
        if details_segments:
            contexte["details_segments"] = details_segments
    except Exception:
        pass

    try:
        from prediction_churn import predire_clients_a_risque
        churn = predire_clients_a_risque(seuil=0.7)
        if churn.get("succes"):
            clients = churn.get("clients", [])[:20]
            contexte["clients_a_risque"] = clients
            contexte["nb_clients_a_risque"] = churn.get("nombre_clients", len(clients))
    except Exception:
        contexte["clients_a_risque"] = []
        contexte["nb_clients_a_risque"] = 0

    try:
        from visualisations import (
            graphique_comparaison_segments,
            graphique_repartition_produits,
        )
        from pathlib import Path

        charts_dir = Path(__file__).parent.parent / "outputs" / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        chemins = {}
        fns = [("repartition_produits", graphique_repartition_produits)]
        if not segment:
            fns.insert(0, ("comparaison_segments", graphique_comparaison_segments))
        for nom, fn in fns:
            try:
                result = fn()
                fig = result.get("_figure")
                if fig is not None:
                    path = charts_dir / f"{nom}.png"
                    fig.write_image(str(path), width=1000, height=560, scale=2)
                    chemins[nom] = str(path)
            except Exception:
                continue
        if chemins:
            contexte["graphiques"] = chemins
    except Exception:
        pass

    return contexte


def generer_reporting_complet(
    periode_actuelle: str = "T4-2024",
    periode_precedente: str = "T3-2024",
    seuil_pourcentage: float = 10.0,
    type_document: str = "both",
    force_llm: bool = True,
    utiliser_llm: Optional[bool] = None,
    segment: Optional[str] = None,
    produit: Optional[int] = None,
    audience: str = "direction",
    objectif: Optional[str] = None,
    titre_personnalise: Optional[str] = None,
    question_originale: str = "",
) -> Dict[str, Any]:
    """
    Génère un reporting COMPLÈTEMENT PERSONNALISÉ.
    PERSONNALISATION: segment, produit, audience, objectif, titre, question.
    force_llm=True (défaut) : toujours essayer Ollama.
    """
    if utiliser_llm is not None:
        force_llm = utiliser_llm
    resultats: Dict[str, Any] = {
        "succes": True,
        "etapes": {},
        "fichiers_generes": [],
    }

    try:
        print("📊 Détection des signaux faibles...")
        signaux_result = detecter_signaux_faibles(
            seuil_pourcentage=seuil_pourcentage,
            periode_actuelle=periode_actuelle,
            periode_precedente=periode_precedente,
        )

        if not signaux_result.get("donnees_trouvees"):
            return {
                "succes": False,
                "erreur": "Aucun signal faible détecté ou données manquantes",
                "details": signaux_result,
            }

        signaux_tous = signaux_result["signaux"]
        signaux = _filtrer_signaux(signaux_tous, segment=segment, produit=produit)
        print(f"✅ {len(signaux_tous)} signaux détectés → {len(signaux)} après filtrage"
              f"{(' (segment=' + segment + ')') if segment else ''}"
              f"{(' (produit=' + str(produit) + ')') if produit else ''}")
        resultats["etapes"]["detection"] = {
            "nombre_signaux": len(signaux),
            "signaux_bruts": len(signaux_tous),
            "seuil": seuil_pourcentage,
            "filtres": {"segment": segment, "produit": produit},
        }

        temp_synthese = _temperature_dynamique(0.3, question_originale, 0.25)
        print(f"📝 Génération de la synthèse (Ollama, T={temp_synthese})...")
        synthese_result = generer_synthese_points_cles(
            signaux,
            utiliser_llm=force_llm,
            question_originale=question_originale,
            audience=audience,
            objectif=objectif,
            segment=segment,
            produit=produit,
            temperature=temp_synthese,
        )
        if not synthese_result.get("succes"):
            return {
                "succes": False,
                "erreur": "Échec de génération de la synthèse",
                "details": synthese_result,
            }

        synthese_texte = synthese_result["synthese_texte"]
        resultats["etapes"]["synthese"] = {
            "nombre_puces": len(synthese_result["puces"]),
            "mode": synthese_result.get("mode", "template"),
            "temperature": temp_synthese,
            "audience": audience,
            "objectif": objectif,
        }

        print("💬 Génération des commentaires (Ollama)...")
        commentaires = []
        top_signaux = signaux[:5]
        for idx, signal in enumerate(top_signaux):
            temp_comment = _temperature_dynamique(
                0.35, question_originale + str(idx), 0.25
            )
            commentaire_result = generer_commentaire_gestion(
                signal,
                utiliser_llm=force_llm,
                question_originale=question_originale,
                audience=audience,
                objectif=objectif,
                segment=segment,
                produit=produit,
                temperature=temp_comment,
            )
            if commentaire_result.get("succes"):
                commentaires.append(commentaire_result["commentaire"])

        resultats["etapes"]["commentaires"] = {
            "nombre_commentaires": len(commentaires),
        }

        print("📦 Construction du contexte enrichi (personnalisé)...")
        contexte = _construire_contexte_enrichi(
            periode_actuelle, periode_precedente, signaux,
            segment=segment, produit=produit, audience=audience,
            objectif=objectif, question_originale=question_originale,
            titre_personnalise=titre_personnalise,
        )

        if titre_personnalise:
            titre = str(titre_personnalise).strip()
        else:
            titre = f"Reporting Trimestriel — {periode_actuelle}"
            if segment:
                titre += f" — {segment}"
            if produit:
                titre += f" (Produit {produit})"

        if type_document in ["word", "both"]:
            print("📄 Génération du rapport Word personnalisé...")
            word_result = generer_rapport_word(
                titre=titre,
                synthese=synthese_texte,
                commentaires=commentaires,
                indicateurs=signaux,
                contexte_enrichi=contexte,
                segment=segment,
                produit=produit,
                audience=audience,
                objectif=objectif,
                question_originale=question_originale,
            )
            if word_result.get("succes"):
                print(f"✅ Rapport Word: {word_result['fichier']}")
                resultats["fichiers_generes"].append({
                    "type": "word",
                    "fichier": word_result["fichier"],
                    "chemin": word_result["chemin_complet"],
                })
            else:
                print(f"❌ Échec Word: {word_result.get('erreur')}")

        if type_document in ["pptx", "both"]:
            print("📊 Génération de la présentation PowerPoint personnalisée...")
            pptx_result = generer_presentation_pptx(
                titre=titre,
                synthese=synthese_texte,
                commentaires=commentaires,
                indicateurs=signaux,
                contexte_enrichi=contexte,
                segment=segment,
                produit=produit,
                audience=audience,
                objectif=objectif,
                question_originale=question_originale,
            )
            if pptx_result.get("succes"):
                print(f"✅ Présentation PowerPoint: {pptx_result['fichier']}")
                resultats["fichiers_generes"].append({
                    "type": "pptx",
                    "fichier": pptx_result["fichier"],
                    "chemin": pptx_result["chemin_complet"],
                })
            else:
                print(f"❌ Échec PowerPoint: {pptx_result.get('erreur')}")

        resultats["periode_actuelle"] = periode_actuelle
        resultats["periode_precedente"] = periode_precedente
        resultats["nombre_signaux"] = len(signaux)
        resultats["nombre_fichiers"] = len(resultats["fichiers_generes"])
        resultats["personnalisation"] = {
            "segment": segment,
            "produit": produit,
            "audience": audience,
            "objectif": objectif,
            "titre": titre,
        }
        resultats["message"] = (
            f"Reporting personnalisé généré: {resultats['nombre_fichiers']} fichier(s), "
            f"{len(signaux)} signaux analysés ({periode_precedente} → {periode_actuelle})."
        )

        return resultats

    except Exception as e:
        return {
            "succes": False,
            "erreur": f"Erreur lors de la génération du reporting: {str(e)}",
        }


if __name__ == "__main__":
    print("=" * 80)
    print("GÉNÉRATION DE REPORTING COMPLET (MODE RAPIDE)")
    print("=" * 80)
    result = generer_reporting_complet(type_document="both")
    print(result)
