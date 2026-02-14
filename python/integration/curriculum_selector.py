import json
import os
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

def generate_curriculum_groups(scenario_path):
    """
    Analyzes the scenario and creates a list of agent groups for progressive training.
    Focuses on trains that share routes (potential conflicts).
    """
    try:
        with open(scenario_path, 'r') as f:
            data = json.load(f)
        
        trains = data.get('trains', [])
        if not trains:
            return []
            
        # 1. Identify pairs that share tracks
        pairs = []
        for i in range(len(trains)):
            for j in range(i + 1, len(trains)):
                t1 = trains[i]
                t2 = trains[j]
                
                # Check shared tracks
                route1 = set(t1.get('planned_route', []))
                route2 = set(t2.get('planned_route', []))
                shared = route1.intersection(route2)
                
                if shared:
                    # Calculate potential conflict score
                    # More shared tracks + closer departure times = higher risk
                    score = len(shared)
                    
                    # Departure time diff (rough estimation)
                    try:
                        time1 = datetime.strptime(t1['scheduled_departure_time'], "%H:%M:%S")
                        time2 = datetime.strptime(t2['scheduled_departure_time'], "%H:%M:%S")
                        diff_min = abs((time1 - time2).total_seconds()) / 60
                        # Reward closeness (inverse score)
                        if diff_min < 120: # Within 2 hours
                            score += (120 - diff_min) / 10
                    except:
                        pass
                        
                    pairs.append({
                        "ids": [str(t1['id']), str(t2['id'])],
                        "score": score
                    })
        
        # Sort by conflict risk
        pairs.sort(key=lambda x: x['score'], reverse=True)
        
        # 2. Build progressive levels
        levels = {
            "1": [], # 1 Critical Pair
            "2": [], # 2 Critical Pairs
            "3": [], # 4 Critical Pairs
            "4": [], # 8 Critical Pairs
            "5": []  # All Agents
        }
        
        all_ids = [str(t['id']) for t in trains]
        
        # Level 1: The most critical pair
        if len(pairs) >= 1:
            levels["1"] = pairs[0]["ids"]
            
        # Level 2: Top 2 pairs
        l2_ids = set()
        for p in pairs[:2]:
            l2_ids.update(p["ids"])
        levels["2"] = list(l2_ids)
        
        # Level 3: Top 4 pairs
        l3_ids = set()
        for p in pairs[:4]:
            l3_ids.update(p["ids"])
        levels["3"] = list(l3_ids)
        
        # Level 4: Top 8 pairs
        l4_ids = set()
        for p in pairs[:8]:
            l4_ids.update(p["ids"])
        levels["4"] = list(l4_ids)
        
        # Level 5: All
        levels["5"] = all_ids
        
        return levels

    except Exception as e:
        print(f"Error generating curriculum groups: {e}")
        return {}

if __name__ == "__main__":
    # Default scenario
    scenario = "scenarios/siena_empoli_real.json"
    if os.path.exists(scenario):
        groups = generate_curriculum_groups(scenario)
        with open("api/models/training/curriculum_groups.json", "w") as f:
            json.dump(groups, f, indent=2)
        print(f"✅ Curriculum groups generated based on {scenario}")
    else:
        print(f"❌ Scenario {scenario} not found.")
