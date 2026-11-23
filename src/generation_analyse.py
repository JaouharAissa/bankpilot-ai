"""
Module de génération d'analyses textuelles via LLM (Ollama).
Ollama est toujours tenté en premier. Les templates déterministes
ne servent que de filet de sécurité (timeout, erreur, indisponibilité).
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any
import ollama


logger = logging.getLogger("generation_analyse")
if not logger.handlers:
    logger.setLevel(logging.INFO)
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    handler = logging.FileHandler(log_dir / "audit.log", encoding="utf-8")

    class JsonFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "level": record.levelname,
                "logger": "generation_analyse",
                "message": record.getMessage(),
            }
            extra = getattr(record, "extra_data", None)
            if extra:
                log_data.update(extra)
            return json.dumps(log_data, ensure_ascii=False)

    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.propagate = False


def _formater_euro(valeur: float) -> str:
    try:
        return f"{float(valeur):,.2f} €".replace(",", " ")
    except (TypeError, ValueError):
        return "N/A"


def generer_commentaire_deterministe(donnees: Dict[str, Any]) -> str:
    """Filet de sécurité uniquement — ne pas utiliser comme chemin par défaut."""
    dimension = (
        donnees.get("dimension")
        or donnees.get("segment")
        or donnees.get("indicateur")
        or "Indicateur"
    )
    valeur_actuelle = donnees.get("valeur_actuelle", 0)
    valeur_precedente = donnees.get("valeur_precedente", 0)
    variation = donnees.get("variation_pourcentage", 0)
    tendance = donnees.get("tendance", "stable")

    if isinstance(valeur_actuelle, dict):
        valeur_actuelle = valeur_actuelle.get(
            "pnb_total", list(valeur_actuelle.values())[0] if valeur_actuelle else 0
        )
    if isinstance(valeur_precedente, dict):
        valeur_precedente = valeur_precedente.get(
            "pnb_total", list(valeur_precedente.values())[0] if valeur_precedente else 0
        )
    if isinstance(variation, dict):
        variation = variation.get(
            "pnb_total", list(variation.values())[0] if variation else 0
        )

    try:
        variation = float(variation)
    except (TypeError, ValueError):
        variation = 0.0

    if variation > 0:
        sens = "en hausse"
        orientation = (
            "Cette dynamique positive mérite d'être consolidée dans le plan d'action commercial."
        )
    elif variation < 0:
        sens = "en baisse"
        orientation = (
            "Cette évolution défavorable nécessite un suivi rapproché et des actions correctives."
        )
    else:
        sens = "stable"
        orientation = "La situation reste inchangée sur la période analysée."

    return (
        f"L'indicateur « {dimension} » est {sens} de {variation:+.2f}% "
        f"({_formater_euro(valeur_precedente)} → {_formater_euro(valeur_actuelle)}). "
        f"La tendance observée est « {tendance} ». {orientation}"
    )


def _synthese_deterministe(liste_indicateurs: List[Dict[str, Any]]) -> List[str]:
    tries = sorted(
        liste_indicateurs,
        key=lambda x: abs(float(x.get("variation_pourcentage") or 0)),
        reverse=True,
    )[:5]
    puces = []
    for ind in tries:
        dimension = ind.get("dimension", ind.get("segment", "N/A"))
        variation = float(ind.get("variation_pourcentage") or 0)
        actuelle = ind.get("valeur_actuelle", 0)
        tendance = ind.get("tendance", "stable")
        puces.append(
            f"{dimension}: {variation:+.2f}% "
            f"(valeur actuelle {_formater_euro(actuelle)}, tendance {tendance})"
        )
    return puces


def generer_commentaire_gestion(
    donnees_structurees: Dict[str, Any],
    utiliser_llm: bool = True,
    question_originale: str = "",
    audience: str = "direction",
    objectif: str | None = None,
    segment: str | None = None,
    produit: int | None = None,
    temperature: float = 0.35,
) -> Dict[str, Any]:
    """
    Rédige un commentaire de gestion PERSONNALISÉ.
    Personnalisation : question utilisateur, audience, objectif, segment, produit.
    Par défaut: Ollama d'abord. Template seulement si Ollama échoue.
    """
    if not donnees_structurees or not isinstance(donnees_structurees, dict):
        return {"succes": False, "erreur": "Les données structurées sont requises"}

    if not utiliser_llm:
        commentaire = generer_commentaire_deterministe(donnees_structurees)
        logger.info(
            "Commentaire déterministe (LLM désactivé)",
            extra={"extra_data": {"type": "commentaire_gestion", "mode": "template"}},
        )
        return {
            "succes": True,
            "commentaire": commentaire,
            "donnees_source": donnees_structurees,
            "type": "commentaire_gestion",
            "mode": "template",
        }

    donnees_json = json.dumps(donnees_structurees, indent=2, ensure_ascii=False)

    audience_ton = {
        "direction": "Ton très synthétique, orienté décision, en 3-4 phrases, pour le comité de direction. Va droit au but avec les points d'arbitrage.",
        "controle": "Ton détaillé, orienté chiffres et justification des écarts, pour le contrôleur de gestion. Mentionne explicitement les écarts et pistes de rapprochement.",
        "commercial": "Ton orienté clients et segments, pour l'équipe commerciale. Relie les chiffres à des actions commerciales (relances, renforcement).",
        "conseil": "Ton exhaustif et traçable, pour l'audit / conseil. Insiste sur la source des données et la méthodologie implicite.",
    }.get(audience, "Ton professionnel et neutre, adapté à un comité de direction.")

    objectif_orientation = ""
    if objectif == "reunion":
        objectif_orientation = " Le commentaire doit préparer une réunion : identifier le point de vigilance et la décision à prendre."
    elif objectif == "investigation":
        objectif_orientation = " Le commentaire doit servir d'investigation : proposer une ou deux pistes d'explication possibles (sans inventer de chiffres)."
    elif objectif == "validation":
        objectif_orientation = " Le commentaire doit servir à la validation de période : qualifier l'écart par rapport à l'objectif implicite."
    elif objectif == "strategique":
        objectif_orientation = " Le commentaire doit avoir une lecture stratégique : relier cette évolution à une orientation à moyen terme."

    contexte_perso = ""
    if question_originale and len(question_originale) > 3:
        contexte_perso += f"\n\nCONTEXTE DE LA DEMANDE UTILISATEUR (à intégrer si pertinent) : « {question_originale.strip()} »"
    if segment:
        contexte_perso += f"\nFiltre actif : segment = {segment}."
    if produit:
        contexte_perso += f"\nFiltre actif : nombre de produits = {produit}."

    prompt_systeme = f"""Tu es un analyste financier senior spécialisé en contrôle de gestion bancaire.

RÈGLES STRICTES:
1. Rédige un commentaire de gestion professionnel de 3 à 4 phrases — PERSONNALISÉ selon le contexte.
2. Base-toi UNIQUEMENT sur les données JSON fournies (dimension/segment, valeur actuelle, valeur précédente, variation, tendance).
3. INTERDICTION d'inventer, d'estimer ou d'arrondir un chiffre qui n'apparaît pas dans le JSON.
4. Cite explicitement les valeurs actuelle et précédente ainsi que la variation en %.
5. {audience_ton}
6. Si une question utilisateur est fournie, essaie d'y répondre DANS ce commentaire en utilisant les chiffres disponibles.
7. Pas de HTML, pas de puces, un seul paragraphe.{objectif_orientation}

Format: un paragraphe de 3-4 phrases."""

    prompt_utilisateur = (
        "Voici TOUTES les données structurées déjà calculées. "
        "Rédige le commentaire PERSONNALISÉ en n'utilisant que ces chiffres:\n\n"
        f"{donnees_json}{contexte_perso}\n\n"
        "Commentaire de gestion (3-4 phrases):"
    )

    logger.info(
        "Appel Ollama pour commentaire de gestion",
        extra={
            "extra_data": {
                "type": "commentaire_gestion",
                "mode": "ollama_call",
                "dimension": donnees_structurees.get("dimension")
                or donnees_structurees.get("segment"),
            }
        },
    )

    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": prompt_systeme},
                {"role": "user", "content": prompt_utilisateur},
            ],
            keep_alive="30m",
            options={"temperature": temperature, "num_predict": 500, "num_ctx": 4096},
        )
        commentaire = (response.get("message") or {}).get("content", "").strip()
        if not commentaire:
            raise ValueError("Réponse Ollama vide")

        logger.info(
            "Commentaire Ollama généré",
            extra={
                "extra_data": {
                    "type": "commentaire_gestion",
                    "mode": "llm",
                    "longueur": len(commentaire),
                }
            },
        )
        return {
            "succes": True,
            "commentaire": commentaire,
            "donnees_source": donnees_structurees,
            "type": "commentaire_gestion",
            "mode": "llm",
        }
    except Exception as e:
        logger.warning(
            f"Ollama indisponible pour commentaire, fallback déterministe: {e}",
            extra={"extra_data": {"type": "commentaire_gestion", "mode": "template_fallback"}},
        )
        return {
            "succes": True,
            "commentaire": generer_commentaire_deterministe(donnees_structurees),
            "donnees_source": donnees_structurees,
            "type": "commentaire_gestion",
            "mode": "template_fallback",
        }


def generer_synthese_points_cles(
    liste_indicateurs: List[Dict[str, Any]],
    utiliser_llm: bool = True,
    question_originale: str = "",
    audience: str = "direction",
    objectif: str | None = None,
    segment: str | None = None,
    produit: int | None = None,
    temperature: float = 0.3,
) -> Dict[str, Any]:
    """
    Synthèse en 5 puces max — PERSONNALISÉE selon la demande.
    Personnalisation : question utilisateur, audience, objectif, segment, produit.
    Par défaut: Ollama d'abord. Template seulement si Ollama échoue.
    """
    if not liste_indicateurs or not isinstance(liste_indicateurs, list):
        return {"succes": False, "erreur": "Une liste d'indicateurs est requise"}

    indicateurs_tries = sorted(
        liste_indicateurs,
        key=lambda x: abs(float(x.get("variation_pourcentage") or 0)),
        reverse=True,
    )

    if not utiliser_llm:
        puces = _synthese_deterministe(indicateurs_tries)
        return {
            "succes": True,
            "puces": puces,
            "synthese_texte": "\n".join([f"• {p}" for p in puces]),
            "nombre_indicateurs": len(liste_indicateurs),
            "type": "synthese_points_cles",
            "mode": "template",
        }

    donnees_json = json.dumps(indicateurs_tries, indent=2, ensure_ascii=False)

    audience_ton = {
        "direction": "Puces courtes et percutantes, focus sur les décisions et arbitrages.",
        "controle": "Puces détaillées avec les chiffres précis et les écarts explicites (justification).",
        "commercial": "Puces orientées segments/clients, avec des leviers commerciaux implicites.",
        "conseil": "Puces exhaustives avec traçabilité et contexte méthodologique.",
    }.get(audience, "Puces professionnelles et neutres, adaptées à un comité de direction.")

    objectif_orientation = ""
    if objectif == "reunion":
        objectif_orientation = " La 1ère puce doit poser le sujet de la réunion ; la dernière puce propose un point de décision."
    elif objectif == "investigation":
        objectif_orientation = " La synthèse doit faire apparaître les pistes d'investigation prioritaires (sans inventer)."
    elif objectif == "validation":
        objectif_orientation = " La synthèse doit mettre en avant les écarts à valider et les points de vigilance."
    elif objectif == "strategique":
        objectif_orientation = " La synthèse doit dégager des orientations stratégiques lisibles."

    contexte_perso = ""
    if question_originale and len(question_originale) > 3:
        contexte_perso += (
            "\n\nCONTEXTE / QUESTION UTILISATEUR (répondre explicitement si possible) : "
            f"« {question_originale.strip()} »"
        )
    if segment:
        contexte_perso += f"\nFiltre actif : segment = {segment}. Priorise les infos liées à {segment}."
    if produit:
        contexte_perso += f"\nFiltre actif : nombre de produits = {produit}."

    prompt_systeme = f"""Tu es un analyste financier senior qui synthétise des indicateurs déjà calculés.

RÈGLES STRICTES:
1. Exactement 5 puces maximum, une ligne chacune, format « • texte ».
2. Priorise les plus grosses variations (en valeur absolue) en premier.
3. Reprends les chiffres EXACTS du JSON (dimension, valeur actuelle, valeur précédente, variation %).
4. INTERDICTION d'inventer un chiffre, un segment ou une variation absents du JSON.
5. {audience_ton}
6. Si une question utilisateur est fournie, utilise AU MOINS une puce pour y RÉPONDRE EXPLICITEMENT avec les chiffres disponibles.
7. Pas d'introduction, pas de conclusion, uniquement les puces.
8. Chaque puce doit être UNIQUE et ne pas répéter le contenu d'une autre.{objectif_orientation}"""

    prompt_utilisateur = (
        "Voici la liste des indicateurs déjà calculés et triés. "
        "Rédige la synthèse PERSONNALISÉE (max 5 puces) sans ajouter de chiffre non fourni:\n\n"
        f"{donnees_json}{contexte_perso}\n\n"
        "Synthèse:"
    )

    logger.info(
        "Appel Ollama pour synthèse points clés",
        extra={
            "extra_data": {
                "type": "synthese_points_cles",
                "mode": "ollama_call",
                "nombre_indicateurs": len(indicateurs_tries),
            }
        },
    )

    try:
        response = ollama.chat(
            model="llama3.1",
            messages=[
                {"role": "system", "content": prompt_systeme},
                {"role": "user", "content": prompt_utilisateur},
            ],
            keep_alive="30m",
            options={"temperature": temperature, "num_predict": 500, "num_ctx": 4096},
        )
        synthese_brute = (response.get("message") or {}).get("content", "").strip()
        puces = []
        for ligne in synthese_brute.split("\n"):
            ligne = ligne.strip()
            if ligne and (ligne.startswith("•") or ligne.startswith("-") or ligne.startswith("*")):
                puce = ligne.lstrip("•-* ").strip()
                if puce:
                    puces.append(puce)
        if not puces and synthese_brute:
            puces = [l.strip() for l in synthese_brute.split("\n") if l.strip()][:5]
        puces = puces[:5]
        if not puces:
            raise ValueError("Aucune puce extraite de la réponse Ollama")

        logger.info(
            "Synthèse Ollama générée",
            extra={
                "extra_data": {
                    "type": "synthese_points_cles",
                    "mode": "llm",
                    "nombre_puces": len(puces),
                }
            },
        )
        return {
            "succes": True,
            "puces": puces,
            "synthese_texte": "\n".join([f"• {p}" for p in puces]),
            "nombre_indicateurs": len(liste_indicateurs),
            "type": "synthese_points_cles",
            "mode": "llm",
        }
    except Exception as e:
        logger.warning(
            f"Ollama indisponible pour synthèse, fallback déterministe: {e}",
            extra={"extra_data": {"type": "synthese_points_cles", "mode": "template_fallback"}},
        )
        puces = _synthese_deterministe(indicateurs_tries)
        return {
            "succes": True,
            "puces": puces,
            "synthese_texte": "\n".join([f"• {p}" for p in puces]),
            "nombre_indicateurs": len(liste_indicateurs),
            "type": "synthese_points_cles",
            "mode": "template_fallback",
        }
