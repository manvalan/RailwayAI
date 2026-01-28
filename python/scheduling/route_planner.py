"""
Route Planning Engine for Railway Network

Implements Dijkstra's algorithm to find optimal routes between stations
and provides time estimation for journey planning.
"""

from typing import Dict, List, Optional, Tuple
import heapq
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class RouteGraph:
    """Graph representation of railway network for pathfinding"""
    
    def __init__(self, tracks: List[Dict], stations: List[Dict]):
        """
        Initialize route graph from tracks and stations.
        
        Args:
            tracks: List of track dictionaries with id, station_ids, length_km
            stations: List of station dictionaries with id, name
        """
        self.tracks = {t['id']: t for t in tracks}
        self.stations = {s['id']: s for s in stations}
        self.graph = self._build_graph(tracks)
        logger.info(f"RouteGraph initialized with {len(stations)} stations and {len(tracks)} tracks")
    
    def _build_graph(self, tracks: List[Dict]) -> Dict[int, List[Tuple[int, int, float]]]:
        """
        Build adjacency list from tracks.
        
        Returns:
            Dict mapping station_id -> [(neighbor_station_id, track_id, distance_km), ...]
        """
        graph = defaultdict(list)
        # Add normal track connections
        for track in tracks:
            if len(track['station_ids']) != 2:
                continue
            
            s1, s2 = track['station_ids']
            length = track['length_km']
            track_id = track['id']
            
            graph[s1].append((s2, track_id, length))
            graph[s2].append((s1, track_id, length))
        
        # Note: parent_hub_id is kept in station data for identification purposes
        # (visualization, priority in conflict resolution, emergency routing)
        # but we do NOT create automatic virtual edges between hub stations
        # to keep AV and Regional networks physically separated.
                    
        return dict(graph)
    
    def find_route(self, origin: int, destination: int) -> Optional[List[int]]:
        """
        Find shortest route (by distance) from origin to destination using Dijkstra's algorithm.
        
        Args:
            origin: Origin station ID
            destination: Destination station ID
        
        Returns:
            List of track IDs forming the route, or None if no route exists
        """
        if origin not in self.stations:
            logger.error(f"Origin station {origin} not found")
            return None
        
        if destination not in self.stations:
            logger.error(f"Destination station {destination} not found")
            return None
        
        if origin == destination:
            logger.warning(f"Origin and destination are the same: {origin}")
            return []
        
        # Dijkstra's algorithm
        distances = {station_id: float('inf') for station_id in self.stations}
        distances[origin] = 0
        previous = {}
        track_used = {}  # Maps (from_station, to_station) -> track_id
        
        pq = [(0, origin)]
        visited = set()
        
        while pq:
            current_dist, current_station = heapq.heappop(pq)
            
            if current_station in visited:
                continue
            
            visited.add(current_station)
            
            if current_station == destination:
                break
            
            if current_dist > distances[current_station]:
                continue
            
            # Explore neighbors
            for neighbor, track_id, length_km in self.graph.get(current_station, []):
                distance = current_dist + length_km
                
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current_station
                    track_used[(current_station, neighbor)] = track_id
                    heapq.heappush(pq, (distance, neighbor))
        
        # Check if destination was reached
        if destination not in previous and destination != origin:
            logger.warning(f"No route found from station {origin} to {destination}")
            return None
        
        # Reconstruct path
        path_stations = []
        current = destination
        while current != origin:
            path_stations.append(current)
            if current not in previous:
                logger.error(f"Route reconstruction failed at station {current}")
                return None
            current = previous[current]
        path_stations.append(origin)
        path_stations.reverse()
        
        # Convert station path to track IDs
        track_path = []
        for i in range(len(path_stations) - 1):
            s1, s2 = path_stations[i], path_stations[i + 1]
            if (s1, s2) not in track_used:
                # Might be a virtual Hub edge if not found in tracks but valid in graph
                # But Dijkstra should have recorded it in 'track_used'
                logger.error(f"Track not found between stations {s1} and {s2}")
                return None
            
            track_id = track_used[(s1, s2)]
            if track_id != -1: # exclude virtual transfer tracks from the physical track path
                track_path.append(track_id)
        
        logger.info(f"Route found from {origin} to {destination}: {len(track_path)} tracks, "
                   f"{distances[destination]:.1f} km")
        
        return track_path


class RoutePlanner:
    """High-level route planning with time estimation and route details"""
    
    def __init__(self, tracks: List[Dict], stations: List[Dict]):
        """
        Initialize route planner.
        
        Args:
            tracks: List of track dictionaries
            stations: List of station dictionaries
        """
        self.graph = RouteGraph(tracks, stations)
        self.tracks = {t['id']: t for t in tracks}
        self.stations = {s['id']: s for s in stations}
    
    def plan_route(self, origin: int, destination: int, 
                   avg_speed_kmh: float = 120.0) -> Optional[Dict]:
        """
        Plan complete route with time estimates and segment details.
        
        Args:
            origin: Origin station ID
            destination: Destination station ID
            avg_speed_kmh: Average speed for time estimation (default: 120 km/h)
        
        Returns:
            Dict with route details:
            {
                'origin_station': int,
                'destination_station': int,
                'segments': List[Dict],  # Each segment has track_id, entry/exit stations, distance, time
                'total_distance_km': float,
                'total_time_minutes': float,
                'track_ids': List[int]
            }
            or None if no route found
        """
        track_path = self.graph.find_route(origin, destination)
        if track_path is None:
            return None
        
        if not track_path:  # Empty path (origin == destination)
            return {
                'origin_station': origin,
                'destination_station': destination,
                'segments': [],
                'total_distance_km': 0.0,
                'total_time_minutes': 0.0,
                'track_ids': []
            }
        
        segments = []
        total_distance = 0.0
        total_time = 0.0
        
        current_station = origin
        for track_id in track_path:
            if track_id not in self.tracks:
                logger.error(f"Track {track_id} not found in track database")
                return None
            
            track = self.tracks[track_id]
            
            # Determine exit station (the one that's not the current station)
            s1, s2 = track['station_ids']
            exit_station = s2 if s1 == current_station else s1
            
            distance = track['length_km']
            time_minutes = (distance / avg_speed_kmh) * 60.0
            
            segments.append({
                'track_id': track_id,
                'entry_station_id': current_station,
                'exit_station_id': exit_station,
                'distance_km': distance,
                'estimated_time_minutes': time_minutes,
                'is_single_track': track.get('is_single_track', True)
            })
            
            total_distance += distance
            total_time += time_minutes
            current_station = exit_station
        
        origin_name = self.stations.get(origin, {}).get('name', f'Station {origin}')
        dest_name = self.stations.get(destination, {}).get('name', f'Station {destination}')
        
        logger.info(f"Planned route {origin_name} → {dest_name}: "
                   f"{total_distance:.1f} km, {total_time:.1f} min, {len(segments)} segments")
        
        return {
            'origin_station': origin,
            'destination_station': destination,
            'segments': segments,
            'total_distance_km': total_distance,
            'total_time_minutes': total_time,
            'track_ids': track_path
        }
