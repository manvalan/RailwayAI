# Railway AI Scheduler - Guida Libreria C++

## 📚 Uso come Libreria (non REST API)

Railway AI Scheduler può essere usato in **3 modalità**:

1. **Libreria Statica** (`.a` / `.lib`) - Link al compile-time
2. **Libreria Dinamica** (`.so` / `.dylib` / `.dll`) - Link al runtime
3. **REST API** (FastAPI) - HTTP/JSON

Questa guida copre le modalità 1 e 2.

---

## 🔧 Build della Libreria

### Compilazione

```bash
# Clone repository
git clone https://github.com/manvalan/RailwayAI.git
cd RailwayAI

# Build librerie C++
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Output librerie:
# - build/librailway_scheduler_core.a  (statica)
# - build/librailwayai.dylib          (dinamica - macOS)
# - build/librailwayai.so             (dinamica - Linux)
# - build/librailwayai.dll            (dinamica - Windows)
```

### Opzioni CMake

```bash
# Solo libreria statica
cmake -B build -DBUILD_SHARED_LIBS=OFF

# Solo libreria dinamica
cmake -B build -DBUILD_SHARED_LIBS=ON

# Con Python bindings
cmake -B build -DFDC_SCHEDULER_BUILD_PYTHON=ON

# Con esempi
cmake -B build -DFDC_SCHEDULER_BUILD_EXAMPLES=ON
```

---

## 📦 Uso come Libreria Statica

### Vantaggi
✅ Nessuna dipendenza runtime  
✅ Deployment semplice (single binary)  
✅ Performance ottimali  
✅ Link-time optimization (LTO)  

### Esempio Minimo

**File: `my_scheduler_app.cpp`**

```cpp
#include <iostream>
#include "railway_scheduler.h"

int main() {
    // Crea scheduler
    railway::RailwayScheduler scheduler(20, 10); // 20 tracks, 10 stations
    
    // Aggiungi treno
    railway::Train train;
    train.id = 1;
    train.current_track = 0;
    train.position_km = 10.5;
    train.velocity_kmh = 120.0;
    train.priority = 8;
    train.destination_station = 5;
    
    scheduler.add_train(train);
    
    // Rileva conflitti
    auto conflicts = scheduler.detect_conflicts();
    std::cout << "Conflitti rilevati: " << conflicts.size() << std::endl;
    
    // Risolvi
    if (!conflicts.empty()) {
        auto adjustments = scheduler.resolve_conflicts(conflicts);
        scheduler.apply_adjustments(adjustments);
        std::cout << "Applicati " << adjustments.size() << " aggiustamenti" << std::endl;
    }
    
    // Statistiche
    auto stats = scheduler.get_statistics();
    std::cout << "Efficienza rete: " << stats.network_efficiency * 100 << "%" << std::endl;
    
    return 0;
}
```

### Compilazione con Libreria Statica

```bash
# macOS/Linux
g++ -std=c++17 my_scheduler_app.cpp \
    -I/path/to/RailwayAI/cpp/include \
    -L/path/to/RailwayAI/build \
    -lrailway_scheduler_core \
    -o my_app

# Windows (MSVC)
cl /std:c++17 /EHsc my_scheduler_app.cpp \
   /I"C:\path\to\RailwayAI\cpp\include" \
   /link railway_scheduler_core.lib \
   /OUT:my_app.exe
```

### CMake per Progetto Esterno

**File: `CMakeLists.txt`**

```cmake
cmake_minimum_required(VERSION 3.15)
project(MySchedulerApp)

set(CMAKE_CXX_STANDARD 17)

# Trova libreria RailwayAI
find_library(RAILWAY_SCHEDULER_LIB
    NAMES railway_scheduler_core
    PATHS /path/to/RailwayAI/build
)

# Aggiungi include
include_directories(/path/to/RailwayAI/cpp/include)

# Eseguibile
add_executable(my_app my_scheduler_app.cpp)
target_link_libraries(my_app ${RAILWAY_SCHEDULER_LIB})
```

---

## 🔗 Uso come Libreria Dinamica

### Vantaggi
✅ Aggiornamenti senza ricompilare app  
✅ Condivisione tra più applicazioni  
✅ Dimensione binary ridotta  
✅ Plugin architecture possibile  

### Esempio con Libreria Dinamica

**Stesso codice C++, diversa compilazione:**

```bash
# macOS
g++ -std=c++17 my_scheduler_app.cpp \
    -I/path/to/RailwayAI/cpp/include \
    -L/path/to/RailwayAI/build \
    -lrailwayai \
    -o my_app

# Linux
g++ -std=c++17 my_scheduler_app.cpp \
    -I/path/to/RailwayAI/cpp/include \
    -L/path/to/RailwayAI/build \
    -lrailwayai \
    -Wl,-rpath,/path/to/RailwayAI/build \
    -o my_app

# Windows
cl /std:c++17 /EHsc my_scheduler_app.cpp \
   /I"C:\path\to\RailwayAI\cpp\include" \
   /link railwayai.lib \
   /OUT:my_app.exe
```

### Runtime Setup

```bash
# macOS
export DYLD_LIBRARY_PATH=/path/to/RailwayAI/build:$DYLD_LIBRARY_PATH

# Linux
export LD_LIBRARY_PATH=/path/to/RailwayAI/build:$LD_LIBRARY_PATH

# Windows
set PATH=C:\path\to\RailwayAI\build;%PATH%
```

---

## 📊 Esempio Avanzato: Ottimizzazione Rete Completa

```cpp
#include <iostream>
#include <vector>
#include "railway_scheduler.h"

class NetworkOptimizer {
private:
    railway::RailwayScheduler scheduler_;
    
public:
    NetworkOptimizer(int num_tracks, int num_stations)
        : scheduler_(num_tracks, num_stations) {}
    
    // Carica rete da file
    bool load_network(const std::string& filename) {
        // Parse network configuration
        // Add tracks, stations, trains
        return true;
    }
    
    // Ottimizza tutta la rete
    OptimizationResult optimize() {
        OptimizationResult result;
        
        // 1. Rileva tutti i conflitti
        auto conflicts = scheduler_.detect_conflicts();
        result.initial_conflicts = conflicts.size();
        
        // 2. Risolvi iterativamente
        int iterations = 0;
        while (!conflicts.empty() && iterations < 10) {
            auto adjustments = scheduler_.resolve_conflicts(conflicts);
            scheduler_.apply_adjustments(adjustments);
            
            conflicts = scheduler_.detect_conflicts();
            iterations++;
        }
        
        // 3. Statistiche finali
        auto stats = scheduler_.get_statistics();
        result.final_conflicts = conflicts.size();
        result.network_efficiency = stats.network_efficiency;
        result.total_delay_minutes = stats.total_delay_minutes;
        result.iterations = iterations;
        
        return result;
    }
    
    struct OptimizationResult {
        int initial_conflicts;
        int final_conflicts;
        double network_efficiency;
        double total_delay_minutes;
        int iterations;
    };
};

int main() {
    NetworkOptimizer optimizer(50, 20); // 50 tracks, 20 stations
    
    if (optimizer.load_network("network.json")) {
        auto result = optimizer.optimize();
        
        std::cout << "=== Optimization Results ===" << std::endl;
        std::cout << "Initial conflicts: " << result.initial_conflicts << std::endl;
        std::cout << "Final conflicts: " << result.final_conflicts << std::endl;
        std::cout << "Network efficiency: " << result.network_efficiency * 100 << "%" << std::endl;
        std::cout << "Total delay: " << result.total_delay_minutes << " minutes" << std::endl;
        std::cout << "Iterations: " << result.iterations << std::endl;
    }
    
    return 0;
}
```

---

## 🎯 Confronto Modalità di Utilizzo

| Caratteristica | Libreria Statica | Libreria Dinamica | REST API |
|----------------|------------------|-------------------|----------|
| **Performance** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Deployment** | Semplice | Media | Complessa |
| **Aggiornamenti** | Ricompilare | Sostituire .so/.dll | Hot-reload |
| **Overhead** | Nessuno | Nessuno | HTTP/JSON |
| **Multi-language** | No | No | Sì |
| **Microservices** | No | No | Sì |
| **Latency** | <1ms | <1ms | 5-10ms |

### Quando Usare Cosa?

#### ✅ Usa Libreria Statica quando:
- Performance critiche (real-time systems)
- Deployment embedded/edge
- Single binary desiderato
- Nessuna necessità di hot-reload

#### ✅ Usa Libreria Dinamica quando:
- Aggiornamenti frequenti
- Shared library tra più app
- Plugin architecture
- Dimensione binary importante

#### ✅ Usa REST API quando:
- Integrazione multi-linguaggio
- Microservices architecture
- Client remoti (web, mobile)
- Non serve performance estrema

---

## 🔐 API Pubblica della Libreria

### Core Classes

```cpp
namespace railway {

// Main scheduler class
class RailwayScheduler {
public:
    RailwayScheduler(int num_tracks, int num_stations);
    
    // Train management
    void add_train(const Train& train);
    void remove_train(int train_id);
    std::vector<Train> get_all_trains() const;
    
    // Conflict detection
    std::vector<Conflict> detect_conflicts() const;
    
    // Conflict resolution
    std::vector<ScheduleAdjustment> resolve_conflicts(
        const std::vector<Conflict>& conflicts
    );
    
    // Apply changes
    void apply_adjustments(const std::vector<ScheduleAdjustment>& adjustments);
    
    // Statistics
    Statistics get_statistics() const;
};

// Data structures
struct Train {
    int id;
    int current_track;
    double position_km;
    double velocity_kmh;
    int priority;
    int destination_station;
    double delay_minutes;
    bool is_delayed;
};

struct Conflict {
    int train1_id;
    int train2_id;
    double time_overlap_seconds;
    double position_km;
    std::string type; // "collision", "overtaking", "congestion"
};

struct ScheduleAdjustment {
    int train_id;
    double time_adjustment_minutes;
    int new_track;
    std::string reason;
};

struct Statistics {
    int total_trains;
    int delayed_trains;
    int active_conflicts;
    double network_efficiency;
    double total_delay_minutes;
    double average_velocity_kmh;
};

} // namespace railway
```

---

## 📚 Esempi Completi nel Repository

### Esempi Disponibili

```bash
# C++ Examples (build/examples/)
./build/python_bindings_demo      # Python bindings
./build/performance_benchmark     # Performance tests
./build/reroute_demo             # Route optimization
./build/speed_optimizer_demo     # Energy optimization
./build/realtime_demo            # Real-time tracking

# Python Examples (examples/)
python examples/example_usage.py           # Basic usage
python examples/test_real_opposite_trains.py  # Complex scenarios
python examples/fdc_integration_demo.py       # FDC integration
```

### Codice Sorgente Esempi

- `examples/external_app/simple_client.cpp` - Client C++ minimale
- `examples/external_app/json_api_demo.cpp` - JSON API usage
- `cpp/src/railway_scheduler.cpp` - Implementazione completa

---

## 🐛 Troubleshooting

### Errore: "undefined reference to ..."

```bash
# Verifica che la libreria sia compilata
ls -la build/librailway_scheduler_core.a

# Aggiungi flag di linking
g++ ... -lrailway_scheduler_core -lstdc++
```

### Errore: "cannot open shared object file"

```bash
# macOS
export DYLD_LIBRARY_PATH=/path/to/build:$DYLD_LIBRARY_PATH

# Linux
export LD_LIBRARY_PATH=/path/to/build:$LD_LIBRARY_PATH
sudo ldconfig /path/to/build  # Opzionale
```

### Errore: "incompatible C++ standard"

```bash
# Assicurati di usare C++17
g++ -std=c++17 ...
```

---

## 📖 Documentazione Aggiuntiva

- **API Reference:** `API_REFERENCE.md`
- **JSON API:** `JSON_API_REFERENCE.md`
- **FDC Integration:** `FDC_API_REFERENCE.md`
- **Performance:** `TRAINING_RESULTS.md`

---

## 🤝 Supporto

Per domande sull'uso come libreria:
- **Issues:** https://github.com/manvalan/RailwayAI/issues
- **Discussions:** https://github.com/manvalan/RailwayAI/discussions
- **Tag:** `library-usage`, `c++`, `static-library`, `dynamic-library`

---

**Railway AI Scheduler - Flexible Integration for Every Use Case**
