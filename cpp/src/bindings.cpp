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
        .def_readwrite("planned_route", &Train::planned_route)
        .def_readwrite("route_index", &Train::route_index)
        .def_readwrite("position_on_track", &Train::position_on_track)
        .def_readwrite("has_arrived", &Train::has_arrived)
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
        .def_readwrite("estimated_time_min", &Conflict::estimated_time_min)
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
        .def_readwrite("confidence", &ScheduleAdjustment::confidence)
        .def("__repr__", [](const ScheduleAdjustment& a) {
            return "<Adjustment train=" + std::to_string(a.train_id) + 
                   " delay=" + std::to_string(a.time_adjustment_minutes) + "min" +
                   " confidence=" + std::to_string(a.confidence) +
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
             py::arg("num_stations") = 10)
        
        .def("initialize_network", &RailwayScheduler::initialize_network)
        .def("add_train", &RailwayScheduler::add_train)
        .def("remove_train", &RailwayScheduler::remove_train)
        .def("update_train_state", &RailwayScheduler::update_train_state)
        .def("step", &RailwayScheduler::step)
        .def("detect_conflicts", &RailwayScheduler::detect_conflicts)
        .def("are_trains_in_conflict", &RailwayScheduler::are_trains_in_conflict)
        .def("predict_future_conflicts", &RailwayScheduler::predict_future_conflicts)
        .def("resolve_conflicts", &RailwayScheduler::resolve_conflicts)
        .def("apply_adjustments", &RailwayScheduler::apply_adjustments)
        .def("optimize_network", &RailwayScheduler::optimize_network)
        .def("load_ml_model", &RailwayScheduler::load_ml_model)
        .def("predict_with_ml", &RailwayScheduler::predict_with_ml)
        .def("get_network_state", &RailwayScheduler::get_network_state)
        .def("get_train_info", &RailwayScheduler::get_train_info)
        .def("get_statistics", &RailwayScheduler::get_statistics)
        .def("get_event_log", &RailwayScheduler::get_event_log);
    
    m.attr("__version__") = "0.1.0";
}
