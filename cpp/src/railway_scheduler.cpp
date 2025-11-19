/*
 * Implementazione core dello scheduler in C++.
 */

#include "railway_scheduler.h"
#include <algorithm>
#include <cmath>
#include <sstream>
#include <iomanip>

namespace railway {

// ============================================================================
// RailwayScheduler Implementation
// ============================================================================

RailwayScheduler::RailwayScheduler(int num_tracks, int num_stations)
    : ml_model_handle_(nullptr), ml_model_loaded_(false) {
    // Inizializzazione
    log_event("RailwayScheduler initialized with " + 
              std::to_string(num_tracks) + " tracks and " + 
              std::to_string(num_stations) + " stations");
}

RailwayScheduler::~RailwayScheduler() {
    // Cleanup
}

void RailwayScheduler::initialize_network(
    const std::vector<Track>& tracks,
    const std::vector<Station>& stations) {
    
    tracks_.clear();
    stations_.clear();
    
    for (const auto& track : tracks) {
        tracks_[track.id] = track;
    }
    
    for (const auto& station : stations) {
        stations_[station.id] = station;
    }
    
    log_event("Network initialized: " + std::to_string(tracks.size()) + 
              " tracks, " + std::to_string(stations.size()) + " stations");
}

void RailwayScheduler::add_train(const Train& train) {
    trains_[train.id] = train;
    
    // Aggiorna track
    if (tracks_.count(train.current_track)) {
        tracks_[train.current_track].active_train_ids.push_back(train.id);
    }
    
    log_event("Train " + std::to_string(train.id) + " added to track " + 
              std::to_string(train.current_track));
}

void RailwayScheduler::remove_train(int train_id) {
    if (trains_.count(train_id)) {
        int track_id = trains_[train_id].current_track;
        trains_.erase(train_id);
        
        // Rimuovi da track
        if (tracks_.count(track_id)) {
            auto& train_ids = tracks_[track_id].active_train_ids;
            train_ids.erase(
                std::remove(train_ids.begin(), train_ids.end(), train_id),
                train_ids.end()
            );
        }
        
        log_event("Train " + std::to_string(train_id) + " removed");
    }
}

void RailwayScheduler::update_train_state(int train_id, 
                                          double position_km,
                                          double velocity_kmh,
                                          bool is_delayed) {
    if (trains_.count(train_id)) {
        trains_[train_id].position_km = position_km;
        trains_[train_id].velocity_kmh = velocity_kmh;
        trains_[train_id].is_delayed = is_delayed;
        trains_[train_id].last_update = std::chrono::system_clock::now();
    }
}

std::vector<Conflict> RailwayScheduler::detect_conflicts() const {
    std::vector<Conflict> conflicts;
    
    // Raggruppa treni per binario
    std::unordered_map<int, std::vector<int>> trains_by_track;
    for (const auto& [train_id, train] : trains_) {
        trains_by_track[train.current_track].push_back(train_id);
    }
    
    // Controlla conflitti su ogni binario
    for (const auto& [track_id, train_ids] : trains_by_track) {
        if (!tracks_.count(track_id)) continue;
        
        const Track& track = tracks_.at(track_id);
        
        // Controlla ogni coppia di treni
        for (size_t i = 0; i < train_ids.size(); ++i) {
            for (size_t j = i + 1; j < train_ids.size(); ++j) {
                const Train& t1 = trains_.at(train_ids[i]);
                const Train& t2 = trains_.at(train_ids[j]);
                
                if (track.is_single_track) {
                    // Binario singolo: controlla collisioni frontali
                    if (check_single_track_collision(t1, t2, track)) {
                        Conflict conflict;
                        conflict.train1_id = t1.id;
                        conflict.train2_id = t2.id;
                        conflict.track_id = track_id;
                        conflict.conflict_type = "head_on";
                        conflict.estimated_collision_time_minutes = calculate_meeting_time(t1, t2);
                        conflict.severity = 10; // Massima gravità
                        conflicts.push_back(conflict);
                    }
                } else {
                    // Binario multiplo: controlla se troppo vicini
                    double distance = std::abs(t1.position_km - t2.position_km);
                    if (distance < 2.0) { // Meno di 2km
                        Conflict conflict;
                        conflict.train1_id = t1.id;
                        conflict.train2_id = t2.id;
                        conflict.track_id = track_id;
                        conflict.conflict_type = "overtaking";
                        conflict.estimated_collision_time_minutes = 
                            distance / ((t1.velocity_kmh + t2.velocity_kmh) / 2.0) * 60.0;
                        conflict.severity = 5;
                        conflicts.push_back(conflict);
                    }
                }
            }
        }
        
        // Controlla capacità binario
        if (train_ids.size() > static_cast<size_t>(track.capacity)) {
            // Crea conflitti di capacità
            for (size_t i = track.capacity; i < train_ids.size(); ++i) {
                Conflict conflict;
                conflict.train1_id = train_ids[i];
                conflict.train2_id = -1; // No specific train
                conflict.track_id = track_id;
                conflict.conflict_type = "capacity_exceeded";
                conflict.estimated_collision_time_minutes = 0;
                conflict.severity = 7;
                conflicts.push_back(conflict);
            }
        }
    }
    
    return conflicts;
}

bool RailwayScheduler::are_trains_in_conflict(int train1_id, int train2_id) const {
    auto conflicts = detect_conflicts();
    
    for (const auto& conflict : conflicts) {
        if ((conflict.train1_id == train1_id && conflict.train2_id == train2_id) ||
            (conflict.train1_id == train2_id && conflict.train2_id == train1_id)) {
            return true;
        }
    }
    
    return false;
}

std::vector<Conflict> RailwayScheduler::predict_future_conflicts(
    double time_horizon_minutes) const {
    
    std::vector<Conflict> future_conflicts;
    
    // Simula posizioni future dei treni
    std::unordered_map<int, Train> future_trains;
    
    for (const auto& [train_id, train] : trains_) {
        Train future_train = train;
        
        // Calcola posizione futura
        double distance_traveled = (train.velocity_kmh / 60.0) * time_horizon_minutes;
        future_train.position_km += distance_traveled;
        
        // Clamp alla lunghezza del binario
        if (tracks_.count(train.current_track)) {
            double track_length = tracks_.at(train.current_track).length_km;
            future_train.position_km = std::min(future_train.position_km, track_length);
        }
        
        future_trains[train_id] = future_train;
    }
    
    // Rilevamento conflitti su posizioni future
    // (Logica simile a detect_conflicts ma su future_trains)
    
    return future_conflicts;
}

std::vector<ScheduleAdjustment> RailwayScheduler::resolve_conflicts(
    const std::vector<Conflict>& conflicts) {
    
    if (ml_model_loaded_) {
        // Usa ML model se disponibile
        NetworkState state = get_network_state();
        return predict_with_ml(state, conflicts);
    } else {
        // Fallback ad euristiche con supporto cambio binario
        return ConflictResolver::resolve_by_priority(conflicts, trains_, tracks_);
    }
}

void RailwayScheduler::apply_adjustments(
    const std::vector<ScheduleAdjustment>& adjustments) {
    
    for (const auto& adj : adjustments) {
        if (trains_.count(adj.train_id)) {
            Train& train = trains_[adj.train_id];
            
            // Applica ritardo temporale
            train.scheduled_arrival_minutes += adj.time_adjustment_minutes;
            
            if (adj.time_adjustment_minutes > 0) {
                train.is_delayed = true;
                train.delay_minutes += adj.time_adjustment_minutes;
            }
            
            // Cambio binario se necessario
            if (adj.new_track_id >= 0 && adj.new_track_id != train.current_track) {
                // Rimuovi da vecchio binario
                if (tracks_.count(train.current_track)) {
                    auto& old_trains = tracks_[train.current_track].active_train_ids;
                    old_trains.erase(
                        std::remove(old_trains.begin(), old_trains.end(), train.id),
                        old_trains.end()
                    );
                }
                
                // Aggiungi a nuovo binario
                train.current_track = adj.new_track_id;
                if (tracks_.count(adj.new_track_id)) {
                    tracks_[adj.new_track_id].active_train_ids.push_back(train.id);
                }
            }
            
            log_event("Applied adjustment to train " + std::to_string(adj.train_id) + 
                     ": " + adj.reason);
        }
    }
}

void RailwayScheduler::optimize_network() {
    // Ottimizzazione globale della rete
    auto conflicts = detect_conflicts();
    
    if (!conflicts.empty()) {
        auto adjustments = resolve_conflicts(conflicts);
        apply_adjustments(adjustments);
        
        log_event("Network optimization: resolved " + 
                 std::to_string(conflicts.size()) + " conflicts");
    }
}

bool RailwayScheduler::load_ml_model(const std::string& model_path) {
    // TODO: Implementazione con LibTorch
    // Per ora stub
    log_event("ML model loading from: " + model_path);
    ml_model_loaded_ = false;
    return false;
}

std::vector<ScheduleAdjustment> RailwayScheduler::predict_with_ml(
    const NetworkState& state,
    const std::vector<Conflict>& conflicts) {
    
    // TODO: Implementazione con LibTorch
    // Per ora fallback con supporto cambio binario
    return ConflictResolver::resolve_by_priority(conflicts, trains_, tracks_);
}

NetworkState RailwayScheduler::get_network_state() const {
    NetworkState state;
    
    state.timestamp = std::chrono::system_clock::now();
    
    for (const auto& [_, train] : trains_) {
        state.trains.push_back(train);
    }
    
    for (const auto& [_, track] : tracks_) {
        state.tracks.push_back(track);
    }
    
    for (const auto& [_, station] : stations_) {
        state.stations.push_back(station);
    }
    
    return state;
}

Train RailwayScheduler::get_train_info(int train_id) const {
    if (trains_.count(train_id)) {
        return trains_.at(train_id);
    }
    return Train();
}

RailwayScheduler::Statistics RailwayScheduler::get_statistics() const {
    Statistics stats;
    
    stats.total_trains = trains_.size();
    stats.delayed_trains = 0;
    stats.average_delay_minutes = 0.0;
    
    for (const auto& [_, train] : trains_) {
        if (train.is_delayed) {
            stats.delayed_trains++;
            stats.average_delay_minutes += train.delay_minutes;
        }
    }
    
    if (stats.delayed_trains > 0) {
        stats.average_delay_minutes /= stats.delayed_trains;
    }
    
    stats.active_conflicts = detect_conflicts().size();
    
    // Calcola efficienza (1.0 = nessun ritardo, 0.0 = tutti in ritardo)
    if (stats.total_trains > 0) {
        stats.network_efficiency = 1.0 - (static_cast<double>(stats.delayed_trains) / 
                                         stats.total_trains);
    } else {
        stats.network_efficiency = 1.0;
    }
    
    return stats;
}

std::vector<std::string> RailwayScheduler::get_event_log(int max_events) const {
    int start = std::max(0, static_cast<int>(event_log_.size()) - max_events);
    return std::vector<std::string>(event_log_.begin() + start, event_log_.end());
}

// ========================================
// Internal Helpers
// ========================================

bool RailwayScheduler::check_single_track_collision(
    const Train& t1, const Train& t2, const Track& track) const {
    
    // Determina direzione treni
    bool t1_forward = t1.position_km < track.length_km / 2.0;
    bool t2_forward = t2.position_km < track.length_km / 2.0;
    
    // Se stessa direzione, no collisione frontale
    if (t1_forward == t2_forward) {
        return false;
    }
    
    // Direzioni opposte: calcola tempo di incontro
    double meeting_time = calculate_meeting_time(t1, t2);
    
    // Conflitto se incontro entro 5 minuti
    return meeting_time < 5.0 && meeting_time > 0;
}

double RailwayScheduler::calculate_meeting_time(const Train& t1, const Train& t2) const {
    double distance = std::abs(t1.position_km - t2.position_km);
    double relative_velocity = t1.velocity_kmh + t2.velocity_kmh;
    
    if (relative_velocity < 0.1) {
        return std::numeric_limits<double>::infinity();
    }
    
    return (distance / relative_velocity) * 60.0; // in minuti
}

std::vector<int> RailwayScheduler::find_alternative_route(
    int train_id, int destination) const {
    // TODO: Implementare algoritmo pathfinding (Dijkstra/A*)
    return std::vector<int>();
}

std::vector<Conflict> RailwayScheduler::prioritize_conflicts(
    const std::vector<Conflict>& conflicts) const {
    
    std::vector<Conflict> prioritized = conflicts;
    
    // Ordina per severità (decrescente)
    std::sort(prioritized.begin(), prioritized.end(),
              [](const Conflict& a, const Conflict& b) {
                  return a.severity > b.severity;
              });
    
    return prioritized;
}

void RailwayScheduler::log_event(const std::string& message) {
    auto now = std::chrono::system_clock::now();
    std::string timestamp = format_timestamp(now);
    event_log_.push_back("[" + timestamp + "] " + message);
    
    // Limita dimensione log
    if (event_log_.size() > 1000) {
        event_log_.erase(event_log_.begin());
    }
}

// ============================================================================
// ConflictResolver Implementation
// ============================================================================

std::vector<ScheduleAdjustment> ConflictResolver::resolve_by_priority(
    const std::vector<Conflict>& conflicts,
    const std::unordered_map<int, Train>& trains,
    const std::unordered_map<int, Track>& tracks) {
    
    std::vector<ScheduleAdjustment> adjustments;
    
    for (const auto& conflict : conflicts) {
        if (conflict.train2_id < 0) continue; // Skip capacity conflicts
        
        const Train& t1 = trains.at(conflict.train1_id);
        const Train& t2 = trains.at(conflict.train2_id);
        
        ScheduleAdjustment adj;
        
        // Identifica il treno a priorità minore
        bool t1_lower_priority = t1.priority < t2.priority;
        const Train& lower_priority_train = t1_lower_priority ? t1 : t2;
        const Train& higher_priority_train = t1_lower_priority ? t2 : t1;
        
        adj.train_id = lower_priority_train.id;
        
        // STRATEGIA 1: Prova cambio binario in stazione
        bool can_change_track = false;
        int alternative_track = -1;
        
        if (conflict.track_id == lower_priority_train.current_track &&
            conflict.track_id == higher_priority_train.current_track) {
            
            // Verifica se il treno è vicino a una stazione
            if (tracks.count(conflict.track_id)) {
                const Track& current_track = tracks.at(conflict.track_id);
                
                if (is_near_station(lower_priority_train, current_track, 5.0)) {
                    // Cerca binario alternativo usando la funzione helper
                    alternative_track = find_alternative_track(
                        lower_priority_train,
                        conflict.track_id,
                        tracks,
                        trains
                    );
                    
                    can_change_track = (alternative_track >= 0);
                }
            }
        }
        
        if (can_change_track && alternative_track >= 0) {
            // RISOLUZIONE CON CAMBIO BINARIO IN STAZIONE
            adj.time_adjustment_minutes = 0.5; // Minimo ritardo per manovra cambio binario
            adj.new_track_id = alternative_track;
            adj.new_platform = -1;
            adj.reason = "Track switch at station to avoid conflict (priority-based)";
            adj.confidence = 0.90; // Alta confidenza - cambio binario molto efficace
        } else {
            // RISOLUZIONE CON RITARDO TEMPORALE (fallback)
            adj.time_adjustment_minutes = 5.0 * conflict.severity;
            adj.new_track_id = -1;
            adj.new_platform = -1;
            
            if (tracks.count(conflict.track_id) && 
                is_near_station(lower_priority_train, tracks.at(conflict.track_id), 5.0)) {
                adj.reason = "Time delay to avoid conflict (no alternative track available at station)";
            } else {
                adj.reason = "Time delay to avoid conflict (not near station for track switch)";
            }
            adj.confidence = 0.75; // Media confidenza - solo ritardo
        }
        
        adjustments.push_back(adj);
    }
    
    return adjustments;
}

int ConflictResolver::find_alternative_track(
    const Train& train,
    int current_track_id,
    const std::unordered_map<int, Track>& tracks,
    const std::unordered_map<int, Train>& trains) {
    
    if (!tracks.count(current_track_id)) {
        return -1;
    }
    
    const Track& current_track = tracks.at(current_track_id);
    
    // Itera sui binari per trovare alternative
    for (const auto& [track_id, track] : tracks) {
        if (track_id == current_track_id) continue;
        
        // CRITERIO 1: Deve connettere le stesse stazioni (o stazioni compatibili)
        bool connects_destination = false;
        for (int station_id : track.station_ids) {
            if (station_id == train.destination_station) {
                connects_destination = true;
                break;
            }
        }
        
        if (!connects_destination) {
            continue; // Skip binari che non portano a destinazione
        }
        
        // CRITERIO 2: Non deve essere congestionato
        int trains_on_track = 0;
        for (const auto& [tid, t] : trains) {
            if (t.current_track == track_id) {
                trains_on_track++;
            }
        }
        
        // Verifica capacità
        if (trains_on_track >= track.capacity) {
            continue; // Binario pieno
        }
        
        // CRITERIO 3: Preferisci binari multi-track su single-track
        if (track.is_single_track && !current_track.is_single_track) {
            continue; // Evita downgrade a single-track
        }
        
        // Binario alternativo valido trovato!
        return track_id;
    }
    
    return -1; // Nessun binario alternativo disponibile
}

bool ConflictResolver::is_near_station(
    const Train& train,
    const Track& track,
    double max_distance_km) {
    
    // Verifica distanza dalle stazioni sul binario
    // In un sistema reale, dovresti avere le posizioni esatte delle stazioni
    // Per ora, assumiamo stazioni a inizio (0km) e fine binario (length_km)
    
    double distance_to_start = std::abs(train.position_km);
    double distance_to_end = std::abs(train.position_km - track.length_km);
    
    // Anche stazioni intermedie ogni ~50km (semplificato)
    double min_distance = std::min(distance_to_start, distance_to_end);
    
    // Verifica se c'è una stazione intermedia vicina
    for (double station_pos = 50.0; station_pos < track.length_km; station_pos += 50.0) {
        double distance = std::abs(train.position_km - station_pos);
        min_distance = std::min(min_distance, distance);
    }
    
    return min_distance <= max_distance_km;
}

std::vector<ScheduleAdjustment> ConflictResolver::minimize_total_delay(
    const std::vector<Conflict>& conflicts,
    const std::unordered_map<int, Train>& trains,
    const std::unordered_map<int, Track>& tracks) {
    
    // TODO: Implementare ottimizzazione globale
    return resolve_by_priority(conflicts, trains, tracks);
}

std::vector<ScheduleAdjustment> ConflictResolver::resolve_single_track_conflicts(
    const std::vector<Conflict>& conflicts,
    const std::unordered_map<int, Train>& trains,
    const std::unordered_map<int, Track>& tracks) {
    
    std::vector<ScheduleAdjustment> adjustments;
    
    // Raggruppa conflitti per binario
    std::unordered_map<int, std::vector<Conflict>> conflicts_by_track;
    for (const auto& conflict : conflicts) {
        conflicts_by_track[conflict.track_id].push_back(conflict);
    }
    
    for (const auto& [track_id, track_conflicts] : conflicts_by_track) {
        auto track_it = tracks.find(track_id);
        if (track_it == tracks.end()) continue;
        
        const Track& track = track_it->second;
        
        // Caso critico: binario unico con treni in direzioni opposte
        if (track.is_single_track && track_conflicts.size() >= 1) {
            
            // Identifica treni in conflitto
            std::vector<int> conflicting_train_ids;
            for (const auto& conflict : track_conflicts) {
                conflicting_train_ids.push_back(conflict.train1_id);
                if (conflict.train2_id != -1) {
                    conflicting_train_ids.push_back(conflict.train2_id);
                }
            }
            
            // Rimuovi duplicati
            std::sort(conflicting_train_ids.begin(), conflicting_train_ids.end());
            conflicting_train_ids.erase(
                std::unique(conflicting_train_ids.begin(), conflicting_train_ids.end()),
                conflicting_train_ids.end()
            );
            
            // Per ogni treno in conflitto, cerca di deviarlo in stazione
            for (int train_id : conflicting_train_ids) {
                auto train_it = trains.find(train_id);
                if (train_it == trains.end()) continue;
                
                const Train& train = train_it->second;
                
                // Strategia 1: Se il treno è vicino a una stazione, devialo su binario di stazione
                if (is_near_station(train, track, 10.0)) {  // 10km threshold per binario unico
                    
                    // Cerca binari di stazione disponibili (multi-track)
                    int best_station_track = -1;
                    int min_train_count = 9999;
                    
                    for (const auto& [other_track_id, other_track] : tracks) {
                        // Cerca binari multi-track (stazioni) connessi
                        if (other_track_id == track_id) continue;
                        if (other_track.is_single_track) continue;
                        
                        // Verifica se binario connette alla destinazione del treno
                        bool connects = false;
                        for (int station_id : other_track.station_ids) {
                            if (station_id == train.destination_station) {
                                connects = true;
                                break;
                            }
                        }
                        
                        // Preferisci binari con meno treni (meno congestione)
                        int train_count = other_track.active_train_ids.size();
                        if (connects && train_count < min_train_count && train_count < other_track.capacity) {
                            min_train_count = train_count;
                            best_station_track = other_track_id;
                        }
                    }
                    
                    if (best_station_track != -1) {
                        // Devia il treno su binario di stazione
                        ScheduleAdjustment adj;
                        adj.train_id = train_id;
                        adj.new_track_id = best_station_track;
                        adj.time_adjustment_minutes = 1.0;  // Tempo per cambio binario
                        adj.new_platform = -1;
                        adj.reason = "Single-track conflict: diverted to station track " + 
                                   std::to_string(best_station_track);
                        adj.confidence = 0.85;
                        adjustments.push_back(adj);
                        continue;  // Vai al prossimo treno
                    }
                }
                
                // Strategia 2: Se non può deviare, il treno con priorità minore aspetta
                // Trova il treno con priorità massima nel conflitto
                int max_priority = 0;
                int priority_train_id = -1;
                
                for (int id : conflicting_train_ids) {
                    auto t_it = trains.find(id);
                    if (t_it != trains.end() && t_it->second.priority > max_priority) {
                        max_priority = t_it->second.priority;
                        priority_train_id = id;
                    }
                }
                
                // Se questo non è il treno prioritario, aspetta
                if (train_id != priority_train_id) {
                    ScheduleAdjustment adj;
                    adj.train_id = train_id;
                    adj.new_track_id = -1;  // Resta sul binario
                    adj.time_adjustment_minutes = 8.0 * (conflicting_train_ids.size() - 1);  // Aspetta
                    adj.new_platform = -1;
                    adj.reason = "Single-track conflict: waiting for priority train " + 
                               std::to_string(priority_train_id);
                    adj.confidence = 0.70;
                    adjustments.push_back(adj);
                }
            }
        }
    }
    
    // Se non abbiamo trovato soluzioni specifiche, usa risoluzione standard
    if (adjustments.empty()) {
        return resolve_by_priority(conflicts, trains, tracks);
    }
    
    return adjustments;
}

// ============================================================================
// Utility Functions
// ============================================================================

double calculate_track_distance(double pos1_km, double pos2_km) {
    return std::abs(pos1_km - pos2_km);
}

std::chrono::system_clock::time_point minutes_to_timestamp(double minutes) {
    auto now = std::chrono::system_clock::now();
    auto duration = std::chrono::minutes(static_cast<int>(minutes));
    return now + duration;
}

std::string format_timestamp(const std::chrono::system_clock::time_point& tp) {
    auto time_t = std::chrono::system_clock::to_time_t(tp);
    std::stringstream ss;
    ss << std::put_time(std::localtime(&time_t), "%Y-%m-%d %H:%M:%S");
    return ss.str();
}

} // namespace railway
