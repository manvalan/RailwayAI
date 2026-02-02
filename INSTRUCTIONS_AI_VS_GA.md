# 🧠 Istruzioni per l'Agente: Neural Network (AI) vs Genetic Algorithm (GA)

In questo progetto esistono due motori di ottimizzazione. È fondamentale non confonderli.

## 1. Rete Neurale (IL VERO CERVELLO AI)
Utilizza l'architettura **LSTM + Multi-Head Attention**. È addestrata su dati storici per fornire soluzioni istantanee.

- **QUANDO USARE**: Per decisioni in tempo reale, analisi di conflitti correnti e performance massime.
- **ENDPOINT**: `POST /api/v1/optimize`
- **IMPLEMENTAZIONE**: Chiama il metodo `model(network_tensor, train_tensor)` in `api/server.py`.
- **REQUISITO**: Il modello deve essere caricato con successo (controlla `/api/v1/health` -> `model_loaded: true`).
- **VELOCITÀ**: < 100ms.

## 2. Algoritmo Genetico (IL SOLUTORE DI COMPILAZIONE)
È un approccio euristico basato sulla simulazione temporale. Non è "intelligenza artificiale" nel senso di Deep Learning, ma un solutore di forza bruta intelligente.

- **QUANDO USARE**: Per la pianificazione a lungo termine (scheduling futuro), quando servono rotte complete station-to-station (route planning) o come fallback.
- **ENDPOINT**: `POST /api/v1/optimize_scheduled`
- **IMPLEMENTAZIONE**: Utilizza la classe `ConflictResolver` in `python/scheduling/conflict_resolver.py`.
- **REQUISITO**: Necessita di `tracks` e `stations` dettagliati nel payload.
- **VELOCITÀ**: > 1000ms (dipende dalle iterazioni).

---

### ⚠️ REGOLE D'ORO PER L'AGENTE
1. Se l'utente chiede: **"Usa l'AI"** o **"Ottimizza con la rete neurale"**, devi usare `/api/v1/optimize`.
2. Se l'utente chiede: **"Pianifica il viaggio"** o **"Risolvi conflitti futuri sulla linea"**, devi usare `/api/v1/optimize_scheduled`.
3. In caso di errore `Model not loaded`, significa che la Rete Neurale non è disponibile. NON fingere che il GA sia l'AI; spiega all'utente che il modello non è stato trovato (controlla `api/models/`).
4. **ATTENZIONE**: La Rete Neurale richiede che i dati siano codificati in tensori (normalization). L'Algoritmo Genetico lavora direttamente su dati JSON.
