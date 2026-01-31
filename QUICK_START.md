# 🚀 RailwayAI - Quick Start Guide

## Avvio Rapido (5 minuti)

### 1. Avvia il Server
```bash
cd /Users/michelebigi/RailwayAI
docker-compose up -d
```

### 2. Verifica che funzioni
```bash
curl http://localhost:8002/api/v1/health
```

Dovresti vedere:
```json
{"status": "healthy", "model_loaded": true}
```

### 3. Ottieni un Token di Autenticazione
```bash
curl -X POST http://localhost:8002/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "railway2024"}'
```

Salva il `token` dalla risposta.

### 4. Richiedi una Proposta di Orari

Crea un file `test_proposal.json`:
```json
{
  "stations": [
    {"id": 1, "name": "Milano", "num_platforms": 12},
    {"id": 2, "name": "Bologna", "num_platforms": 8},
    {"id": 3, "name": "Firenze", "num_platforms": 10}
  ],
  "tracks": [
    {"id": 10, "station_ids": [1, 2], "length_km": 218, "is_single_track": false, "capacity": 2},
    {"id": 20, "station_ids": [2, 3], "length_km": 80, "is_single_track": false, "capacity": 2}
  ],
  "target_lines": 3
}
```

Invia la richiesta:
```bash
curl -X POST http://localhost:8002/api/v1/propose_schedule \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d @test_proposal.json
```

### 5. Risultato Atteso

Riceverai una proposta con linee ottimizzate:
```json
{
  "success": true,
  "proposal": {
    "proposed_lines": [
      {
        "id": "L1",
        "origin": 1,
        "destination": 3,
        "stops": [1, 2, 3],
        "frequency": "Every 60 min"
      }
    ]
  }
}
```

---

## Utilizzo nell'App Swift

### Setup Iniziale

1. Apri `AppConfig.swift`
2. Verifica che l'URL sia corretto:
   - **Simulatore iOS**: `http://localhost:8002`
   - **iPhone fisico**: `http://192.168.1.X:8002` (IP del tuo Mac)

### Esempio Completo

```swift
import Foundation

// 1. Login
AuthenticationManager.shared.login(username: "admin", password: "railway2024") { result in
    guard case .success = result else {
        print("❌ Login fallito")
        return
    }
    
    // 2. Carica la rete
    let graph = RailwayGraphManager.shared
    // ... carica stations e tracks ...
    
    // 3. Richiedi proposta
    ScheduleProposer.shared.requestProposal(using: graph, targetLines: 5) { result in
        switch result {
        case .success(let response):
            print("✅ Ricevute \(response.proposal.proposedLines.count) linee!")
            
            for line in response.proposal.proposedLines {
                print("Linea \(line.id):")
                print("  Da: \(line.originId) a \(line.destinationId)")
                print("  Fermate: \(line.stops)")
                print("  Frequenza: \(line.frequency)")
            }
            
        case .failure(let error):
            print("❌ Errore: \(error)")
        }
    }
}
```

---

## Test di Robustezza

Verifica che il sistema risolva correttamente i conflitti:

```bash
cd /Users/michelebigi/RailwayAI
python3 tests/verify_conflict_resolver.py
```

Output atteso:
```
INFO:__main__:FINAL RESULT: SUCCESS! All conflicts resolved and verified.
```

---

## Troubleshooting Rapido

| Problema | Soluzione |
|----------|-----------|
| "Connection refused" | `docker-compose up -d` |
| "401 Unauthorized" | Rifare il login e ottenere un nuovo token |
| Server lento | Riduci `target_lines` a 3 invece di 5 |
| iPhone non si connette | Usa l'IP del Mac invece di `localhost` |

---

## Prossimi Passi

📖 Leggi la guida completa: `GUIDA_UTILIZZO_AI.md`

🧪 Esplora gli esempi: `tests/verify_conflict_resolver.py`

🚀 Contribuisci: https://github.com/manvalan/RailwayAI
