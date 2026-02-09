
import json
from datetime import datetime

def populate_real_trains(scenario_path, output_path):
    with open(scenario_path, 'r') as f:
        scenario = json.load(f)
    
    # Mapping station names to IDs in siena_empoli_clean.json
    s_map = {
        "Siena": 28,
        "Poggibonsi": 9,
        "Certaldo": 5,
        "Castelfiorentino": 7,
        "Empoli": 0,
        "Firenze SMN": 14
    }

    # Real data from Trenitalia / Viaggiatreno (Morning/Early Afternoon sample)
    real_trains_data = [
        # Direction: NORTH (Siena -> Firenze)
        {"number": 18200, "stops": [("Siena", "05:43"), ("Poggibonsi", "06:06"), ("Certaldo", "06:17"), ("Castelfiorentino", "06:25"), ("Empoli", "06:45"), ("Firenze SMN", "07:23")], "prio": 5},
        {"number": 18214, "stops": [("Siena", "08:18"), ("Poggibonsi", "08:42"), ("Certaldo", "08:54"), ("Castelfiorentino", "09:02"), ("Empoli", "09:21"), ("Firenze SMN", "09:52")], "prio": 8}, # Pendolari peak
        {"number": 18226, "stops": [("Siena", "14:18"), ("Poggibonsi", "14:42"), ("Certaldo", "14:54"), ("Castelfiorentino", "15:02"), ("Empoli", "15:21"), ("Firenze SMN", "15:52")], "prio": 5},
        
        # Direction: SOUTH (Firenze -> Siena)
        {"number": 18201, "stops": [("Firenze SMN", "06:20"), ("Empoli", "06:50"), ("Castelfiorentino", "07:04"), ("Certaldo", "07:13"), ("Poggibonsi", "07:29"), ("Siena", "07:55")], "prio": 5},
        {"number": 18205, "stops": [("Firenze SMN", "09:10"), ("Empoli", "09:40"), ("Castelfiorentino", "09:55"), ("Certaldo", "10:03"), ("Poggibonsi", "10:15"), ("Siena", "10:40")], "prio": 5},
        {"number": 18211, "stops": [("Firenze SMN", "12:10"), ("Empoli", "12:40"), ("Castelfiorentino", "12:55"), ("Certaldo", "13:03"), ("Poggibonsi", "13:15"), ("Siena", "13:40")], "prio": 5}
    ]

    new_trains = []
    for idx, t_data in enumerate(real_trains_data):
        origin_name = t_data["stops"][0][0]
        dest_name = t_data["stops"][-1][0]
        origin_id = s_map[origin_name]
        
        # Find a track connected to the origin station to avoid 'current_track' warnings
        # We look for the first track that contains the origin_id
        starting_track = None
        for track in scenario["tracks"]:
            if origin_id in track["station_ids"]:
                starting_track = track["id"]
                break
        
        if starting_track is None:
            print(f"Warning: Could not find a starting track for station {origin_name} (ID {origin_id})")
            starting_track = 0 # Fallback

        # Build Stops list for the scenario format
        stops_list = []
        for s_name, t_str in t_data["stops"]:
            stops_list.append({
                "station_id": s_map[s_name],
                "arrival_time": t_str,
                "departure_time": t_str,
                "min_dwell_minutes": 2
            })
            
        new_trains.append({
            "id": idx + 1,
            "number": t_data["number"],
            "name": f"Regionale {t_data['number']}",
            "origin_station_id": origin_id,
            "destination_station_id": s_map[dest_name],
            "scheduled_departure_time": t_data["stops"][0][1],
            "current_track": starting_track,
            "position_km": 0.0,
            "velocity_kmh": 0.0, # Starting from standstill
            "priority": t_data["prio"],
            "stops": stops_list,
            "delay_minutes": 0
        })

    scenario["trains"] = new_trains
    
    with open(output_path, 'w') as f:
        json.dump(scenario, f, indent=2)
    
    print(f"Injected {len(new_trains)} real-time trains into {output_path}")

if __name__ == "__main__":
    populate_real_trains('scenarios/siena_empoli_clean.json', 'scenarios/siena_empoli_realtime.json')
