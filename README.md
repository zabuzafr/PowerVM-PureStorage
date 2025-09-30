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

## 🧩 Schémas d’architecture & séquence

### 1) Vue d’ensemble (flux nominal → PRA)

```mermaid
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
