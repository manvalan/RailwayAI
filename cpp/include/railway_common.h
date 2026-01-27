#ifndef RAILWAY_COMMON_H
#define RAILWAY_COMMON_H

#include <string>
#include <vector>
#include <chrono>

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
    int current_track;           ///< Current track ID
    double position_km;          ///< Current position in kilometers
    double velocity_kmh;         ///< Current velocity in km/h
    double scheduled_arrival_minutes; ///< Target arrival time
    int destination_station;     ///< Destination station ID
    int priority;                ///< Priority level (1-10)
    bool is_delayed;             ///< Whether train is currently delayed
    double delay_minutes;        ///< Current delay in minutes
    
    // Internal routing / simulation fields
    std::vector<int> planned_route;
    int route_index = 0;
    double position_on_track = 0.0;
    std::chrono::system_clock::time_point last_update;
    bool has_arrived = false;

    Train() : id(0), current_track(0), position_km(0), velocity_kmh(0), 
              scheduled_arrival_minutes(0), destination_station(0), 
              priority(5), is_delayed(false), delay_minutes(0) {}
};

/**
 * @brief Represents a track segment in the railway network
 */
struct RAILWAY_API Track {
    int id;                      ///< Unique track identifier
    double length_km;            ///< Track length in kilometers
    bool is_single_track;        ///< True if single-track
    int capacity;                ///< Maximum number of trains
    std::vector<int> station_ids; ///< Stations connected by this track
    
    // Internal simulation fields
    std::vector<int> active_train_ids;
};

/**
 * @brief Represents a railway station
 */
struct RAILWAY_API Station {
    int id;                      ///< Unique station identifier
    std::string name;            ///< Station name
    int num_platforms;           ///< Number of available platforms
    std::vector<int> connected_track_ids;
    std::vector<bool> platform_occupied;
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
    std::string conflict_type;   ///< type: head_on, overtaking, etc.
};

} // namespace railway

#endif // RAILWAY_COMMON_H
