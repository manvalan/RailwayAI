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

// ============================================================================
// JSON API Implementation
// ============================================================================

namespace {
    // Helper: Simple JSON string builder
    class JsonBuilder {
    public:
        JsonBuilder& start_object() {
            json_ += "{";
            need_comma_ = false;
            return *this;
        }
        
        JsonBuilder& end_object() {
            json_ += "}";
            need_comma_ = true;
            return *this;
        }
        
        JsonBuilder& start_array(const std::string& key) {
            add_comma();
            json_ += "\"" + key + "\":[";
            need_comma_ = false;
            return *this;
        }
        
        JsonBuilder& end_array() {
            json_ += "]";
            need_comma_ = true;
            return *this;
        }
        
        JsonBuilder& add(const std::string& key, const std::string& value) {
            add_comma();
            json_ += "\"" + key + "\":\"" + value + "\"";
            return *this;
        }
        
        JsonBuilder& add(const std::string& key, int value) {
            add_comma();
            json_ += "\"" + key + "\":" + std::to_string(value);
            return *this;
        }
        
        JsonBuilder& add(const std::string& key, double value) {
            add_comma();
            json_ += "\"" + key + "\":" + std::to_string(value);
            return *this;
        }
        
        JsonBuilder& add(const std::string& key, bool value) {
            add_comma();
            json_ += "\"" + key + "\":" + (value ? "true" : "false");
            return *this;
        }
        
        JsonBuilder& array_separator() {
            if (need_comma_) json_ += ",";
            need_comma_ = true;
            return *this;
        }
        
        std::string str() const { return json_; }
        
    private:
        void add_comma() {
            if (need_comma_) json_ += ",";
            need_comma_ = true;
        }
        
        std::string json_;
        bool need_comma_ = false;
    };
    
    // Helper: Simple JSON parser for train data
    std::vector<Train> parse_trains_from_json(const std::string& json) {
        std::vector<Train> trains;
        
        // Very simple parser - finds "trains" array and extracts train objects
        size_t trains_pos = json.find("\"trains\"");
        if (trains_pos == std::string::npos) {
            return trains;
        }
        
        size_t array_start = json.find('[', trains_pos);
        if (array_start == std::string::npos) {
            return trains;
        }
        
        // Parse each train object
        size_t pos = array_start + 1;
        while (pos < json.size()) {
            // Find next object
            size_t obj_start = json.find('{', pos);
            if (obj_start == std::string::npos) break;
            
            size_t obj_end = json.find('}', obj_start);
            if (obj_end == std::string::npos) break;
            
            // Extract train data
            std::string obj = json.substr(obj_start, obj_end - obj_start + 1);
            Train train;
            
            // Parse fields (simple extraction)
            auto extract_int = [&](const std::string& key) -> int {
                size_t k = obj.find("\"" + key + "\"");
                if (k == std::string::npos) return 0;
                size_t colon = obj.find(':', k);
                if (colon == std::string::npos) return 0;
                size_t comma = obj.find_first_of(",}", colon);
                return std::stoi(obj.substr(colon + 1, comma - colon - 1));
            };
            
            auto extract_double = [&](const std::string& key) -> double {
                size_t k = obj.find("\"" + key + "\"");
                if (k == std::string::npos) return 0.0;
                size_t colon = obj.find(':', k);
                if (colon == std::string::npos) return 0.0;
                size_t comma = obj.find_first_of(",}", colon);
                return std::stod(obj.substr(colon + 1, comma - colon - 1));
            };
            
            auto extract_bool = [&](const std::string& key) -> bool {
                size_t k = obj.find("\"" + key + "\"");
                if (k == std::string::npos) return false;
                size_t colon = obj.find(':', k);
                if (colon == std::string::npos) return false;
                return obj.find("true", colon) < obj.find("false", colon);
            };
            
            train.id = extract_int("id");
            train.position_km = extract_double("position_km");
            train.velocity_kmh = extract_double("velocity_kmh");
            train.current_track = extract_int("current_track");
            train.destination_station = extract_int("destination_station");
            train.delay_minutes = extract_double("delay_minutes");
            train.priority = extract_int("priority");
            train.is_delayed = extract_bool("is_delayed");
            
            trains.push_back(train);
            
            // Check for end of array
            pos = obj_end + 1;
            size_t next_comma = json.find(',', pos);
            size_t array_end = json.find(']', pos);
            if (array_end < next_comma) break;
            pos = next_comma + 1;
        }
        
        return trains;
    }
}

std::string RailwaySchedulerAPI::detect_conflicts_json(const std::string& json_input) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    try {
        // Parse trains from JSON
        std::vector<Train> trains = parse_trains_from_json(json_input);
        
        // Detect conflicts
        std::vector<Conflict> conflicts = detect_conflicts(trains);
        
        // Build JSON response
        JsonBuilder json;
        json.start_object();
        json.start_array("conflicts");
        
        for (size_t i = 0; i < conflicts.size(); ++i) {
            if (i > 0) json.array_separator();
            
            json.start_object()
                .add("train1_id", conflicts[i].train1_id)
                .add("train2_id", conflicts[i].train2_id)
                .add("track_id", conflicts[i].track_id)
                .add("estimated_time_min", conflicts[i].estimated_time_min)
                .add("severity", conflicts[i].severity)
                .end_object();
        }
        
        json.end_array();
        json.add("total_conflicts", static_cast<int>(conflicts.size()));
        
        auto end_time = std::chrono::high_resolution_clock::now();
        auto duration = std::chrono::duration_cast<std::chrono::microseconds>(
            end_time - start_time);
        double processing_time = duration.count() / 1000.0;
        
        json.add("processing_time_ms", processing_time);
        json.add("success", true);
        json.end_object();
        
        return json.str();
        
    } catch (const std::exception& e) {
        JsonBuilder json;
        json.start_object()
            .start_array("conflicts").end_array()
            .add("total_conflicts", 0)
            .add("processing_time_ms", 0.0)
            .add("success", false)
            .add("error_message", e.what())
            .end_object();
        return json.str();
    }
}

std::string RailwaySchedulerAPI::optimize_json(const std::string& json_input) {
    auto start_time = std::chrono::high_resolution_clock::now();
    
    try {
        // Parse trains from JSON
        std::vector<Train> trains = parse_trains_from_json(json_input);
        
        // Optimize
        OptimizationResult result = optimize(trains);
        
        // Build JSON response
        JsonBuilder json;
        json.start_object();
        
        // Resolutions array
        json.start_array("resolutions");
        for (size_t i = 0; i < result.resolutions.size(); ++i) {
            if (i > 0) json.array_separator();
            
            json.start_object()
                .add("train_id", result.resolutions[i].train_id)
                .add("time_adjustment_min", result.resolutions[i].time_adjustment_min)
                .add("new_track", result.resolutions[i].new_track)
                .add("confidence", result.resolutions[i].confidence)
                .end_object();
        }
        json.end_array();
        
        // Remaining conflicts array
        json.start_array("remaining_conflicts");
        for (size_t i = 0; i < result.remaining_conflicts.size(); ++i) {
            if (i > 0) json.array_separator();
            
            json.start_object()
                .add("train1_id", result.remaining_conflicts[i].train1_id)
                .add("train2_id", result.remaining_conflicts[i].train2_id)
                .add("track_id", result.remaining_conflicts[i].track_id)
                .add("estimated_time_min", result.remaining_conflicts[i].estimated_time_min)
                .add("severity", result.remaining_conflicts[i].severity)
                .end_object();
        }
        json.end_array();
        
        json.add("total_delay_minutes", result.total_delay_minutes);
        json.add("optimization_time_ms", result.optimization_time_ms);
        json.add("success", result.success);
        json.add("error_message", result.error_message);
        json.end_object();
        
        return json.str();
        
    } catch (const std::exception& e) {
        JsonBuilder json;
        json.start_object()
            .start_array("resolutions").end_array()
            .start_array("remaining_conflicts").end_array()
            .add("total_delay_minutes", 0.0)
            .add("optimization_time_ms", 0.0)
            .add("success", false)
            .add("error_message", e.what())
            .end_object();
        return json.str();
    }
}

std::string RailwaySchedulerAPI::get_statistics_json() const {
    double avg_time_ms;
    int total_optimizations;
    get_statistics(avg_time_ms, total_optimizations);
    
    JsonBuilder json;
    json.start_object()
        .add("version", version())
        .add("ml_ready", is_ml_ready())
        .add("avg_optimization_time_ms", avg_time_ms)
        .add("total_optimizations", total_optimizations)
        .end_object();
    
    return json.str();
}

} // namespace railway
