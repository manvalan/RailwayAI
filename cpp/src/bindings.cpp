/*
 * Binding Python per l'interfaccia C++ usando pybind11.
 * Permette di chiamare l'execution engine C++ da Python.
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/chrono.h>
#include "railway_scheduler.h"

namespace py = pybind11;
using namespace railway;

PYBIND11_MODULE(railway_cpp, m) {
    m.doc() = "Railway AI Scheduler - C++ Bindings";
    
    // ========================================================================
    // Structures
    // ========================================================================
    
    py::class_<Train>(m, "Train")
        .def(py::init<>())
        .def_readwrite("id", &Train::id)
        .def_readwrite("current_track", &Train::current_track)
        .def_readwrite("position_km", &Train::position_km)
        .def_readwrite("velocity_kmh", &Train::velocity_kmh)
        .def_readwrite("scheduled_arrival_minutes", &Train::scheduled_arrival_minutes)
        .def_readwrite("destination_station", &Train::destination_station)
        .def_readwrite("priority", &Train::priority)
        .def_readwrite("is_delayed", &Train::is_delayed)
        .def_readwrite("delay_minutes", &Train::delay_minutes)
        .def("__repr__", [](const Train& t) {
            return "<Train id=" + std::to_string(t.id) + 
                   " track=" + std::to_string(t.current_track) + 
                   " pos=" + std::to_string(t.position_km) + "km>";
        });
    
    py::class_<Track>(m, "Track")
        .def(py::init<>())
        .def_readwrite("id", &Track::id)
        .def_readwrite("length_km", &Track::length_km)
        .def_readwrite("is_single_track", &Track::is_single_track)
        .def_readwrite("capacity", &Track::capacity)
        .def_readwrite("station_ids", &Track::station_ids)
        .def_readwrite("active_train_ids", &Track::active_train_ids)
        .def("__repr__", [](const Track& t) {
            return "<Track id=" + std::to_string(t.id) + 
                   " length=" + std::to_string(t.length_km) + "km" +
                   " single=" + (t.is_single_track ? "true" : "false") + ">";
        });
    
    py::class_<Station>(m, "Station")
        .def(py::init<>())
        .def_readwrite("id", &Station::id)
        .def_readwrite("name", &Station::name)
        .def_readwrite("num_platforms", &Station::num_platforms)
        .def_readwrite("connected_track_ids", &Station::connected_track_ids)
        .def_readwrite("platform_occupied", &Station::platform_occupied)
        .def("__repr__", [](const Station& s) {
            return "<Station id=" + std::to_string(s.id) + 
                   " name='" + s.name + "'" +
                   " platforms=" + std::to_string(s.num_platforms) + ">";
        });
    
    py::class_<Conflict>(m, "Conflict")
        .def(py::init<>())
        .def_readwrite("train1_id", &Conflict::train1_id)
        .def_readwrite("train2_id", &Conflict::train2_id)
        .def_readwrite("track_id", &Conflict::track_id)
        .def_readwrite("estimated_collision_time_minutes", &Conflict::estimated_collision_time_minutes)
        .def_readwrite("conflict_type", &Conflict::conflict_type)
        .def_readwrite("severity", &Conflict::severity)
        .def("__repr__", [](const Conflict& c) {
            return "<Conflict trains=(" + std::to_string(c.train1_id) + "," + 
                   std::to_string(c.train2_id) + ") type=" + c.conflict_type + 
                   " severity=" + std::to_string(c.severity) + ">";
        });
    
    py::class_<ScheduleAdjustment>(m, "ScheduleAdjustment")
        .def(py::init<>())
        .def_readwrite("train_id", &ScheduleAdjustment::train_id)
        .def_readwrite("time_adjustment_minutes", &ScheduleAdjustment::time_adjustment_minutes)
        .def_readwrite("new_track_id", &ScheduleAdjustment::new_track_id)
        .def_readwrite("new_platform", &ScheduleAdjustment::new_platform)
        .def_readwrite("reason", &ScheduleAdjustment::reason)
        .def("__repr__", [](const ScheduleAdjustment& a) {
            return "<Adjustment train=" + std::to_string(a.train_id) + 
                   " delay=" + std::to_string(a.time_adjustment_minutes) + "min" +
                   " reason='" + a.reason + "'>";
        });
    
    py::class_<NetworkState>(m, "NetworkState")
        .def(py::init<>())
        .def_readwrite("trains", &NetworkState::trains)
        .def_readwrite("tracks", &NetworkState::tracks)
        .def_readwrite("stations", &NetworkState::stations)
        .def_readwrite("timestamp", &NetworkState::timestamp);
    
    py::class_<RailwayScheduler::Statistics>(m, "Statistics")
        .def(py::init<>())
        .def_readwrite("total_trains", &RailwayScheduler::Statistics::total_trains)
        .def_readwrite("delayed_trains", &RailwayScheduler::Statistics::delayed_trains)
        .def_readwrite("active_conflicts", &RailwayScheduler::Statistics::active_conflicts)
        .def_readwrite("average_delay_minutes", &RailwayScheduler::Statistics::average_delay_minutes)
        .def_readwrite("network_efficiency", &RailwayScheduler::Statistics::network_efficiency)
        .def("__repr__", [](const RailwayScheduler::Statistics& s) {
            return "<Statistics trains=" + std::to_string(s.total_trains) + 
                   " delayed=" + std::to_string(s.delayed_trains) + 
                   " conflicts=" + std::to_string(s.active_conflicts) + 
                   " efficiency=" + std::to_string(s.network_efficiency) + ">";
        });
    
    // ========================================================================
    // Main Scheduler Class
    // ========================================================================
    
    py::class_<RailwayScheduler>(m, "RailwayScheduler")
        .def(py::init<int, int>(), 
             py::arg("num_tracks") = 20,
             py::arg("num_stations") = 10,
             "Inizializza lo scheduler con numero di binari e stazioni")
        
        // Network management
        .def("initialize_network", &RailwayScheduler::initialize_network,
             "Inizializza la rete ferroviaria con binari e stazioni")
        .def("add_train", &RailwayScheduler::add_train,
             "Aggiunge un treno al sistema")
        .def("remove_train", &RailwayScheduler::remove_train,
             "Rimuove un treno dal sistema")
        .def("update_train_state", &RailwayScheduler::update_train_state,
             py::arg("train_id"),
             py::arg("position_km"),
             py::arg("velocity_kmh"),
             py::arg("is_delayed") = false,
             "Aggiorna posizione e stato di un treno")
        
        // Conflict detection
        .def("detect_conflicts", &RailwayScheduler::detect_conflicts,
             "Rileva conflitti nella rete corrente")
        .def("are_trains_in_conflict", &RailwayScheduler::are_trains_in_conflict,
             "Verifica se due treni specifici sono in conflitto")
        .def("predict_future_conflicts", &RailwayScheduler::predict_future_conflicts,
             py::arg("time_horizon_minutes"),
             "Predice conflitti futuri entro un orizzonte temporale")
        
        // Schedule optimization
        .def("resolve_conflicts", &RailwayScheduler::resolve_conflicts,
             "Risolve conflitti e propone aggiustamenti")
        .def("apply_adjustments", &RailwayScheduler::apply_adjustments,
             "Applica aggiustamenti alla schedule")
        .def("optimize_network", &RailwayScheduler::optimize_network,
             "Ottimizza l'intera rete per efficienza")
        
        // ML integration
        .def("load_ml_model", &RailwayScheduler::load_ml_model,
             py::arg("model_path"),
             "Carica il modello ML addestrato")
        .def("predict_with_ml", &RailwayScheduler::predict_with_ml,
             py::arg("state"),
             py::arg("conflicts"),
             "Usa il modello ML per predire aggiustamenti")
        
        // Queries
        .def("get_network_state", &RailwayScheduler::get_network_state,
             "Ottieni lo stato corrente della rete")
        .def("get_train_info", &RailwayScheduler::get_train_info,
             "Ottieni informazioni su un treno specifico")
        .def("get_statistics", &RailwayScheduler::get_statistics,
             "Ottieni statistiche di performance")
        .def("get_event_log", &RailwayScheduler::get_event_log,
             py::arg("max_events") = 100,
             "Ottieni log degli eventi recenti")
        
        .def("__repr__", [](const RailwayScheduler& s) {
            auto stats = s.get_statistics();
            return "<RailwayScheduler trains=" + std::to_string(stats.total_trains) + 
                   " conflicts=" + std::to_string(stats.active_conflicts) + ">";
        });
    
    // ========================================================================
    // Conflict Resolver (static methods)
    // ========================================================================
    
    py::class_<ConflictResolver>(m, "ConflictResolver")
        .def_static("resolve_by_priority", &ConflictResolver::resolve_by_priority,
                   "Risolve conflitti basandosi su priorità treni")
        .def_static("minimize_total_delay", &ConflictResolver::minimize_total_delay,
                   "Risolve minimizzando il ritardo totale")
        .def_static("resolve_single_track_conflicts", 
                   &ConflictResolver::resolve_single_track_conflicts,
                   "Risolve conflitti su binari singoli");
    
    // ========================================================================
    // Utility Functions
    // ========================================================================
    
    m.def("calculate_track_distance", &calculate_track_distance,
          py::arg("pos1_km"), py::arg("pos2_km"),
          "Calcola distanza tra due punti su un binario");
    
    m.def("minutes_to_timestamp", &minutes_to_timestamp,
          py::arg("minutes"),
          "Converte minuti in timestamp");
    
    m.def("format_timestamp", &format_timestamp,
          py::arg("timestamp"),
          "Formatta un timestamp per logging");
    
    // ========================================================================
    // Module metadata
    // ========================================================================
    
    m.attr("__version__") = "0.1.0";
}
