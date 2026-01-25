"""
Network Analyzer for Railway Capacity Planning

Analyzes railway network capacity, demand, and identifies bottlenecks
to support intelligent schedule optimization.
"""

from typing import Dict, List, Optional, Tuple
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class NetworkAnalyzer:
    """Analyzes railway network capacity and utilization"""
    
    def __init__(self, tracks: List[Dict], stations: List[Dict]):
        """
        Initialize network analyzer.
        
        Args:
            tracks: List of track dictionaries
            stations: List of station dictionaries
        """
        self.tracks = {t['id']: t for t in tracks}
        self.stations = {s['id']: s for s in stations}
        logger.info(f"NetworkAnalyzer initialized with {len(tracks)} tracks and {len(stations)} stations")
    
    def analyze_capacity(self, trains: List[Dict], time_window_hours: float = 16.0) -> Dict:
        """
        Analyze network capacity and demand.
        
        Args:
            trains: List of trains to schedule
            time_window_hours: Time window in hours (e.g., 16 for 06:00-22:00)
        
        Returns:
            Dict with capacity metrics for each track
        """
        track_metrics = {}
        
        for track_id, track in self.tracks.items():
            # Calculate theoretical capacity (trains per hour)
            theoretical_capacity = self._calculate_theoretical_capacity(track, time_window_hours)
            
            # Calculate demand (how many trains will use this track)
            demand = self._calculate_demand(track_id, trains)
            
            # Calculate utilization
            utilization = demand / theoretical_capacity if theoretical_capacity > 0 else 0
            
            # Identify if this is a bottleneck
            is_bottleneck = utilization > 0.8 or track['is_single_track']
            
            track_metrics[track_id] = {
                'theoretical_capacity': theoretical_capacity,
                'demand': demand,
                'utilization': utilization,
                'is_bottleneck': is_bottleneck,
                'is_single_track': track['is_single_track'],
                'capacity': track['capacity'],
                'length_km': track['length_km']
            }
            
            logger.debug(f"Track {track_id}: capacity={theoretical_capacity:.1f}, "
                        f"demand={demand}, utilization={utilization:.2%}")
        
        return track_metrics
    
    def _calculate_theoretical_capacity(self, track: Dict, time_window_hours: float) -> float:
        """
        Calculate theoretical capacity of a track.
        
        Formula: (time_window / time_to_traverse) * track_capacity
        
        Args:
            track: Track dictionary
            time_window_hours: Time window in hours
        
        Returns:
            Number of trains that can use this track in the time window
        """
        avg_speed_kmh = 120.0  # Average train speed
        time_to_traverse_hours = track['length_km'] / avg_speed_kmh
        
        # How many "slots" are available in the time window
        if time_to_traverse_hours > 0:
            slots = time_window_hours / time_to_traverse_hours
            # Multiply by track capacity (parallel trains)
            theoretical_capacity = slots * track['capacity']
        else:
            theoretical_capacity = float('inf')
        
        return theoretical_capacity
    
    def _calculate_demand(self, track_id: int, trains: List[Dict]) -> int:
        """
        Calculate how many trains will potentially use this track.
        
        This is a simplified estimation - in reality, we'd need route planning
        to know exactly which trains use which tracks.
        
        Args:
            track_id: Track ID
            trains: List of trains
        
        Returns:
            Estimated number of trains using this track
        """
        track = self.tracks[track_id]
        station_ids = set(track['station_ids'])
        
        demand = 0
        for train in trains:
            # Check if train's origin or destination is on this track
            origin = train.get('origin_station')
            destination = train.get('destination_station')
            
            if origin in station_ids or destination in station_ids:
                demand += 1
        
        return demand
    
    def identify_bottlenecks(self, track_metrics: Dict) -> List[int]:
        """
        Identify bottleneck tracks.
        
        Args:
            track_metrics: Output from analyze_capacity
        
        Returns:
            List of track IDs that are bottlenecks
        """
        bottlenecks = []
        
        for track_id, metrics in track_metrics.items():
            if metrics['is_bottleneck']:
                bottlenecks.append(track_id)
                logger.info(f"Bottleneck identified: Track {track_id} "
                           f"(utilization={metrics['utilization']:.2%}, "
                           f"single_track={metrics['is_single_track']})")
        
        return bottlenecks
    
    def calculate_network_utilization(self, track_metrics: Dict) -> Dict:
        """
        Calculate overall network utilization statistics.
        
        Args:
            track_metrics: Output from analyze_capacity
        
        Returns:
            Dict with network-wide statistics
        """
        utilizations = [m['utilization'] for m in track_metrics.values()]
        
        if not utilizations:
            return {
                'average': 0.0,
                'min': 0.0,
                'max': 0.0,
                'std_dev': 0.0
            }
        
        avg_utilization = sum(utilizations) / len(utilizations)
        min_utilization = min(utilizations)
        max_utilization = max(utilizations)
        
        # Standard deviation
        variance = sum((u - avg_utilization) ** 2 for u in utilizations) / len(utilizations)
        std_dev = variance ** 0.5
        
        return {
            'average': avg_utilization,
            'min': min_utilization,
            'max': max_utilization,
            'std_dev': std_dev,
            'total_tracks': len(utilizations)
        }
