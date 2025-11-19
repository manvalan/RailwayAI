/*
 * Header principale per l'interfaccia C++ dello scheduler ferroviario.
 * Definisce le strutture dati e le API per l'integrazione con Python.
 */

#ifndef RAILWAY_SCHEDULER_H
#define RAILWAY_SCHEDULER_H

#include <vector>
#include <string>
#include <memory>
#include <chrono>
#include <unordered_map>

namespace railway {

// ============================================================================
// Data Structures
// ============================================================================

/**
 * Rappresenta un treno nella rete ferroviaria.
 */
struct Train {
    int id;
    int current_track;
    double position_km;
    double velocity_kmh;
    double scheduled_arrival_minutes;
    int destination_station;
    int priority;
    bool is_delayed;
    double delay_minutes;
    
    // Timestamp per tracking real-time
    std::chrono::system_clock::time_point last_update;
};

/**
 * Rappresenta un binario.
 */
struct Track {
    int id;
    double length_km;
    bool is_single_track;
    int capacity;
    std::vector<int> station_ids;
    
    // Treni attualmente sul binario
    std::vector<int> active_train_ids;
};

/**
 * Rappresenta una stazione.
 */
struct Station {
    int id;
    std::string name;
    int num_platforms;
    std::vector<int> connected_track_ids;
    
    // Occupazione piattaforme
    std::vector<bool> platform_occupied;
};

/**
 * Rappresenta un conflitto tra due treni.
 */
struct Conflict {
    int train1_id;
    int train2_id;
    int track_id;
    double estimated_collision_time_minutes;
    std::string conflict_type; // "head_on", "overtaking", "station_congestion"
    int severity; // 1-10
};

/**
 * Soluzione proposta per risolvere conflitti.
 */
struct ScheduleAdjustment {
    int train_id;
    double time_adjustment_minutes; // Positivo = ritardo, negativo = anticipo
    int new_track_id; // -1 se nessun cambio binario
    int new_platform; // -1 se nessun cambio piattaforma
    std::string reason;
    double confidence = 0.50; // Confidenza della risoluzione (0.0-1.0)
};

/**
 * Stato completo della rete ferroviaria.
 */
struct NetworkState {
    std::vector<Train> trains;
    std::vector<Track> tracks;
    std::vector<Station> stations;
    std::chrono::system_clock::time_point timestamp;
};

// ============================================================================
// Core Scheduler Class
// ============================================================================

/**
 * Scheduler principale che interfaccia il modello ML con l'execution engine.
 */
class RailwayScheduler {
public:
    RailwayScheduler(int num_tracks = 20, int num_stations = 10);
    ~RailwayScheduler();
    
    // ========================================
    // Network Management
    // ========================================
    
    /**
     * Inizializza la rete ferroviaria con configurazione.
     */
    void initialize_network(
        const std::vector<Track>& tracks,
        const std::vector<Station>& stations
    );
    
    /**
     * Aggiunge un treno al sistema.
     */
    void add_train(const Train& train);
    
    /**
     * Rimuove un treno dal sistema.
     */
    void remove_train(int train_id);
    
    /**
     * Aggiorna la posizione e lo stato di un treno.
     */
    void update_train_state(int train_id, 
                           double position_km,
                           double velocity_kmh,
                           bool is_delayed = false);
    
    // ========================================
    // Conflict Detection
    // ========================================
    
    /**
     * Rileva tutti i conflitti nella rete corrente.
     * Usa algoritmi ottimizzati per detection in tempo reale.
     */
    std::vector<Conflict> detect_conflicts() const;
    
    /**
     * Verifica se due treni specifici sono in conflitto.
     */
    bool are_trains_in_conflict(int train1_id, int train2_id) const;
    
    /**
     * Predice conflitti futuri basandosi su traiettorie.
     */
    std::vector<Conflict> predict_future_conflicts(double time_horizon_minutes) const;
    
    // ========================================
    // Schedule Optimization
    // ========================================
    
    /**
     * Risolve i conflitti e propone aggiustamenti.
     * Usa il modello ML se disponibile, altrimenti euristiche.
     */
    std::vector<ScheduleAdjustment> resolve_conflicts(
        const std::vector<Conflict>& conflicts
    );
    
    /**
     * Applica gli aggiustamenti proposti alla schedule.
     */
    void apply_adjustments(const std::vector<ScheduleAdjustment>& adjustments);
    
    /**
     * Ottimizza l'intera rete per efficienza.
     */
    void optimize_network();
    
    // ========================================
    // ML Model Integration
    // ========================================
    
    /**
     * Carica il modello ML addestrato.
     * @param model_path Path al file .pth del modello PyTorch
     */
    bool load_ml_model(const std::string& model_path);
    
    /**
     * Usa il modello ML per predire aggiustamenti.
     */
    std::vector<ScheduleAdjustment> predict_with_ml(
        const NetworkState& state,
        const std::vector<Conflict>& conflicts
    );
    
    // ========================================
    // Queries & Statistics
    // ========================================
    
    /**
     * Ottieni lo stato corrente della rete.
     */
    NetworkState get_network_state() const;
    
    /**
     * Ottieni informazioni su un treno specifico.
     */
    Train get_train_info(int train_id) const;
    
    /**
     * Ottieni statistiche di performance.
     */
    struct Statistics {
        int total_trains;
        int delayed_trains;
        int active_conflicts;
        double average_delay_minutes;
        double network_efficiency; // 0-1
    };
    
    Statistics get_statistics() const;
    
    /**
     * Ottieni log degli eventi recenti.
     */
    std::vector<std::string> get_event_log(int max_events = 100) const;
    
private:
    // ========================================
    // Internal State
    // ========================================
    
    std::unordered_map<int, Train> trains_;
    std::unordered_map<int, Track> tracks_;
    std::unordered_map<int, Station> stations_;
    
    std::vector<std::string> event_log_;
    
    // ML model handle (opaco, gestito da pybind11)
    void* ml_model_handle_;
    bool ml_model_loaded_;
    
    // ========================================
    // Internal Helpers
    // ========================================
    
    /**
     * Calcola se due treni su binario singolo sono in collisione.
     */
    bool check_single_track_collision(const Train& t1, const Train& t2, const Track& track) const;
    
    /**
     * Calcola tempo di incontro tra due treni.
     */
    double calculate_meeting_time(const Train& t1, const Train& t2) const;
    
    /**
     * Trova percorso alternativo per un treno.
     */
    std::vector<int> find_alternative_route(int train_id, int destination) const;
    
    /**
     * Assegna priorità ai conflitti.
     */
    std::vector<Conflict> prioritize_conflicts(const std::vector<Conflict>& conflicts) const;
    
    /**
     * Logga un evento.
     */
    void log_event(const std::string& message);
};

// ============================================================================
// Conflict Resolution Algorithms
// ============================================================================

/**
 * Algoritmi euristici per risoluzione conflitti (fallback quando ML non disponibile).
 */
class ConflictResolver {
public:
    /**
     * Risoluzione basata su priorità treni con supporto cambio binario.
     * 
     * Strategia:
     * 1. Se treno a bassa priorità è vicino a stazione (<5km):
     *    - Cerca binario alternativo disponibile
     *    - Cambia binario se possibile (ritardo 0.5min per manovra)
     * 2. Altrimenti applica ritardo temporale (5min * severity)
     */
    static std::vector<ScheduleAdjustment> resolve_by_priority(
        const std::vector<Conflict>& conflicts,
        const std::unordered_map<int, Train>& trains,
        const std::unordered_map<int, Track>& tracks
    );
    
    /**
     * Risoluzione minimizzando ritardo totale.
     */
    static std::vector<ScheduleAdjustment> minimize_total_delay(
        const std::vector<Conflict>& conflicts,
        const std::unordered_map<int, Train>& trains,
        const std::unordered_map<int, Track>& tracks
    );
    
    /**
     * Risoluzione per binari singoli (gestione incroci).
     * 
     * Gestisce il caso critico di stazioni multi-binario che collegano 
     * linee a binario unico in direzioni opposte:
     * 
     * Strategia 1 (Deviazione in stazione):
     * - Se treno è vicino a stazione (entro 10km)
     * - Cerca binari multi-track disponibili nella stazione
     * - Devia il treno su binario di stazione con meno congestione
     * - Ritardo: 1.0min per manovra, confidenza: 85%
     * 
     * Strategia 2 (Attesa per priorità):
     * - Se deviazione non possibile
     * - Il treno con priorità minore aspetta
     * - Ritardo: 8min × numero treni in conflitto
     * - Confidenza: 70%
     * 
     * Previene deadlock su binari unici con traffico bidirezionale.
     */
    static std::vector<ScheduleAdjustment> resolve_single_track_conflicts(
        const std::vector<Conflict>& conflicts,
        const std::unordered_map<int, Train>& trains,
        const std::unordered_map<int, Track>& tracks
    );
    
    /**
     * Trova binari alternativi disponibili per un treno.
     * Verifica che:
     * 1. Il binario alternativo connetta le stesse stazioni
     * 2. Non sia congestionato
     * 3. Sia disponibile nel tempo stimato
     * 
     * @param train Treno che necessita cambio binario
     * @param current_track_id Binario corrente
     * @param tracks Mappa di tutti i binari
     * @param trains Mappa di tutti i treni (per verificare congestione)
     * @return ID del binario alternativo, o -1 se non disponibile
     */
    static int find_alternative_track(
        const Train& train,
        int current_track_id,
        const std::unordered_map<int, Track>& tracks,
        const std::unordered_map<int, Train>& trains
    );
    
    /**
     * Verifica se un treno è vicino a una stazione dove può cambiare binario.
     * 
     * @param train Treno da verificare
     * @param track Binario corrente
     * @param max_distance_km Distanza massima dalla stazione (default 5km)
     * @return true se il treno è vicino a una stazione
     */
    static bool is_near_station(
        const Train& train,
        const Track& track,
        double max_distance_km = 5.0
    );
};

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Calcola distanza tra due punti su un binario.
 */
double calculate_track_distance(double pos1_km, double pos2_km);

/**
 * Converte minuti in timestamp.
 */
std::chrono::system_clock::time_point minutes_to_timestamp(double minutes);

/**
 * Formatta un timestamp per logging.
 */
std::string format_timestamp(const std::chrono::system_clock::time_point& tp);

} // namespace railway

#endif // RAILWAY_SCHEDULER_H
