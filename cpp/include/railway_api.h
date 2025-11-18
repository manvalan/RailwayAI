/**
 * @file railway_api.h
 * @brief Public C++ API for Railway AI Scheduler Library
 * 
 * This header provides a clean, stable interface for integrating the
 * Railway AI Scheduler into external C++ applications.
 * 
 * Usage:
 *   1. Link against librailwayai.dylib (macOS) or librailwayai.so (Linux)
 *   2. Include this header
 *   3. Create RailwaySchedulerAPI instance
 *   4. Call optimize() with your railway network data
 * 
 * @version 1.0.0
 * @date 2025-11-19
 */

#ifndef RAILWAY_API_H
#define RAILWAY_API_H

#include <string>
#include <vector>
#include <memory>
#include <cstdint>

// Export macros for shared library
#ifdef _WIN32
    #ifdef RAILWAY_API_EXPORTS
        #define RAILWAY_API __declspec(dllexport)
    #else
        #define RAILWAY_API __declspec(dllimport)
    #endif
#else
    #define RAILWAY_API __attribute__((visibility("default")))
#endif

namespace railway {

/**
 * @brief Represents a train in the railway network
 */
struct RAILWAY_API Train {
    int id;                      ///< Unique train identifier
    double position_km;          ///< Current position in kilometers
    double velocity_kmh;         ///< Current velocity in km/h
    int current_track;           ///< Current track ID
    int destination_station;     ///< Destination station ID
    double delay_minutes;        ///< Current delay in minutes
    int priority;                ///< Priority level (1-10, higher = more important)
    bool is_delayed;             ///< Whether train is currently delayed
};

/**
 * @brief Represents a track segment in the railway network
 */
struct RAILWAY_API Track {
    int id;                      ///< Unique track identifier
    double length_km;            ///< Track length in kilometers
    bool is_single_track;        ///< True if single-track (bidirectional conflicts)
    int capacity;                ///< Maximum number of trains
    std::vector<int> station_ids; ///< Stations connected by this track
};

/**
 * @brief Represents a railway station
 */
struct RAILWAY_API Station {
    int id;                      ///< Unique station identifier
    std::string name;            ///< Station name
    int num_platforms;           ///< Number of available platforms
};

/**
 * @brief Detected conflict between two trains
 */
struct RAILWAY_API Conflict {
    int train1_id;               ///< First train ID
    int train2_id;               ///< Second train ID
    int track_id;                ///< Track where conflict occurs
    double estimated_time_min;   ///< Estimated time until conflict (minutes)
    double severity;             ///< Conflict severity score (0.0-1.0)
};

/**
 * @brief Resolution action for a train
 */
struct RAILWAY_API Resolution {
    int train_id;                ///< Train to apply action to
    double time_adjustment_min;  ///< Time adjustment in minutes (negative = slow down)
    int new_track;               ///< New track assignment (-1 = no change)
    double confidence;           ///< ML model confidence (0.0-1.0)
};

/**
 * @brief Complete optimization result
 */
struct RAILWAY_API OptimizationResult {
    std::vector<Resolution> resolutions;     ///< Proposed resolutions
    std::vector<Conflict> remaining_conflicts; ///< Conflicts still present
    double total_delay_minutes;              ///< Total system delay after optimization
    double optimization_time_ms;             ///< Time taken to compute (milliseconds)
    bool success;                            ///< Whether optimization succeeded
    std::string error_message;               ///< Error message if failed
};

/**
 * @brief Configuration for the scheduler
 */
struct RAILWAY_API SchedulerConfig {
    bool use_ml_model;           ///< Use ML model (true) or C++ heuristics (false)
    std::string model_path;      ///< Path to .pth model file (if use_ml_model=true)
    int max_iterations;          ///< Maximum optimization iterations
    double convergence_threshold; ///< Stop when improvement < threshold
    bool verbose;                ///< Enable verbose logging
    
    SchedulerConfig() 
        : use_ml_model(true)
        , model_path("models/scheduler_supervised_best.pth")
        , max_iterations(100)
        , convergence_threshold(0.01)
        , verbose(false) {}
};

/**
 * @brief Main API class for Railway AI Scheduler
 * 
 * This class provides the primary interface for external applications
 * to use the Railway AI Scheduler library.
 * 
 * Example usage:
 * @code
 * railway::RailwaySchedulerAPI scheduler;
 * scheduler.initialize(config);
 * scheduler.set_network(tracks, stations);
 * 
 * auto result = scheduler.optimize(trains);
 * for (const auto& res : result.resolutions) {
 *     std::cout << "Train " << res.train_id 
 *               << " adjust time by " << res.time_adjustment_min << " min\n";
 * }
 * @endcode
 */
class RAILWAY_API RailwaySchedulerAPI {
public:
    /**
     * @brief Constructor
     */
    RailwaySchedulerAPI();
    
    /**
     * @brief Destructor
     */
    ~RailwaySchedulerAPI();
    
    /**
     * @brief Initialize the scheduler with configuration
     * @param config Scheduler configuration
     * @return true if initialization succeeded, false otherwise
     */
    bool initialize(const SchedulerConfig& config = SchedulerConfig());
    
    /**
     * @brief Set the railway network topology
     * @param tracks List of track segments
     * @param stations List of stations
     * @return true if network setup succeeded, false otherwise
     */
    bool set_network(const std::vector<Track>& tracks, 
                     const std::vector<Station>& stations);
    
    /**
     * @brief Detect conflicts in current train configuration
     * @param trains Current train states
     * @return List of detected conflicts
     */
    std::vector<Conflict> detect_conflicts(const std::vector<Train>& trains);
    
    /**
     * @brief Optimize train schedule to minimize delays and conflicts
     * @param trains Current train states
     * @return Optimization result with proposed resolutions
     */
    OptimizationResult optimize(const std::vector<Train>& trains);
    
    /**
     * @brief Get version information
     * @return Version string (e.g., "1.0.0")
     */
    static std::string version();
    
    /**
     * @brief Check if ML model is loaded and ready
     * @return true if ML model is available, false if using C++ fallback
     */
    bool is_ml_ready() const;
    
    /**
     * @brief Get performance statistics
     * @param avg_time_ms Average optimization time in milliseconds
     * @param total_optimizations Total number of optimizations performed
     */
    void get_statistics(double& avg_time_ms, int& total_optimizations) const;

private:
    class Impl;
    std::unique_ptr<Impl> pImpl; ///< PIMPL idiom for ABI stability
};

} // namespace railway

#endif // RAILWAY_API_H
