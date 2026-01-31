# 🚄 RailwayAI - Guida Completa alle Funzionalità AI

## Indice
1. [Introduzione](#introduzione)
2. [Configurazione Iniziale](#configurazione-iniziale)
3. [Feature 1: Fast Schedule Proposal](#feature-1-fast-schedule-proposal)
4. [Feature 2: Conflict Resolution](#feature-2-conflict-resolution)
5. [Feature 3: HUB Station Management](#feature-3-hub-station-management)
6. [Integrazione Swift App](#integrazione-swift-app)
7. [Troubleshooting](#troubleshooting)

---

## Introduzione

RailwayAI è un sistema di intelligenza artificiale per la gestione e ottimizzazione delle reti ferroviarie. Il sistema è composto da:

- **Backend Python** (API REST) - Esegue gli algoritmi AI
- **Frontend Swift** (iOS App) - Interfaccia utente per visualizzazione e controllo
- **Database SQLite** - Gestione utenti e configurazioni

---

## Configurazione Iniziale

### 1. Avvio del Server

**Con Docker (Consigliato)**:
```bash
cd /Users/michelebigi/RailwayAI
docker-compose up -d
```

Il server sarà disponibile su: `http://localhost:8002`

**Verifica dello stato**:
```bash
curl http://localhost:8002/api/v1/health
```

Risposta attesa:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "version": "1.0"
}
```

### 2. Autenticazione

Prima di utilizzare le API, è necessario autenticarsi.

**Login con username/password**:
```bash
curl -X POST http://localhost:8002/api/v1/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "railway2024"
  }'
```

Risposta:
```json
{
  "success": true,
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "username": "admin",
    "role": "admin"
  }
}
```

**Utilizzo del Token**:
Nelle richieste successive, includi l'header:
```
Authorization: Bearer <token>
```

---

## Feature 1: Fast Schedule Proposal

### Descrizione
Genera automaticamente una proposta di linee ferroviarie ottimizzate in meno di 1 secondo, analizzando la topologia della rete.

### Endpoint
```
POST /api/v1/propose_schedule
```

### Parametri di Input

```json
{
  "stations": [
    {
      "id": 1,
      "name": "Milano Centrale",
      "num_platforms": 24,
      "lat": 45.4842,
      "lon": 9.2041,
      "parent_hub_id": null
    },
    {
      "id": 2,
      "name": "Bologna Centrale",
      "num_platforms": 16,
      "lat": 44.5075,
      "lon": 11.3425,
      "parent_hub_id": null
    }
  ],
  "tracks": [
    {
      "id": 10,
      "station_ids": [1, 2],
      "length_km": 218.5,
      "is_single_track": false,
      "capacity": 2
    }
  ],
  "target_lines": 5
}
```

### Risposta

```json
{
  "success": true,
  "proposal": {
    "proposed_lines": [
      {
        "id": "L1",
        "origin": 1,
        "destination": 2,
        "stops": [1, 2],
        "frequency": "Every 60 min",
        "first_departure_minute": 0
      }
    ],
    "schedule_preview": [
      {
        "line": "L1",
        "departure": "00:00:00",
        "origin": 1,
        "destination": 2,
        "stops": [1, 2]
      }
    ]
  },
  "meta": {
    "execution_speed": "0.23s"
  }
}
```

### Cosa fa l'AI

1. **Analizza la topologia**: Identifica stazioni "hub" (con molte connessioni) e stazioni "terminali" (capolinea)
2. **Calcola percorsi ottimali**: Usa BFS per trovare tutti i percorsi validi
3. **Ottimizza con Algoritmo Genetico**:
   - Massimizza la copertura della rete
   - Premia gli interscambi (linee che si incrociano)
   - Suggerisce frequenze realistiche (30, 60, 120 minuti)
4. **Restituisce stazioni intermedie**: Ogni linea include tutte le fermate del percorso

### Esempio Pratico (Swift)

```swift
import Foundation

// 1. Ottieni il grafo dalla tua app
let graph = RailwayGraphManager.shared

// 2. Richiedi la proposta
ScheduleProposer.shared.requestProposal(using: graph, targetLines: 5) { result in
    switch result {
    case .success(let response):
        print("✅ Ricevute \(response.proposal.proposedLines.count) linee!")
        
        for line in response.proposal.proposedLines {
            print("Linea \(line.id): da stazione \(line.originId) a \(line.destinationId)")
            print("  Fermate: \(line.stops)")
            print("  Frequenza: \(line.frequency)")
        }
        
    case .failure(let error):
        print("❌ Errore: \(error.localizedDescription)")
    }
}
```

---

## Feature 2: Conflict Resolution

### Descrizione
Risolve automaticamente i conflitti tra treni (es: due treni sullo stesso binario unico) calcolando ritardi minimi necessari.

### Endpoint
```
POST /api/v1/optimize
```

### Parametri di Input

```json
{
  "trains": [
    {
      "id": 1,
      "origin_station": 1,
      "destination_station": 3,
      "scheduled_departure_time": "08:00:00",
      "velocity_kmh": 120.0,
      "planned_route": [10, 20],
      "priority": 5
    },
    {
      "id": 2,
      "origin_station": 3,
      "destination_station": 1,
      "scheduled_departure_time": "08:10:00",
      "velocity_kmh": 120.0,
      "planned_route": [20, 10],
      "priority": 5
    }
  ],
  "stations": [...],
  "tracks": [
    {
      "id": 20,
      "station_ids": [2, 3],
      "length_km": 10.0,
      "is_single_track": true,
      "capacity": 1
    }
  ],
  "max_iterations": 100,
  "ga_max_iterations": 300,
  "ga_population_size": 100
}
```

### Risposta

```json
{
  "success": true,
  "resolutions": [
    {
      "train_id": 2,
      "time_adjustment_min": 15.5,
      "dwell_delays": [0.0],
      "confidence": 1.0
    }
  ],
  "conflicts_resolved": 10,
  "total_delay": 15.5,
  "iterations": 87,
  "fitness": -15.0
}
```

### Cosa fa l'AI

1. **Simulazione Temporale**: Proietta la posizione di ogni treno nei prossimi 60-120 minuti
2. **Rilevamento Conflitti**: Identifica quando due treni si trovano sullo stesso binario
3. **Algoritmo Genetico**:
   - Genera migliaia di soluzioni (combinazioni di ritardi)
   - Valuta ogni soluzione con una funzione di fitness
   - Evolve verso la soluzione ottimale (zero conflitti, minimo ritardo)
4. **Validazione**: Verifica che la soluzione proposta elimini effettivamente tutti i conflitti

### Test di Robustezza

Puoi verificare il funzionamento con il test incluso:

```bash
cd /Users/michelebigi/RailwayAI
python3 tests/verify_conflict_resolver.py
```

Output atteso:
```
INFO:__main__:--- Phase 1: Verify Initial Conflict ---
INFO:__main__:SUCCESS: Detected 10 initial conflicts.
INFO:__main__:--- Phase 2: Resolve Conflict ---
INFO:__main__:Resolution Result: 10 conflicts resolved.
INFO:__main__:--- Phase 3: Verify Resolution Robustness ---
INFO:__main__:FINAL RESULT: SUCCESS! All conflicts resolved and verified.
```

---

## Feature 3: HUB Station Management

### Descrizione
Gestisce le stazioni come HUB logici per rappresentare complessi ferroviari multi-stazione (es. Milano Centrale tradizionale + Milano Centrale AV). Il sistema permette di:
- Collegare logicamente stazioni fisicamente vicine
- Visualizzarle come un unico punto di interscambio sulla mappa
- Comunicare questa informazione all'AI per ottimizzazioni intelligenti

### Campo `parent_hub_id`

Ogni stazione può avere un campo opzionale `parent_hub_id`:

```json
{
  "id": 12,
  "name": "Milano Centrale AV",
  "num_platforms": 4,
  "parent_hub_id": 5
}
```

**Significato**:
- Se `parent_hub_id` è `null` → Stazione indipendente
- Se `parent_hub_id` è `5` → Questa stazione è collegata all'HUB con stazione principale ID 5

### Implementazione Swift (v1.0 - 2026-01-29)

#### 1. Modello Dati

Nel file `Models.swift`, il campo `parentHubId` è stato aggiunto al modello `Node`:

```swift
struct Node: Identifiable, Codable {
    var id: String
    var name: String
    var parentHubId: String?  // ID della stazione principale dell'HUB
    
    // Visual defaults prioritize HUB status
    var defaultVisualType: StationVisualType {
        if parentHubId != nil { return .filledSquare }  // HUB = quadrato
        // ... altri casi
    }
    
    var defaultColor: String {
        if parentHubId != nil { return "#FF3B30" }  // HUB = rosso
        // ... altri casi
    }
}
```

#### 2. UI di Configurazione

In `StationEditView.swift`, è disponibile un picker per collegare stazioni:

```swift
Section("Hub e Interscambi") {
    Picker("Appartiene a HUB", selection: $station.parentHubId) {
        Text("Nessun HUB (Indipendente)").tag(String?.none)
        Divider()
        ForEach(availableHubs) { node in
            Text(node.name).tag(String?.some(node.id))
        }
    }
    .onChange(of: station.parentHubId) { newHubId in
        // Auto-apply visual style
        station.visualType = station.defaultVisualType
        station.customColor = station.defaultColor
        
        // Auto-position near parent hub
        if let hubId = newHubId,
           let parentHub = network.nodes.first(where: { $0.id == hubId }) {
            station.latitude = parentHub.latitude - 0.01
            station.longitude = parentHub.longitude - 0.01
        }
    }
}
```

#### 3. Visualizzazione sulla Mappa

**Offset Visivo Fisso**: Le stazioni collegate a un HUB vengono visualizzate con un offset di **30 pixel** in basso a sinistra rispetto alla stazione principale. Questo offset è **sempre visibile** indipendentemente dal livello di zoom.

```swift
// In RailwayMapView.swift
private func finalPosition(for node: Node, in size: CGSize, bounds: MapBounds) -> CGPoint {
    let basePosition = schematicPoint(for: node, in: size, bounds: bounds)
    
    if node.parentHubId != nil {
        // Offset fisso di 30px (bottom-left)
        return CGPoint(x: basePosition.x - 30, y: basePosition.y + 30)
    }
    return basePosition
}
```

**Nome Nascosto**: Solo la stazione principale mostra il nome, evitando ridondanza visiva:

```swift
.overlay(alignment: .top) {
    if node.parentHubId == nil {  // Solo se NON è parte di un HUB
        Text(node.name)
            .font(.system(size: 14, weight: .black))
            // ...
    }
}
```

#### 4. Movimento Sincronizzato

Quando trascini una stazione dell'HUB, l'altra si muove automaticamente:

```swift
.onChanged { val in
    // Move this node
    node.latitude = (node.latitude ?? 0) + dLat
    node.longitude = (node.longitude ?? 0) + dLon
    
    // Also move linked hub stations
    if let parentHubId = node.parentHubId {
        // This is a child, move the parent too
        network.nodes[parentIndex].latitude += dLat
        network.nodes[parentIndex].longitude += dLon
    } else {
        // This is a parent, move all children
        for i in network.nodes.indices {
            if network.nodes[i].parentHubId == node.id {
                network.nodes[i].latitude += dLat
                network.nodes[i].longitude += dLon
            }
        }
    }
}
```

#### 5. Comunicazione AI

In `RailwayGraphManager.swift`, il campo viene mappato correttamente per l'AI:

```swift
let stations: [AGStation] = network.nodes.compactMap { node in
    guard let id = stationMapping[node.id] else { return nil }
    
    var hubId: Int? = nil
    if let pid = node.parentHubId {
        hubId = stationMapping[pid]  // Converti String → Int
    }
    
    return AGStation(
        id: id,
        name: node.name,
        lat: node.latitude,
        lon: node.longitude,
        num_platforms: node.platforms ?? 2,
        parent_hub_id: hubId  // ← Inviato all'AI
    )
}
```

### Utilizzo

**Identificazione HUB**:
Gli algoritmi AI riconoscono automaticamente gli HUB e:
- Danno priorità ai treni che passano per questi nodi
- Premiano le soluzioni che massimizzano gli interscambi negli HUB
- Permettono visualizzazioni speciali nell'app Swift

**Importante**: 
Le reti AV e Regionali rimangono **fisicamente separate**. Il campo serve solo per identificazione logica, non crea collegamenti automatici tra reti diverse.

### Esempio Pratico

1. **Crea due stazioni**:
   - "Milano Centrale" (ID: `station-1`)
   - "Milano Centrale AV" (ID: `station-2`)

2. **Collega la stazione AV all'HUB**:
   - Seleziona "Milano Centrale AV"
   - Nell'ispettore, scegli "Milano Centrale" dal picker "Appartiene a HUB"
   - La stazione AV si posiziona automaticamente in basso a sinistra

3. **Risultato sulla mappa**:
   ```
   ┌─────────────────┐
   │ Milano Centrale │  ← Stazione principale (mostra nome)
   └─────────────────┘
         
         🟥  ← Stazione AV (solo simbolo, 30px offset)
   ```

4. **Nel JSON inviato all'AI**:
   ```json
   {
     "stations": [
       {
         "id": 1,
         "name": "Milano Centrale",
         "parent_hub_id": null
       },
       {
         "id": 2,
         "name": "Milano Centrale AV",
         "parent_hub_id": 1
       }
     ]
   }
   ```


---

## Integrazione Swift App

### 1. Configurazione URL

Nel file `AppConfig.swift`:

```swift
public struct AppConfig {
    static let currentEnvironment: Environment = .local
    
    public enum Environment {
        case local
        case production
        
        var baseURL: String {
            switch self {
            case .local:
                return "http://localhost:8002"
            case .production:
                return "https://your-server.com"
            }
        }
    }
    
    public static var apiBaseURL: String {
        return currentEnvironment.baseURL
    }
}
```

**Nota**: Se usi un iPhone fisico, cambia `localhost` con l'IP del tuo Mac (es. `http://192.168.1.15:8002`).

### 2. Autenticazione

```swift
// Login
AuthenticationManager.shared.login(username: "admin", password: "railway2024") { result in
    switch result {
    case .success(let response):
        print("✅ Login riuscito! Token salvato automaticamente")
    case .failure(let error):
        print("❌ Errore login: \(error)")
    }
}

// Le richieste successive includeranno automaticamente il token
```

### 3. Richiesta Proposta Orari

```swift
let graph = RailwayGraphManager.shared

ScheduleProposer.shared.requestProposal(using: graph, targetLines: 5) { result in
    switch result {
    case .success(let response):
        // Usa response.proposal.proposedLines per aggiornare la UI
        updateScheduleView(with: response.proposal)
        
    case .failure(let error):
        showError(error)
    }
}
```

---

## Troubleshooting

### Problema: "Connection refused"

**Causa**: Il server non è in esecuzione.

**Soluzione**:
```bash
docker-compose up -d
# Verifica
curl http://localhost:8002/api/v1/health
```

### Problema: "401 Unauthorized"

**Causa**: Token mancante o scaduto.

**Soluzione**:
1. Effettua nuovamente il login
2. Verifica che `AuthenticationManager.shared` sia usato correttamente (singleton)

### Problema: "No conflicts detected" ma ci sono conflitti evidenti

**Causa**: I treni potrebbero non avere `planned_route` definito.

**Soluzione**:
Assicurati che ogni treno abbia:
```json
{
  "id": 1,
  "planned_route": [10, 20, 30],  // Array di Track IDs
  "scheduled_departure_time": "08:00:00"
}
```

### Problema: "Execution too slow"

**Causa**: Rete troppo grande per l'algoritmo genetico.

**Soluzione**:
Riduci i parametri:
```json
{
  "ga_max_iterations": 100,  // invece di 300
  "ga_population_size": 50   // invece di 100
}
```

---

## Contatti e Supporto

Per problemi tecnici o domande:
- **Repository**: https://github.com/manvalan/RailwayAI
- **Issues**: Apri una issue su GitHub
- **Logs**: Controlla i log del container Docker con `docker logs railwayai`

---

## Changelog

### v1.0 (2026-01-29)
- ✅ Fast Schedule Proposal con stazioni intermedie
- ✅ Conflict Resolver robusto (testato)
- ✅ HUB Station identification con `parent_hub_id`
- ✅ Interchange awareness negli algoritmi genetici
- ✅ Test suite per validazione conflitti
