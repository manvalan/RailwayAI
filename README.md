# Railway AI Scheduler 🚂🤖

**Versione 2.0.0** - Production Ready (20 Novembre 2025)

Sistema di scheduling ferroviario intelligente basato su rete neurale con interfaccia C++ ad alte prestazioni.

[![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)](https://github.com/manvalan/RailwayAI)
[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)]()
[![C++](https://img.shields.io/badge/C++-17-blue.svg)]()
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)]()

## 📋 Panoramica

Railway AI Scheduler è un sistema avanzato per l'ottimizzazione degli orari ferroviari che combina:
- **Machine Learning con PyTorch**: Rete neurale addestrata per risolvere conflitti complessi (62.3% migliore del C++)
- **Execution Engine C++17**: Algoritmi ottimizzati per elaborazione in tempo reale
- **Real-Time Optimization**: Tracking GPS e predizione conflitti con 77% confidence
- **Energy Optimization**: 70-80% risparmio energetico con speed optimization
- **Python Bindings**: API completa via pybind11 v2.11.1
- **🌍 Dataset Multi-Paese Europeo**: Training su 7 nazioni (Italia, Francia, Germania, Svizzera, Paesi Bassi, Austria, Spagna)

### 🔧 Modalità di Utilizzo

Railway AI Scheduler può essere integrato in **3 modalità**:

1. **📚 Libreria C++ Statica/Dinamica** ([Guida](LIBRARY_USAGE.md))
   - Integrazione diretta nel tuo codice C++
   - Performance massime (< 1ms latency)
   - Zero overhead
   - Librerie: `librailway_scheduler_core.a` (statica), `librailwayai.dylib/.so/.dll` (dinamica)

2. **🐍 Python Bindings**
   - API Pythonica completa via pybind11
   - Type hints, NumPy integration
   - Ideale per data science e ML

3. **🌐 REST API** (FastAPI)
   - HTTP/JSON endpoints
   - Multi-language support
   - Microservices architecture

### 🎯 Caratteristiche Principali

#### Phase 4 - Advanced Features (7/8 completate - 87.5%) ✅

✅ **Python Bindings (Phase 4.1)**
- Interfaccia completa via pybind11 v2.11.1
- API Pythonica con type hints
- 9/9 test suite passing
- Integrazione con data science tools

✅ **Performance Profiling (Phase 4.2)**
- Profiler ad alta risoluzione (microsecondi)
- Suite benchmark completa
- Metriche dettagliate per network, pathfinding, conflict resolution

✅ **Route Rerouting (Phase 4.3)**
- RouteOptimizer con quality scoring
- Ottimizzazione batch
- Percorsi alternativi automatici
- Tempo medio: ~0.06ms per reroute

✅ **Dynamic Speed Optimization (Phase 4.4)**
- SpeedOptimizer con fisica realistica
- 3 modalità: COMFORT, BALANCED, ECO
- **70-80% riduzione consumo energetico** 🌱
- Fasi di coasting per risparmio energetico
- Modelli di resistenza (rolling, aerodynamic, gradient)

✅ **Real-Time Optimization (Phase 4.6)** 🆕
- RealTimeOptimizer con tracking posizione GPS
- **Predizione conflitti con 77% confidence**
- 5 tipi di schedule adjustments
- 3 modalità: CONSERVATIVE, BALANCED, AGGRESSIVE
- Sistema callback per eventi real-time

✅ **API Security & Monitoring (Phase 4.7)** 🆕
- **JWT Authentication**: Protezione degli endpoint con token sicuri.
- **WebSocket Monitoring**: Streaming live dello stato della rete e log.
- **Thread-Safety**: Core C++ protetto da mutex per uso concorrente.
- **LibTorch Inference**: Esecuzione modelli AI direttamente in C++.

#### Core Features

✅ **Rilevamento conflitti in tempo reale**
- Collisioni frontali su binari singoli
- Sorpassi pericolosi su binari multipli
- Congestione nelle stazioni
- **Predizione proattiva con GPS tracking** 🆕

✅ **Risoluzione intelligente**
- Modello ML addestrato (62.3% migliore del C++ solver)
- Algoritmi euristici come fallback
- Minimizzazione del ritardo totale
- Cambio binario automatico in stazione
- **Zero-delay solutions** via FDC Integration

✅ **Alta performance**
- Small networks (10-50 nodes): < 1ms
- Medium networks (100-500 nodes): < 10ms
- Large networks (1000+ nodes): < 100ms
- Route rerouting: ~0.06ms average

✅ **Multi-language Support**
- Core engine in C++17
- **Python bindings completi** (pybind11)
- API JSON native
- REST API FastAPI
- Integrabile da qualsiasi linguaggio

## 🏗️ Architettura

```
RailwayAI/
├── python/                    # Componenti Python/ML
│   ├── models/               # Reti neurali
│   │   └── scheduler_network.py
│   ├── training/             # Scripts di training
│   │   └── train_model.py
│   ├── data/                 # Generazione dati
│   │   └── data_generator.py
│   ├── data_acquisition/     # 🌍 Acquisizione dati europei
│   │   ├── european_railways.py
│   │   ├── gtfs_cache_manager.py
│   │   └── gtfs_parser.py
│   ├── scheduling/           # 🚂 Ottimizzatori avanzati
│   │   └── opposite_train_optimizer.py  # NEW!
│   └── integration/          # 🏢 Integrazioni sistemi esterni
│       └── fdc_integration.py        # FDC v2.0 format (NEW!)
│
├── cpp/                      # Core C++
│   ├── include/             # Headers
│   │   └── railway_scheduler.h
│   └── src/                 # Implementazione
│       ├── railway_scheduler.cpp
│       └── bindings.cpp     # Bindings pybind11
│
├── api/                      # 📡 REST API Services
│   ├── opposite_train_api.py        # Endpoint treni opposti (NEW!)
│   ├── fdc_integration_api.py       # 🏢 FDC Integration API v2.0 (NEW!)
│   ├── test_opposite_train_client.py
│   └── test_fdc_integration_client.py
│
├── data/                     # Dataset
│   ├── gtfs_cache/          # Cache compresso dati europei
│   └── european/            # Dati GTFS raw (git-ignored)
├── models/                   # Modelli addestrati
├── tests/                    # Test suite
├── examples/                 # Esempi d'uso
│
├── CMakeLists.txt           # Build system
├── requirements.txt         # Dipendenze Python
├── setup.sh                 # Setup automatico
└── README.md
```

## 🚀 Quick Start

### 📦 Prerequisiti

**Obbligatori:**
- Python 3.8+
- CMake >= 3.15
- Compilatore C++17 (GCC 7+, Clang 5+, MSVC 2017+)
- PyTorch 2.0+

**Dipendenze C++ (auto-download via CMake):**
- Boost >= 1.70 (Graph library)
- nlohmann/json v3.11.3
- pugixml v1.14 (RailML support)
- pybind11 v2.11.1 (Python bindings)

**Standalone:** ✅ Zero dipendenze esterne obbligatorie (tutte gestite da CMake)

### 💾 Installazione

```bash
# 1. Clone repository
git clone https://github.com/manvalan/RailwayAI.git
cd RailwayAI

# 2. Build completo con Python bindings
cmake -B build -DFDC_SCHEDULER_BUILD_PYTHON=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)  # Linux/macOS
# cmake --build build -j4        # Windows

# 3. Setup Python environment
python3 -m venv venv
source venv/bin/activate         # Linux/macOS
# venv\Scripts\activate          # Windows

# 4. Installa dipendenze Python
pip install -r requirements.txt

# 5. Test Python bindings
cd build
python3 -c "import fdc_scheduler_py; print('✅ Success!')"
```

```bash
# 1. Compila la libreria
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_LIBTORCH=ON
cmake --build . -j$(nproc)
```

### 🔒 Autenticazione API

L'API ora richiede un token JWT per gli endpoint di ottimizzazione.

1. **Ottieni il token**:
```bash
curl -X POST "http://localhost:8002/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin"
```

2. **Usa il token**:
```bash
curl -X POST "http://localhost:8002/api/v2/optimize" \
     -H "Authorization: Bearer <TUO_TOKEN>" \
     -H "Content-Type: application/json" \
     -d '{"conflicts": [...], "network": {...}}'
```

### 📡 Monitoraggio Live

Puoi monitorare il sistema in tempo reale in due modi:
- **Dashboard Web**: Naviga su `http://localhost:8002/static/monitoring.html`
- **WebSocket**: Connettiti a `ws://localhost:8002/ws/monitoring`

### 🐳 Docker Deployment

Per avviare l'intero stack in un container isolato:

```bash
docker-compose up --build -d
```

L'API sarà disponibile su `http://localhost:8002`.

### 📦 Creazione Release (.tgz)

Per creare un pacchetto di distribuzione pronto per il server di produzione (include l'esportazione automatica dei modelli ML):

```bash
./scripts/package_release.sh
```
make -j$(nproc)

# 2. Le librerie sono pronte in build/:
#    - librailway_scheduler_core.a (statica)
#    - librailwayai.dylib/.so/.dll (dinamica)

# 3. Esempio di compilazione con libreria statica
g++ -std=c++17 my_app.cpp \
    -I../cpp/include \
    -L. -lrailway_scheduler_core \
    -lboost_graph -lpthread \
    -o my_app
```

📚 **Guida completa**: Vedi [LIBRARY_USAGE.md](LIBRARY_USAGE.md) per esempi dettagliati, API reference e integrazione CMake.

### ⚡ Quick Setup (Alternativa)

```bash
# Setup automatico tutto-in-uno
chmod +x setup.sh
./setup.sh

# Attiva ambiente
source venv/bin/activate
```

### Setup Manuale (Alternativa)

```bash
# Crea ambiente virtuale
python3 -m venv venv
source venv/bin/activate

# Installa dipendenze Python
pip install -r requirements.txt
pip install pybind11[global]

# Compila modulo C++
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --config Release
cd ..

# Copia modulo compilato
cp build/python/railway_cpp* python/
```

## 📚 Uso Base

### 1. Acquisizione Dati Reali (Opzionale)

Il sistema può usare **dati reali** da gestori ferroviari italiani:

```bash
# Test API (consigliato per iniziare)
python python/data_acquisition/download_real_data.py --demo

# Scarica orari GTFS da RFI/Trenitalia
python python/data_acquisition/download_real_data.py --gtfs

# Scarica grafo infrastruttura da OpenStreetMap
python python/data_acquisition/download_real_data.py --graph

# Raccoglie dati real-time (ritardi, situazione treni)
python python/data_acquisition/download_real_data.py --realtime --duration 24

# Tutto insieme
python python/data_acquisition/download_real_data.py --all
```

**Fonti dati supportate:**
- 📊 **GTFS**: Orari ufficiali RFI/Trenitalia
- 🗺️ **OpenStreetMap**: Grafo infrastruttura ferroviaria
- ⏱️ **viaggiatreno.it API**: Dati real-time e ritardi

### 2. Scarica Dati Europei Multi-Paese (Nuovo! 🇪🇺)

Il sistema supporta ora dati da **7 paesi europei** per migliorare la generalizzazione:

```bash
# Mostra paesi disponibili
python python/data_acquisition/european_railways.py --list

# Scarica dati GTFS (Francia, Paesi Bassi, etc.)
python python/data_acquisition/european_railways.py \
  --countries france_sncf netherlands_ns switzerland_sbb

# Parsa e genera dataset unificato
python python/data_acquisition/european_data_parser.py

# Output: data/european_training_data.npz
# - 650+ rotte da Francia + Paesi Bassi
# - 87K fermate
# - 5K scenari conflitto
```

**Paesi supportati**: 🇮🇹 Italia, 🇫🇷 Francia, 🇩🇪 Germania, 🇨🇭 Svizzera, 🇳🇱 Paesi Bassi, 🇦🇹 Austria, 🇪🇸 Spagna

📖 **Documentazione completa**: Vedi [EUROPEAN_DATA.md](EUROPEAN_DATA.md)

### 3. Genera Dataset Sintetico (Alternativa Rapida)

Se non hai accesso ai dati reali, usa il generatore sintetico:

```python
from python.data.data_generator import generate_training_dataset

# Genera scenari di rete ferroviaria
generate_training_dataset(
    num_samples=1000,
    output_path="data/training_data.npz"
)
```

### 4. Addestra Rete Neurale

```bash
# Training standard (dati italiani)
python python/training/train_model.py

# Training multi-paese europeo (consigliato per migliore generalizzazione)
python python/training/train_european.py --epochs 50 --batch-size 64

# Output: models/scheduler_european.pth
```

Questo addestrerà il modello e salverà il checkpoint in `models/scheduler_best.pth`.

**Training con dati reali:** Modifica `train_model.py` per puntare ai file `.npz` scaricati:
```python
config = {
    'train_data_path': 'data/gtfs_training_data.npz',  # Dati reali
    # ... resto configurazione
}
```

**Training multi-paese**: Il nuovo `train_european.py` combina automaticamente dati da Italia, UK e nuovi paesi europei con weighted sampling per bilanciare le fonti.

### 4. Usa lo Scheduler C++

```python
import sys
sys.path.insert(0, 'python')
import railway_cpp

# Inizializza scheduler
scheduler = railway_cpp.RailwayScheduler(num_tracks=20, num_stations=10)

# Crea un treno
train = railway_cpp.Train()
train.id = 1
train.current_track = 0
train.position_km = 10.5
train.velocity_kmh = 120.0
train.priority = 8
train.destination_station = 5

# Aggiungi alla rete
scheduler.add_train(train)

# Rileva conflitti
conflicts = scheduler.detect_conflicts()
print(f"Conflitti rilevati: {len(conflicts)}")

# Risolvi conflitti
if conflicts:
    adjustments = scheduler.resolve_conflicts(conflicts)
    scheduler.apply_adjustments(adjustments)
    print(f"Applicati {len(adjustments)} aggiustamenti")

# Ottieni statistiche
stats = scheduler.get_statistics()
print(f"Efficienza rete: {stats.network_efficiency:.2%}")
print(f"Treni in ritardo: {stats.delayed_trains}/{stats.total_trains}")
```

## 🎯 Esempio Completo

```python
import railway_cpp as rc

# Setup rete
scheduler = rc.RailwayScheduler()

# Definisci binari
track1 = rc.Track()
track1.id = 0
track1.length_km = 50.0
track1.is_single_track = True  # Binario singolo!
track1.capacity = 1
track1.station_ids = [0, 1]

track2 = rc.Track()
track2.id = 1
track2.length_km = 30.0
track2.is_single_track = False
track2.capacity = 2
track2.station_ids = [1, 2]

# Definisci stazioni
station1 = rc.Station()
station1.id = 0
station1.name = "Milano Centrale"
station1.num_platforms = 8

station2 = rc.Station()
station2.id = 1
station2.name = "Bologna Centrale"
station2.num_platforms = 6

# Inizializza rete
scheduler.initialize_network(
    tracks=[track1, track2],
    stations=[station1, station2]
)

# Aggiungi treni
train1 = rc.Train()
train1.id = 1
train1.current_track = 0
train1.position_km = 5.0
train1.velocity_kmh = 100.0
train1.priority = 9  # Alta priorità (Intercity)
train1.destination_station = 1

train2 = rc.Train()
train2.id = 2
train2.current_track = 0
train2.position_km = 45.0  # Direzione opposta!
train2.velocity_kmh = 80.0
train2.priority = 5  # Priorità media (Regionale)
train2.destination_station = 0

scheduler.add_train(train1)
scheduler.add_train(train2)

# Simula un passo temporale
print("=== Stato Iniziale ===")
stats = scheduler.get_statistics()
print(f"Treni attivi: {stats.total_trains}")

conflicts = scheduler.detect_conflicts()
print(f"Conflitti: {len(conflicts)}")

if conflicts:
    for conflict in conflicts:
        print(f"  - {conflict}")
    
    # Risolvi
    adjustments = scheduler.resolve_conflicts(conflicts)
    print(f"\n=== Risoluzione ===")
    for adj in adjustments:
        print(f"  - {adj}")
    
    scheduler.apply_adjustments(adjustments)

# Stato finale
print(f"\n=== Stato Finale ===")
final_stats = scheduler.get_statistics()
print(f"Efficienza: {final_stats.network_efficiency:.2%}")
print(f"Conflitti risolti: {len(conflicts)} → {final_stats.active_conflicts}")
```

## 🚄 Cambio Binario Intelligente (NEW!)

Il sistema implementa una **strategia avanzata di cambio binario automatico** per risolvere conflitti in modo efficiente, specialmente nelle stazioni dove più linee convergono.

### Funzionamento

Quando viene rilevato un conflitto tra treni, il sistema:

1. **Verifica prossimità a stazione**: Controlla se il treno è entro 5km da una stazione (10km per binari unici)
2. **Cerca binari alternativi** con criteri intelligenti:
   - ✅ Deve connettere alla destinazione del treno
   - ✅ Deve avere capacità disponibile
   - ✅ Non deve essere congestionato
   - ✅ Preferisce multi-track su single-track
3. **Applica la migliore strategia**:
   - **Strategia 1 (Preferita)**: Cambio binario in stazione
     - Ritardo: 0.5-1.0 min (solo manovra)
     - Confidenza: 85-90%
   - **Strategia 2 (Fallback)**: Ritardo temporale
     - Ritardo: 5-8 min × gravità conflitto
     - Confidenza: 70-75%

### Caso d'Uso Critico: Stazioni Multi-Binario + Linee a Binario Unico

```
Linea A (binario unico) ←--[Treno 1]-- STAZIONE (4 binari) --[Treno 2]--→ Linea B (binario unico)
```

**Problema**: Due treni arrivano da direzioni opposte su linee a binario unico verso la stessa stazione.

**Soluzione Intelligente**:
- Il sistema rileva il conflitto in anticipo (10km threshold)
- Devia uno o entrambi i treni su binari di stazione disponibili
- Minimizza i ritardi (1min vs 8min)
- Previene deadlock su binari unici

### Esempio Demo

```bash
# Esegui demo completa con 3 scenari
python examples/demo_single_track_station.py
```

**Scenari testati:**
1. **Treni da direzioni opposte**: Cambio binario automatico in stazione
2. **Conflitto con priorità diverse**: Gestione intelligente delle priorità
3. **Binario saturo**: Deviazione su binari alternativi

**Risultati tipici:**
```
✓ Conflitto risolto con cambio binario
  Treno: 102
  Ritardo: 0.5 min (manovra cambio binario)
  Nuovo binario: 2 (stazione)
  Confidenza: 90%
  Motivo: Track switch at station to avoid conflict
```

### API per Cambio Binario

```python
import railway_cpp as rc

# Verifica se treno può cambiare binario
can_switch = rc.ConflictResolver.is_near_station(
    train=train,
    track=current_track,
    max_distance_km=5.0
)

# Trova binario alternativo
alternative = rc.ConflictResolver.find_alternative_track(
    train=train,
    current_track_id=current_track_id,
    tracks=all_tracks,
    trains=all_trains
)

if alternative >= 0:
    print(f"Binario alternativo trovato: {alternative}")
```

### Vantaggi

✅ **Ritardi minimi**: 0.5-1min (cambio) vs 5-8min (attesa)  
✅ **Previene deadlock**: Gestione intelligente binari unici bidirezionali  
✅ **Alta efficienza**: Utilizza capacità stazione in modo ottimale  
✅ **Confidenza misurabile**: Score 0.0-1.0 per ogni risoluzione  

## 🎮 Esempi e Demo

Il progetto include demo completi per tutte le feature avanzate:

### Python Bindings Demo
```bash
# API completa Python con pybind11
./build/python_bindings_demo

# Output:
# ✅ Network creation
# ✅ Train management
# ✅ Conflict detection
# ✅ 9/9 tests passing
```

### Performance Benchmark
```bash
# Suite benchmark completa
./build/performance_benchmark

# Metriche:
# - Small networks (10-50 nodes): < 1ms
# - Medium networks (100-500 nodes): < 10ms
# - Large networks (1000+ nodes): < 100ms
```

### Route Rerouting Demo
```bash
# Ottimizzazione percorsi alternativi
./build/reroute_demo

# Features:
# - Quality scoring
# - Batch optimization
# - Avg time: ~0.06ms per reroute
```

### Speed Optimizer Demo 🌱
```bash
# Ottimizzazione energetica avanzata
./build/speed_optimizer_demo

# Risultati:
# - COMFORT mode: 72% energy savings
# - BALANCED mode: 75% energy savings
# - ECO mode: 80% energy savings
# - Coasting phases: automatic
```

### Real-Time Optimization Demo 🆕
```bash
# Tracking GPS e predizione conflitti
./build/realtime_demo

# 5 scenari completi:
# 1. Basic train tracking
# 2. Conflict prediction (77% confidence)
# 3. Preventive adjustments
# 4. Emergency rerouting
# 5. Multi-train coordination
```

### Esempi Python ML
```bash
# Demo rapido ML
python examples/demo_quick.py

# Esempio completo con C++ engine
python examples/example_usage.py

# Test real-world con opposite trains
python examples/test_real_opposite_trains.py

# FDC Integration demo
python examples/fdc_integration_demo.py
```

## 📊 Performance Metrics

### Runtime Performance
| Operazione | Tempo | Note |
|------------|-------|------|
| Small networks (10-50 nodes) | < 1ms | Conflict detection |
| Medium networks (100-500 nodes) | < 10ms | Full optimization |
| Large networks (1000+ nodes) | < 100ms | Complex scenarios |
| Conflict resolution | < 50ms | Per conflict |
| Route rerouting | ~0.06ms | Average |
| ML inference | ~1.5ms | Per scenario |

### Energy Optimization
| Mode | Energy Savings | Use Case |
|------|---------------|----------|
| COMFORT | 70-72% | Passenger comfort priority |
| BALANCED | 75% | Best compromise |
| ECO | 78-80% | Maximum efficiency |

### Real-Time Prediction
- **Conflict prediction accuracy**: 77% confidence
- **GPS tracking frequency**: 1-10 Hz
- **Adjustment latency**: < 100ms
- **Callback response**: Real-time events

## 🧠 Architettura Rete Neurale

### Input
- **Stato Rete**: Configurazione binari e stazioni
- **Stato Treni**: Posizione, velocità, ritardi, priorità
- **Conflitti**: Matrice binaria di conflitti

### Architettura
```
Input Encoders
├── Network Encoder: [tracks + stations] → [256]
└── Train Encoder (LSTM): [num_trains, 8] → [128]

Main Network
├── Multi-head Attention (8 heads)
├── Fully Connected Layers [384 → 512 → 256]
└── Layer Normalization

Output Heads
├── Time Adjustments: [num_trains] (±30 min)
├── Conflict Priorities: [num_trains × num_trains]
└── Track Assignments: [num_trains × num_tracks]
```

### Loss Function
```python
total_loss = time_loss + 2.0 × track_loss + 3.0 × conflict_loss
```

## ⚡ Performance

### Benchmarks Runtime
- **Rilevamento conflitti**: < 1ms per 50 treni
- **Risoluzione ML**: ~1.5ms per scenario (inferenza)
- **Throughput**: > 200 aggiornamenti/sec
- **Memoria**: ~100MB per rete completa

### Risultati Training

#### Modello Real-World (Italian + UK Networks)
Addestrato su 1050 scenari realistici da 7 reti ferroviarie (4 italiane + 3 UK):

**Reti Italiane:**
- Milano-Bologna (219km, 6 stazioni, 120 treni/giorno)
- Roma-Napoli (225km, 4 stazioni, 100 treni/giorno)
- Torino-Milano (143km, 3 stazioni, 90 treni/giorno)
- Firenze-Roma (261km, 4 stazioni, 85 treni/giorno)

**Reti UK:**
- London-Birmingham (160km, 3 stazioni, 150 treni/giorno)
- London-Manchester (320km, 4 stazioni, 110 treni/giorno)
- Edinburgh-Glasgow (75km, 3 stazioni, 200 treni/giorno)

**Prestazioni:**
```
Training: 150 epoche
Best Val Loss: 2.5174 (epoch 40)
Parametri: 1,359,034

Confronto vs C++ Solver:
- ML Model:     189.6 min ritardo medio
- C++ Solver:   502.5 min ritardo medio
- Improvement:  62.3% più efficiente ✅
- Win rate:     50% scenari (10/20)
```

### Ottimizzazioni
- Core C++ per algoritmi critici
- LSTM per sequenze temporali
- Attention mechanism per conflitti
- Batch processing per training
- Supervised learning con target realistici

## 🔧 Configurazione Avanzata

### Training Personalizzato

```python
config = {
    'train_data_path': 'data/training_data.npz',
    'val_data_path': 'data/validation_data.npz',
    
    # Architettura
    'input_dim': 256,
    'hidden_dim': 512,
    'num_trains': 50,
    'num_tracks': 20,
    'num_stations': 10,
    
    # Hyperparameters
    'batch_size': 32,
    'num_epochs': 100,
    'learning_rate': 0.001,
    'weight_decay': 0.0001,
    
    'checkpoint_path': 'models/scheduler_custom.pth',
}

train_model(config)
```

### Abilitare LibTorch (opzionale)

Per inferenza ML direttamente in C++:

```bash
# Scarica LibTorch
wget https://download.pytorch.org/libtorch/cpu/libtorch-cxx11-abi-shared-with-deps-2.0.0%2Bcpu.zip
unzip libtorch-*.zip

# Compila con LibTorch
cmake .. -DUSE_LIBTORCH=ON -DCMAKE_PREFIX_PATH=/path/to/libtorch
cmake --build . --config Release
```

## 🧪 Testing

```bash
# Unit tests Python
pytest tests/

# Unit tests C++ (se compilato con BUILD_TESTS=ON)
cd build
cmake .. -DBUILD_TESTS=ON
cmake --build .
ctest

# Test JSON API
cd examples/external_app
./json_api_demo
```

## 📚 Documentazione

- **[API_REFERENCE.md](API_REFERENCE.md)** - Documentazione completa API C++
- **[JSON_API_REFERENCE.md](JSON_API_REFERENCE.md)** - Guida API JSON (NUOVO!)
- **[TRAINING_RESULTS.md](TRAINING_RESULTS.md)** - Risultati training real-world
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Guida deployment production
- **[STRATEGY.md](STRATEGY.md)** - Strategia di training e architettura
- **[STATUS.md](STATUS.md)** - Stato del progetto

## 📊 Visualizzazione

```python
import matplotlib.pyplot as plt
import json

# Carica training history
with open('models/scheduler_best_history.json', 'r') as f:
    history = json.load(f)

# Plot loss
epochs = [h['epoch'] for h in history]
train_loss = [h['train_loss'] for h in history]
val_loss = [h['val_loss'] for h in history]

plt.figure(figsize=(10, 6))
plt.plot(epochs, train_loss, label='Train Loss')
plt.plot(epochs, val_loss, label='Validation Loss')
plt.xlabel('Epoch')
plt.ylabel('Loss')
plt.legend()
plt.title('Training Progress')
plt.grid(True)
plt.savefig('training_progress.png')
```

## 🤝 Contributing

Contribuzioni benvenute! Per favore:

1. Fork il repository
2. Crea un branch per la feature (`git checkout -b feature/amazing-feature`)
3. Commit i cambiamenti (`git commit -m 'Add amazing feature'`)
4. Push al branch (`git push origin feature/amazing-feature`)
5. Apri una Pull Request

## 🏢 NUOVO: FDC Integration API v2.0

**API di integrazione avanzata** con formato JSON potenziato per sistemi esterni (Ferrovie della Contea, etc.).

### Perché FDC API v2.0?

Le versioni precedenti restituivano solo **ritardi generici** (`delay_minutes`), costringendo i sistemi esterni a "spostare ciecamente tutti i fermate". 

**FDC v2.0** fornisce **modifiche dettagliate e actionable**:
- ✅ **DOVE** applicare le modifiche (stazione, tratta specifica)
- ✅ **COME** risolvere il conflitto (6 tipi: velocità, binario, sosta, partenza, skip, percorso)
- ✅ **PARAMETRI** esatti (quale binario, quale velocità, quale stazione)
- ✅ **IMPATTO** dettagliato (tempo aggiunto, stazioni coinvolte, passeggeri)
- ✅ **ALTERNATIVE** multiple con ranking (2-3 soluzioni per conflitto)
- ✅ **ANALISI CONFLITTI** (originali, risolti, rimasti)

### 🎯 Innovazione Chiave: Zero-Delay Solutions

**Esempio**: Due treni arrivano contemporaneamente allo stesso binario
- ❌ **Vecchio approccio**: Ritarda uno dei due → +3 minuti
- ✅ **FDC v2.0**: Cambia binario al secondo treno → **0 minuti di ritardo!**

### Modifiche Supportate

```
1️⃣ speed_reduction/increase    → Cambia velocità su tratta specifica
2️⃣ platform_change             → Riassegna binario in stazione  
3️⃣ dwell_time_increase/decrease → Modifica tempo di sosta
4️⃣ departure_delay/advance     → Anticipa/ritarda partenza
5️⃣ stop_skip                   → Salta fermata intermedia
6️⃣ route_change                → Cambia percorso completo
```

### Quick Start

```bash
# Avvia API server (porta 8002)
python api/fdc_integration_api.py

# In un altro terminale, test
python api/test_fdc_integration_client.py

# Documentazione interattiva
open http://localhost:8002/docs
```

### Esempio Richiesta

```bash
curl -X POST http://localhost:8002/api/v2/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "conflicts": [{
      "conflict_type": "platform_conflict",
      "location": "MONZA",
      "trains": [
        {"train_id": "IC101", "platform": 1, "priority": 8},
        {"train_id": "R203", "platform": 1, "priority": 5}
      ],
      "severity": "high",
      "time_overlap_seconds": 60
    }],
    "network": {
      "stations": ["MILANO_CENTRALE", "MONZA", "COMO"],
      "available_platforms": {"MONZA": [1, 2, 3]},
      "max_speeds": {"MILANO_MONZA": 140.0}
    }
  }'
```

### Esempio Risposta

```json
{
  "success": true,
  "total_impact_minutes": 0.0,  // ZERO DELAY!
  "ml_confidence": 0.96,
  "modifications": [{
    "train_id": "R203",
    "modification_type": "platform_change",
    "section": {"station": "MONZA"},
    "parameters": {
      "new_platform": 2,
      "original_platform": 1
    },
    "impact": {
      "time_increase_seconds": 0,
      "affected_stations": ["MONZA"],
      "passenger_impact_score": 0.1
    },
    "reason": "Cambio binario risolve conflitto a MONZA",
    "confidence": 0.95
  }],
  "conflict_analysis": {
    "original_conflicts": [{"type": "platform_conflict", ...}],
    "resolved_conflicts": 1,
    "remaining_conflicts": 0
  },
  "alternatives": [
    {"description": "Ritarda R203 di 2 minuti", "confidence": 0.80, ...}
  ]
}
```

### Endpoints

| Endpoint | Descrizione |
|----------|-------------|
| `POST /api/v2/optimize` | Ottimizzazione completa con conflitti multipli |
| `POST /api/v2/optimize/simple` | Formato minimale backward-compatible |
| `GET /api/v2/modification-types` | Lista tipi modifiche supportate |
| `POST /api/v2/validate` | Validazione pre-flight modifiche |
| `GET /api/v2/health` | Health check |
| `GET /docs` | Documentazione interattiva Swagger |

### Integrazione Python

```python
from python.integration.fdc_integration import (
    FDCIntegrationBuilder, ModificationType
)

# Builder pattern per costruire risposte
builder = FDCIntegrationBuilder()
builder.set_ml_confidence(0.95)

# Aggiungi modifica (cambio binario)
builder.add_platform_change(
    train_id="IC101",
    station="MONZA",
    new_platform=2,
    original_platform=1,
    affected_stations=["MONZA"],
    reason="Risolve conflitto",
    confidence=0.96
)

# Traccia conflitto originale
builder.add_conflict(
    conflict_type=ConflictType.PLATFORM_CONFLICT,
    location="MONZA",
    trains=["IC101", "R203"],
    severity="high"
)

# Genera risposta JSON
response = builder.build_success()
print(response.to_dict())
```

📖 **Specifiche complete**: [RAILWAY_AI_INTEGRATION_SPECS.md](RAILWAY_AI_INTEGRATION_SPECS.md)
🎬 **Demo esempi**: `examples/fdc_integration_demo.py`
🧪 **Test suite**: `api/test_fdc_integration_client.py` (5 scenari, tutti passing ✅)

---

## 🚂 Ottimizzatore Treni Opposti

Sistema avanzato per scheduling di treni che viaggiano in **senso opposto** su linee con sezioni miste **singolo/doppio binario**. 

### Caratteristiche
- 🔍 Analisi topologia rete (single vs double track)
- ⏰ Ottimizzazione orari partenza con conflitto detection
- 🚉 Identificazione automatica punti incrocio ottimali
- 📊 Ranking proposte con confidence scoring
- 📡 REST API FastAPI (porta 8001)
- ⚡ Tempo calcolo < 5ms per scenari realistici

### Quick Start

```bash
# Avvia API server
python api/opposite_train_api.py

# Test con client demo
python api/test_opposite_train_client.py

# Documentazione interattiva
open http://localhost:8001/docs
```

### Esempio Uso

```python
from python.scheduling.opposite_train_optimizer import (
    OppositeTrainScheduler, TrackSection, TrainPath
)

# Definisci rete (40 km, 2 sezioni singolo binario)
sections = [
    TrackSection(1, 0.0, 5.0, num_tracks=2, can_cross=True),
    TrackSection(2, 5.0, 20.0, num_tracks=1),  # SINGOLO
    TrackSection(3, 20.0, 25.0, num_tracks=2, can_cross=True),
]

# Treni opposti
train1 = TrainPath("IC 501", "forward", 0.0, 25.0, 100.0)
train2 = TrainPath("IC 502", "backward", 25.0, 0.0, 100.0)

# Ottimizza
scheduler = OppositeTrainScheduler(sections)
proposals = scheduler.find_optimal_schedule(
    train1, train2, start_time, end_time, frequency_minutes=30
)

# Migliore soluzione
print(f"IC 501: {proposals[0].train1_departure}")
print(f"IC 502: {proposals[0].train2_departure}")
print(f"Incrocio: km {proposals[0].crossing_point_km}")
```

📖 **Documentazione completa**: [OPPOSITE_TRAIN_SCHEDULER.md](OPPOSITE_TRAIN_SCHEDULER.md)

## 🗺️ Roadmap

### ✅ Phase 4 - Advanced Features (62.5% completata)

**Completato:**
- [x] ✅ **Phase 4.1**: Python Bindings (pybind11 v2.11.1)
  - API completa con type hints
  - 9/9 test suite passing
  - Integrazione data science tools

- [x] ✅ **Phase 4.2**: Performance Profiling
  - Profiler ad alta risoluzione (μs)
  - Suite benchmark completa
  - Metriche network/pathfinding/conflict

- [x] ✅ **Phase 4.3**: Route Rerouting
  - RouteOptimizer con quality scoring
  - Batch optimization
  - ~0.06ms avg per reroute

- [x] ✅ **Phase 4.4**: Dynamic Speed Optimization
  - SpeedOptimizer con fisica realistica
  - **70-80% risparmio energetico** 🌱
  - 3 modalità: COMFORT, BALANCED, ECO
  - Coasting phases automatiche

- [x] ✅ **Phase 4.6**: Real-Time Optimization 🆕
  - GPS tracking e predizione conflitti
  - **77% confidence** prediction accuracy
  - 5 tipi schedule adjustments
  - Sistema callback real-time

**Opzionale/Futuro:**
- [ ] ⏭️ **Phase 4.5**: REST API Server (richiede cpp-httplib)
- [ ] 🔮 **Phase 4.7**: Machine Learning Integration
- [ ] 🔮 **Phase 4.8**: WebSocket real-time updates

### ✅ Core Features (Completate)
- [x] ✅ Ottimizzatore treni opposti con REST API
- [x] ✅ Dataset multi-paese europeo (7 nazioni)
- [x] ✅ Sistema cache GTFS compresso (145x riduzione)
- [x] ✅ Cambio binario automatico in stazioni
- [x] ✅ **FDC Integration API v2.0** con formato JSON potenziato

### 🚀 Future Enhancements
- [ ] Integrazione LibTorch per inferenza C++ nativa
- [ ] Algoritmo pathfinding avanzato (A*, Dijkstra)
- [ ] Ottimizzazione multi-obiettivo (delay + energy + passengers)
- [ ] Dashboard web real-time con WebSocket
- [ ] Export modello ONNX per deployment edge
- [ ] Supporto GPU acceleration (CUDA/ROCm)
- [ ] Visualizzazione 3D della rete ferroviaria
- [ ] Multi-train optimization (coordinazione >2 treni)
- [ ] Integrazione sistemi esterni (SCADA, CTC)
- [ ] Predictive maintenance scheduling

## 📄 Licenza

Questo progetto è rilasciato sotto licenza MIT. Vedi `LICENSE` per dettagli.

## 🙏 Acknowledgments

- PyTorch team per il framework ML
- pybind11 per i bindings C++/Python
- Comunità open source ferroviaria

## 📧 Contatti

Per domande, suggerimenti o supporto:
- Email: your.email@example.com
- Issues: [GitHub Issues](https://github.com/yourusername/RailwayAI/issues)

---

**Made with ❤️ for smarter railways**
