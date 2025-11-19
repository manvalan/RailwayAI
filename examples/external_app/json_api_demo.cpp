#include <iostream>
#include <string>
#include "railway_api.h"

int main() {
    std::cout << "\n";
    std::cout << "======================================================================\n";
    std::cout << "  🚂 Railway AI Scheduler - JSON API Demo\n";
    std::cout << "======================================================================\n";
    std::cout << "\n";
    
    // Create scheduler
    railway::RailwaySchedulerAPI scheduler;
    
    // Initialize
    railway::SchedulerConfig config;
    config.verbose = true;
    config.max_iterations = 100;
    
    if (!scheduler.initialize(config)) {
        std::cerr << "❌ Failed to initialize scheduler\n";
        return 1;
    }
    
    std::cout << "✅ Scheduler initialized (version " << scheduler.version() << ")\n\n";
    
    // Test 1: Detect conflicts with JSON
    std::cout << "📊 Test 1: Conflict Detection JSON API\n";
    std::cout << "----------------------------------------------------------------------\n";
    
    std::string input_json = R"({
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
            },
            {
                "id": 102,
                "position_km": 18.0,
                "velocity_kmh": 100.0,
                "current_track": 1,
                "destination_station": 3,
                "delay_minutes": 0.0,
                "priority": 5,
                "is_delayed": false
            },
            {
                "id": 103,
                "position_km": 25.0,
                "velocity_kmh": 130.0,
                "current_track": 1,
                "destination_station": 4,
                "delay_minutes": 10.0,
                "priority": 9,
                "is_delayed": true
            }
        ]
    })";
    
    std::cout << "Input JSON:\n" << input_json << "\n\n";
    
    std::string conflicts_result = scheduler.detect_conflicts_json(input_json);
    std::cout << "Output JSON:\n" << conflicts_result << "\n\n";
    
    // Test 2: Optimize schedule with JSON
    std::cout << "⚡ Test 2: Optimization JSON API\n";
    std::cout << "----------------------------------------------------------------------\n";
    
    std::string optimize_json = R"({
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
            },
            {
                "id": 202,
                "position_km": 12.0,
                "velocity_kmh": 110.0,
                "current_track": 1,
                "destination_station": 5,
                "delay_minutes": 8.0,
                "priority": 6,
                "is_delayed": true
            },
            {
                "id": 203,
                "position_km": 30.0,
                "velocity_kmh": 140.0,
                "current_track": 2,
                "destination_station": 6,
                "delay_minutes": 0.0,
                "priority": 10,
                "is_delayed": false
            },
            {
                "id": 204,
                "position_km": 32.0,
                "velocity_kmh": 100.0,
                "current_track": 2,
                "destination_station": 6,
                "delay_minutes": 5.0,
                "priority": 4,
                "is_delayed": true
            }
        ],
        "max_iterations": 100
    })";
    
    std::cout << "Input JSON:\n" << optimize_json << "\n\n";
    
    std::string optimize_result = scheduler.optimize_json(optimize_json);
    std::cout << "Output JSON:\n" << optimize_result << "\n\n";
    
    // Test 3: Get statistics
    std::cout << "📈 Test 3: Statistics JSON API\n";
    std::cout << "----------------------------------------------------------------------\n";
    
    std::string stats = scheduler.get_statistics_json();
    std::cout << "Statistics JSON:\n" << stats << "\n\n";
    
    std::cout << "======================================================================\n";
    std::cout << "  ✅ All JSON API tests completed successfully!\n";
    std::cout << "======================================================================\n";
    std::cout << "\n";
    
    return 0;
}
