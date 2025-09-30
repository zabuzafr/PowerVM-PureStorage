# PRA.py — IBM Power LPARs → Pure Storage integration for Disaster Recovery

## 🧭 Contexte & Historique

`PRA.py` est la **version Python (2019)** d’un script initialement écrit en **Perl (2005)**.  
Il a été conçu pour **automatiser la définition des LPARs** d’un site nominal vers un **site PRA (Plan de Reprise d’Activité)**.

Objectif principal : garantir que les environnements AIX critiques puissent être redéployés **en moins de 5 minutes** en cas de sinistre.

### Fonctions clés
- Découverte des LPARs et WWPN via **IBM HMC**  
- Préservation des **adresses MAC** pour maintenir les règles firewall/ACL entre sites  
- Mise à jour des hôtes sur les **baies Pure Storage**  
- Respect des conventions de nommage des **LUNs** et **snapshots répliqués**

---

## 🎯 Objectifs

- Automatiser le PRA AIX  
- Réduire le RTO à moins de 5 minutes  
- Conserver les **MAC** pour garantir des règles réseau identiques  
- Aligner **compute ↔ storage ↔ réseau**  
- Moderniser un ancien script Perl en Python maintenable  

---

##⚙️ Fonctionnement
- Connexion SSH à la HMC
- Récupération des lsyscfg et lshwres
- Parsing des WWPNs + validation des MAC
- Mise à jour des hôtes sur Pure Storage
- Vérification des LUNs/snapshots répliqués
- Définition des LPAR PRA avec MAC identiques
- Déclenchement PRA (si sinistre)

---

## 📦 Prérequis
- Python 3.8+
- Bibliothèques pparamiko
- SDK ou REST API Pure Storage
- Accès réseau :
  -- SSH vers la HMC
  -- HTTPS vers la baie Pure Storage
  -- Comptes avec droits lecture HMC, écriture hôtes Pure

---
🚀Usage (prototype)
python PRA.py \
  -H <hmc_host> -u <hmc_user> -w <hmc_password> \
  -P <pure_mgmt_ip> -s <pure_user|token> -p <pure_password> \
  --system <managed_system> \
  --exclude-lpar lpar1,lpar2
🔒 Bénéfices
RTO < 5 minutes
MAC identiques ⇒ firewalls/ACL cohérents
Nommage standardisé (LPARs, LUNs, Snapshots)
Automatisation idempotente
🛠️ Limitations actuelles
Fonction update_pure_host_wwn à implémenter
Gestion des adresses MAC côté PRA à compléter
CLI à migrer vers argparse
Script au stade de POC
🧪 Tests conseillés
Unitaires : normalisation WWPN, parsing, validation MAC
Intégration : mocks Paramiko, API Pure
PRA dry-run avant production
🗺️ Roadmap
2005 — Perl v1 : découverte LPAR/WWPN (site nominal → PRA)
2019 — Python v1 (PRA.py) : migration Perl → Python, intégration Paramiko
2020 — Python v2 : ajout support Pure Storage (API REST) + standards de nommage LUN/Snapshots
2022 — Python v3 : conservation stricte des MAC pour cohérence firewall/ACL
2024 — Python v4 (POC Cloud) : mode --dry-run, rapport Markdown, intégration CI/CD
2025+ — Vision :
Intégration Ansible / Terraform
Supervision PRA via Grafana/Prometheus
IA/LLM pour génération dynamique de playbooks PRA
Support cloud hybride (Azure, AWS)
📄 Licence
À définir (ex: MIT, Apache 2.0)


