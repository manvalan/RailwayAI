# Railway AI API Extension - Quick Start Guide

## 🎯 Nuove Funzionalità

L'API ora supporta:
- ✅ **Route Planning automatico** tra stazioni
- ✅ **Simulazione temporale** per prevedere conflitti futuri
- ✅ **Orari di partenza programmati**
- ✅ **Rilevamento conflitti su binari unici**

## 📡 Nuovo Endpoint

### `POST /api/v1/optimize_scheduled`

Ottimizza treni con partenze programmate e direzioni opposte.

**Request:**
```json
{
  "trains": [
    {
      "id": 0,
      "origin_station": 11,
      "destination_station": 1,
      "scheduled_departure_time": "12:00:00",
      "velocity_kmh": 160,
      "priority": 5,
      "position_km": 0,
      "current_track": 18
    }
  ],
  "tracks": [...],
  "stations": [...],
  "max_iterations": 60
}
```

**Response:**
```json
{
  "success": true,
  "conflicts_detected": 5,
  "conflicts_resolved": 2,
  "total_delay_minutes": 25.0,
  "resolutions": [
    {
      "train_id": 1,
      "time_adjustment_min": 25.0,
      "track_assignment": 65,
      "confidence": 0.85
    }
  ]
}
```

## 🚀 Come Usarlo

### 1. Avvia il Server

```bash
cd /Users/michelebigi/RailwayAI
python3 api/server.py
```

### 2. Ottieni il Token

```bash
curl -X POST "http://localhost:8002/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin"
```

### 3. Testa con lo Scenario Bywater-Nobottle

```bash
python3 test_scheduled_optimization.py
```

## 📊 Scenario di Test

**Treno 1:** Bywater (11) → Nobottle (1) @ 12:00  
**Treno 2:** Nobottle (1) → Bywater (11) @ 12:00

**Conflitto atteso:** Collisione frontale su binario unico tra Little Delvings e Withwell

**Risoluzione attesa:** Uno dei due treni viene ritardato di ~15-20 minuti per permettere l'incrocio in una stazione con doppio binario.

## 🔧 Nuovi Campi Train Model

```python
origin_station: Optional[int]              # Stazione di partenza
scheduled_departure_time: Optional[str]    # Orario partenza (HH:MM:SS)
planned_route: Optional[List[int]]         # Percorso pianificato (track IDs)
current_route_index: int                   # Posizione nel percorso
```

## 📝 Note

- Il route planning è **automatico** se fornisci `origin_station` e `destination_station`
- La simulazione temporale usa `max_iterations` come orizzonte temporale (in minuti)
- I conflitti vengono rilevati **prima** che accadano
- Le risoluzioni includono ritardi ottimali per evitare collisioni
