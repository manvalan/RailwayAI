
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from python.scheduling.temporal_simulator import TemporalSimulator
from python.scheduling.route_planner import RoutePlanner
from python.scheduling.conflict_resolver import ConflictResolver
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_robust_conflict_resolution():
    """
    Test scenario:
    Station A (ID 1) --- Track 1 (ID 10) --- Station B (ID 2) --- Track 2 (ID 20) --- Station C (ID 3)
    
    Track 10: Double track (capacity 2)
    Track 20: Single track (capacity 1)
    
    Train 1: Station A -> Station C (Tracks: 10, 20)
    Train 2: Station C -> Station A (Tracks: 20, 10)
    
    If both depart at 08:00:00, they will meet on Track 20 (Single Track) -> CONFLICT.
    """
    
    stations = [
        {'id': 1, 'name': 'Station A', 'num_platforms': 2},
        {'id': 2, 'name': 'Station B', 'num_platforms': 2},
        {'id': 3, 'name': 'Station C', 'num_platforms': 2}
    ]
    
    tracks = {
        10: {'id': 10, 'length_km': 10.0, 'is_single_track': False, 'capacity': 2, 'station_ids': [1, 2]},
        20: {'id': 20, 'length_km': 10.0, 'is_single_track': True, 'capacity': 1, 'station_ids': [2, 3]}
    }
    
    # Speed 60 km/h -> 1 km/min
    # Train 1: Dep A at T=0. Arrives B at T=10. Dwells 3m. Dep B at T=13. Enters Track 20.
    # Train 2: Dep C at T=0. Enters Track 20 at T=0.
    # On Track 20:
    # Train 2 is there from T=0 to T=10.
    # Train 1 is there from T=13 to T=23.
    # No conflict at T=0 if they both depart then? 
    # Wait, let's make it a conflict.
    
    # Corrected Scenario:
    # Train 1: Dep A at 08:00:00. Arrives B at 08:10. Dep B at 08:13.
    # Train 2: Dep C at 08:10:00. Enters Track 20 at 08:10.
    # Train 2 will be on Track 20 from 08:10 to 08:20.
    # Train 1 will be on Track 20 from 08:13 to 08:23.
    # OVERLAP on Single Track 20!
    
    trains = [
        {
            'id': 1,
            'name': 'Express 1',
            'origin_station': 1,
            'destination_station': 3,
            'velocity_kmh': 60.0,
            'scheduled_departure_time': '08:00:00',
            'planned_route': [10, 20]
        },
        {
            'id': 2,
            'name': 'Express 2',
            'origin_station': 3,
            'destination_station': 1,
            'velocity_kmh': 60.0,
            'scheduled_departure_time': '08:10:00',
            'planned_route': [20, 10]
        }
    ]
    
    sim = TemporalSimulator(tracks)
    planner = RoutePlanner([tracks[10], tracks[20]], stations)
    resolver = ConflictResolver(sim, planner)
    
    logger.info("--- Phase 1: Verify Initial Conflict ---")
    initial_conflicts = sim.detect_future_conflicts(trains, time_horizon_minutes=60)
    
    if not initial_conflicts:
        logger.error("FAILED: No initial conflict detected, test scenario is invalid.")
        return
    
    logger.info(f"SUCCESS: Detected {len(initial_conflicts)} initial conflicts.")
    for c in initial_conflicts:
        logger.info(f" Conflict at T+{c['time_offset_minutes']} on Track {c['track_id']} type {c['conflict_type']}")

    logger.info("--- Phase 2: Resolve Conflict ---")
    result = resolver.resolve_conflicts(trains, time_horizon_minutes=60, max_iterations=100)
    
    logger.info(f"Resolution Result: {result['conflicts_resolved']} conflicts resolved.")
    
    if result['conflicts_resolved'] == 0:
        logger.error("FAILED: Resolver could not find a solution.")
        return

    logger.info("--- Phase 3: Verify Resolution Robustness ---")
    # Apply resolutions
    resolutions = result['resolutions']
    adjusted_trains = []
    for t in trains:
        t_adj = t.copy()
        for res in resolutions:
            if res['train_id'] == t['id']:
                # Apply departure delay
                h, m, s = map(int, t['scheduled_departure_time'].split(':'))
                total_min = h*60 + m + res['time_adjustment_min']
                t_adj['scheduled_departure_time'] = f"{int(total_min // 60):02d}:{int(total_min % 60):02d}:{s:02d}"
                t_adj['dwell_delays'] = res.get('dwell_delays', [])
        adjusted_trains.append(t_adj)
        
    final_conflicts = sim.detect_future_conflicts(adjusted_trains, time_horizon_minutes=60)
    
    if not final_conflicts:
        logger.info("FINAL RESULT: SUCCESS! All conflicts resolved and verified.")
    else:
        logger.error(f"FINAL RESULT: FAILED. {len(final_conflicts)} conflicts remain.")

if __name__ == "__main__":
    test_robust_conflict_resolution()
