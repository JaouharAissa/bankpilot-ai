# 🤖 Assistant IA - Contrôleur de Gestion

Assistant intelligent pour l'analyse financière avec IA locale (Llama 3.1 via Ollama).

## 🚀 Démarrage Rapide

### Prérequis
- Python 3.8+
- Ollama installé ([ollama.com](https://ollama.com))

### Installation (5 minutes)

```bash
# 1. Installer les dépendances
pip install -r requirements.txt

# 2. Télécharger le modèle IA
ollama pull llama3.1

# 3. Initialiser la base de données
python src/setup_db.py

# 4. Lancer l'application
streamlit run src/app.py
```

**Accès:** http://localhost:8501

### Premier Test
Posez cette question dans le chat:
```
Quel est le PNB moyen du segment France ?
```

---

## 📚 Documentation

- **GUIDE_COMPLET.md** - Guide utilisateur complet avec tests des 18 outils
- **POWER_BI_GUIDE.md** - Intégration Power BI (100% locale)
- **design_tokens.md** - Identité visuelle et design système

---

## 📊 Fonctionnalités

### 💬 Chat Intelligent (18 outils)
- Posez des questions en langage naturel
- L'IA interroge automatiquement la base de données
- Réponses basées sur vos données réelles

### 📊 Reporting Automatisé
- Détection automatique de signaux faibles
- Génération de rapports Word
- Création de présentations PowerPoint
- Commentaires de gestion générés par IA

### 📈 Analyses
- Comparaison entre segments géographiques
- Évolution temporelle (T1-T4 2024)
- Statistiques globales du portefeuille

## 🎯 Exemples de Questions

```
"Quel est le PNB moyen du segment France ?"
"Compare France et Germany"
"Détecte les signaux faibles entre T3 et T4 2024"
"Génère un rapport Word pour T4-2024"
"Quelle est la rentabilité des clients avec 2 produits ?"
```

## 📁 Structure du Projet

```
assistant ai/
├── src/
│   ├── app.py                      # Interface web Streamlit
│   ├── assistant.py                # Assistant IA (RAG + Function Calling)
│   ├── outils_donnees.py           # Outils de consultation (5 outils)
│   ├── detection_tendances.py     # Détection de signaux
│   ├── generation_analyse.py      # Commentaires IA
│   ├── generation_documents.py    # Génération Word/PowerPoint
│   ├── reporting_complet.py       # Workflow automatisé
│   └── setup_db.py                 # Initialisation base de données
├── data/
│   ├── Churn_Modelling.csv        # Dataset (10,000 clients)
│   └── cdg_test.db                 # Base SQLite
├── outputs/                        # Rapports générés
├── logs/
│   └── audit.log                   # Logs des opérations
└── requirements.txt                # Dépendances Python
```

## 🛠️ Technologies

- **IA**: Llama 3.1 (via Ollama) - 100% local
- **Base de données**: SQLite
- **Interface**: Streamlit
- **Documents**: python-docx, python-pptx
- **Architecture**: RAG + Function Calling

## 📊 Données

- **Source**: Dataset bancaire Kaggle (10,000 clients)
- **Segments**: France (5,014), Germany (2,509), Spain (2,477)
- **Périodes**: T1-2024, T2-2024, T3-2024, T4-2024 ⚠️ **simulées** (répartition aléatoire)
  - Le dataset source ne contient pas de colonne date
  - Pour utiliser des périodes réelles, voir commentaires dans `src/setup_db.py`
- **Métriques**: PNB, Coûts, Rentabilité

## 🔒 Sécurité

- ✅ 100% local (aucune donnée envoyée sur internet)
- ✅ Requêtes SQL paramétrées (pas d'injection SQL)
- ✅ Lecture seule (pas de modification des données)
- ✅ Logging complet (audit.log)

## 🎓 Comment ça Marche ?

L'assistant utilise une architecture **RAG** (Retrieval Augmented Generation) :

1. Vous posez une question en français
2. L'IA (Llama 3.1) comprend votre intention
3. L'IA choisit le bon outil (parmi 18 disponibles)
4. L'outil interroge la base de données SQLite
5. L'IA formule une réponse avec les données réelles

**Note**: L'IA n'est pas "entraînée" sur vos données. Elle les interroge en temps réel.

## 🆘 Support

**Problème avec Ollama ?**
- Vérifiez qu'Ollama est lancé
- Testez : `ollama list` (doit afficher llama3.1)
- Redémarrez Ollama si nécessaire

**Base de données vide ?**
- Relancez : `python src/setup_db.py`

## 📝 Licence

Projet éducatif - Utilisation libre

---

**Version**: 2.1  
**Dernière mise à jour**: Août 2026

---

## Historique des corrections

- **MISSION_COMPLETE.md** : checklist des 11 tâches (API key retirée, 100 % local, Power BI local, git/cache, outputs, tests, docs, boutons, Fast Dispatcher, design, validation).
- **RAPPORT_VALIDATION_FINALE.md** : rapport de go-live (pytest, isolation réseau, structure, outils, checklist production).
- **BUGFIX_BOUTONS_TELECHARGEMENT.md** : correctif des boutons Word/PPT qui disparaissaient après 2 minutes (chemins stockés dans le message).
- **CONSOLIDATION_DOCS.md** : fusion des anciens .md/.txt vers README, GUIDE_COMPLET, POWER_BI_GUIDE et design_tokens.

Ces quatre fichiers ont été fusionnés ici puis supprimés pour éviter les doublons.
