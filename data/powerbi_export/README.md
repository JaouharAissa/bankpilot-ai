# Exports Power BI → Assistant CDG

Placez ici vos fichiers exportés depuis Power BI (CSV ou Excel).

## Comment exporter depuis Power BI Desktop

1. Ouvrez votre rapport Power BI
2. Sélectionnez la table / requête (ex: clients, pnb_analytique)
3. Accueil → Transformer les données → clic droit sur la table → Exporter
   OU: Fichier → Exporter → vers CSV / Excel
4. Enregistrez le fichier dans ce dossier: `data/powerbi_export/`

## Colonnes acceptées

### Option A — Schéma métier (recommandé)
client_id, segment, periode, age, anciennete, produit, solde,
pnb_simule, cout_simule, rentabilite, est_actif, a_quitte

### Option B — Format type Churn / banque
CustomerId (ou client_id), Geography (ou segment), Age, Tenure,
NumOfProducts, Balance, IsActiveMember, Exited
(+ optionnel: periode, pnb_simule, cout_simule, rentabilite)

Si PNB/coûts absents: PNB = Solde × 2%, Coût = Solde × 0.8%.

## Synchroniser

```bash
python sync_powerbi.py rebuild
# ou surveillance automatique:
python sync_powerbi.py watch
```

Dans Streamlit: sidebar → **Données Power BI** → Actualiser / Rebuild.

Le chatbot lit toujours `data/cdg_test.db` — dès que l'export change, rebuild → réponses à jour.
