#!/usr/bin/env python3
"""
Expert Dataset Generator for Imitation Learning

Generates training examples by:
1. Loading real European railway schedules
2. Introducing realistic conflicts
3. Solving them with GA (expert)
4. Saving state-action pairs for supervised learning
"""

import sys
import os
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import json
import numpy as np
import torch
from typing import List, Dict, Tuple
import logging
from tqdm import tqdm

from python.scheduling.schedule_optimizer import ScheduleOptimizer
from python.marl_scheduling.env import RailwayGymEnv
from python.marl_scheduling.scenario_loader import ScenarioLoader

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExpertDatasetGenerator:
    """Generate expert demonstrations using GA"""
    
    def __init__(self, output_dir: str = "data/expert_demonstrations"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.optimizer = ScheduleOptimizer()
        
    def load_real_scenarios(self) -> List[Dict]:
        """Load real European railway scenarios"""
        scenarios = []
        scenario_dir = Path("scenarios")
        
        # Load all real scenario files
        for scenario_file in scenario_dir.glob("*_real*.json"):
            try:
                with open(scenario_file) as f:
                    scenario = json.load(f)
                    if self._validate_scenario(scenario):
                        scenarios.append({
                            "name": scenario_file.stem,
                            "data": scenario
                        })
                        logger.info(f"✓ Loaded scenario: {scenario_file.name}")
            except Exception as e:
                logger.warning(f"Failed to load {scenario_file}: {e}")
        
        return scenarios
    
    def _validate_scenario(self, scenario: Dict) -> bool:
        """Validate scenario has required fields"""
        required = ["stations", "tracks", "trains"]
        return all(k in scenario for k in required) and len(scenario["trains"]) > 0
    
    def introduce_conflicts(self, scenario: Dict, conflict_rate: float = 0.3) -> Dict:
        """Introduce realistic conflicts by adjusting departure times"""
        modified = scenario.copy()
        trains = modified["trains"]
        
        # Group trains by route similarity
        n_conflicts = int(len(trains) * conflict_rate)
        
        for _ in range(n_conflicts):
            # Pick two random trains
            if len(trains) < 2:
                break
                
            i, j = np.random.choice(len(trains), 2, replace=False)
            
            # Make them depart at similar times (create conflict)
            base_time = trains[i].get("scheduled_departure_time", "08:00:00")
            # Add small random offset (0-5 minutes)
            offset = np.random.randint(0, 5)
            trains[j]["scheduled_departure_time"] = self._add_minutes(base_time, offset)
        
        return modified
    
    def _add_minutes(self, time_str: str, minutes: int) -> str:
        """Add minutes to HH:MM:SS time string"""
        h, m, s = map(int, time_str.split(":"))
        total_minutes = h * 60 + m + minutes
        new_h = (total_minutes // 60) % 24
        new_m = total_minutes % 60
        return f"{new_h:02d}:{new_m:02d}:{s:02d}"
    
    def solve_with_ga(self, scenario: Dict) -> Tuple[Dict, float]:
        """Solve scenario using GA and return solution + fitness"""
        try:
            # Convert to optimizer format
            trains = scenario["trains"]
            tracks = scenario["tracks"]
            stations = scenario["stations"]
            
            # Run GA optimization
            result = self.optimizer.optimize(
                trains=trains,
                tracks=tracks,
                stations=stations,
                max_iterations=200,
                population_size=80
            )
            
            if result and "resolutions" in result:
                return result, result.get("fitness", 0.0)
            
        except Exception as e:
            logger.error(f"GA optimization failed: {e}")
        
        return None, 0.0
    
    def extract_state_action_pairs(self, scenario: Dict, solution: Dict) -> List[Tuple]:
        """Extract (state, action) pairs from GA solution"""
        pairs = []
        
        try:
            # Create environment
            env = RailwayGymEnv(
                scenario["tracks"],
                scenario["stations"],
                scenario["trains"]
            )
            
            # Get initial state
            obs, _ = env.reset()
            
            # Extract actions from solution
            resolutions = solution.get("resolutions", [])
            
            for resolution in resolutions:
                train_id = resolution["train_id"]
                
                if train_id not in obs:
                    continue
                
                # Get state for this train
                state = obs[train_id]
                
                # Convert state to vector
                state_vec = self._state_to_vector(state)
                
                # Convert resolution to action
                action = self._resolution_to_action(resolution)
                
                pairs.append((state_vec, action))
        
        except Exception as e:
            logger.error(f"Failed to extract pairs: {e}")
        
        return pairs
    
    def _state_to_vector(self, state: Dict) -> np.ndarray:
        """Convert state dict to normalized vector"""
        return np.array([
            state["position"][0] / 10.0,  # Normalize position
            state["current_track"][0] / 1000.0,  # Normalize track ID
            state["velocity"][0] / 200.0,  # Normalize velocity
            *[x / 5.0 for x in state["neighbor_occupancy"]]  # Normalize neighbors
        ], dtype=np.float32)
    
    def _resolution_to_action(self, resolution: Dict) -> int:
        """Convert GA resolution to discrete action"""
        # Action space: 0=wait, 1=proceed_slow, 2=proceed_normal, 3=proceed_fast
        time_adj = resolution.get("time_adjustment_min", 0.0)
        
        if time_adj > 5:
            return 0  # Wait
        elif time_adj > 0:
            return 1  # Slow
        elif time_adj == 0:
            return 2  # Normal
        else:
            return 3  # Fast
    
    def generate_dataset(self, num_examples: int = 10000) -> str:
        """Generate complete dataset"""
        logger.info(f"🎯 Generating {num_examples} expert demonstrations...")
        
        # Load real scenarios
        scenarios = self.load_real_scenarios()
        if not scenarios:
            logger.error("No scenarios loaded!")
            return None
        
        logger.info(f"📚 Loaded {len(scenarios)} real scenarios")
        
        all_pairs = []
        successful = 0
        
        with tqdm(total=num_examples, desc="Generating examples") as pbar:
            while len(all_pairs) < num_examples:
                # Pick random scenario
                scenario_info = np.random.choice(scenarios)
                scenario = scenario_info["data"]
                
                # Introduce conflicts
                conflicted = self.introduce_conflicts(scenario)
                
                # Solve with GA
                solution, fitness = self.solve_with_ga(conflicted)
                
                if solution and fitness > -1000:  # Only use good solutions
                    # Extract state-action pairs
                    pairs = self.extract_state_action_pairs(conflicted, solution)
                    all_pairs.extend(pairs)
                    successful += 1
                    pbar.update(len(pairs))
        
        # Save dataset
        dataset_path = self.output_dir / "expert_dataset.pt"
        
        states = torch.FloatTensor([p[0] for p in all_pairs[:num_examples]])
        actions = torch.LongTensor([p[1] for p in all_pairs[:num_examples]])
        
        torch.save({
            "states": states,
            "actions": actions,
            "num_examples": len(states),
            "scenarios_used": len(scenarios),
            "success_rate": successful / (successful + 1)
        }, dataset_path)
        
        logger.info(f"✅ Dataset saved: {dataset_path}")
        logger.info(f"   Examples: {len(states)}")
        logger.info(f"   Success rate: {successful / (successful + 1):.2%}")
        
        return str(dataset_path)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--examples", type=int, default=10000, help="Number of examples to generate")
    parser.add_argument("--output", type=str, default="data/expert_demonstrations", help="Output directory")
    args = parser.parse_args()
    
    generator = ExpertDatasetGenerator(output_dir=args.output)
    dataset_path = generator.generate_dataset(num_examples=args.examples)
    
    if dataset_path:
        print(f"\n✅ Dataset ready: {dataset_path}")
        print(f"Next step: python python/training/train_supervised.py --dataset {dataset_path}")
