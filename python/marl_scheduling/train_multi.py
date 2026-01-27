import os
import argparse
import random
import logging
from train_mappo import train_mappo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario_dir", type=str, required=True, help="Directory containing JSON scenarios")
    parser.add_argument("--episodes_per_scenario", type=int, default=100)
    parser.add_argument("--total_loops", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--out_dir", type=str, default="checkpoints_universal")
    
    args = parser.parse_args()
    
    scenarios = [os.path.join(args.scenario_dir, f) for f in os.listdir(args.scenario_dir) if f.endswith('.json')]
    
    if not scenarios:
        logger.error(f"No JSON scenarios found in {args.scenario_dir}")
        return

    logger.info(f"Found {len(scenarios)} scenarios. Starting Universal Multi-Scenario Training...")
    
    current_checkpoint = None
    
    for loop in range(args.total_loops):
        logger.info(f"--- Starting Training Loop {loop+1}/{args.total_loops} ---")
        random.shuffle(scenarios)
        
        for scenario_path in scenarios:
            logger.info(f"Training on: {os.path.basename(scenario_path)}")
            
            # Create sub-args for train_mappo
            class SubArgs:
                def __init__(self, s, e, l, o, c):
                    self.scenario = s
                    self.episodes = e
                    self.lr = l
                    self.out_dir = o
                    self.checkpoint = c
                    self.save_interval = e # Save at the end of each scenario
            
            sub_args = SubArgs(scenario_path, args.episodes_per_scenario, args.lr, args.out_dir, current_checkpoint)
            
            # Execute training on this scenario
            train_mappo(sub_args)
            
            # Update checkpoint for next scenario
            # train_mappo saves to mappo_universal_ep{ep}.pth. We'll find the latest.
            current_checkpoint = os.path.join(args.out_dir, f"mappo_universal_ep{args.episodes_per_scenario}.pth")

    logger.info("Multi-scenario training complete. Universal model ready in " + args.out_dir)

if __name__ == "__main__":
    main()
