---
description: Guida all'ottimizzazione AI focalizzata su singola linea e treni di sfondo
---

# Guida all'Integrazione App: Ottimizzazione Selettiva

Questa guida spiega come adattare l'applicazione Swift per utilizzare la nuova funzionalità di "Ottimizzazione Focalizzata", che permette di ottimizzare una specifica linea ignorando il calcolo complesso per gli altri treni (trattati come ostacoli statici).

## 💡 Il Concetto
Invece di chiedere all'AI di ottimizzare 50 treni contemporaneamente (causando crash o lentezza), ora inviamo **tutti** i treni per dare il contesto dell'occupazione dei binari, ma specifichiamo quali sono gli `active_agent_ids` su cui l'AI deve effettivamente lavorare.

## 1. Modifica dei Modelli (Swift)
Assicurati che `AIRequestPayload` nel tuo file `RailwayGraphManager.swift` includa il campo `active_agent_ids`:

```swift
struct AIRequestPayload: Codable {
    let trains: [Train]
    let stations: [Station]
    let tracks: [Track]
    let activeAgentIds: [Int]? // Aggiungi questo
    // ... altri campi
    
    enum CodingKeys: String, CodingKey {
        case trains, stations, tracks
        case activeAgentIds = "active_agent_ids" // Mappa snake_case
        case maxIterations = "max_iterations"
        // ...
    }
}
```

## 2. Selezione della Linea Interessata
Quando l'utente seleziona una linea o un treno nella tua View (es. `LineDetailView`), identifica gli ID dei treni che compongono quella linea:

```swift
// Esempio di logica nel ViewModel
func optimizeCurrentLine() {
    let allTrains = appState.simulator.trains
    
    // Identifica solo i treni della linea "A" (Target)
    let focusIds = allTrains
        .filter { $0.lineName == "Linea A" }
        .map { $0.id }
    
    // Genera il JSON passando i Focus IDs
    if let json = RailwayGraphManager.shared.generateAIRequestJSON(
        for: allTrains, 
        focusAgentIds: focusIds
    ) {
        // Esegui la chiamata POST a /api/v1/optimize
        NetworkManager.shared.sendOptimizationRequest(json: json)
    }
}
```

## 3. Vantaggi per l'App
- **Stabilità**: Il server non va in crash per Out-Of-Memory perché calcola i gradienti solo per pochi agenti.
- **Realismo**: Gli altri treni NON spariscono; l'AI li vede e coordina le precedenze della linea target per evitare collisioni con loro.
- **Velocità**: Risposta dell'AI in pochi secondi invece di minuti.

## 4. Test Rapido (Python/Postman)
Se vuoi testare manualmente prima di toccare il codice Swift, invia un body così:
```json
{
  "trains": [
    {"id": 1, "current_track": 10, ...},
    {"id": 2, "current_track": 15, ...}
  ],
  "active_agent_ids": [1],
  "max_iterations": 100
}
```
*L'AI sposterà il treno 1 per evitare il treno 2, ma non cercherà di ottimizzare l'arrivo del treno 2.*
