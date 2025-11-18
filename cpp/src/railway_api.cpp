/**
 * @file railway_api.cpp
 * @brief Implementation of Railway AI Scheduler Public API
 */

#include "railway_api.h"
#include <chrono>
#include <algorithm>
#include <numeric>
#include <cmath>

namespace railway {

// PIMPL implementation
class RailwaySchedulerAPI::Impl {
public:
    SchedulerConfig config;
    
    // Statistics
    std::vector<double> optimization_times;
    int total_optimizations = 0;
    
    bool ml_ready = false;
};

RailwaySchedulerAPI::RailwaySchedulerAPI() 
    : pImpl(std::make_unique<Impl>()) {
}

RailwaySchedulerAPI::~RailwaySchedulerAPI() = default;

bool RailwaySchedulerAPI::initialize(const SchedulerConfig& config) {
    pImpl->config = config;
    
    // Initialize ML model if requested
    if (config.use_ml_model) {
        // TODO: Load PyTorch model here when we add C++ inference
        // For now, fall back to C++ heuristics
        if (config.verbose) {
            // Note: ML inference from C++ requires libtorch
            // Currently using C++ heuristic solver
        }
        pImpl->ml_ready = false;
    } else {
        pImpl->ml_ready = false;
    }
    
    return true;
}

bool RailwaySchedulerAPI::set_network(const std::vector<Track>&, 
                                       const std::vector<Station>&) {
    // Note: Network topology is implicit in train current_track assignments
    // No persistent network storage needed for this simplified API
    return true;
}

std::vector<Conflict> RailwaySchedulerAPI::detect_conflicts(
    const std::vector<Train>& trains) {
    
    // Simplified conflict detection without full internal conversion
    std::vector<Conflict> api_conflicts;
    
    // Check single-track conflicts
    for (size_t i = 0; i < trains.size(); i++) {
        for (size_t j = i + 1; j < trains.size(); j++) {
            const auto& t1 = trains[i];
            const auto& t2 = trains[j];
            
            // Same track and close proximity
            if (t1.current_track == t2.current_track) {
                double distance = std::abs(t1.position_km - t2.position_km);
                
                if (distance < 10.0) {  // Within 10km
                    Conflict conflict;
                    conflict.train1_id = t1.id;
                    conflict.train2_id = t2.id;
                    conflict.track_id = t1.current_track;
                    conflict.estimated_time_min = distance / ((t1.velocity_kmh + t2.velocity_kmh) / 2.0) * 60.0;
                    conflict.severity = 1.0 - (distance / 10.0);
                    api_conflicts.push_back(conflict);
                }
            }
        }
    }
    
    return api_conflicts;
}

OptimizationResult RailwaySchedulerAPI::optimize(const std::vector<Train>& trains) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    OptimizationResult result;
    result.success = false;
    
    try {
        // Detect conflicts
        auto conflicts = detect_conflicts(trains);
        
        if (conflicts.empty()) {
            result.success = true;
            result.total_delay_minutes = 0.0;
            for (const auto& t : trains) {
                result.total_delay_minutes += t.delay_minutes;
            }
        } else {
            // Resolve conflicts using simple heuristics
            // Priority-based: higher priority trains get precedence
            for (const auto& c : conflicts) {
                // Find the two conflicting trains
                const Train* t1 = nullptr;
                const Train* t2 = nullptr;
                
                for (const auto& t : trains) {
                    if (t.id == c.train1_id) t1 = &t;
                    if (t.id == c.train2_id) t2 = &t;
                }
                
                if (t1 && t2) {
                    // Lower priority train slows down
                    if (t1->priority < t2->priority) {
                        Resolution res;
                        res.train_id = t1->id;
                        res.time_adjustment_min = -3.0;  // Slow down by 3 min
                        res.new_track = -1;
                        res.confidence = 0.85;
                        result.resolutions.push_back(res);
                    } else {
                        Resolution res;
                        res.train_id = t2->id;
                        res.time_adjustment_min = -3.0;
                        res.new_track = -1;
                        res.confidence = 0.85;
                        result.resolutions.push_back(res);
                    }
                }
            }
            
            // Calculate total delay after resolution
            result.total_delay_minutes = 0.0;
            for (const auto& t : trains) {
                double adjusted_delay = t.delay_minutes;
                
                // Apply time adjustments
                for (const auto& res : result.resolutions) {
                    if (res.train_id == t.id) {
                        adjusted_delay += std::abs(res.time_adjustment_min);
                    }
                }
                
                result.total_delay_minutes += adjusted_delay;
            }
            
            result.success = true;
        }
        
    } catch (const std::exception& e) {
        result.success = false;
        result.error_message = e.what();
    }
    
    // Calculate optimization time
    auto end_time = std::chrono::high_resolution_clock::now();
    auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - start_time);
    result.optimization_time_ms = duration.count() / 1000.0;
    
    // Update statistics
    pImpl->optimization_times.push_back(result.optimization_time_ms);
    pImpl->total_optimizations++;
    
    return result;
}

std::string RailwaySchedulerAPI::version() {
    return "1.0.0";
}

bool RailwaySchedulerAPI::is_ml_ready() const {
    return pImpl->ml_ready;
}

void RailwaySchedulerAPI::get_statistics(double& avg_time_ms, 
                                          int& total_optimizations) const {
    total_optimizations = pImpl->total_optimizations;
    
    if (pImpl->optimization_times.empty()) {
        avg_time_ms = 0.0;
    } else {
        avg_time_ms = std::accumulate(
            pImpl->optimization_times.begin(), 
            pImpl->optimization_times.end(), 
            0.0) / pImpl->optimization_times.size();
    }
}

} // namespace railway
