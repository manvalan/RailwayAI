"""
Temporal Simulation Engine for Railway Network

Simulates train positions over time and detects future conflicts
before they occur, enabling proactive scheduling decisions.
"""

from typing import List, Dict, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class TemporalSimulator:
    """Simulate train positions over time and detect future conflicts"""
    
    def __init__(self, tracks: Dict[int, Dict]):
        """
        Initialize temporal simulator.
        
        Args:
            tracks: Dict mapping track_id -> track dict with length_km, is_single_track, etc.
        """
        self.tracks = tracks
        logger.info(f"TemporalSimulator initialized with {len(tracks)} tracks")
    
    def simulate_train_position(self, train: Dict, time_offset_minutes: float) -> Dict:
        """
        Calculate train position at a given time offset from departure.
        
        Args:
            train: Train dict with:
                - id: train ID
                - planned_route: List of track IDs (optional)
                - current_track: Current track ID
                - velocity_kmh: Average velocity
                - position_km: Current position (if already departed)
            time_offset_minutes: Minutes since scheduled departure (can be negative)
        
        Returns:
            Dict with:
                - train_id: int
                - current_track: int
                - position_km: float
                - velocity_kmh: float
                - route_index: int (index in planned_route)
                - has_arrived: bool
        """
        train_id = train['id']
        
        # If time offset is negative or zero, train hasn't departed yet
        if time_offset_minutes <= 0:
            planned_route = train.get('planned_route', [train.get('current_track', 0)])
            if not planned_route:
                planned_route = [train.get('current_track', 0)]
            
            return {
                'train_id': train_id,
                'current_track': planned_route[0],
                'position_km': 0.0,
                'velocity_kmh': 0.0,
                'route_index': 0,
                'has_arrived': False
            }
        
        # Calculate distance traveled
        velocity_kmh = train.get('velocity_kmh', 120.0)
        distance_traveled = (velocity_kmh / 60.0) * time_offset_minutes
        
        # Find which track segment the train is on
        remaining_time = time_offset_minutes
        planned_route = train.get('planned_route') or []
        dwell_delays = train.get('dwell_delays') or []  # Ensure it's a list even if None in dict
        
        # If no planned route, use the single track logic
        if not planned_route:
            current_track = train.get('current_track', 0)
            track = self.tracks.get(current_track)
            if not track:
                logger.warning(f"Train {train_id}: current track {current_track} not found")
                return {
                    'train_id': train_id,
                    'current_track': current_track,
                    'position_km': 0.0,
                    'velocity_kmh': 0.0,
                    'route_index': 0,
                    'has_arrived': False
                }
            
            track_length = track['length_km']
            time_to_traverse = (track_length / velocity_kmh) * 60.0
            
            if remaining_time <= time_to_traverse:
                position = (remaining_time / 60.0) * velocity_kmh
                return {
                    'train_id': train_id,
                    'current_track': current_track,
                    'position_km': position,
                    'velocity_kmh': velocity_kmh,
                    'route_index': 0,
                    'has_arrived': False
                }
            else:
                return {
                    'train_id': train_id,
                    'current_track': current_track,
                    'position_km': track_length,
                    'velocity_kmh': 0.0,
                    'route_index': 0,
                    'has_arrived': True
                }

        # Simulation with route and intermediate dwell times
        for idx, track_id in enumerate(planned_route):
            track = self.tracks.get(track_id)
            if not track:
                logger.warning(f"Train {train_id}: track {track_id} in route not found")
                continue
            
            track_length = track['length_km']
            time_to_traverse = (track_length / velocity_kmh) * 60.0
            
            # Check if train is currently on this track
            if remaining_time <= time_to_traverse:
                position_on_track = (remaining_time / 60.0) * velocity_kmh
                return {
                    'train_id': train_id,
                    'current_track': track_id,
                    'position_km': position_on_track,
                    'velocity_kmh': velocity_kmh,
                    'route_index': idx,
                    'has_arrived': False
                }
            
            remaining_time -= time_to_traverse
            
            # Check for dwell time at the station AFTER this track
            # Only if it's not the final destination
            if idx < len(planned_route) - 1:
                # Default dwell time (e.g., 2 minutes) + adjustment from GA
                base_dwell = 2.0 
                adjustment = dwell_delays[idx] if idx < len(dwell_delays) else 0.0
                dwell_time = base_dwell + adjustment
                
                if remaining_time <= dwell_time:
                    # Train is stopped at the station (exit of this track)
                    return {
                        'train_id': train_id,
                        'current_track': track_id,
                        'position_km': track_length,
                        'velocity_kmh': 0.0,
                        'route_index': idx,
                        'has_arrived': False,
                        'is_stopped_at_station': True
                    }
                
                remaining_time -= dwell_time
        
        # Train has reached destination
        last_track_id = planned_route[-1]
        last_track = self.tracks.get(last_track_id, {'length_km': 0})
        
        return {
            'train_id': train_id,
            'current_track': last_track_id,
            'position_km': last_track['length_km'],
            'velocity_kmh': 0.0,
            'route_index': len(planned_route) - 1,
            'has_arrived': True
        }
    
    def detect_future_conflicts(self, 
                                trains: List[Dict], 
                                time_horizon_minutes: float = 60.0,
                                time_step_minutes: float = 1.0) -> List[Dict]:
        """
        Detect conflicts over a time horizon by simulating train positions.
        
        Args:
            trains: List of train dicts with planned routes
            time_horizon_minutes: How far into the future to simulate (default: 60 min)
            time_step_minutes: Time resolution for simulation (default: 1 min)
        
        Returns:
            List of conflict dicts with:
                - time_offset_minutes: When the conflict occurs
                - track_id: Which track
                - train1_id, train2_id: Conflicting trains
                - train1_position_km, train2_position_km: Positions
                - distance_km: Distance between trains
                - conflict_type: 'single_track', 'too_close', or 'same_position'
                - severity: 1-10 rating
        """
        conflicts = []
        conflict_set = set()  # To avoid duplicate conflicts
        
        num_steps = int(time_horizon_minutes / time_step_minutes)
        
        logger.info(f"Simulating {len(trains)} trains over {time_horizon_minutes} minutes "
                   f"with {time_step_minutes} min steps ({num_steps} steps)")
        
        # Simulate at each time step
        for step in range(num_steps + 1):
            t = step * time_step_minutes
            
            # Get all train positions at time t
            positions_by_track = {}
            
            for train in trains:
                pos = self.simulate_train_position(train, t)
                
                # Skip trains that have arrived
                if pos['has_arrived']:
                    continue
                
                track_id = pos['current_track']
                
                if track_id not in positions_by_track:
                    positions_by_track[track_id] = []
                positions_by_track[track_id].append(pos)
            
            # Check for conflicts on each track
            for track_id, train_positions in positions_by_track.items():
                if len(train_positions) < 2:
                    continue
                
                track = self.tracks.get(track_id)
                if not track:
                    continue
                
                is_single_track = track.get('is_single_track', True)
                capacity = track.get('capacity', 1)
                
                # Check capacity
                if len(train_positions) > capacity:
                    # Capacity exceeded - create conflicts between all pairs
                    for i in range(len(train_positions)):
                        for j in range(i + 1, len(train_positions)):
                            pos1, pos2 = train_positions[i], train_positions[j]
                            
                            # Create unique conflict ID to avoid duplicates
                            conflict_id = (
                                min(pos1['train_id'], pos2['train_id']),
                                max(pos1['train_id'], pos2['train_id']),
                                track_id,
                                int(t)  # Round to minute
                            )
                            
                            if conflict_id in conflict_set:
                                continue
                            
                            conflict_set.add(conflict_id)
                            
                            distance = abs(pos1['position_km'] - pos2['position_km'])
                            
                            # Determine conflict type and severity
                            if distance < 0.1:
                                conflict_type = 'same_position'
                                severity = 10
                            elif is_single_track:
                                conflict_type = 'single_track'
                                severity = 9
                            elif distance < 2.0:
                                conflict_type = 'too_close'
                                severity = 7
                            else:
                                conflict_type = 'capacity_exceeded'
                                severity = 6
                            
                            conflicts.append({
                                'time_offset_minutes': t,
                                'track_id': track_id,
                                'train1_id': pos1['train_id'],
                                'train2_id': pos2['train_id'],
                                'train1_position_km': pos1['position_km'],
                                'train2_position_km': pos2['position_km'],
                                'distance_km': distance,
                                'conflict_type': conflict_type,
                                'severity': severity,
                                'is_single_track': is_single_track
                            })
        
        logger.info(f"Detected {len(conflicts)} conflicts over {time_horizon_minutes} minutes")
        
        # Sort by time and severity
        conflicts.sort(key=lambda c: (c['time_offset_minutes'], -c['severity']))
        
        return conflicts
    
    def find_meeting_point(self, train1: Dict, train2: Dict) -> Optional[Dict]:
        """
        Find where and when two trains will meet on their routes.
        
        Args:
            train1, train2: Train dicts with planned routes
        
        Returns:
            Dict with meeting information or None if they don't meet
        """
        route1 = train1.get('planned_route', [])
        route2 = train2.get('planned_route', [])
        
        if not route1 or not route2:
            return None
        
        # Find common tracks
        common_tracks = set(route1) & set(route2)
        
        if not common_tracks:
            return None
        
        # For each common track, calculate when each train will be there
        for track_id in common_tracks:
            idx1 = route1.index(track_id)
            idx2 = route2.index(track_id)
            
            # Calculate time to reach this track
            time1 = self._time_to_track(train1, idx1)
            time2 = self._time_to_track(train2, idx2)
            
            track = self.tracks.get(track_id)
            if not track:
                continue
            
            track_length = track['length_km']
            
            # Calculate time to traverse the track
            traverse_time1 = (track_length / train1.get('velocity_kmh', 120)) * 60
            traverse_time2 = (track_length / train2.get('velocity_kmh', 120)) * 60
            
            # Check if time windows overlap
            if (time1 <= time2 <= time1 + traverse_time1) or \
               (time2 <= time1 <= time2 + traverse_time2):
                return {
                    'track_id': track_id,
                    'train1_arrival_time': time1,
                    'train2_arrival_time': time2,
                    'overlap_minutes': min(time1 + traverse_time1, time2 + traverse_time2) - max(time1, time2)
                }
        
        return None
    
    def _time_to_track(self, train: Dict, track_index: int) -> float:
        """Calculate time in minutes to reach a specific track in the route."""
        route = train.get('planned_route', [])
        velocity = train.get('velocity_kmh', 120.0)
        
        total_distance = 0.0
        for i in range(track_index):
            track = self.tracks.get(route[i])
            if track:
                total_distance += track['length_km']
        
        return (total_distance / velocity) * 60.0
