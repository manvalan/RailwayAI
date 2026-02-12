# Documentazione Rete Neurale: RailwayAI

## 1. Descrizione e Architettura della Rete

La rete neurale è il cuore decisionale del sistema **RailwayAI**. Il suo scopo è apprendere strategie complesse per ottimizzare il traffico ferroviario in tempo reale, risolvendo conflitti e minimizzando i ritardi senza richiedere regole if-then manuali.

### Architettura: MAPPO (Multi-Agent Proximal Policy Optimization)

Il sistema utilizza un approccio **Multi-Agente (MARL)** basato sull'algoritmo **PPO (Proximal Policy Optimization)**. Non c'è un "unico controllore centrale", ma ogni treno è un **agente autonomo** che prende decisioni basate sulla sua visione locale del mondo, pur condividendo i pesi della rete (Parameter Sharing) per accelerare l'apprendimento.

*   **Tipo:** Actor-Critic (Due reti distinte che lavorano insieme).
*   **Framework:** PyTorch.
*   **Input (Osservazioni - 15 dimensioni):**
    *   Ogni agente (treno) osserva:
        1.  La propria posizione sul binario (normalizzata 0-1).
        2.  La propria velocità attuale.
        3.  Il proprio ritardo accumulato.
        4.  La priorità del treno.
        5.  L'occupazione dei binari vicini (visione locale del traffico).
        6.  La distanza dalla prossima stazione.
*   **Output (Azioni - 4 discrete):**
    *   0: **Mantieni Velocità** (Coasting).
    *   1: **Accelera** (Aumenta velocità).
    *   2: **Frena** (Decelera).
    *   3: **Stop/Wait** (Fermati al segnale o in stazione).

### Implementazione Tecnica

*   **File Principali:**
    *   `python/marl_scheduling/models.py`: Definisce le classi `Actor` e `Critic`.
    *   `python/marl_scheduling/train_mappo.py`: Loop di addestramento principale.
    *   `python/marl_scheduling/env.py`: L'ambiente simulato che calcola fisica, collisioni e reward.
*   **Struttura Reti:**
    *   **Attore (Policy):** MLP (Multi-Layer Perceptron) a 3 strati (Input 15 -> Hidden 64 -> Hidden 64 -> Output 4). Usa attivazione `Tanh` o `ReLU`.
    *   **Critico (Value Function):** Simile all'attore, ma output singolo (stima del valore dello stato).

---

## 2. Il Fine (Obiettivo)

L'obiettivo ultimo è addestrare una rete capace di gestire **qualsiasi scenario ferroviario** (dalla linea semplice a nodi complessi come Firenze SMN) in modo **generalizzato**.

La rete deve imparare a bilanciare due obiettivi contrastanti:
1.  **Sicurezza:** **Zero collisioni** e rispetto delle distanze di sicurezza.
2.  **Efficienza:** **Minimizzare i ritardi** complessivi e massimizzare la fluidità del traffico.

Non vogliamo programmare le regole ("se c'è rosso fermati"), ma vogliamo che la rete *capisca* da sola che passare col rosso causa un disastro (reward negativo) e quindi impari a fermarsi.

---

## 3. Strategia di Training (Procedura Attuale)

Attualmente stiamo seguendo una strategia di **Curriculum Learning** (Apprendimento Graduale), simile a come si insegna a scuola: si parte dalle basi e si aumenta la difficoltà solo quando l'alunno è pronto.

### Fasi del Training:

1.  **Livello 1 (Lineare Semplice):**
    *   Scenario: Binario unico, 2 treni che vanno in direzioni opposte.
    *   Obiettivo: Imparare a non scontrarsi frontalmente (uno deve aspettare nello scambio).
    *   Stato: **SUPERATO**.

2.  **Livello 2 (Lineare Complesso):**
    *   Scenario: Linea più lunga, più stazioni, 4+ treni con diverse priorità.
    *   Obiettivo: Gestire sorpassi e incroci multipli.
    *   Stato: **STAGNANTE / SUPERATO PARZIALMENTE**. La rete ha imparato a non fare incidenti, ma è diventata troppo "prudente" (lenta).

3.  **Livello 3 (Hub / Star Topology):** *<-- Siamo Qui (Forzato)*
    *   Scenario: Nodo centrale con diramazioni a stella.
    *   Obiettivo: Gestire il traffico convergente verso un punto critico.

### Metodologia Operativa:
*   **Idle Training:** Il sistema sfrutta i momenti in cui il server non è utilizzato dagli utenti umani per lanciare sessioni di addestramento in background (`idle_training.py`).
*   **Checkpointing:** Salvataggio frequente dei pesi (`.pth`) ogni 50 episodi.
*   **Entropia:** Monitoriamo l'entropia per capire se la rete sta esplorando (valori alti) o se è sicura delle sue azioni (valori bassi).

---

## 4. Problemi Riscontrati e Soluzioni Adottate

Durante il percorso abbiamo affrontato diversi ostacoli critici:

### A. Il "Reset" Infinito (Livello 1 Loop)
*   **Problema:** La rete tornava sempre al Livello 1 dopo ogni riavvio del server, perdendo i progressi.
*   **Causa:** Errore nel codice che cercava i checkpoint nella cartella sbagliata (`models/training` invece di `checkpoints/`).
*   **Soluzione:** Fix del percorso nel codice `idle_training.py` e allineamento delle cartelle tra ambiente locale e Docker remoto.

### B. Stagnazione al Livello 2 (The "Lazy Agent")
*   **Problema:** Al Livello 2, la rete ha trovato un "minimo locale": per evitare incidenti (penalità gravissima), ha deciso di fermare quasi tutti i treni o muoverli pianissimo.
*   **Risultato:** Reward stabile a -600 (sicuro ma inutile), senza mai raggiungere la soglia di sblocco per il L3.
*   **Azione Correttiva:** Abbiamo forzato manualmente il passaggio al Livello 3 per "rompere" questa strategia conservativa e costringere la rete a riadattarsi.

### C. Confusione dei Checkpoint (L2 vs L3)
*   **Problema:** Anche dopo aver forzato il codice al L3, il sistema ricaricava il vecchio checkpoint L2 e tornava indietro.
*   **Soluzione Drastica:** Pulizia totale della cartella checkpoint sul server. Abbiamo archiviato i vecchi file e lasciato un unico file rinominato forzatamente come L3 (`mappo_curriculum_l3_ep30000.pth`), obbligando il sistema a partire da lì.

### D. Discrepanza Locale vs Remoto
*   **Problema:** I file di log locali mostravano attività che non corrispondeva a quella reale sul server Docker.
*   **Soluzione:** Abbiamo spento il training locale (`enabled=False`) e ci siamo concentrati esclusivamente sulla gestione via SSH del server remoto, che è molto più potente.
