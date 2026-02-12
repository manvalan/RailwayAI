# Piano di Training RailwayAI 2.0: Strategia "Anti-Pigrizia" e Robustezza

Questo documento definisce le modifiche architetturali e algoritmiche per evolvere il sistema di training di RailwayAI, superando i limiti di stagnazione (Livello 2) e garantendo un apprendimento progressivo e resiliente.

---

## 1. Architettura "The Slow-Burner" (Ottimizzazione Risorse)
**Obiettivo:** Massimizzare l'efficienza di apprendimento su hardware limitato, evitando saturazione e crash.

### A. Modifiche a `train_mappo.py` e Configurazioni PPO
*   **Mini-Batch Stabili:**
    *   `batch_size`: Ridotto a **64** (era variabile/alto).
    *   `ppo_epoch`: Aumentato a **15** (era 10). La rete "riflette" di più su ogni batch di dati raccolti.
*   **Parallelismo Leggero:**
    *   `num_env`: Impostato a **4** processi paralleli (tramite `SubprocVecEnv` o simile leggero). Questo aumenta la diversità statistica senza uccidere la CPU.
    *   `torch.set_num_threads(2)`: Limitazione esplicita dei thread PyTorch per evitare context switching eccessivo sui core del server.

### B. Buffer di Esperienza Circolare (Opzionale/Fase 2)
*   **Implementazione:** Un buffer FIFO che mantiene le traiettorie migliori degli ultimi N episodi.
*   **Logica:** Se un episodio ha `reward > soglia_eccellenza` e `conflitti == 0`, viene salvato e riutilizzato per 2-3 epoch aggiuntive. (Da valutare impatto RAM).

---

## 2. Strategia "Anti-Pigrizia" (Sblocco L2 -> L3)
**Obiettivo:** Punire la stasi e incentivare il rischio calcolato.

### A. Progressive Penalty Shaping (in `env.py`)
Modifica della funzione di reward per penalizzare non linearmente i ritardi.
*   **Formula:** `penalty = (delay_steps / 100.0) ** 2.5`
*   **Effetto:**
    *   Ritardo breve (attesa semaforo): Penalità trascurabile.
    *   Ritardo lungo (stazione bloccata): Penalità devastante.
    *   **Risultato:** La rete impara che "meglio rischiare una manovra lenta che stare fermi per sempre".

### B. Curriculum Sincronizzato (Epsilon-Greedy Level Sampling)
Invece di un "switch" secco L2->L3, usiamo un approccio probabilistico in `curriculum.py` o `train_mappo.py`.
*   **Logica:**
    *   `p_l3 = 0.2` (Iniziale: 20% probabilità di scenario L3).
    *   Ogni episodio: `current_level = 3 if random() < p_l3 else 2`.
    *   **Adattamento:** Se `avg_reward_l3` migliora, `p_l3` aumenta gradualmente fino a 1.0 (100%).
*   **Vantaggio:** La rete mantiene le competenze del L2 mentre esplora il L3 senza "dimenticare" tutto di colpo (Catastrophic Forgetting mitigato).

---

## 3. Gestione Remota e Checkpointing Robusto
**Obiettivo:** Tolleranza ai guasti e ripristino automatico intelligente.

### A. Strict File Locking (`idle_training.py`)
*   **Nuovo File:** `checkpoints/LATEST_SUCCESSFUL_LEVEL.json`
*   **Contenuto:**
    ```json
    {
      "level": 3,
      "episode": 35200,
      "avg_reward": -450.0,
      "timestamp": "2026-02-12T22:00:00"
    }
    ```
*   **Logica di Avvio:**
    1.  Legge questo file JSON.
    2.  Forza il caricamento del checkpoint corrispondente (`mappo_curriculum_l{level}_ep{episode}.pth`).
    3.  Ignora eventuali file "orfani" o incompleti.

### B. Health Check Automatizzato (`train_mappo.py` -> `monitor.json`)
Ogni 100 episodi, il training scrive un report di salute.
*   **Metriche:** `collision_rate`, `avg_speed`, `entropy`.
*   **Auto-Correction:**
    *   Se `avg_speed < 5 km/h` (Pigrizia estrema) -> **Iniettare Rumore** (`entropy_coef *= 1.5`).
    *   Se `collision_rate > 10%` (Caos totale) -> **Ridurre Learning Rate** (`lr *= 0.8`).

---

## 4. Pipeline di Implementazione

1.  **Codice Locale:** Applicare le modifiche ai file Python (`train_mappo.py`, `env.py`, `idle_training.py`).
2.  **Verifica:** Test rapido in locale (10 episodi) per assicurarsi che non crashi.
3.  **Commit git:** Aggiornare il repository.
4.  **Deploy Server:**
    *   `git pull` sul server.
    *   `docker build` (per aggiornare le dipendenze se necessario).
    *   `docker restart`.
5.  **Monitoraggio:** Verifica dai log che la strategia "Anti-Pigrizia" stia funzionando (es. `p_l3` che aumenta).
