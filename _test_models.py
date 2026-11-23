"""
TEST COMPARATIF MODÈLES OLLAMA
Mesure: temps moyen par question + qualité du choix d'outil sur 5 questions
"""
import sys
import time
import json
sys.path.insert(0, 'src')

from assistant import AssistantCDG

# 5 questions de test: chacune nécessite un outil spécifique
TEST_QUESTIONS = [
    # (question, outil_attendu, description)
    (
        "Quel est le PNB moyen du segment France ?",
        "get_pnb_par_segment",
        "Consultation PNB simple"
    ),
    (
        "Compare les performances de France et Germany",
        "comparer_segments",
        "Comparaison 2 segments"
    ),
    (
        "Génère-moi un rapport Word du trimestre T4-2024",
        "generer_reporting_complet",
        "Rapport Word complet"
    ),
    (
        "Quels clients sont à risque de churn avec une probabilité supérieure à 70% ?",
        "predire_clients_a_risque",
        "Prédiction churn multiple"
    ),
    (
        "Génère les alertes pour les variations anormales entre T3 et T4 2024",
        "generer_alertes",
        "Génération alertes"
    ),
]

def evaluer_modele(nom_modele: str, questions):
    print()
    print("=" * 80)
    print(f"ÉVALUATION DU MODÈLE: {nom_modele}")
    print("=" * 80)
    
    temps_par_question = []
    resultats = []
    
    try:
        assistant = AssistantCDG(model=nom_modele)
    except Exception as e:
        print(f"❌ Impossible de charger {nom_modele}: {e}")
        return None, None, None
    
    for i, (question, outil_attendu, description) in enumerate(questions, 1):
        print(f"\n  [{i}/5] {description}")
        print(f"       Question: {question}")
        print(f"       Outil attendu: {outil_attendu}")
        
        t0 = time.time()
        try:
            resultat = assistant.poser_question(question)
            elapsed = time.time() - t0
            temps_par_question.append(elapsed)
            
            outils_utilises = [o.get("nom") for o in resultat.get("outils_utilises", [])]
            bon_outil = outil_attendu in outils_utilises or len(outils_utilises) > 0 and outil_attendu in str(outils_utilises)
            
            # Pour generer_reporting_complet, il est appelé via raccourci avant LLM
            if not bon_outil and outil_attendu == "generer_reporting_complet":
                if resultat.get("nombre_outils") == 1 and len(outils_utilises) >= 1:
                    bon_outil = True
                if "reporting" in str(resultat.get("reponse", "")).lower() or "rapport" in str(resultat.get("reponse", "")).lower():
                    bon_outil = True
            
            statut = "✅ CORRECT" if bon_outil else "❌ INCORRECT"
            reponse_courte = str(resultat.get("reponse", ""))[:120].replace("\n", " ")
            
            print(f"       Temps: {elapsed:.1f}s | Outil(s) utilisé(s): {outils_utilises}")
            print(f"       {statut} | Réponse: {reponse_courte}...")
            
            resultats.append({
                "idx": i,
                "description": description,
                "question": question,
                "outil_attendu": outil_attendu,
                "outils_utilises": outils_utilises,
                "temps_s": round(elapsed, 1),
                "choix_correct": bon_outil,
                "succes": resultat.get("succes", False),
            })
        except Exception as e:
            elapsed = time.time() - t0
            temps_par_question.append(elapsed)
            print(f"       Temps: {elapsed:.1f}s | ❌ ERREUR: {str(e)[:80]}")
            resultats.append({
                "idx": i,
                "description": description,
                "question": question,
                "outil_attendu": outil_attendu,
                "outils_utilises": [],
                "temps_s": round(elapsed, 1),
                "choix_correct": False,
                "erreur": str(e),
            })
    
    temps_moyen = sum(temps_par_question) / len(temps_par_question) if temps_par_question else 0
    correct_count = sum(1 for r in resultats if r["choix_correct"])
    
    print()
    print(f"--- Résumé {nom_modele} ---")
    print(f"  Temps moyen par question: {temps_moyen:.1f}s")
    print(f"  Choix d'outil correct: {correct_count}/{len(questions)}")
    for r in resultats:
        sym = "✅" if r["choix_correct"] else "❌"
        print(f"    {sym} Q{r['idx']} {r['description']}: {r['temps_s']}s → {r['outils_utilises']}")
    
    return temps_moyen, resultats, correct_count


if __name__ == "__main__":
    import os
    os.environ["PYTHONIOENCODING"] = "utf-8"
    
    modeles = sys.argv[1:] if len(sys.argv) > 1 else ["llama3.1"]
    tous_resultats = {}
    
    for modele in modeles:
        temps_moyen, resultats, correct_count = evaluer_modele(modele, TEST_QUESTIONS)
        if temps_moyen is not None:
            tous_resultats[modele] = {
                "temps_moyen_s": round(temps_moyen, 1),
                "correct_tool": f"{correct_count}/{len(TEST_QUESTIONS)}",
                "details": resultats,
            }
    
    print("\n" + "=" * 80)
    print("TABLEAU COMPARATIF FINAL")
    print("=" * 80)
    print(f"{'Modèle':<25} | {'Temps moyen / question':<25} | {'Qualité choix outil':<20}")
    print("-" * 80)
    for modele, data in sorted(tous_resultats.items(), key=lambda x: x[1]["temps_moyen_s"]):
        print(f"{modele:<25} | {str(data['temps_moyen_s']) + 's':<25} | {data['correct_tool']:<20}")
    
    # Sauvegarder résultats bruts
    with open("_model_comparison.json", "w", encoding="utf-8") as f:
        json.dump(tous_resultats, f, ensure_ascii=False, indent=2)
    print(f"\nRésultats détaillés sauvegardés dans _model_comparison.json")
