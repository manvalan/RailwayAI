/**
 * @file simple_client.cpp
 * @brief Example of using Railway AI Scheduler library in external application
 * 
 * This demonstrates how to integrate librailwayai into your own C++ project.
 * 
 * Compile:
 *   g++ -std=c++17 simple_client.cpp -lrailwayai -o simple_client
 * 
 * Run:
 *   ./simple_client
 */

#include <railway_api.h>
#include <iostream>
#include <iomanip>

int main() {
    std::cout << "\n";
    std::cout << "========================================\n";
    std::cout << "  Railway AI Scheduler - Demo Client\n";
    std::cout << "========================================\n\n";
    
    // 1. Create and initialize scheduler
    railway::RailwaySchedulerAPI scheduler;
    
    railway::SchedulerConfig config;
    config.use_ml_model = false;  // Use C++ heuristics (ML requires Python)
    config.verbose = true;
    
    if (!scheduler.initialize(config)) {
        std::cerr << "Failed to initialize scheduler\n";
        return 1;
    }
    
    std::cout << "✓ Scheduler initialized (version " 
              << railway::RailwaySchedulerAPI::version() << ")\n";
    std::cout << "  Mode: " << (scheduler.is_ml_ready() ? "ML" : "C++ Heuristics") << "\n\n";
    
    // 2. Define railway network
    std::vector<railway::Track> tracks = {
        {0, 120.0, false, 15, {0, 1, 2}},    // Milano-Bologna-Firenze (double track)
        {1, 80.0, true, 8, {2, 3}},          // Firenze-Roma (single track)
        {2, 45.0, false, 10, {0, 4}},        // Milano-Torino (double track)
    };
    
    std::vector<railway::Station> stations = {
        {0, "Milano Centrale", 24},
        {1, "Bologna Centrale", 16},
        {2, "Firenze SMN", 18},
        {3, "Roma Termini", 32},
        {4, "Torino Porta Nuova", 20}
    };
    
    if (!scheduler.set_network(tracks, stations)) {
        std::cerr << "Failed to set network\n";
        return 1;
    }
    
    std::cout << "✓ Network configured:\n";
    std::cout << "  " << tracks.size() << " tracks\n";
    std::cout << "  " << stations.size() << " stations\n\n";
    
    // 3. Define train scenario with conflicts
    std::vector<railway::Train> trains = {
        // Two trains on same single-track segment (conflict!)
        {101, 15.0, 160.0, 1, 3, 2.0, 9, true},   // Express Milano→Roma (delayed)
        {102, 65.0, 140.0, 1, 2, 0.0, 7, false},  // Regional Roma→Firenze
        
        // Train on double-track (no conflict)
        {103, 80.0, 180.0, 0, 2, 0.0, 10, false}, // High-speed Milano→Firenze
        
        // Another delayed train
        {104, 5.0, 120.0, 2, 4, 5.5, 6, true},    // Regional Milano→Torino
    };
    
    std::cout << "Scenario: " << trains.size() << " trains\n";
    for (const auto& t : trains) {
        std::cout << "  Train " << t.id 
                  << ": position " << std::fixed << std::setprecision(1) << t.position_km << "km"
                  << ", track " << t.current_track
                  << ", delay " << t.delay_minutes << " min"
                  << (t.is_delayed ? " [DELAYED]" : " [ON TIME]")
                  << "\n";
    }
    std::cout << "\n";
    
    // 4. Detect conflicts
    auto conflicts = scheduler.detect_conflicts(trains);
    
    std::cout << "Conflict Detection:\n";
    if (conflicts.empty()) {
        std::cout << "  ✓ No conflicts detected\n\n";
    } else {
        std::cout << "  ⚠ " << conflicts.size() << " conflict(s) detected:\n";
        for (const auto& c : conflicts) {
            std::cout << "    • Train " << c.train1_id << " vs Train " << c.train2_id
                      << " on track " << c.track_id
                      << " (severity: " << std::setprecision(2) << c.severity << ")\n";
        }
        std::cout << "\n";
    }
    
    // 5. Optimize schedule
    std::cout << "Running optimization...\n";
    auto result = scheduler.optimize(trains);
    
    if (!result.success) {
        std::cerr << "✗ Optimization failed: " << result.error_message << "\n";
        return 1;
    }
    
    std::cout << "✓ Optimization completed in " << std::setprecision(3) 
              << result.optimization_time_ms << " ms\n\n";
    
    // 6. Display results
    std::cout << "Optimization Results:\n";
    std::cout << "  Total system delay: " << std::setprecision(1) 
              << result.total_delay_minutes << " minutes\n";
    std::cout << "  Resolutions: " << result.resolutions.size() << "\n\n";
    
    if (!result.resolutions.empty()) {
        std::cout << "Proposed Actions:\n";
        for (const auto& res : result.resolutions) {
            std::cout << "  Train " << res.train_id << ":\n";
            
            if (res.time_adjustment_min != 0.0) {
                if (res.time_adjustment_min > 0) {
                    std::cout << "    → Speed up by " << res.time_adjustment_min << " min\n";
                } else {
                    std::cout << "    → Slow down by " << -res.time_adjustment_min << " min\n";
                }
            }
            
            if (res.new_track >= 0) {
                std::cout << "    → Reroute to track " << res.new_track << "\n";
            }
            
            std::cout << "    (confidence: " << std::setprecision(1) 
                      << (res.confidence * 100.0) << "%)\n";
        }
        std::cout << "\n";
    }
    
    if (!result.remaining_conflicts.empty()) {
        std::cout << "⚠ Warning: " << result.remaining_conflicts.size() 
                  << " conflicts could not be fully resolved\n\n";
    } else {
        std::cout << "✓ All conflicts resolved!\n\n";
    }
    
    // 7. Get performance statistics
    double avg_time_ms;
    int total_opts;
    scheduler.get_statistics(avg_time_ms, total_opts);
    
    std::cout << "Statistics:\n";
    std::cout << "  Total optimizations: " << total_opts << "\n";
    std::cout << "  Average time: " << std::setprecision(3) << avg_time_ms << " ms\n";
    
    std::cout << "\n========================================\n";
    std::cout << "  Demo completed successfully!\n";
    std::cout << "========================================\n\n";
    
    return 0;
}
