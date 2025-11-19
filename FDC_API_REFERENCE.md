# FDC Integration API - Quick Reference

## 🎯 Scopo

API REST per integrazione con sistemi esterni (FDC, etc.) che fornisce **modifiche dettagliate e actionable** invece di ritardi generici.

## 🚀 Avvio Rapido

```bash
# 1. Avvia server (porta 8002)
python api/fdc_integration_api.py

# 2. Test API
python api/test_fdc_integration_client.py

# 3. Documentazione interattiva
open http://localhost:8002/docs
```

## 📊 Endpoints

### 1. POST /api/v2/optimize

**Ottimizzazione completa con analisi conflitti.**

**Input**:
```json
{
  "conflicts": [
    {
      "conflict_type": "platform_conflict|timing_conflict|speed_conflict|capacity_conflict",
      "location": "STATION_ID",
      "trains": [
        {
          "train_id": "IC101",
          "arrival": "2025-11-19T08:08:00",
          "departure": "2025-11-19T08:10:00",
          "platform": 1,
          "current_speed_kmh": 140.0,
          "priority": 8
        }
      ],
      "severity": "low|medium|high",
      "time_overlap_seconds": 60
    }
  ],
  "network": {
    "stations": ["STATION_A", "STATION_B"],
    "available_platforms": {
      "STATION_A": [1, 2, 3]
    },
    "max_speeds": {
      "SECTION_ID": 140.0
    }
  },
  "preferences": {
    "minimize_delays": true,
    "prefer_platform_changes": true
  }
}
```

**Output**:
```json
{
  "success": true,
  "optimization_type": "multi_train_coordination",
  "total_impact_minutes": 0.0,
  "ml_confidence": 0.96,
  "modifications": [
    {
      "train_id": "IC101",
      "modification_type": "platform_change",
      "section": {
        "station": "STATION_A"
      },
      "parameters": {
        "new_platform": 2,
        "original_platform": 1
      },
      "impact": {
        "time_increase_seconds": 0,
        "affected_stations": ["STATION_A"],
        "passenger_impact_score": 0.1
      },
      "reason": "Risolve conflitto binario",
      "confidence": 0.95
    }
  ],
  "conflict_analysis": {
    "original_conflicts": [
      {
        "type": "platform_conflict",
        "location": "STATION_A",
        "trains": ["IC101", "R203"],
        "severity": "high",
        "time_overlap_seconds": 60
      }
    ],
    "resolved_conflicts": 1,
    "remaining_conflicts": 0,
    "unresolved_conflicts": []
  },
  "alternatives": [
    {
      "description": "Ritarda IC101 di 2 minuti",
      "total_impact_minutes": 2.0,
      "confidence": 0.80,
      "modifications": [...]
    }
  ]
}
```

### 2. POST /api/v2/optimize/simple

**Endpoint minimale backward-compatible.**

**Input**:
```json
{
  "train_id": "IC101",
  "origin_station": "MILANO_CENTRALE",
  "delay_seconds": 180,
  "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
  "reason": "Ritardo per evitare conflitto",
  "confidence": 0.85
}
```

**Output**:
```json
{
  "success": true,
  "total_impact_minutes": 3.0,
  "ml_confidence": 0.85,
  "modifications": [
    {
      "train_id": "IC101",
      "modification_type": "departure_delay",
      "section": {"station": "MILANO_CENTRALE"},
      "parameters": {"delay_seconds": 180},
      "impact": {
        "time_increase_seconds": 180,
        "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"]
      }
    }
  ]
}
```

### 3. POST /api/v2/validate

**Validazione pre-flight di modifiche.**

**Input**:
```json
{
  "modifications": [
    {
      "train_id": "IC101",
      "modification_type": "platform_change",
      "section": {"station": "MONZA"},
      "parameters": {"new_platform": 2, "original_platform": 1},
      "impact": {
        "time_increase_seconds": 0,
        "affected_stations": ["MONZA"]
      }
    }
  ]
}
```

**Output (successo)**:
```json
{
  "valid": true,
  "message": "Tutte le 1 modifiche sono valide"
}
```

**Output (errore)**:
```json
{
  "valid": false,
  "errors": [
    {
      "modification_index": 1,
      "train_id": "R203",
      "error": "Campi mancanti: section, parameters, impact"
    }
  ]
}
```

### 4. GET /api/v2/modification-types

**Lista tipi modifiche supportate.**

**Output**:
```json
{
  "modification_types": [
    {
      "type": "speed_reduction",
      "description": "Riduce velocità su una tratta"
    },
    {
      "type": "platform_change",
      "description": "Cambia binario in stazione"
    },
    ...
  ]
}
```

### 5. GET /api/v2/health

**Health check.**

**Output**:
```json
{
  "status": "healthy",
  "service": "railwayai-fdc-integration",
  "timestamp": "2025-11-19T10:30:00"
}
```

## 🎨 Tipi di Modifica

### 1. speed_reduction / speed_increase

Cambia velocità su una tratta specifica.

**Parameters**:
```json
{
  "new_speed_kmh": 100.0,
  "original_speed_kmh": 140.0
}
```

**Section**:
```json
{
  "from_station": "MILANO_CENTRALE",
  "to_station": "MONZA"
}
```

### 2. platform_change

Riassegna binario in stazione.

**Parameters**:
```json
{
  "new_platform": 2,
  "original_platform": 1
}
```

**Section**:
```json
{
  "station": "MONZA"
}
```

### 3. dwell_time_increase / dwell_time_decrease

Modifica tempo di sosta.

**Parameters**:
```json
{
  "additional_seconds": 120,
  "original_dwell_seconds": 60
}
```

**Section**:
```json
{
  "station": "COMO"
}
```

### 4. departure_delay / departure_advance

Anticipa/ritarda partenza.

**Parameters**:
```json
{
  "delay_seconds": 180
}
```

**Section**:
```json
{
  "station": "MILANO_CENTRALE"
}
```

### 5. stop_skip

Salta fermata intermedia.

**Parameters**:
```json
{
  "reason": "Recupero ritardo"
}
```

**Section**:
```json
{
  "station": "SESTO_SAN_GIOVANNI"
}
```

### 6. route_change

Cambia percorso completo.

**Parameters**:
```json
{
  "new_route": ["MILANO", "SARONNO", "COMO"],
  "original_route": ["MILANO", "MONZA", "COMO"]
}
```

**Section**:
```json
{
  "from_station": "MILANO_CENTRALE",
  "to_station": "COMO"
}
```

## 💡 Best Practices

### 1. Preferisci Cambio Binario a Ritardi

❌ **Non ottimale**:
```json
{
  "modification_type": "departure_delay",
  "parameters": {"delay_seconds": 180}
}
```

✅ **Ottimale (zero delay!)**:
```json
{
  "modification_type": "platform_change",
  "parameters": {"new_platform": 2, "original_platform": 1}
}
```

### 2. Fornisci Sempre Alternative

```json
{
  "modifications": [...],  // Soluzione principale
  "alternatives": [
    {"description": "Alternativa 1", "confidence": 0.80},
    {"description": "Alternativa 2", "confidence": 0.75}
  ]
}
```

### 3. Traccia Conflitti Risolti

```json
{
  "conflict_analysis": {
    "original_conflicts": 3,
    "resolved_conflicts": 3,
    "remaining_conflicts": 0
  }
}
```

### 4. Specifica Confidence per ML

```json
{
  "ml_confidence": 0.92,  // Confidence globale
  "modifications": [
    {
      "confidence": 0.95  // Confidence per singola modifica
    }
  ]
}
```

## 🧪 Testing

```bash
# Test completo (5 scenari)
python api/test_fdc_integration_client.py

# Output atteso:
# ✅ TEST 1: Platform conflict → 0 min delay
# ✅ TEST 2: Timing conflict → 2 min delay  
# ✅ TEST 3: Simple endpoint → 3 min delay
# ✅ TEST 4: Modification types → 9 types
# ✅ TEST 5: Validation → 1 error detected
```

## 📚 Documentazione Completa

- **Specifiche FDC**: [RAILWAY_AI_INTEGRATION_SPECS.md](RAILWAY_AI_INTEGRATION_SPECS.md)
- **Demo Python**: [examples/fdc_integration_demo.py](examples/fdc_integration_demo.py)
- **Modulo Python**: [python/integration/fdc_integration.py](python/integration/fdc_integration.py)
- **README generale**: [README.md](README.md)

## 🐛 Troubleshooting

### API non parte

```bash
# Verifica dipendenze
pip install fastapi uvicorn pydantic

# Verifica porta libera
lsof -i :8002
```

### Test falliscono

```bash
# Assicurati che API sia in esecuzione
curl http://localhost:8002/api/v2/health

# Reinstalla requests
pip install requests
```

### Errore JSON validation

```bash
# Valida JSON prima di inviarlo
curl -X POST http://localhost:8002/api/v2/validate \
  -H "Content-Type: application/json" \
  -d '{"modifications": [...]}'
```

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/RailwayAI/issues)
- **Email**: your.email@example.com
- **Documentation**: http://localhost:8002/docs (quando API è in esecuzione)
