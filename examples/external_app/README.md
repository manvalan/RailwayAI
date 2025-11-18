# External Application Example

This directory demonstrates how to use the Railway AI Scheduler library in your own C++ application.

## Method 1: Direct Compilation

```bash
# Make sure library is built
cd ../..
mkdir build && cd build
cmake ..
make railwayai

# Compile client
cd ../examples/external_app
g++ -std=c++17 -I../../cpp/include simple_client.cpp -L../../build -lrailwayai -o simple_client

# Run (macOS)
export DYLD_LIBRARY_PATH=../../build:$DYLD_LIBRARY_PATH
./simple_client

# Run (Linux)
export LD_LIBRARY_PATH=../../build:$LD_LIBRARY_PATH
./simple_client
```

## Method 2: CMake Build

```bash
mkdir build && cd build
cmake ..
make
./simple_client
```

## Method 3: System-wide Installation

```bash
# Install library system-wide
cd ../..
mkdir build && cd build
cmake ..
make
sudo make install

# Now compile from anywhere
cd ../examples/external_app
g++ -std=c++17 simple_client.cpp -lrailwayai -o simple_client
./simple_client
```

## Expected Output

```
========================================
  Railway AI Scheduler - Demo Client
========================================

✓ Scheduler initialized (version 1.0.0)
  Mode: C++ Heuristics

✓ Network configured:
  3 tracks
  5 stations

Scenario: 4 trains
  Train 101: position 15.0km, track 1, delay 2.0 min [DELAYED]
  Train 102: position 65.0km, track 1, delay 0.0 min [ON TIME]
  Train 103: position 80.0km, track 0, delay 0.0 min [ON TIME]
  Train 104: position 5.0km, track 2, delay 5.5 min [DELAYED]

Conflict Detection:
  ⚠ 1 conflict(s) detected:
    • Train 101 vs Train 102 on track 1 (severity: 0.75)

Running optimization...
✓ Optimization completed in 0.082 ms

Optimization Results:
  Total system delay: 7.5 minutes
  Resolutions: 2

Proposed Actions:
  Train 101:
    → Slow down by 3.0 min
    (confidence: 85.0%)
  Train 102:
    → Reroute to track 0
    (confidence: 85.0%)

✓ All conflicts resolved!

Statistics:
  Total optimizations: 1
  Average time: 0.082 ms

========================================
  Demo completed successfully!
========================================
```

## Integration in Your Project

See `simple_client.cpp` for complete example. Basic steps:

1. Include header:
```cpp
#include <railway_api.h>
```

2. Create scheduler:
```cpp
railway::RailwaySchedulerAPI scheduler;
scheduler.initialize();
```

3. Define network:
```cpp
std::vector<railway::Track> tracks = {...};
std::vector<railway::Station> stations = {...};
scheduler.set_network(tracks, stations);
```

4. Optimize:
```cpp
std::vector<railway::Train> trains = {...};
auto result = scheduler.optimize(trains);
```

For complete API documentation, see `API_REFERENCE.md` in the root directory.
