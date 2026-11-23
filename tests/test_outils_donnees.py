"""
Tests automatisés pour les fonctions critiques de l'assistant
"""

import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

import pytest
from outils_donnees import get_pnb_par_segment, get_statistiques_globales
from prediction_churn import predire_risque_churn, charger_modele


class TestOutilsDonnees:
    """Tests des outils de données"""
    
    def test_segment_existant_retourne_resultat(self):
        """Vérifie qu'une requête sur un segment existant retourne un résultat"""
        result = get_pnb_par_segment("France")
        
        assert result is not None, "Le résultat ne doit pas être None"
        assert result.get('donnees_trouvees') == True, "Les données doivent être trouvées"
        assert 'pnb_moyen' in result, "Le résultat doit contenir pnb_moyen"
        assert result['pnb_moyen'] > 0, "Le PNB moyen doit être positif"
        assert result['nombre_clients'] > 0, "Le nombre de clients doit être positif"
    
    def test_segment_inexistant_ne_plante_pas(self):
        """Vérifie qu'une requête sur un segment inexistant ne plante pas"""
        result = get_pnb_par_segment("PaysInexistant")
        
        assert result is not None, "Le résultat ne doit pas être None"
        assert result.get('donnees_trouvees') == False, "Les données ne doivent pas être trouvées"
        assert 'erreur' in result or result.get('nombre_clients') == 0, "Doit indiquer l'absence de résultats"
    
    def test_statistiques_globales_structure(self):
        """Vérifie que les statistiques globales ont la bonne structure"""
        result = get_statistiques_globales()
        
        assert result is not None
        assert result.get('donnees_trouvees') == True
        assert 'global' in result
        assert 'par_segment' in result
        assert 'par_produit' in result
        assert isinstance(result['par_segment'], list)
        assert len(result['par_segment']) > 0


class TestPredictionChurn:
    """Tests du modèle de prédiction de churn"""
    
    def test_modele_charge_correctement(self):
        """Vérifie que le modèle se charge correctement"""
        result = charger_modele()
        
        assert result is not None
        assert result.get('succes') == True, "Le chargement doit réussir"
        assert 'model' in result, "Le résultat doit contenir le modèle"
        assert 'features' in result, "Le résultat doit contenir les features"
    
    def test_prediction_retourne_probabilite_valide(self):
        """Vérifie que la prédiction retourne une probabilité entre 0 et 1"""
        # Utiliser un client ID du dataset
        result = predire_risque_churn(15634602)
        
        assert result is not None
        assert result.get('succes') == True, "La prédiction doit réussir"
        assert 'probabilite_churn' in result, "Doit contenir la probabilité"
        
        proba = result['probabilite_churn']
        assert 0 <= proba <= 1, f"La probabilité doit être entre 0 et 1, reçu: {proba}"
        assert isinstance(proba, (int, float)), "La probabilité doit être un nombre"
    
    def test_prediction_client_inexistant(self):
        """Vérifie que la prédiction sur un client inexistant gère l'erreur"""
        result = predire_risque_churn(99999999)
        
        assert result is not None
        assert result.get('succes') == False, "La prédiction doit échouer"
        assert 'erreur' in result, "Doit contenir un message d'erreur"


class TestIntegration:
    """Tests d'intégration"""
    
    def test_workflow_complet_segment(self):
        """Test d'un workflow complet: requête segment -> vérification données"""
        result = get_pnb_par_segment("Germany")
        
        assert result.get('donnees_trouvees') == True
        assert result['nombre_clients'] > 0
        assert result['pnb_moyen'] > 0
        assert result['pnb_total'] > 0
        
        # Vérifier la cohérence
        assert result['pnb_total'] >= result['pnb_moyen'], "Le PNB total doit être >= au PNB moyen"


class TestGenerationDocuments:
    """Tests de génération de documents"""
    
    def test_generation_documents_word_pptx(self):
        """Vérifie la génération des documents Word et PowerPoint"""
        from generation_documents import generer_rapport_word, generer_presentation_pptx
        from reporting_complet import generer_reporting_complet
        
        res = generer_reporting_complet()
        assert res['succes'] is True, "La génération doit réussir"
        assert len(res['fichiers_generes']) == 2, "Doit générer 2 fichiers (Word + PowerPoint)"
        
        word_file = next(f for f in res['fichiers_generes'] if f['type'] == 'word')
        ppt_file = next(f for f in res['fichiers_generes'] if f['type'] == 'pptx')
        
        assert Path(word_file['chemin']).exists(), "Le fichier Word doit exister"
        assert Path(word_file['chemin']).stat().st_size > 10000, "Document Word substantiel attendu"
        
        assert Path(ppt_file['chemin']).exists(), "Le fichier PowerPoint doit exister"
        assert Path(ppt_file['chemin']).stat().st_size > 20000, "Présentation PowerPoint substantielle attendue"


class TestPowerBISync:
    """Tests de synchronisation Power BI (100% local)"""
    
    def test_powerbi_sync_locale(self):
        """Vérifie la synchronisation Power BI locale (CSV → SQLite)"""
        from powerbi_sync import get_statut_synchronisation, synchroniser_donnees_powerbi
        
        sync_res = synchroniser_donnees_powerbi(source_label="Pytest Test Sync")
        assert sync_res['succes'] is True, "La synchronisation doit réussir"
        assert "statut" in sync_res, "Le résultat doit contenir le statut"
        
        statut = get_statut_synchronisation()
        assert statut['statut'] == "synchronisé", "Le statut doit être 'synchronisé'"
        assert statut['nombre_clients'] == 10000, "Doit avoir 10000 clients"
        assert statut['pnb_total'] > 0, "Le PNB total doit être positif"


class TestAssistantOllama:
    """Tests de l'assistant Ollama avec function calling"""
    
    def test_assistant_function_calling(self):
        """
        Vérifie que l'assistant Ollama répond correctement avec function calling.
        Note: Peut prendre 30s-5min sur CPU (normal pour Ollama).
        """
        from assistant import AssistantCDG
        
        assistant = AssistantCDG()
        
        # Question simple pour tester le function calling
        q = "Quel est le PNB moyen du segment France ?"
        res = assistant.poser_question(q)
        
        # Vérifications de base
        assert res['succes'] is True, f"La question doit réussir: {q}"
        assert len(res['reponse']) > 20, "La réponse doit être substantielle"
        
        # Si Ollama est disponible, vérifier qu'un outil a été appelé
        if assistant.ollama_disponible:
            assert len(res.get('outils_utilises', [])) > 0, \
                "Ollama doit appeler au moins un outil (function calling)"
            outil_appele = res['outils_utilises'][0]['nom']
            assert outil_appele in ('get_pnb_par_segment', 'get_statistiques_globales'), \
                f"Outil attendu pour cette question, reçu: {outil_appele}"


if __name__ == "__main__":
    # Exécuter les tests avec pytest
    pytest.main([__file__, "-v", "--tb=short"])
