import sys
import os
from pathlib import Path

# Limit threads and force stability for background training
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["MKL_SERVICE_FORCE_INTEL"] = "1"
os.environ["OMP_PROC_BIND"] = "FALSE"
os.environ["TORCH_NUM_THREADS"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = "" 
os.environ["MKL_THREADING_LAYER"] = "SEQUENTIAL" 

import numpy as np
import argparse
import logging

# Add current directory to sys.path
current_dir = Path(__file__).parent.absolute()
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Force INFO level logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger(__name__)

def train_mappo(args):
    """
    MAPPO training with scenario scaling and checkpointing.
    Supports Curriculum Learning.
    """
    # Heavy imports inside to ensure quick process startup signal
    import torch
    import torch.optim as optim
    from env import RailwayGymEnv
    from scenario_loader import ScenarioLoader
    from constraints import SafetyConstraintLayer
    from models import ActorNetwork, CriticNetwork
    from curriculum import CurriculumManager

    current_level = args.level
    
    def setup_level(level):
        if args.curriculum:
            logger.info(f"Setting up Curriculum Level {level}...")
            scenario = CurriculumManager.get_scenario_for_level(level)
            ScenarioLoader._inject_default_routes(scenario)
        else:
            logger.info(f"Loading static scenario: {args.scenario}")
            scenario = ScenarioLoader.load_scenario(args.scenario)
        
        env = RailwayGymEnv(scenario['tracks'], scenario['stations'], scenario['trains'])
        return env, scenario

    env, scenario = setup_level(current_level)
    
    agent_ids = env.agent_ids
    obs_dim = 8  # 1 (pos) + 1 (track) + 1 (vel) + 5 (neighbors)
    
    # Universal Policy (Shared Weights)
    actor = ActorNetwork(obs_dim)
    critic = CriticNetwork(obs_dim)
    
    # Load checkpoint if exists
    if args.checkpoint and os.path.exists(args.checkpoint):
        logger.info(f"Loading checkpoint from {args.checkpoint}")
        ckpt = torch.load(args.checkpoint)
        critic.load_state_dict(ckpt['critic'])
        actor.load_state_dict(ckpt['actor'])
    
    actor_opt = optim.Adam(actor.parameters(), lr=args.lr)
    critic_opt = optim.Adam(critic.parameters(), lr=args.lr)
    
    safety_layer = SafetyConstraintLayer(env.raw_tracks)
    
    os.makedirs(args.out_dir, exist_ok=True)
    
    running_reward = 0
    window_size = 5
    
    for episode in range(args.episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            actions = {}
            all_o_tensors = []
            
            # Map agents to current identifiers (they might change if level changes)
            current_agent_ids = env.agent_ids
            
            for aid in current_agent_ids:
                o = obs.get(aid)
                if o is None: continue
                o_vec = np.concatenate([o['position'], [o['current_track']], o['velocity'], o['neighbor_occupancy']])
                o_tensor = torch.FloatTensor(o_vec).unsqueeze(0)
                all_o_tensors.append(o_tensor)
                
                probs = actor(o_tensor)
                dist = torch.distributions.Categorical(probs)
                action = dist.sample()
                actions[aid] = action.item()
            
            if not all_o_tensors:
                break

            # Critic processing (Mean Field)
            batch_obs = torch.cat(all_o_tensors, dim=0)
            value = critic(batch_obs)
            
            # Constraint Layer (Safety)
            safe_actions = safety_layer.apply_constraints(actions, {"trains": env.trains})
            
            # Environment STEP
            next_obs, rewards, done, truncated, info = env.step(safe_actions)
            
            total_reward = sum(rewards.values())
            episode_reward += total_reward
            obs = next_obs
            if truncated: done = True
                
        # Curriculum update logic
        running_reward = 0.9 * running_reward + 0.1 * episode_reward if episode > 0 else episode_reward
        
        if episode % 1 == 0:
            logger.info(f"Episode {episode} (L{current_level}): Reward = {episode_reward:.2f}, Conflicts = {info.get('conflicts', 0)}")
            
        if args.curriculum and episode > 0 and episode % window_size == 0:
            new_level = CurriculumManager.determine_level(running_reward, current_level, threshold=-10.0 * current_level)
            if new_level != current_level:
                current_level = new_level
                env, scenario = setup_level(current_level)
                safety_layer = SafetyConstraintLayer(env.raw_tracks)
                logger.info(f"Network complexity increased to Level {current_level}")

        # Checkpoint
        if episode > 0 and episode % args.save_interval == 0:
            ckpt_path = os.path.join(args.out_dir, f"mappo_curriculum_l{current_level}_ep{episode}.pth")
            torch.save({
                'critic': critic.state_dict(),
                'actor': actor.state_dict(),
                'episode': episode,
                'level': current_level
            }, ckpt_path)
            logger.info(f"Saved checkpoint: {ckpt_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=str, default="scenarios/toscana_cleaned.json")
    parser.add_argument("--curriculum", action="store_true", help="Use progressive complexity")
    parser.add_argument("--level", type=int, default=1, help="Start level for curriculum (1-5)")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_interval", type=int, default=50)
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--out_dir", type=str, default="checkpoints")
    parser.add_argument("--background", action="store_true", help="Running in background mode")
    
    args = parser.parse_args()
    train_mappo(args)

