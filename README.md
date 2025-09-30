= PRA.py — IBM Power LPARs → Pure Storage integration for Disaster Recovery
Pierre-Jacques MIMIFIR <contact@zabuzafr.dev>
:toc:
:icons: font
:sectnums:
:source-highlighter: rouge
:mermaid: true

== 🧭 Contexte & Historique

`PRA.py` est la **version Python (2019)** d’un script initialement écrit en **Perl (2005)**.  
Il a été conçu pour **automatiser la définition des LPARs** d’un site nominal vers un **site PRA (Plan de Reprise d’Activité)**.

Objectif principal : garantir que les environnements AIX critiques puissent être redéployés **en moins de 5 minutes** en cas de sinistre.

Fonctions clés :
- Découverte des LPARs et WWPN via **IBM HMC**
- Préservation des **adresses MAC** pour maintenir les règles firewall/ACL entre sites
- Mise à jour des hôtes sur les **baies Pure Storage**
- Respect des conventions de nommage des **LUNs** et **snapshots répliqués**

== 🎯 Objectifs

* Automatiser le PRA AIX
* RTO < 5 minutes
* Conserver les **MAC** → règles réseau identiques
* Aligner compute ↔ storage ↔ réseau
* Remplacer le script Perl par une version Python maintenable

== 🧩 Schémas d’architecture & séquence

=== 1) Vue d’ensemble (flux nominal → PRA)

[mermaid, target=architecture, format=svg]
----
flowchart LR
  subgraph Site_Nominal
    HMC[IBM HMC] --- PVM[PowerVM / Managed Systems]
    PVM --> LPARS[LPARs (AIX)]
    LPARS --> WWPN[WWPNs FC]
    LPARS -. MACs conservées .- NETN[Politiques Réseau / FW]
    FA1[Pure Storage (Prod)] --> LUNS[LUNs]
    LUNS --> SNAP[Snapshots]
  end

  subgraph Réplication
    SNAP -->|réplication| REPL[Snapshots répliqués]
  end

  subgraph Site_PRA
    FA2[Pure Storage (PRA)] --> REPL
    PVM2[PowerVM (PRA)] --- HMC
    LPARS2[LPARs (AIX) PRA] -. MACs identiques .- NETP[FW/ACL identiques]
    LPARS2 --> WWPN2[WWPNs (sync)]
  end

  HMC -->|Découverte LPAR/WWPN| PRApy[PRA.py]
  PRApy -->|Maj hôtes + WWPN| FA1
  PRApy -->|Maj hôtes + WWPN| FA2
  PRApy -->|Garantit nommage LUN/Snap| FA1
  PRApy -->|Garantit nommage LUN/Snap| FA2
----

=== 2) Séquence de reprise (DR)

[mermaid, target=sequence, format=svg]
----
sequenceDiagram
  autonumber
  participant Op as Operator/Orchestrateur
  participant PRA as PRA.py
  participant HMC as IBM HMC
  participant FA1 as Pure (Prod)
  participant FA2 as Pure (PRA)

  Op->>PRA: Lancer PRA (Nominal → PRA)
  PRA->>HMC: lsyscfg / lshwres (LPAR; WWPN; MAC)
  HMC-->>PRA: Inventaire (WWPNs, MACs)

  PRA->>PRA: Normaliser WWPNs / valider MACs / nommage LUN/Snap
  PRA->>FA1: Vérifier hôtes/LUNs/snapshots
  FA1-->>PRA: OK / corrections idempotentes

  PRA->>FA2: Créer/mettre à jour hôtes (LPAR) + associer WWPNs
  FA2-->>PRA: Hôtes alignés

  PRA->>HMC: Préparer définitions LPAR PRA (MAC identiques)
  HMC-->>PRA: Définitions prêtes

  Op->>HMC: Activer LPARs PRA
  Note over Op,HMC: RTO visé < 5 min grâce à l’alignement compute/storage/réseau
----

== ⚙️ Fonctionnement

. Connexion SSH à la HMC
. Récupération des `lsyscfg` et `lshwres`
. Parsing des WWPNs + validation des MAC
. Mise à jour des hôtes sur Pure Storage
. Vérification des LUNs/snapshots répliqués
. Définition des LPAR PRA avec **MAC identiques**
. Déclenchement PRA (si sinistre)

== 📦 Prérequis

- Python 3.8+
- Bibliothèques :
** `paramiko`
** SDK ou REST API **Pure Storage**
- Accès réseau :
** SSH HMC
** HTTPS Pure Storage
- Comptes avec droits lecture HMC, écriture hôtes Pure

== 🚀 Usage (prototype)

[source,bash]
----
python PRA.py \
  -H <hmc_host> -u <hmc_user> -w <hmc_password> \
  -P <pure_mgmt_ip> -s <pure_user|token> -p <pure_password> \
  --system <managed_system> \
  --exclude-lpar lpar1,lpar2
----

== 🔒 Bénéfices

* RTO < 5 minutes
* MAC identiques ⇒ firewalls/ACL cohérents
* Nommage standardisé (LPARs, LUNs, Snapshots)
* Automatisation idempotente

== 🛠️ Limitations actuelles

* Fonction `update_pure_host_wwn` à implémenter
* Gestion des adresses MAC côté PRA à compléter
* CLI à migrer vers `argparse`
* Script au stade de **POC**

== 🧪 Tests conseillés

* Unitaires : normalisation WWPN, parsing, validation MAC
* Intégration : mocks Paramiko, API Pure
* PRA dry-run avant production

== 📄 Licence
MIT
