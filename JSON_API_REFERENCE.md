# 🔌 Railway AI Scheduler - JSON API Reference

## Overview

La libreria Railway AI Scheduler ora include **API JSON native in C++** per facile integrazione con qualsiasi linguaggio o sistema che supporti JSON.

### Vantaggi delle API JSON
- ✅ **Interoperabilità**: Usa da qualsiasi linguaggio (C++, Python, JavaScript, Java, etc.)
- ✅ **Standard**: Formato JSON universalmente supportato
- ✅ **Semplicità**: No binding necessari, solo string I/O
- ✅ **HTTP-Ready**: Perfetto per REST API e microservizi
- ✅ **Type-Safe**: Parsing integrato con validazione

---

## API Methods

### 1. `detect_conflicts_json`

Rileva conflitti tra treni a partire da input JSON.

#### Signature
```cpp
std::string detect_conflicts_json(const std::string& json_input);
```

#### Input JSON Format
```json
{
  "trains": [
    {
      "id": 101,
      "position_km": 15.0,
      "velocity_kmh": 120.0,
      "current_track": 1,
      "destination_station": 3,
      "delay_minutes": 5.0,
      "priority": 8,
      "is_delayed": true
    }
  ]
}
```

**Campi obbligatori per ogni train:**
- `id` (int): Identificatore unico treno
- `position_km` (double): Posizione corrente in km
- `velocity_kmh` (double): Velocità corrente in km/h
- `current_track` (int): ID binario corrente
- `destination_station` (int): ID stazione destinazione
- `delay_minutes` (double): Ritardo attuale in minuti
- `priority` (int): Priorità 1-10 (più alto = più importante)
- `is_delayed` (bool): Se il treno è in ritardo

#### Output JSON Format
```json
{
  "conflicts": [
    {
      "train1_id": 101,
      "train2_id": 102,
      "track_id": 1,
      "estimated_time_min": 12.5,
      "severity": 0.85
    }
  ],
  "total_conflicts": 2,
  "processing_time_ms": 0.053,
  "success": true
}
```

**Campi output:**
- `conflicts`: Array di conflitti rilevati
  - `train1_id`: ID primo treno coinvolto
  - `train2_id`: ID secondo treno coinvolto
  - `track_id`: ID binario dove avviene il conflitto
  - `estimated_time_min`: Tempo stimato fino al conflitto (minuti)
  - `severity`: Gravità del conflitto 0.0-1.0
- `total_conflicts`: Numero totale di conflitti
- `processing_time_ms`: Tempo di elaborazione in millisecondi
- `success`: Se l'operazione è riuscita

#### Esempio C++
```cpp
#include "railway_api.h"

railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();

std::string input = R"({
  "trains": [
    {"id": 1, "position_km": 10.0, "velocity_kmh": 120.0, 
     "current_track": 1, "destination_station": 3, 
     "delay_minutes": 5.0, "priority": 8, "is_delayed": true},
    {"id": 2, "position_km": 12.0, "velocity_kmh": 100.0,
     "current_track": 1, "destination_station": 3,
     "delay_minutes": 0.0, "priority": 5, "is_delayed": false}
  ]
})";

std::string result = scheduler.detect_conflicts_json(input);
std::cout << result << std::endl;
```

#### Esempio Python (via ctypes)
```python
import ctypes
import json

# Carica libreria
lib = ctypes.CDLL('./librailwayai.dylib')
lib.detect_conflicts_json.argtypes = [ctypes.c_char_p]
lib.detect_conflicts_json.restype = ctypes.c_char_p

# Input
input_data = {
    "trains": [
        {"id": 1, "position_km": 10.0, "velocity_kmh": 120.0, 
         "current_track": 1, "destination_station": 3,
         "delay_minutes": 5.0, "priority": 8, "is_delayed": True}
    ]
}

# Chiama API
result_json = lib.detect_conflicts_json(
    json.dumps(input_data).encode('utf-8')
)

# Parse risultato
result = json.loads(result_json.decode('utf-8'))
print(f"Conflitti rilevati: {result['total_conflicts']}")
```

---

### 2. `optimize_json`

Ottimizza lo schedule dei treni per minimizzare ritardi e conflitti.

#### Signature
```cpp
std::string optimize_json(const std::string& json_input);
```

#### Input JSON Format
```json
{
  "trains": [
    {
      "id": 201,
      "position_km": 10.0,
      "velocity_kmh": 120.0,
      "current_track": 1,
      "destination_station": 5,
      "delay_minutes": 15.0,
      "priority": 7,
      "is_delayed": true
    }
  ],
  "max_iterations": 100
}
```

**Campi input:**
- `trains`: Array di treni (stesso formato di `detect_conflicts_json`)
- `max_iterations` (opzionale): Numero massimo iterazioni ottimizzazione (default: 100)

#### Output JSON Format
```json
{
  "resolutions": [
    {
      "train_id": 202,
      "time_adjustment_min": -3.0,
      "new_track": -1,
      "confidence": 0.85
    }
  ],
  "remaining_conflicts": [
    {
      "train1_id": 203,
      "train2_id": 204,
      "track_id": 2,
      "estimated_time_min": 8.0,
      "severity": 0.45
    }
  ],
  "total_delay_minutes": 34.0,
  "optimization_time_ms": 0.003,
  "success": true,
  "error_message": ""
}
```

**Campi output:**
- `resolutions`: Array di azioni proposte
  - `train_id`: ID treno da modificare
  - `time_adjustment_min`: Aggiustamento tempo (negativo = rallenta)
  - `new_track`: Nuovo binario (-1 = nessun cambio)
  - `confidence`: Confidenza della risoluzione 0.0-1.0
- `remaining_conflicts`: Conflitti ancora presenti dopo ottimizzazione
- `total_delay_minutes`: Ritardo totale del sistema dopo ottimizzazione
- `optimization_time_ms`: Tempo di ottimizzazione in millisecondi
- `success`: Se l'ottimizzazione è riuscita
- `error_message`: Messaggio di errore (vuoto se success=true)

#### Esempio C++
```cpp
railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();

std::string input = R"({
  "trains": [
    {"id": 1, "position_km": 10.0, "velocity_kmh": 120.0,
     "current_track": 1, "destination_station": 5,
     "delay_minutes": 15.0, "priority": 7, "is_delayed": true},
    {"id": 2, "position_km": 12.0, "velocity_kmh": 110.0,
     "current_track": 1, "destination_station": 5,
     "delay_minutes": 8.0, "priority": 6, "is_delayed": true}
  ],
  "max_iterations": 100
})";

std::string result = scheduler.optimize_json(input);

// Parse e applica risoluzioni...
```

#### Esempio cURL (REST API)
```bash
curl -X POST http://localhost:8080/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "trains": [
      {
        "id": 1,
        "position_km": 10.0,
        "velocity_kmh": 120.0,
        "current_track": 1,
        "destination_station": 5,
        "delay_minutes": 15.0,
        "priority": 7,
        "is_delayed": true
      }
    ]
  }'
```

---

### 3. `get_statistics_json`

Ottieni statistiche di performance dello scheduler.

#### Signature
```cpp
std::string get_statistics_json() const;
```

#### Output JSON Format
```json
{
  "version": "1.0.0",
  "ml_ready": false,
  "avg_optimization_time_ms": 0.003,
  "total_optimizations": 42
}
```

**Campi output:**
- `version`: Versione della libreria
- `ml_ready`: Se il modello ML è caricato
- `avg_optimization_time_ms`: Tempo medio di ottimizzazione
- `total_optimizations`: Numero totale di ottimizzazioni eseguite

#### Esempio C++
```cpp
railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();

// Esegui alcune ottimizzazioni...

std::string stats = scheduler.get_statistics_json();
std::cout << "Statistics: " << stats << std::endl;
```

---

## Integrazione con Altri Linguaggi

### Node.js (via ffi-napi)

```javascript
const ffi = require('ffi-napi');

const lib = ffi.Library('./librailwayai.dylib', {
  'optimize_json': ['string', ['string']]
});

const input = JSON.stringify({
  trains: [
    {
      id: 1,
      position_km: 10.0,
      velocity_kmh: 120.0,
      current_track: 1,
      destination_station: 5,
      delay_minutes: 15.0,
      priority: 7,
      is_delayed: true
    }
  ]
});

const result = JSON.parse(lib.optimize_json(input));
console.log('Total delay:', result.total_delay_minutes);
```

### Go

```go
package main

/*
#cgo LDFLAGS: -L. -lrailwayai
#include <stdlib.h>
extern char* optimize_json(char* input);
*/
import "C"
import (
    "encoding/json"
    "fmt"
    "unsafe"
)

func main() {
    input := map[string]interface{}{
        "trains": []map[string]interface{}{
            {
                "id": 1,
                "position_km": 10.0,
                "velocity_kmh": 120.0,
                "current_track": 1,
                "destination_station": 5,
                "delay_minutes": 15.0,
                "priority": 7,
                "is_delayed": true,
            },
        },
    }
    
    inputJSON, _ := json.Marshal(input)
    cInput := C.CString(string(inputJSON))
    defer C.free(unsafe.Pointer(cInput))
    
    cResult := C.optimize_json(cInput)
    result := C.GoString(cResult)
    
    var data map[string]interface{}
    json.Unmarshal([]byte(result), &data)
    
    fmt.Printf("Total delay: %.2f minutes\n", 
               data["total_delay_minutes"].(float64))
}
```

### Rust

```rust
use std::ffi::{CString, CStr};
use std::os::raw::c_char;
use serde_json::json;

extern "C" {
    fn optimize_json(input: *const c_char) -> *const c_char;
}

fn main() {
    let input = json!({
        "trains": [
            {
                "id": 1,
                "position_km": 10.0,
                "velocity_kmh": 120.0,
                "current_track": 1,
                "destination_station": 5,
                "delay_minutes": 15.0,
                "priority": 7,
                "is_delayed": true
            }
        ]
    });
    
    let input_str = CString::new(input.to_string()).unwrap();
    
    unsafe {
        let result_ptr = optimize_json(input_str.as_ptr());
        let result_str = CStr::from_ptr(result_ptr).to_str().unwrap();
        let result: serde_json::Value = serde_json::from_str(result_str).unwrap();
        
        println!("Total delay: {} minutes", 
                 result["total_delay_minutes"]);
    }
}
```

---

## Performance

### Benchmarks

| Operazione | Tempo Medio | Note |
|-----------|-------------|------|
| `detect_conflicts_json` | 0.05 ms | 3 treni, 2 conflitti |
| `optimize_json` | 0.003 ms | 4 treni, 2 conflitti |
| `get_statistics_json` | < 0.001 ms | Instant |
| JSON parsing overhead | ~0.02 ms | Dipende dalla dimensione |

**Nota**: I tempi sono per scenario singolo. Per batch processing, usa le API C++ native per performance ottimali.

---

## Error Handling

Tutte le API JSON ritornano sempre un JSON valido, anche in caso di errore:

```json
{
  "success": false,
  "error_message": "Invalid train data: missing required field 'id'",
  "conflicts": [],
  "total_conflicts": 0,
  "processing_time_ms": 0.0
}
```

**Best practices:**
1. Controlla sempre il campo `success`
2. Gestisci `error_message` per debugging
3. Valida l'input JSON prima di chiamare le API
4. Usa try-catch per parsing errori

---

## Compilazione

### Con g++
```bash
g++ -std=c++17 -I/path/to/include your_app.cpp \
    -L/path/to/lib -lrailwayai -o your_app
```

### Con CMake
```cmake
find_library(RAILWAYAI_LIB railwayai HINTS ${CMAKE_SOURCE_DIR}/lib)
target_link_libraries(your_app ${RAILWAYAI_LIB})
target_include_directories(your_app PRIVATE ${CMAKE_SOURCE_DIR}/include)
```

---

## REST API Wrapper (Esempio)

Esempio di server HTTP minimale che espone le API JSON:

```cpp
// Simple HTTP server using cpp-httplib
#include "railway_api.h"
#include "httplib.h"

int main() {
    railway::RailwaySchedulerAPI scheduler;
    scheduler.initialize();
    
    httplib::Server svr;
    
    svr.Post("/api/conflicts", [&](const httplib::Request& req, 
                                     httplib::Response& res) {
        res.set_content(scheduler.detect_conflicts_json(req.body), 
                        "application/json");
    });
    
    svr.Post("/api/optimize", [&](const httplib::Request& req, 
                                    httplib::Response& res) {
        res.set_content(scheduler.optimize_json(req.body), 
                        "application/json");
    });
    
    svr.Get("/api/stats", [&](const httplib::Request&, 
                               httplib::Response& res) {
        res.set_content(scheduler.get_statistics_json(), 
                        "application/json");
    });
    
    svr.listen("0.0.0.0", 8080);
}
```

---

## Esempi Completi

Vedi:
- `examples/external_app/json_api_demo.cpp` - Demo completo C++
- `api/server.py` - REST API Python con FastAPI
- `API_REFERENCE.md` - Documentazione completa API C++

---

**Versione**: 1.1.0  
**Data**: 19 Novembre 2025  
**Repository**: [github.com/manvalan/RailwayAI](https://github.com/manvalan/RailwayAI)
