"""
Génération de documents Word et PowerPoint détaillés
Design professionnel (design_tokens.md) + sections enrichies (stats, segments, churn, graphiques)
PERSONNALISÉ: segment/produit/audience/objectif/question
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from pptx import Presentation
from pptx.util import Inches as PptxInches, Pt as PptxPt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.shapes import MSO_SHAPE


AUDIENCE_TITRES = {
    "direction": "Synthèse Direction",
    "controle": "Rapport de Contrôle de Gestion",
    "commercial": "Rapport Équipe Commerciale",
    "conseil": "Rapport d'Audit et Conseil",
}

AUDIENCE_SOUS_TITRES = {
    "direction": "Pour le Comité de Direction — Synthèse et décisions",
    "controle": "Pour le Contrôleur de Gestion — Analyse détaillée",
    "commercial": "Pour l'Équipe Commerciale — Axes clients et segments",
    "conseil": "Pour l'Audit / Conseil — Vue exhaustive et traçabilité",
}

OBJECTIF_INTROS = {
    "reunion": "Ce document prépare la réunion en regroupant les indicateurs clés et les éléments de décision essentiels.",
    "investigation": "Ce document présente une analyse détaillée pour comprendre les évolutions observées.",
    "validation": "Ce document présente le bilan de la période et les éléments de validation.",
    "strategique": "Cette note stratégique analyse la période pour éclairer les orientations futures.",
}


def _resoudre_audience(audience: Optional[str]) -> str:
    if not audience:
        return "direction"
    a = str(audience).lower().strip()
    if a in AUDIENCE_TITRES:
        return a
    return "direction"


def _resoudre_objectif(obj: Optional[str]) -> Optional[str]:
    if not obj:
        return None
    o = str(obj).lower().strip()
    return o if o in OBJECTIF_INTROS else None


def _construire_introduction_personnalisee(
    contexte: Optional[Dict[str, Any]],
    audience: str,
    objectif: Optional[str],
    question_originale: str = "",
) -> List[str]:
    """
    Génère 2-4 lignes d'introduction SUR MESURÉES selon la demande utilisateur.
    Ne JAMAIS inventer un chiffre : uniquement s'appuyer sur le contexte fourni
    (stats globales, filtres, audience, question.
    """
    lignes: List[str] = []
    filtres = (contexte or {}).get("filtres") or {}
    stats = (contexte or {}).get("stats_globales") or {}
    question = (question_originale or "").strip()

    if question and len(question) > 3:
        lignes.append(
            f"Ce document a été préparé en réponse à la demande suivante : « {question} »."
        )

    # Bloc sur mesure selon audience + objectif
    intro_audience = {
        "direction": (
            "Il présente les indicateurs consolidés nécessaires aux décisions du comité de direction, "
            "avec focus sur les arbitrages à réaliser sur les segments et produits."
        ),
        "controle": (
            "Il fournit une vision détaillée et chiffrée pour permettre la justification des écarts "
            "et le rapprochement avec les référentiels."
        ),
        "commercial": (
            "Il met en avant les dynamiques clients et segments, avec des pistes d'actions commerciales ciblées."
        ),
        "conseil": (
            "Il apporte une traçabilité complète des indicateurs, la source des données et "
            "leur méthode de calcul utilisée pour l'audit."
        ),
    }.get(audience, "")
    if intro_audience:
        lignes.append(intro_audience)

    if objectif == "reunion":
        lignes.append(
            "Document préparatoire à la réunion : points de vigilance, décisions à prendre et chiffres clés."
        )
    elif objectif == "investigation":
        lignes.append(
            "Ce rapport d'investigation liste les variations significatives et propose des pistes "
            "d'analyse pour en comprendre les causes."
        )
    elif objectif == "validation":
        lignes.append(
            "Bilan de période : éléments de validation et points de vigilance avant clôture."
        )
    elif objectif == "strategique":
        lignes.append(
            "Note stratégique : les évolutions de la période sont analysées sous l'angle "
            "des orientations à moyen terme."
        )

    # Bloc filtres / scope
    scope_parts = []
    seg = filtres.get("segment")
    prod = filtres.get("produit")
    if seg:
        scope_parts.append(f"périmètre segment {seg}")
    if prod:
        scope_parts.append(f"clients avec {prod} produit(s)")
    if scope_parts:
        lignes.append("Périmètre d'analyse : " + " — ".join(scope_parts) + ".")

    # 1-2 chiffres clés globaux si disponibles (sans LLM, juste formatage humain)
    if stats:
        nb_clients = stats.get("nombre_total_clients")
        pnb_total = stats.get("pnb_total")
        nb_risque = (contexte or {}).get("nb_clients_a_risque") or 0
        if nb_clients and pnb_total:
            try:
                clients_str = f"{int(nb_clients):,}".replace(",", " ")
                lignes.append(
                    f"Le portefeuille analysé compte {clients_str} clients "
                    f"pour un PNB simulé total de {_fmt_euro(pnb_total)}."
                )
                if nb_risque:
                    lignes.append(
                        f"{nb_risque} client(s) sont identifié(s) à risque élevé de churn."
                    )
            except (TypeError, ValueError):
                pass

    return lignes[:4]


logger = logging.getLogger('generation_documents')
OUTPUT_DIR = Path(__file__).parent.parent / 'outputs'

COLORS = {
    'marine_deep': RGBColor(30, 58, 95),
    'copper_accent': RGBColor(212, 131, 94),
    'white': RGBColor(255, 255, 255),
    'grey_light': RGBColor(248, 249, 250),
    'grey_medium': RGBColor(108, 117, 125),
    'grey_dark': RGBColor(44, 62, 80),
    'success': RGBColor(40, 167, 69),
    'warning': RGBColor(255, 193, 7),
    'danger': RGBColor(192, 57, 43),
}

PPTX_COLORS = {
    'marine_deep': PptxRGBColor(30, 58, 95),
    'copper_accent': PptxRGBColor(212, 131, 94),
    'white': PptxRGBColor(255, 255, 255),
    'grey_light': PptxRGBColor(248, 249, 250),
    'grey_medium': PptxRGBColor(108, 117, 125),
    'grey_dark': PptxRGBColor(44, 62, 80),
    'success': PptxRGBColor(40, 167, 69),
    'danger': PptxRGBColor(192, 57, 43),
}


def _creer_dossier_outputs():
    OUTPUT_DIR.mkdir(exist_ok=True)


def _nettoyer_outputs_anciens(keep_last: int = 3) -> None:
    """Garde uniquement les N fichiers les plus récents de chaque type (docx / pptx)."""
    try:
        for pattern in ("rapport_*.docx", "presentation_*.pptx"):
            fichiers = sorted(
                OUTPUT_DIR.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for ancien in fichiers[keep_last:]:
                try:
                    ancien.unlink()
                except OSError:
                    pass
        for temp in OUTPUT_DIR.glob("~$*"):
            try:
                temp.unlink()
            except OSError:
                pass
    except Exception as e:
        logger.warning(f"Nettoyage outputs/ ignoré: {e}")


def _fmt_euro(v) -> str:
    try:
        return f"{float(v):,.2f} €".replace(",", " ")
    except (TypeError, ValueError):
        return "N/A"


def _fmt_pct(v) -> str:
    try:
        return f"{float(v):+.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def _fmt_short(v) -> str:
    try:
        v = float(v)
        if abs(v) >= 1_000_000:
            return f"{v/1_000_000:.2f}M€"
        if abs(v) >= 1_000:
            return f"{v/1_000:.1f}K€"
        return f"{v:.0f}€"
    except (TypeError, ValueError):
        return "N/A"


def _ajouter_table_shading(cell, color):
    shading_elm = OxmlElement('w:shd')
    shading_elm.set(qn('w:fill'), f"{color[0]:02X}{color[1]:02X}{color[2]:02X}")
    cell._element.get_or_add_tcPr().append(shading_elm)


def _styler_paragraphe(paragraph, font_size=14, bold=False, color=None,
                      spacing_before=0, spacing_after=0, line_spacing=1.6):
    for run in paragraph.runs:
        run.font.size = Pt(font_size)
        run.font.name = 'Inter'
        run.font.bold = bold
        if color:
            run.font.color.rgb = color
    paragraph.paragraph_format.space_before = Pt(spacing_before)
    paragraph.paragraph_format.space_after = Pt(spacing_after)
    paragraph.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    paragraph.paragraph_format.line_spacing = line_spacing


def _heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    try:
        h.style.font.color.rgb = COLORS['marine_deep'] if level == 1 else COLORS['copper_accent']
        h.style.font.size = Pt(24 if level == 1 else 18)
    except Exception:
        pass
    return h


def _creer_page_garde_word(doc, titre, date_str, contexte=None,
                           audience: str = "direction",
                           objectif: Optional[str] = None,
                           question_originale: str = ""):
    audience = _resoudre_audience(contexte.get("audience") if isinstance(contexte, dict) else audience)
    obj = _resoudre_objectif(contexte.get("objectif") if isinstance(contexte, dict) else objectif)
    q_originale = (contexte.get("question_originale") if isinstance(contexte, dict) else question_originale) or ""

    for _ in range(3):
        doc.add_paragraph()

    # Audience en tête (petit, discret)
    tag_audience = doc.add_paragraph(AUDIENCE_TITRES.get(audience, "Analyse de Gestion"))
    tag_audience.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styler_paragraphe(tag_audience, font_size=13, bold=True,
                       color=COLORS['copper_accent'], spacing_after=6)

    titre_para = doc.add_paragraph(titre)
    titre_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styler_paragraphe(titre_para, font_size=32, bold=True,
                       color=COLORS['marine_deep'], spacing_after=12)

    sous_texte = AUDIENCE_SOUS_TITRES.get(audience, "Analyse de Gestion Détaillée")
    sous = doc.add_paragraph(sous_texte)
    sous.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styler_paragraphe(sous, font_size=18, color=COLORS['grey_medium'])

    if contexte:
        periode = f"{contexte.get('periode_precedente', '')} → {contexte.get('periode_actuelle', '')}"
        p = doc.add_paragraph(f"Période d'analyse : {periode}")
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        _styler_paragraphe(p, font_size=14, color=COLORS['copper_accent'])

        filtres = contexte.get("filtres") or {}
        if filtres and (filtres.get("segment") or filtres.get("produit")):
            parties = []
            if filtres.get("segment"):
                parties.append(f"Segment : {filtres['segment']}")
            if filtres.get("produit"):
                parties.append(f"Produit : {filtres['produit']}")
            pf = doc.add_paragraph(" | ".join(parties))
            pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
            _styler_paragraphe(pf, font_size=13, bold=True, color=COLORS['marine_deep'])

    doc.add_paragraph()
    date_para = doc.add_paragraph(f"Rapport généré le {date_str}")
    date_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styler_paragraphe(date_para, font_size=14, color=COLORS['grey_medium'])

    projet = doc.add_paragraph("Assistant Contrôleur de Gestion — Confidentiel")
    projet.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _styler_paragraphe(projet, font_size=12, color=COLORS['grey_medium'])
    doc.add_page_break()

    # Section "Objet du document" (si objectif ou question fournie)
    if obj or q_originale:
        _heading(doc, "Objet du Document", 1)
        if obj and obj in OBJECTIF_INTROS:
            p_obj = doc.add_paragraph(OBJECTIF_INTROS[obj])
            _styler_paragraphe(p_obj, font_size=13, color=COLORS['grey_dark'],
                              spacing_before=6, spacing_after=10)
        if q_originale and len(q_originale) > 3:
            p_q = doc.add_paragraph()
            r1 = p_q.add_run("Question originale : ")
            r1.bold = True
            r1.font.size = Pt(12)
            r1.font.color.rgb = COLORS['copper_accent']
            r2 = p_q.add_run(f"« {q_originale.strip()} »")
            r2.italic = True
            r2.font.size = Pt(12)
            r2.font.color.rgb = COLORS['grey_dark']
            _styler_paragraphe(p_q, font_size=12, spacing_before=4, spacing_after=10)
        doc.add_page_break()


def _tableau_simple(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Table Grid'
    for i, header_text in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header_text
        _ajouter_table_shading(cell, (30, 58, 95))
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(11)
                run.font.color.rgb = COLORS['white']
                run.font.name = 'Inter'
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

    for idx, row in enumerate(rows):
        cells = table.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            if idx % 2 == 1:
                _ajouter_table_shading(cells[i], (248, 249, 250))
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(10)
                    run.font.name = 'Inter'
                    run.font.color.rgb = COLORS['grey_dark']
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return table


def _creer_tableau_professionnel(doc, indicateurs):
    rows = []
    for ind in indicateurs:
        rows.append([
            str(ind.get('dimension', 'N/A')),
            _fmt_euro(ind.get('valeur_actuelle', 0)),
            _fmt_euro(ind.get('valeur_precedente', 0)),
            _fmt_pct(ind.get('variation_pourcentage', 0)),
            str(ind.get('tendance', 'stable')).capitalize(),
        ])
    _tableau_simple(
        doc,
        ['Dimension', 'Valeur Actuelle', 'Valeur Précédente', 'Variation', 'Tendance'],
        rows,
    )


def _section_reponse_demande(
    doc, contexte, audience: str, objectif: Optional[str], question_originale: str
):
    """Section dédiée : réponse explicite à la demande de l'utilisateur."""
    lignes = _construire_introduction_personnalisee(
        contexte, audience, objectif, question_originale
    )
    if not lignes:
        return
    _heading(doc, 'Réponse à Votre Demande', 1)
    for ligne in lignes:
        para = doc.add_paragraph(ligne, style='List Bullet')
        _styler_paragraphe(
            para, font_size=13, color=COLORS['grey_dark'],
            spacing_before=4, spacing_after=8, line_spacing=1.5,
        )
    doc.add_paragraph()


def _section_vue_ensemble(doc, contexte, audience="direction", objectif=None, question_originale=""):
    stats = contexte.get('stats_globales') or {}
    if not stats:
        return
    _heading(doc, 'Vue d\'Ensemble du Portefeuille', 1)

    lignes_intro = _construire_introduction_personnalisee(
        contexte, audience, objectif, question_originale
    )
    if lignes_intro:
        for ligne in lignes_intro[:2]:
            intro = doc.add_paragraph(ligne)
            _styler_paragraphe(intro, font_size=12, color=COLORS['grey_medium'], spacing_after=6)
    else:
        intro = doc.add_paragraph(
            "Cette section présente les indicateurs consolidés du portefeuille client "
            "à la date de génération du rapport."
        )
        _styler_paragraphe(intro, font_size=12, color=COLORS['grey_medium'], spacing_after=12)

    rows = [[
        f"{stats.get('nombre_total_clients', 0):,}".replace(",", " "),
        _fmt_euro(stats.get('pnb_total', 0)),
        _fmt_euro(stats.get('rentabilite_totale', 0)),
        _fmt_euro(stats.get('pnb_moyen', 0)),
        _fmt_euro(stats.get('cout_total', 0)),
        f"{stats.get('anciennete_moyenne', 0):.1f} ans",
    ]]
    _tableau_simple(
        doc,
        ['Clients', 'PNB Total', 'Rentabilité', 'PNB Moyen', 'Coûts Totaux', 'Ancienneté Moy.'],
        rows,
    )
    doc.add_paragraph()


def _section_segments(doc, contexte):
    details = contexte.get('details_segments') or []
    if not details:
        # Fallback léger
        details = contexte.get('par_segment') or []
        if not details:
            return
        _heading(doc, 'Performance par Segment', 1)
        rows = [[
            d.get('segment', ''),
            d.get('nombre_clients', ''),
            _fmt_euro(d.get('rentabilite_moyenne', 0)),
        ] for d in details]
        _tableau_simple(doc, ['Segment', 'Clients', 'Rentabilité Moy.'], rows)
        doc.add_paragraph()
        return

    _heading(doc, 'Performance par Segment Géographique', 1)
    intro = doc.add_paragraph(
        "Comparaison détaillée des segments France, Germany et Spain : volumes, "
        "PNB, rentabilité et marge."
    )
    _styler_paragraphe(intro, font_size=12, color=COLORS['grey_medium'], spacing_after=12)

    rows = []
    for d in details:
        rows.append([
            d.get('segment', ''),
            d.get('nombre_clients', ''),
            _fmt_euro(d.get('pnb_total', 0)),
            _fmt_euro(d.get('pnb_moyen', 0)),
            _fmt_euro(d.get('rentabilite_totale', 0)),
            _fmt_euro(d.get('rentabilite_moyenne', 0)),
            f"{d.get('marge_pourcent', 0):.1f}%" if d.get('marge_pourcent') is not None else "N/A",
        ])
    _tableau_simple(
        doc,
        ['Segment', 'Clients', 'PNB Total', 'PNB Moyen', 'Rentab. Totale', 'Rentab. Moy.', 'Marge %'],
        rows,
    )

    # Graphique si disponible
    graph = (contexte.get('graphiques') or {}).get('comparaison_segments')
    if graph and Path(graph).exists():
        doc.add_paragraph()
        p = doc.add_paragraph("Graphique — Comparaison des segments")
        _styler_paragraphe(p, font_size=12, bold=True, color=COLORS['marine_deep'])
        try:
            doc.add_picture(graph, width=Inches(6.2))
        except Exception:
            pass
    doc.add_paragraph()


def _section_produits(doc, contexte):
    produits = contexte.get('par_produit') or []
    if not produits:
        return
    _heading(doc, 'Répartition par Nombre de Produits', 1)
    rows = [[
        str(p.get('produit', '')),
        p.get('nombre_clients', ''),
        _fmt_euro(p.get('rentabilite_moyenne', 0)),
    ] for p in produits]
    _tableau_simple(doc, ['Nb Produits', 'Clients', 'Rentabilité Moyenne'], rows)

    graph = (contexte.get('graphiques') or {}).get('repartition_produits')
    if graph and Path(graph).exists():
        doc.add_paragraph()
        try:
            doc.add_picture(graph, width=Inches(5.5))
        except Exception:
            pass
    doc.add_paragraph()


def _section_churn(doc, contexte):
    clients = contexte.get('clients_a_risque') or []
    nb = contexte.get('nb_clients_a_risque', len(clients))
    _heading(doc, 'Risque de Churn (Machine Learning)', 1)
    intro = doc.add_paragraph(
        f"{nb} client(s) identifié(s) avec une probabilité de départ ≥ 70% "
        f"(modèle RandomForest). Top 15 ci-dessous."
    )
    _styler_paragraphe(intro, font_size=12, color=COLORS['grey_medium'], spacing_after=12)

    if not clients:
        p = doc.add_paragraph("Aucun client à risque élevé détecté ou modèle indisponible.")
        _styler_paragraphe(p, font_size=12, color=COLORS['grey_medium'])
        return

    rows = []
    for c in clients[:15]:
        proba = c.get('probabilite_churn', c.get('probabilite', 0))
        try:
            proba_pct = f"{float(proba) * 100:.1f}%"
        except (TypeError, ValueError):
            proba_pct = str(proba)
        rows.append([
            str(c.get('client_id', c.get('CustomerId', ''))),
            str(c.get('segment', c.get('Geography', ''))),
            str(c.get('age', '')),
            _fmt_euro(c.get('solde', c.get('Balance', 0))),
            proba_pct,
        ])
    _tableau_simple(doc, ['Client ID', 'Segment', 'Âge', 'Solde', 'Proba. Churn'], rows)
    doc.add_paragraph()


def _section_methodologie(doc, contexte):
    _heading(doc, 'Méthodologie & Notes', 1)
    textes = [
        "Source des données : base SQLite analytique synchronisée depuis Power BI export "
        "ou fichier CSV source (lecture seule).",
        "PNB simulé = Solde × 2% ; Coût = Solde × 0.8% ; Rentabilité = PNB − Coût.",
        f"Période d'analyse : {contexte.get('periode_precedente', 'T3-2024')} → "
        f"{contexte.get('periode_actuelle', 'T4-2024')}.",
        "Les signaux faibles correspondent aux variations de PNB au-delà du seuil configuré.",
        "Le modèle de churn est un RandomForest (features : score crédit, âge, ancienneté, "
        "solde, produits, carte, activité, géographie, genre).",
        "Ce document est généré automatiquement ; vérifier les chiffres critiques avant diffusion.",
    ]
    for t in textes:
        para = doc.add_paragraph(t, style='List Bullet')
        _styler_paragraphe(para, font_size=12, color=COLORS['grey_dark'],
                           spacing_before=4, spacing_after=4)


def _section_conclusion(doc, contexte, audience="direction", objectif=None, question_originale=""):
    audience = _resoudre_audience(audience)
    obj = _resoudre_objectif(objectif)
    filtres = (contexte or {}).get("filtres") or {}
    question = (question_originale or "").strip()

    _heading(doc, "Conclusion & Prochaines Étapes", 1)

    lignes: List[str] = []

    if question and len(question) > 3:
        lignes.append(
            "Synthèse en réponse à votre demande : « " + question + " »."
        )

    if obj == "reunion":
        lignes.append(
            "Préparer les décisions à prendre lors de la réunion sur la base des chiffres présentés."
        )
        lignes.append("Vérifier les points de vigilance associés aux signaux détectés.")
    elif obj == "investigation":
        lignes.append(
            "Les causes des variations observées doivent être approfondies localement "
            "par les équipes opérationnelles (terrain, back-office)."
        )
        lignes.append(
            "Mettre en place un suivi hebdomadaire des segments en forte baisse."
        )
    elif obj == "validation":
        lignes.append("Bilan validé pour la période. Prochaine étape : clôturer les éléments de reporting.")
        lignes.append("Justifier les écarts significatifs et rapprocher les totaux des référentiels financiers.")
    elif obj == "strategique":
        lignes.append(
            "Les évolutions de la période éclairent les orientations stratégiques du prochain exercice."
        )
        lignes.append(
            "Intégrer ces dynamiques dans le plan de développement et les budgets prévisionnels."
        )
    else:
        lignes.append("Les indicateurs de la période sont présentés pour information et décision.")

    if filtres.get("segment"):
        lignes.append(f"Focus : segment {filtres['segment']} — pilotage local renforcé.")
    if filtres.get("produit"):
        lignes.append(f"Focus : portefeuille clients avec {filtres['produit']} produit(s) — renforcement ciblé.")

    if audience == "direction":
        lignes.append("Priorité : arbitrages à réaliser sur les segments en baisse et à fort potentiel.")
        lignes.append("Décision : valider le plan d'actions sur les clients à risque de churn.")
    elif audience == "controle":
        lignes.append("Focus : justification des écarts et rapprochement avec les référentiels financiers.")
        lignes.append("Traçabilité : conserver une copie de ce rapport dans le dossier de clôture.")
    elif audience == "commercial":
        lignes.append("Focus : relances commerciales sur clients à risque et renforcement des segments performants.")
        lignes.append("Lever : proposer des produits complémentaires sur les segments en hausse.")
    elif audience == "conseil":
        lignes.append("Traçabilité : tous les chiffres proviennent de la base analytique SQLite, les détails sont disponibles sur demande.")
        lignes.append("Méthodologie : PNB simulé (2% du solde), coût (0.8%), rentabilité nette (1.2%).")

    nb_risque = (contexte or {}).get("nb_clients_a_risque", 0)
    if nb_risque:
        lignes.append(
            f"Plan d'action immédiat : lancer un plan de rétention sur les {nb_risque} clients à risque élevé."
        )

    lignes.append(
        "Actualiser les données depuis Power BI avant chaque comité de direction (données synchronisées)."
    )

    for t in lignes:
        para = doc.add_paragraph(t, style='List Bullet')
        _styler_paragraphe(para, font_size=12, color=COLORS['grey_dark'],
                          spacing_before=4, spacing_after=4)


def generer_rapport_word(
    titre: str,
    synthese: str,
    commentaires: List[str],
    indicateurs: List[Dict[str, Any]],
    contexte_enrichi: Optional[Dict[str, Any]] = None,
    segment: Optional[str] = None,
    produit: Optional[int] = None,
    audience: str = "direction",
    objectif: Optional[str] = None,
    question_originale: str = "",
) -> Dict[str, Any]:
    """Rapport Word détaillé PERSONNALISÉ (segment, produit, audience, objectif)."""
    try:
        _creer_dossier_outputs()
        contexte = contexte_enrichi or {}
        audience = _resoudre_audience(contexte.get("audience") or audience)
        objectif = _resoudre_objectif(contexte.get("objectif") or objectif)
        filtres = contexte.get("filtres") or {}
        a_segment = filtres.get("segment") or segment
        a_produit = filtres.get("produit") or produit

        doc = Document()
        for sec in doc.sections:
            sec.top_margin = Inches(1)
            sec.bottom_margin = Inches(0.75)
            sec.left_margin = Inches(1)
            sec.right_margin = Inches(1)

        date_str = datetime.now().strftime("%d %B %Y")
        _creer_page_garde_word(
            doc, titre, date_str, contexte,
            audience=audience, objectif=objectif,
            question_originale=question_originale,
        )

        sommaire_items = [
            "1. Synthèse Exécutive",
            "2. Vue d'Ensemble",
            "3. Indicateurs & Signaux Faibles",
        ]
        if not a_segment:
            sommaire_items.append("4. Performance par Segment")
        if not a_produit:
            sommaire_items.append("5. Répartition par Produits")
        if commentaires:
            sommaire_items.append("6. Analyse Détaillée")
        sommaire_items.append("7. Risque de Churn")
        sommaire_items.append("8. Conclusion")
        sommaire_items.append("9. Méthodologie & Notes")

        _heading(doc, 'Sommaire', 1)
        for i, item in enumerate(sommaire_items, 1):
            p = doc.add_paragraph(item)
            _styler_paragraphe(p, font_size=13, color=COLORS['grey_dark'], spacing_after=4)
        doc.add_page_break()

        # 1. Réponse à la demande (personnalisée)
        has_reponse_demande = False
        try:
            lignes_test = _construire_introduction_personnalisee(
                contexte, audience, objectif, question_originale
            )
            if lignes_test:
                _section_reponse_demande(
                    doc, contexte, audience=audience,
                    objectif=objectif, question_originale=question_originale,
                )
                has_reponse_demande = True
                doc.add_page_break()
        except Exception:
            pass

        # 2. Synthèse
        idx_synthese = 2 if has_reponse_demande else 1
        _heading(doc, f'{idx_synthese}. Synthèse Exécutive', 1)
        if synthese:
            for ligne in synthese.split('\n'):
                ligne = ligne.strip().lstrip('•-').strip()
                if ligne:
                    para = doc.add_paragraph(ligne, style='List Bullet')
                    _styler_paragraphe(para, font_size=14, color=COLORS['grey_dark'],
                                      spacing_before=6, spacing_after=6)
        doc.add_paragraph()

        # 3. Vue ensemble
        idx_vue = 3 if has_reponse_demande else 2
        _heading(doc, f'{idx_vue}. Vue d\'Ensemble', 1)
        _section_vue_ensemble(
            doc, contexte, audience=audience, objectif=objectif,
            question_originale=question_originale,
        )

        # 4. Indicateurs
        idx_ind = 4 if has_reponse_demande else 3
        _heading(doc, f'{idx_ind}. Indicateurs & Signaux Faibles', 1)
        if indicateurs:
            filtre_texte = ""
            if a_segment:
                filtre_texte += f" [filtre segment: {a_segment}]"
            if a_produit:
                filtre_texte += f" [filtre produit: {a_produit}]"
            p = doc.add_paragraph(
                f"{len(indicateurs)} signal(aux) détecté(s) entre "
                f"{contexte.get('periode_precedente', 'T3')} et "
                f"{contexte.get('periode_actuelle', 'T4')}{filtre_texte}."
            )
            _styler_paragraphe(p, font_size=12, color=COLORS['grey_medium'], spacing_after=10)
            _creer_tableau_professionnel(doc, indicateurs)
        doc.add_paragraph()

        # 5. Segments (si global)
        idx_seg = 5 if has_reponse_demande else 4
        if not a_segment:
            _section_segments(doc, contexte)
            idx_seg += 1

        # 6. Produits (si global)
        idx_prod = idx_seg
        if not a_produit:
            _section_produits(doc, contexte)
            idx_prod += 1

        # 7. Analyses
        next_idx = idx_prod
        if commentaires:
            _heading(doc, f'{next_idx}. Analyse Détaillée', 1)
            for i, commentaire in enumerate(commentaires, 1):
                dim = ''
                if i - 1 < len(indicateurs):
                    dim = f" — {indicateurs[i-1].get('dimension', '')}"
                _heading(doc, f'Point d\'analyse {i}{dim}', 2)
                para = doc.add_paragraph(commentaire)
                _styler_paragraphe(para, font_size=13, color=COLORS['grey_dark'],
                                  spacing_before=6, spacing_after=14, line_spacing=1.6)
            next_idx += 1

        # Churn
        _heading(doc, f'{next_idx}. Risque de Churn', 1)
        _section_churn(doc, contexte)
        next_idx += 1

        # Conclusion
        _section_conclusion(
            doc, contexte, audience=audience, objectif=objectif,
            question_originale=question_originale,
        )
        next_idx += 1

        # Méthodo
        doc.add_page_break()
        _heading(doc, f'{next_idx}. Méthodologie & Notes', 1)
        _section_methodologie(doc, contexte)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rapport_{timestamp}.docx"
        filepath = OUTPUT_DIR / filename
        doc.save(str(filepath))
        _nettoyer_outputs_anciens(keep_last=3)

        logger.info("Rapport Word personnalisé généré",
                    extra={'extra_data': {
                        'fichier': filename,
                        'audience': audience,
                        'objectif': objectif,
                        'segment': a_segment,
                        'produit': a_produit,
                    }})
        return {
            "succes": True,
            "fichier": filename,
            "chemin_complet": str(filepath),
            "type": "word",
            "timestamp": timestamp,
            "personnalisation": {
                "audience": audience,
                "objectif": objectif,
                "segment": a_segment,
                "produit": a_produit,
            },
        }
    except Exception as e:
        logger.error(f"Erreur génération rapport Word: {e}")
        return {"succes": False, "erreur": f"Erreur lors de la génération: {str(e)}"}


# ===== POWERPOINT =====

def _slide_titre(prs, titre, date_str, contexte=None,
                 audience: str = "direction",
                 objectif: Optional[str] = None):
    audience = _resoudre_audience(contexte.get("audience") if isinstance(contexte, dict) else audience)
    obj = _resoudre_objectif(contexte.get("objectif") if isinstance(contexte, dict) else objectif)
    filtres = (contexte or {}).get("filtres") or {}

    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Badge audience
    box_a = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(1.8), PptxInches(8.4), PptxInches(0.5))
    p_a = box_a.text_frame.paragraphs[0]
    p_a.text = AUDIENCE_TITRES.get(audience, "Analyse de Gestion")
    p_a.font.size = PptxPt(16)
    p_a.font.bold = True
    p_a.font.color.rgb = PPTX_COLORS['copper_accent']
    p_a.alignment = PP_ALIGN.CENTER

    box = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(2.5), PptxInches(8.4), PptxInches(1.8))
    p = box.text_frame.paragraphs[0]
    p.text = titre
    p.font.size = PptxPt(34)
    p.font.bold = True
    p.font.color.rgb = PPTX_COLORS['marine_deep']
    p.alignment = PP_ALIGN.CENTER

    sub = slide.shapes.add_textbox(PptxInches(1), PptxInches(4.3), PptxInches(8), PptxInches(0.7))
    p = sub.text_frame.paragraphs[0]
    sous_texte = AUDIENCE_SOUS_TITRES.get(audience, "Analyse de Gestion Détaillée")
    filtre_txt = ""
    if filtres.get("segment") or filtres.get("produit"):
        parties = []
        if filtres.get("segment"):
            parties.append(f"Segment : {filtres['segment']}")
        if filtres.get("produit"):
            parties.append(f"Produit : {filtres['produit']}")
        filtre_txt = "  ·  " + " | ".join(parties)
    p.text = f"{sous_texte}{filtre_txt}"
    p.font.size = PptxPt(14)
    p.font.color.rgb = PPTX_COLORS['grey_medium']
    p.alignment = PP_ALIGN.CENTER

    sub2 = slide.shapes.add_textbox(PptxInches(1), PptxInches(5.1), PptxInches(8), PptxInches(0.5))
    p2 = sub2.text_frame.paragraphs[0]
    periode = ""
    if contexte:
        periode = f" | {contexte.get('periode_precedente', '')} → {contexte.get('periode_actuelle', '')}"
    p2.text = f"Généré le {date_str}{periode}"
    p2.font.size = PptxPt(14)
    p2.font.color.rgb = PPTX_COLORS['grey_medium']
    p2.alignment = PP_ALIGN.CENTER

    foot = slide.shapes.add_textbox(PptxInches(1), PptxInches(6.6), PptxInches(8), PptxInches(0.4))
    p = foot.text_frame.paragraphs[0]
    p.text = "Assistant Contrôleur de Gestion — Confidentiel"
    p.font.size = PptxPt(13)
    p.font.color.rgb = PPTX_COLORS['grey_medium']
    p.alignment = PP_ALIGN.CENTER


def _add_title(slide, text, top=0.4):
    box = slide.shapes.add_textbox(PptxInches(0.5), PptxInches(top), PptxInches(9), PptxInches(0.6))
    p = box.text_frame.paragraphs[0]
    p.text = text
    p.font.size = PptxPt(26)
    p.font.bold = True
    p.font.color.rgb = PPTX_COLORS['marine_deep']


def _creer_carte_chiffre_cle(slide, left, top, chiffre, label, variation=None):
    width, height = PptxInches(2.7), PptxInches(1.7)
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = PPTX_COLORS['white']
    shape.line.color.rgb = PPTX_COLORS['grey_light']
    shape.line.width = PptxPt(1)
    shape.adjustments[0] = 0.05

    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE

    p = tf.paragraphs[0]
    p.text = chiffre
    p.font.size = PptxPt(28)
    p.font.bold = True
    p.font.color.rgb = PPTX_COLORS['copper_accent']
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = label
    p2.font.size = PptxPt(11)
    p2.font.color.rgb = PPTX_COLORS['grey_medium']
    p2.alignment = PP_ALIGN.CENTER
    p2.space_before = PptxPt(4)

    if variation is not None:
        p3 = tf.add_paragraph()
        p3.text = f"{variation:+.1f}%"
        p3.font.size = PptxPt(13)
        p3.font.bold = True
        p3.font.color.rgb = (
            PPTX_COLORS['success'] if variation > 0
            else PPTX_COLORS['danger'] if variation < 0
            else PPTX_COLORS['grey_medium']
        )
        p3.alignment = PP_ALIGN.CENTER


def _slide_bullets(prs, titre, lignes):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, titre)
    box = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(1.4), PptxInches(8.4), PptxInches(5.5))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for ligne in lignes:
        ligne = ligne.strip().lstrip('•-').strip()
        if not ligne:
            continue
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = ligne
        p.font.size = PptxPt(16)
        p.font.color.rgb = PPTX_COLORS['grey_dark']
        p.space_before = PptxPt(10)
        p.space_after = PptxPt(10)
    return slide


def _slide_kpis_portefeuille(prs, contexte):
    stats = contexte.get('stats_globales') or {}
    if not stats:
        return
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Vue d'Ensemble Portefeuille")
    cards = [
        (_fmt_short(stats.get('nombre_total_clients', 0)).replace('€', ''), "Clients"),
        (_fmt_short(stats.get('pnb_total', 0)), "PNB Total"),
        (_fmt_short(stats.get('rentabilite_totale', 0)), "Rentabilité"),
        (_fmt_short(stats.get('pnb_moyen', 0)), "PNB Moyen"),
        (_fmt_short(stats.get('cout_total', 0)), "Coûts"),
        (f"{contexte.get('nb_clients_a_risque', 0)}", "Clients à risque"),
    ]
    positions = [
        (0.6, 1.5), (3.65, 1.5), (6.7, 1.5),
        (0.6, 3.8), (3.65, 3.8), (6.7, 3.8),
    ]
    for (chiffre, label), (l, t) in zip(cards, positions):
        _creer_carte_chiffre_cle(slide, PptxInches(l), PptxInches(t), str(chiffre), label)


def _slide_segments_table(prs, contexte):
    details = contexte.get('details_segments') or contexte.get('par_segment') or []
    if not details:
        return
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Performance par Segment")

    # Cartes segment
    for i, d in enumerate(details[:3]):
        left = PptxInches(0.6 + i * 3.1)
        top = PptxInches(1.5)
        shape = slide.shapes.add_shape(
            MSO_SHAPE.ROUNDED_RECTANGLE, left, top, PptxInches(2.9), PptxInches(4.5)
        )
        shape.fill.solid()
        shape.fill.fore_color.rgb = PPTX_COLORS['white']
        shape.line.color.rgb = PPTX_COLORS['grey_light']
        shape.adjustments[0] = 0.04
        tf = shape.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = str(d.get('segment', ''))
        p.font.size = PptxPt(20)
        p.font.bold = True
        p.font.color.rgb = PPTX_COLORS['marine_deep']
        p.alignment = PP_ALIGN.CENTER

        lines = [
            f"Clients: {d.get('nombre_clients', 'N/A')}",
            f"PNB: {_fmt_short(d.get('pnb_total', d.get('rentabilite_moyenne', 0)))}",
            f"PNB moy: {_fmt_short(d.get('pnb_moyen', 0))}" if d.get('pnb_moyen') is not None else "",
            f"Rentab.: {_fmt_short(d.get('rentabilite_totale', d.get('rentabilite_moyenne', 0)))}",
            f"Marge: {d.get('marge_pourcent', 'N/A')}%" if d.get('marge_pourcent') is not None else "",
        ]
        for line in lines:
            if not line:
                continue
            pp = tf.add_paragraph()
            pp.text = line
            pp.font.size = PptxPt(13)
            pp.font.color.rgb = PPTX_COLORS['grey_dark']
            pp.alignment = PP_ALIGN.CENTER
            pp.space_before = PptxPt(10)


def _slide_indicateurs_cartes(prs, indicateurs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Indicateurs Clés")
    positions = [
        (0.55, 1.4), (3.65, 1.4), (6.75, 1.4),
        (0.55, 3.7), (3.65, 3.7), (6.75, 3.7),
    ]
    for i, ind in enumerate(indicateurs[:6]):
        left, top = positions[i]
        _creer_carte_chiffre_cle(
            slide,
            PptxInches(left), PptxInches(top),
            _fmt_short(ind.get('valeur_actuelle', 0)),
            str(ind.get('dimension', 'N/A'))[:28],
            ind.get('variation_pourcentage'),
        )


def _slide_detail_indicateur(prs, indicateur, commentaire):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    dim = indicateur.get('dimension', 'Indicateur')
    _add_title(slide, dim)

    _creer_carte_chiffre_cle(
        slide, PptxInches(0.6), PptxInches(1.5),
        _fmt_short(indicateur.get('valeur_actuelle', 0)), "Valeur actuelle"
    )
    _creer_carte_chiffre_cle(
        slide, PptxInches(0.6), PptxInches(3.6),
        _fmt_short(indicateur.get('valeur_precedente', 0)), "Valeur précédente"
    )

    variation = float(indicateur.get('variation_pourcentage') or 0)
    var_shape = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        PptxInches(3.7), PptxInches(1.5),
        PptxInches(5.6), PptxInches(1.5),
    )
    var_shape.fill.solid()
    var_shape.fill.fore_color.rgb = (
        PPTX_COLORS['success'] if variation > 0
        else PPTX_COLORS['danger'] if variation < 0
        else PPTX_COLORS['grey_medium']
    )
    var_shape.line.fill.background()
    var_shape.adjustments[0] = 0.05
    tf = var_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = f"{variation:+.2f}%"
    p.font.size = PptxPt(44)
    p.font.bold = True
    p.font.color.rgb = PPTX_COLORS['white']
    p.alignment = PP_ALIGN.CENTER

    if commentaire:
        box = slide.shapes.add_textbox(
            PptxInches(3.7), PptxInches(3.4), PptxInches(5.6), PptxInches(3.2)
        )
        tf = box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = "Analyse"
        p.font.size = PptxPt(14)
        p.font.bold = True
        p.font.color.rgb = PPTX_COLORS['copper_accent']
        p2 = tf.add_paragraph()
        text = commentaire if len(commentaire) <= 450 else commentaire[:447] + "..."
        p2.text = text
        p2.font.size = PptxPt(13)
        p2.font.color.rgb = PPTX_COLORS['grey_dark']
        p2.space_before = PptxPt(8)


def _slide_churn(prs, contexte):
    clients = contexte.get('clients_a_risque') or []
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Clients à Risque de Churn")
    nb = contexte.get('nb_clients_a_risque', len(clients))

    info = slide.shapes.add_textbox(PptxInches(0.6), PptxInches(1.2), PptxInches(8.8), PptxInches(0.5))
    p = info.text_frame.paragraphs[0]
    p.text = f"{nb} clients avec probabilité ≥ 70% — Top 8 affichés"
    p.font.size = PptxPt(14)
    p.font.color.rgb = PPTX_COLORS['grey_medium']

    box = slide.shapes.add_textbox(PptxInches(0.6), PptxInches(1.8), PptxInches(8.8), PptxInches(5))
    tf = box.text_frame
    tf.word_wrap = True
    header = tf.paragraphs[0]
    header.text = "Client ID          Segment       Âge    Solde         Proba."
    header.font.size = PptxPt(12)
    header.font.bold = True
    header.font.color.rgb = PPTX_COLORS['marine_deep']

    for c in clients[:8]:
        proba = c.get('probabilite_churn', c.get('probabilite', 0))
        try:
            proba_pct = f"{float(proba)*100:.1f}%"
        except (TypeError, ValueError):
            proba_pct = "?"
        line = (
            f"{c.get('client_id', '')}    {c.get('segment', '')}    "
            f"{c.get('age', '')}    {_fmt_short(c.get('solde', 0))}    {proba_pct}"
        )
        pp = tf.add_paragraph()
        pp.text = line
        pp.font.size = PptxPt(13)
        pp.font.color.rgb = PPTX_COLORS['grey_dark']
        pp.space_before = PptxPt(8)


def _slide_reponse_demande(
    prs, contexte, audience="direction", objectif=None, question_originale=""
):
    """Slide dédiée : réponse à la demande utilisateur."""
    lignes = _construire_introduction_personnalisee(
        contexte, audience, objectif, question_originale
    )
    if not lignes:
        return None

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    _add_title(slide, "Réponse à Votre Demande")

    box = slide.shapes.add_textbox(
        PptxInches(0.8), PptxInches(1.5), PptxInches(8.4), PptxInches(5.5)
    )
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for ligne in lignes:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = "• " + ligne
        p.font.size = PptxPt(18)
        p.font.color.rgb = PPTX_COLORS['grey_dark']
        p.space_before = PptxPt(14)
    return slide


def _slide_recommandations(prs, indicateurs, contexte,
                           audience="direction", objectif=None, question_originale=""):
    audience = _resoudre_audience(audience)
    obj = _resoudre_objectif(objectif)
    filtres = (contexte or {}).get("filtres") or {}
    question = (question_originale or "").strip()

    slide = prs.slides.add_slide(prs.slide_layouts[6])
    titre_slide = "Recommandations"
    if obj == "reunion":
        titre_slide = "Décisions & Points de Vigilance (Réunion)"
    elif obj == "investigation":
        titre_slide = "Hypothèses & Pistes d'Investigation"
    elif obj == "validation":
        titre_slide = "Bilan & Actions de Validation"
    elif obj == "strategique":
        titre_slide = "Axes Stratégiques & Orientations"
    _add_title(slide, titre_slide)

    lignes: List[str] = []
    if question and len(question) > 3:
        lignes.append("En réponse à : « " + question + " »")

    baisses = [i for i in indicateurs if float(i.get('variation_pourcentage') or 0) < 0]
    hausses = [i for i in indicateurs if float(i.get('variation_pourcentage') or 0) > 0]
    if baisses:
        top = sorted(baisses, key=lambda x: float(x.get('variation_pourcentage') or 0))[0]
        if obj == "investigation":
            lignes.append(
                f"Piste d'investigation — {top.get('dimension')} : "
                f"creuser les causes de la variation {_fmt_pct(top.get('variation_pourcentage'))}."
            )
        else:
            lignes.append(
                f"Priorité 1 — Investiguer {top.get('dimension')} "
                f"({_fmt_pct(top.get('variation_pourcentage'))})."
            )
    if hausses:
        top = sorted(hausses, key=lambda x: float(x.get('variation_pourcentage') or 0), reverse=True)[0]
        lignes.append(
            f"Consolider la dynamique de {top.get('dimension')} "
            f"({_fmt_pct(top.get('variation_pourcentage'))})."
        )
    if filtres.get("segment"):
        lignes.append(f"Focus : actions spécifiques au segment {filtres['segment']}.")
    if filtres.get("produit"):
        lignes.append(f"Focus : portefeuille Produit {filtres['produit']} — renforcement ciblé.")
    nb_risk = contexte.get('nb_clients_a_risque', 0)
    if nb_risk:
        lignes.append(
            f"Lancer un plan de rétention sur les {nb_risk} clients à risque élevé de churn."
        )
    if audience == "direction":
        lignes.append("Arbitrer les investissements sur les segments en baisse et à fort potentiel.")
        lignes.append("Décision : valider le plan d'actions sur clients à risque.")
    elif audience == "controle":
        lignes.append("Justifier les écarts et rapprocher les données des référentiels financiers.")
        lignes.append("Traçabilité : archiver ce document dans le dossier de clôture.")
    elif audience == "commercial":
        lignes.append("Renforcer les actions commerciales sur les segments et produits en forte hausse.")
        lignes.append("Lever : proposer des produits complémentaires sur les segments en hausse.")
    elif audience == "conseil":
        lignes.append("Traçabilité : l'ensemble des chiffres est auditable depuis la base SQLite.")
        lignes.append("Méthodologie : PNB simulé 2%, coût 0.8%, rentabilité nette 1.2%.")

    if obj == "strategique":
        lignes.append("Intégrer ces évolutions dans la planification stratégique de l'exercice suivant.")
    if obj == "validation":
        lignes.append("Prochaine étape : clôturer la période et lancer la collecte des commentaires terrain.")
    if obj == "reunion":
        lignes.append("Préparer l'ordre du jour et les points de décision en amont de la réunion.")

    lignes.append(
        "Actualiser les données depuis Power BI avant chaque comité de direction."
    )
    if not lignes:
        lignes = ["Maintenir le suivi trimestriel des indicateurs PNB et rentabilité."]

    box = slide.shapes.add_textbox(PptxInches(0.8), PptxInches(1.5), PptxInches(8.4), PptxInches(5))
    tf = box.text_frame
    tf.word_wrap = True
    first = True
    for ligne in lignes:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.text = "• " + ligne
        p.font.size = PptxPt(16)
        p.font.color.rgb = PPTX_COLORS['grey_dark']
        p.space_before = PptxPt(12)


def generer_presentation_pptx(
    titre: str,
    synthese: str,
    commentaires: List[str],
    indicateurs: List[Dict[str, Any]],
    contexte_enrichi: Optional[Dict[str, Any]] = None,
    segment: Optional[str] = None,
    produit: Optional[int] = None,
    audience: str = "direction",
    objectif: Optional[str] = None,
    question_originale: str = "",
) -> Dict[str, Any]:
    """Présentation PowerPoint PERSONNALISÉE (10+ slides, audience/segment/produit)."""
    try:
        _creer_dossier_outputs()
        contexte = contexte_enrichi or {}
        audience = _resoudre_audience(contexte.get("audience") or audience)
        objectif = _resoudre_objectif(contexte.get("objectif") or objectif)
        filtres = contexte.get("filtres") or {}
        a_segment = filtres.get("segment") or segment
        a_produit = filtres.get("produit") or produit

        prs = Presentation()
        prs.slide_width = PptxInches(10)
        prs.slide_height = PptxInches(7.5)
        date_str = datetime.now().strftime("%d %B %Y")

        _slide_titre(prs, titre, date_str, contexte)

        # Slide "Réponse à votre demande" (si on a du contexte)
        try:
            _slide_reponse_demande(
                prs, contexte, audience=audience, objectif=objectif,
                question_originale=question_originale,
            )
        except Exception:
            pass

        lignes_synth = [l for l in (synthese or "").split('\n') if l.strip()]
        _slide_bullets(prs, "Synthèse Exécutive", lignes_synth)

        _slide_kpis_portefeuille(prs, contexte)
        _slide_segments_table(prs, contexte)

        indicateurs_tries = sorted(
            indicateurs,
            key=lambda x: abs(float(x.get('variation_pourcentage') or 0)),
            reverse=True,
        )
        _slide_indicateurs_cartes(prs, indicateurs_tries)

        for i, ind in enumerate(indicateurs_tries[:5]):
            comment = commentaires[i] if i < len(commentaires) else ""
            _slide_detail_indicateur(prs, ind, comment)

        _slide_churn(prs, contexte)
        _slide_recommandations(
            prs, indicateurs_tries, contexte,
            audience=audience, objectif=objectif,
            question_originale=question_originale,
        )

        # Fin
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(PptxInches(1), PptxInches(2.8), PptxInches(8), PptxInches(1))
        p = box.text_frame.paragraphs[0]
        p.text = "Merci de votre attention"
        p.font.size = PptxPt(32)
        p.font.bold = True
        p.font.color.rgb = PPTX_COLORS['marine_deep']
        p.alignment = PP_ALIGN.CENTER
        sub = slide.shapes.add_textbox(PptxInches(1), PptxInches(4), PptxInches(8), PptxInches(0.8))
        p = sub.text_frame.paragraphs[0]
        p.text = "Document généré automatiquement — Assistant CDG"
        p.font.size = PptxPt(14)
        p.font.color.rgb = PPTX_COLORS['grey_medium']
        p.alignment = PP_ALIGN.CENTER

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"presentation_{timestamp}.pptx"
        filepath = OUTPUT_DIR / filename
        prs.save(str(filepath))
        _nettoyer_outputs_anciens(keep_last=3)

        return {
            "succes": True,
            "fichier": filename,
            "chemin_complet": str(filepath),
            "type": "powerpoint",
            "nombre_slides": len(prs.slides),
            "timestamp": timestamp,
        }
    except Exception as e:
        logger.error(f"Erreur génération présentation PowerPoint: {e}")
        return {"succes": False, "erreur": f"Erreur lors de la génération: {str(e)}"}
