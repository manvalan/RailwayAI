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

#include "railway_scheduler.h"

namespace railway {

// PIMPL implementation
class RailwaySchedulerAPI::Impl {
public:
    RailwayScheduler scheduler;
    SchedulerConfig config;
    
    // Statistics
    std::vector<double> optimization_times;
    int total_optimizations = 0;
};

RailwaySchedulerAPI::RailwaySchedulerAPI() 
    : pImpl(std::make_unique<Impl>()) {
}

RailwaySchedulerAPI::~RailwaySchedulerAPI() = default;

bool RailwaySchedulerAPI::initialize(const SchedulerConfig& config) {
    pImpl->config = config;
    
    if (config.use_ml_model && !config.model_path.empty()) {
        return pImpl->scheduler.load_ml_model(config.model_path);
    }
    
    return true;
}

bool RailwaySchedulerAPI::set_network(const std::vector<Track>& tracks, 
                                       const std::vector<Station>& stations) {
    pImpl->scheduler.initialize_network(tracks, stations);
    return true;
}

std::vector<Conflict> RailwaySchedulerAPI::detect_conflicts(
    const std::vector<Train>& trains) {
    
    // Initialize a temporary scheduler for stateless detection if needed,
    // or use the internal one if it already has the network.
    // For this API, we assume the internal scheduler is pre-configured or we add trains temporarily.
    
    // Simplest way to keep it consistent with the core:
    for (const auto& t : trains) {
        pImpl->scheduler.add_train(t);
    }
    
    auto conflicts = pImpl->scheduler.detect_conflicts();
    
    // Clean up temporary trains
    for (const auto& t : trains) {
        pImpl->scheduler.remove_train(t.id);
    }
    
    return conflicts;
}

OptimizationResult RailwaySchedulerAPI::optimize(const std::vector<Train>& trains) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    OptimizationResult result;
    result.success = false;
    
    try {
        // 1. Add trains to internal scheduler
        for (const auto& t : trains) {
            pImpl->scheduler.add_train(t);
        }
        
        // 2. Detect and resolve
        auto conflicts = pImpl->scheduler.detect_conflicts();
        if (conflicts.empty()) {
            result.success = true;
            result.total_delay_minutes = 0.0;
        } else {
            auto adjustments = pImpl->scheduler.resolve_conflicts(conflicts);
            
            // Convert core ScheduleAdjustment to API Resolution
            for (const auto& adj : adjustments) {
                Resolution res;
                res.train_id = adj.train_id;
                res.time_adjustment_min = adj.time_adjustment_minutes;
                res.new_track = adj.new_track_id;
                res.confidence = adj.confidence;
                result.resolutions.push_back(res);
            }
            
            result.success = true;
        }
        
        // 3. Clean up
        for (const auto& t : trains) {
            pImpl->scheduler.remove_train(t.id);
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
    return "2.0.0";
}

bool RailwaySchedulerAPI::is_ml_ready() const {
    // This is a simplification; in a real scenario we'd check the core scheduler's ML state.
    return pImpl->config.use_ml_model;
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

#include <nlohmann/json.hpp>

using json = nlohmann::json;

namespace {
    // Helper: Parse Train from JSON object
    Train json_to_train(const json& j) {
        Train t;
        t.id = j.value("id", 0);
        t.current_track = j.value("current_track", 0);
        t.position_km = j.value("position_km", 0.0);
        t.velocity_kmh = j.value("velocity_kmh", 0.0);
        t.scheduled_arrival_minutes = j.value("scheduled_arrival_minutes", 0.0);
        t.destination_station = j.value("destination_station", 0);
        t.priority = j.value("priority", 0);
        t.is_delayed = j.value("is_delayed", false);
        t.delay_minutes = j.value("delay_minutes", 0.0);
        return t;
    }

    // Heper: Conflict to JSON object
    json conflict_to_json(const Conflict& c) {
        return {
            {"train1_id", c.train1_id},
            {"train2_id", c.train2_id},
            {"track_id", c.track_id},
            {"estimated_time_min", c.estimated_time_min},
            {"severity", c.severity}
        };
    }
}

std::string RailwaySchedulerAPI::detect_conflicts_json(const std::string& json_input) {
    auto start_time = std::chrono::high_resolution_clock::now();
    json response;
    
    try {
        auto j_input = json::parse(json_input);
        std::vector<Train> trains;
        
        if (j_input.contains("trains") && j_input["trains"].is_array()) {
            for (const auto& j_train : j_input["trains"]) {
                trains.push_back(json_to_train(j_train));
            }
        }
        
        auto conflicts = detect_conflicts(trains);
        
        response["conflicts"] = json::array();
        for (const auto& c : conflicts) {
            response["conflicts"].push_back(conflict_to_json(c));
        }
        
        response["total_conflicts"] = conflicts.size();
        response["success"] = true;
        
    } catch (const std::exception& e) {
        response["success"] = false;
        response["error_message"] = e.what();
    }
    
    auto end_time = std::chrono::high_resolution_clock::now();
    double processing_time = std::chrono::duration_cast<std::chrono::microseconds>(
        end_time - start_time).count() / 1000.0;
    
    response["processing_time_ms"] = processing_time;
    return response.dump();
}

std::string RailwaySchedulerAPI::optimize_json(const std::string& json_input) {
    auto start_time = std::chrono::high_resolution_clock::now();
    json response;
    
    try {
        auto j_input = json::parse(json_input);
        std::vector<Train> trains;
        
        if (j_input.contains("trains") && j_input["trains"].is_array()) {
            for (const auto& j_train : j_input["trains"]) {
                trains.push_back(json_to_train(j_train));
            }
        }
        
        OptimizationResult result = optimize(trains);
        
        response["resolutions"] = json::array();
        for (const auto& res : result.resolutions) {
            response["resolutions"].push_back({
                {"train_id", res.train_id},
                {"time_adjustment_min", res.time_adjustment_min},
                {"new_track", res.new_track},
                {"confidence", res.confidence}
            });
        }
        
        response["remaining_conflicts"] = json::array();
        for (const auto& c : result.remaining_conflicts) {
            response["remaining_conflicts"].push_back(conflict_to_json(c));
        }
        
        response["total_delay_minutes"] = result.total_delay_minutes;
        response["optimization_time_ms"] = result.optimization_time_ms;
        response["success"] = result.success;
        if (!result.error_message.empty()) {
            response["error_message"] = result.error_message;
        }
        
    } catch (const std::exception& e) {
        response["success"] = false;
        response["error_message"] = e.what();
    }
    
    return response.dump();
}

std::string RailwaySchedulerAPI::get_statistics_json() const {
    double avg_time_ms;
    int total_optimizations;
    get_statistics(avg_time_ms, total_optimizations);
    
    json response = {
        {"version", version()},
        {"ml_ready", is_ml_ready()},
        {"avg_optimization_time_ms", avg_time_ms},
        {"total_optimizations", total_optimizations}
    };
    
    return response.dump();
}

} // namespace railway

} // namespace railway
