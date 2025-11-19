# External Application Examples - Railway AI Scheduler

Examples of integrating the Railway AI Scheduler library into external C++ applications.

## 📁 Examples

### 1. `simple_client.cpp`
**Struct-based API** - Traditional C++ approach with strongly-typed data structures.

Features:
- Type-safe API
- Zero serialization overhead
- Direct C++ integration
- Ideal for native C++ applications

### 2. `json_api_demo.cpp` 🆕
**JSON API** - Modern approach for maximum interoperability.

Features:
- `detect_conflicts_json()` - Conflict detection from JSON string
- `optimize_json()` - Schedule optimization from JSON string
- `get_statistics_json()` - Performance stats in JSON format
- Works with any language (Python, Node.js, Go, Rust, Java, etc.)
- Perfect for REST APIs and microservices
- No external JSON library dependencies

## 🔨 Compilation

### Build Library First
```bash
cd ../..
mkdir -p build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . --target railwayai
```

### Compile Examples
```bash
cd ../examples/external_app

# Simple client (struct API)
g++ -std=c++17 -I../../cpp/include simple_client.cpp \
    -L../../build -lrailwayai -o simple_client

# JSON API demo
g++ -std=c++17 -I../../cpp/include json_api_demo.cpp \
    -L../../build -lrailwayai -o json_api_demo
```

## 🚀 Running

### macOS
```bash
DYLD_LIBRARY_PATH=../../build ./simple_client
DYLD_LIBRARY_PATH=../../build ./json_api_demo
```

### Linux
```bash
LD_LIBRARY_PATH=../../build ./simple_client
LD_LIBRARY_PATH=../../build ./json_api_demo
```

### Windows
```powershell
set PATH=..\..\build;%PATH%
simple_client.exe
json_api_demo.exe
```

## 📊 Example Output

### simple_client
```
======================================================================
  🚂 Railway AI Scheduler Demo
======================================================================

✅ Scheduler initialized (version 1.0.0)
📊 Network configured: 2 tracks, 4 stations
🚆 Added 4 trains

⚠️  Conflicts detected: 2

=== Conflitti Rilevati ===
  - Train 1 vs Train 2 su binario 1 (severity: 0.70)

=== Optimization Results ===
✅ Optimization successful
  • Resolutions proposed: 2
  • Remaining conflicts: 0
  • Total delay: 7.5 minutes
  • Processing time: 0.011 ms
```

### json_api_demo
```
======================================================================
  🚂 Railway AI Scheduler - JSON API Demo
======================================================================

✅ Scheduler initialized (version 1.0.0)

📊 Test 1: Conflict Detection JSON API
----------------------------------------------------------------------
Output JSON:
{
  "conflicts":[
    {
      "train1_id":101,
      "train2_id":102,
      "track_id":1,
      "estimated_time_min":1.636364,
      "severity":0.700000
    }
  ],
  "total_conflicts":2,
  "processing_time_ms":0.053,
  "success":true
}

⚡ Test 2: Optimization JSON API
----------------------------------------------------------------------
Output JSON:
{
  "resolutions":[
    {
      "train_id":202,
      "time_adjustment_min":-3.000000,
      "new_track":-1,
      "confidence":0.850000
    }
  ],
  "remaining_conflicts":[],
  "total_delay_minutes":34.000000,
  "optimization_time_ms":0.003,
  "success":true
}

✅ All JSON API tests completed successfully!
```

## 🔌 Integration Guide

### Option 1: Struct-Based API (C++)

Best for: Native C++ applications

```cpp
#include "railway_api.h"

railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();

// Create trains using structs
railway::Train train;
train.id = 1;
train.position_km = 10.0;
// ... set other fields

std::vector<railway::Train> trains = {train};

// Optimize
railway::OptimizationResult result = scheduler.optimize(trains);

// Process results
for (const auto& res : result.resolutions) {
    std::cout << "Train " << res.train_id 
              << ": adjust by " << res.time_adjustment_min << " min\n";
}
```

### Option 2: JSON API (Any Language)

Best for: REST APIs, microservices, multi-language integration

```cpp
#include "railway_api.h"

railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();

std::string input = R"({
  "trains": [
    {
      "id": 1,
      "position_km": 10.0,
      "velocity_kmh": 120.0,
      "current_track": 1,
      "destination_station": 3,
      "delay_minutes": 5.0,
      "priority": 8,
      "is_delayed": true
    }
  ]
})";

std::string result = scheduler.optimize_json(input);

// result is valid JSON string - parse with any JSON library
std::cout << result << std::endl;
```

## 🌍 Multi-Language Examples

See **JSON_API_REFERENCE.md** for complete examples in:
- Python (via ctypes)
- Node.js (via ffi-napi)
- Go (via cgo)
- Rust (via FFI)

## 📚 Documentation

- **[API_REFERENCE.md](../../API_REFERENCE.md)** - Complete C++ API reference
- **[JSON_API_REFERENCE.md](../../JSON_API_REFERENCE.md)** - JSON API guide
- **[TRAINING_RESULTS.md](../../TRAINING_RESULTS.md)** - ML model performance
- **[DEPLOYMENT.md](../../DEPLOYMENT.md)** - Production deployment guide

## 🛠️ CMake Integration

To integrate into your CMake project:

```cmake
# Find the library
find_library(RAILWAYAI_LIB railwayai 
             HINTS ${CMAKE_SOURCE_DIR}/../build)

# Include directories
include_directories(${CMAKE_SOURCE_DIR}/../cpp/include)

# Link your executable
add_executable(my_app main.cpp)
target_link_libraries(my_app ${RAILWAYAI_LIB})
```

## ⚡ Performance

| API Type | Overhead | Best For |
|----------|----------|----------|
| Struct-based | ~0 ns | Native C++ apps, maximum performance |
| JSON | ~20-50 μs | REST APIs, multi-language integration |

Both APIs use the same optimized C++ engine underneath.

---

**Version**: 1.1.0  
**Repository**: [github.com/manvalan/RailwayAI](https://github.com/manvalan/RailwayAI)
