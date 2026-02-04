
import numpy as np
import logging
import json
import os

logger = logging.getLogger(__name__)

class CurriculumManager:
    """
    Manages the transition between different levels of complexity for MARL training.
    """
    
    @staticmethod
    def get_scenario_for_level(level: int) -> dict:
        """
        Generates a scenario based on the difficulty level.
        """
        if level == 1:
            return CurriculumManager._generate_l1()
        elif level == 2:
            return CurriculumManager._generate_l2()
        elif level == 3:
            return CurriculumManager._generate_l3()
        elif level == 4:
            return CurriculumManager._generate_l4()
        else:
            return CurriculumManager._generate_l5()

    @staticmethod
    def _generate_l1():
        """Level 1: 2 trains, 1 track, 2 stations (The Basic Conflict)"""
        return {
            "stations": [
                {"id": 1, "name": "Station A", "num_platforms": 2},
                {"id": 2, "name": "Station B", "num_platforms": 2}
            ],
            "tracks": [
                {"id": 1, "length_km": 10.0, "is_single_track": True, "capacity": 1, "station_ids": [1, 2]}
            ],
            "trains": [
                {
                    "id": 1, "origin_station": 1, "destination_station": 2, 
                    "scheduled_departure_time": "08:00:00", "velocity_kmh": 100,
                    "position_km": 0, "current_track": 1, "priority": 5, "delay_minutes": 0
                },
                {
                    "id": 2, "origin_station": 2, "destination_station": 1, 
                    "scheduled_departure_time": "08:00:00", "velocity_kmh": 100,
                    "position_km": 10, "current_track": 1, "priority": 5, "delay_minutes": 0
                }
            ]
        }

    @staticmethod
    def _generate_l2():
        """Level 2: 4 trains, 3 stations, 2 tracks (Bottleneck Management)"""
        return {
            "stations": [
                {"id": 1, "name": "West", "num_platforms": 2},
                {"id": 2, "name": "Center", "num_platforms": 2},
                {"id": 3, "name": "East", "num_platforms": 2}
            ],
            "tracks": [
                {"id": 1, "length_km": 15.0, "is_single_track": False, "capacity": 2, "station_ids": [1, 2]},
                {"id": 2, "length_km": 10.0, "is_single_track": True, "capacity": 1, "station_ids": [2, 3]}
            ],
            "trains": [
                {"id": i, "origin_station": 1 if i % 2 == 0 else 3, 
                 "destination_station": 3 if i % 2 == 0 else 1,
                 "scheduled_departure_time": f"09:0{i}:00", "velocity_kmh": 120,
                 "position_km": 0 if i % 2 == 0 else 25, 
                 "current_track": 1 if i % 2 == 0 else 2,
                 "priority": 5, "delay_minutes": np.random.randint(0, 5)}
                for i in range(4)
            ]
        }

    @staticmethod
    def _generate_l3():
        """Level 3: 8 trains, Star Topology (Junction Management)"""
        stations = [{"id": 0, "name": "Hub", "num_platforms": 4}]
        tracks = []
        trains = []
        for i in range(1, 5):
            stations.append({"id": i, "name": f"Station {i}", "num_platforms": 2})
            tracks.append({"id": i, "length_km": 20.0, "is_single_track": True, "capacity": 1, "station_ids": [0, i]})
            
        for i in range(8):
            start = np.random.randint(1, 5)
            end = np.random.randint(1, 4)
            if end >= start: end += 1 # Ensure different
            
            trains.append({
                "id": i, "origin_station": start, "destination_station": end,
                "scheduled_departure_time": "12:00:00", "velocity_kmh": 140,
                "position_km": 0, "current_track": start,
                "priority": np.random.randint(1, 10), "delay_minutes": 0
            })
        return {"stations": stations, "tracks": tracks, "trains": trains}

    @staticmethod
    def _generate_l4():
        """Level 4: High Congestion on Linear Line"""
        num_stations = 10
        stations = [{"id": i, "name": f"Line {i}", "num_platforms": 2} for i in range(num_stations)]
        tracks = [{"id": i, "length_km": 12.0, "is_single_track": True, "capacity": 1, "station_ids": [i, i+1]} 
                  for i in range(num_stations-1)]
        trains = []
        for i in range(20):
            d = 0 if i < 10 else num_stations-1
            dest = num_stations-1 if i < 10 else 0
            trains.append({
                "id": i, "origin_station": d, "destination_station": dest,
                "scheduled_departure_time": f"15:{i:02d}:00", "velocity_kmh": 110,
                "position_km": 0 if i < 10 else 108, "current_track": 0 if i < 10 else num_stations-2,
                "priority": 5, "delay_minutes": np.random.randint(0, 15)
            })
        return {"stations": stations, "tracks": tracks, "trains": trains}

    @staticmethod
    def _generate_l5():
        """Level 5: Random Grid with many agents"""
        # Load a base from a real scenario but randomize it
        try:
            with open("scenarios/toscana_cleaned.json", "r") as f:
                base = json.load(f)
                # Keep first 20 stations and related tracks/trains
                subset_stations = base['stations'][:20]
                s_ids = {s['id'] for s in subset_stations}
                subset_tracks = [t for t in base['tracks'] if all(sid in s_ids for sid in t['station_ids'])]
                subset_trains = [t for t in base['trains'] if t['origin_station'] in s_ids and t['destination_station'] in s_ids]
                return {"stations": subset_stations, "tracks": subset_tracks, "trains": subset_trains[:50]}
        except:
            return CurriculumManager._generate_l4() # Fallback

    @staticmethod
    def determine_level(episode_reward: float, current_level: int, threshold: float = -100) -> int:
        """
        Heuristic to decide if we should advance to the next level.
        If reward is consistently above threshold, increment level.
        """
        if episode_reward > threshold and current_level < 5:
            logger.info(f"Performance target reached ({episode_reward:.1f} > {threshold}). Advancing to Level {current_level + 1}")
            return current_level + 1
        return current_level
