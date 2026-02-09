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
    import torch.nn.functional as F
    from env import RailwayGymEnv
    from scenario_loader import ScenarioLoader
    from constraints import SafetyConstraintLayer
    from models import ActorNetwork, CriticNetwork
    from curriculum import CurriculumManager

    current_level = args.level
    start_episode = 0
    ckpt = None
    
    # 1. Peek at checkpoint to recover level/episode if available
    imitation_mode = False
    if args.checkpoint and os.path.exists(args.checkpoint):
        try:
            logger.info(f"Peeking at checkpoint {args.checkpoint}...")
            ckpt = torch.load(args.checkpoint, map_location='cpu')
            
            # Detect if it's an imitation model (has model_state_dict but no actor/critic)
            if 'model_state_dict' in ckpt and 'actor' not in ckpt:
                logger.info("🎓 IMITATION MODEL DETECTED. Using as behavioral baseline.")
                imitation_mode = True
                
            if 'level' in ckpt and args.curriculum:
                # Force upgrade if the checkpoint level is lower than the requested level
                resumed_level = ckpt['level']
                if resumed_level < args.level:
                    logger.info(f"Checkpoint level ({resumed_level}) is lower than requested level ({args.level}). FORCING UPGRADE to {args.level}!")
                    current_level = args.level
                else:
                    current_level = resumed_level
                    logger.info(f"Resuming from Curriculum Level: {current_level}")
            if 'episode' in ckpt:
                start_episode = ckpt['episode']
                logger.info(f"Resuming from Episode: {start_episode}")
        except Exception as e:
            logger.warning(f"Could not peek at checkpoint: {e}")

    def setup_level(level):
        if args.curriculum:
            logger.info(f"Setting up Curriculum Level {level}...")
            scenario = CurriculumManager.get_scenario_for_level(level)
            if not scenario or "stations" not in scenario or "tracks" not in scenario:
                 logger.error(f"Generated Level {level} scenario is missing components!")
            ScenarioLoader._inject_default_routes(scenario)
        else:
            logger.info(f"Loading static scenario: {args.scenario}")
            scenario = ScenarioLoader.load_scenario(args.scenario)
        
        active_ids = None
        if args.active_agents:
            active_ids = [int(x) for x in args.active_agents.split(",")]
            logger.info(f"Isolating optimization to agents: {active_ids}")
            
        env = RailwayGymEnv(
            scenario['tracks'], 
            scenario['stations'], 
            scenario['trains'], 
            active_agent_ids=active_ids
        )
        return env, scenario

    env, scenario = setup_level(current_level)
    
    agent_ids = env.agent_ids
    if not agent_ids:
        logger.error("❌ No active agents found in scenario! Training cannot proceed without trains.")
        logger.error("Tip: Ensure 'trains' list is not empty or use scripts/fetch_osm_rail.py --generate-trains (if available).")
        return

    logger.info(f"Initialized environment with {len(agent_ids)} active agents.")
    obs_dim = 15  # 1 (pos) + 1 (track) + 1 (vel) + 12 (occupancy)
    num_actions = 4 # Wait, Slow, Normal, Fast
    
    # 2. Universal Policy (Shared Weights)
    actor = ActorNetwork(obs_dim, num_actions=num_actions)
    critic = CriticNetwork(obs_dim)
    
    # 3. Load weights if checkpoint exists
    if ckpt:
        try:
            logger.info("Loading network weights from checkpoint...")
            if imitation_mode:
                actor.load_state_dict(ckpt['model_state_dict'])
                logger.info("✅ Resumed actor from IMITATION baseline.")
            else:
                actor.load_state_dict(ckpt['actor'])
                critic.load_state_dict(ckpt['critic'])
                logger.info("✅ Resumed PPO weights successfully.")
        except Exception as e:
            logger.warning(f"⚠️ Could not load weights due to architectural mismatch: {e}")
            logger.warning("Starting from scratch with fresh weights instead.")
    
    actor_opt = optim.Adam(actor.parameters(), lr=args.lr)
    critic_opt = optim.Adam(critic.parameters(), lr=args.lr)
    
    safety_layer = SafetyConstraintLayer(env.raw_tracks)


    
    os.makedirs(args.out_dir, exist_ok=True)
    
    running_reward = 0
    window_size = 3 # Smaller window for more frequent level-up checks in background
    
    # Buffer for PPO
    obs_buffer = []
    action_buffer = []
    log_prob_buffer = []
    reward_buffer = []
    value_buffer = []
    mask_buffer = []
    
    ppo_epochs = 4
    mini_batch_size = 32  # Reduced to 32 to prevent OOM kills on small servers
    gamma = 0.99
    gae_lambda = 0.95
    clip_param = 0.2
    
    for episode in range(start_episode, start_episode + args.episodes):
        obs, _ = env.reset()
        episode_reward = 0
        done = False
        
        while not done:
            actions = {}
            log_probs = {}
            values = {}
            
            current_agent_ids = env.agent_ids
            curr_obs_list = []
            curr_action_list = []
            curr_log_prob_list = []
            
            # NEW: Batch processing of all agents in one pass with Attention
            all_agent_keys = list(current_agent_ids)
            o_vec_list = []
            for aid in all_agent_keys:
                o = obs[aid]
                norm_pos = o['position'] / 10.0
                norm_track = [o['current_track'] / 1000.0]
                norm_vel = o['velocity'] / 200.0
                norm_occ = o['neighbor_occupancy'] / 5.0
                o_vec = np.concatenate([norm_pos, norm_track, norm_vel, norm_occ])
                o_vec_list.append(o_vec)
            
            # (NumAgents, ObsDim)
            batch_obs_tensor = torch.FloatTensor(np.array(o_vec_list)).unsqueeze(0) # (1, NumAgents, ObsDim)
            
            # Temperature scaling - reduced from 1.2 to 1.1 to start consolidating gains
            temperature = 1.1 
            
            with torch.no_grad():
                # Forward pass returns (1, NumAgents, NumActions)
                raw_probs = actor(batch_obs_tensor).squeeze(0) # (NumAgents, NumActions)
                
                # Apply temperature and noise injection during SAMPLING
                scaled_probs = torch.pow(raw_probs, 1.0 / temperature)
                scaled_probs = scaled_probs / scaled_probs.sum(dim=-1, keepdim=True)
                
                # EPSILON DECAY: Start at 0.10 and decay to 0.05 to refine the strategy
                # We want less chaos now that we've found the 1-conflict solution multiple times
                epsilon_start = 0.10
                epsilon_end = 0.05
                decay_steps = 10000 
                
                # Calculate current epsilon based on global episode progression
                epsilon = max(epsilon_end, epsilon_start - (episode / decay_steps) * (epsilon_start - epsilon_end))
                
                dist = torch.distributions.Categorical(scaled_probs)
                batch_actions = dist.sample()
                
                for k in range(len(all_agent_keys)):
                    if np.random.random() < epsilon:
                        batch_actions[k] = torch.randint(0, scaled_probs.size(-1), (1,))
                
                batch_log_probs = dist.log_prob(batch_actions)
                
                # Centralized Critic
                val = critic(batch_obs_tensor)
                step_value = val.item()

            for i, aid in enumerate(all_agent_keys):
                actions[aid] = batch_actions[i].item()
                log_probs[aid] = batch_log_probs[i]
                curr_obs_list.append(o_vec_list[i])
                curr_action_list.append(batch_actions[i].item())
                curr_log_prob_list.append(batch_log_probs[i].item())
            
            if not curr_obs_list:
                break

            # Constraint Layer (Safety)
            safe_actions = safety_layer.apply_constraints(actions, {"trains": env.trains})
            
            # Environment STEP
            next_obs, rewards, done, truncated, info = env.step(safe_actions)
            
            total_reward = sum(rewards.values())
            episode_reward += total_reward
            
            # Store in buffer
            obs_buffer.append(curr_obs_list)
            action_buffer.append(curr_action_list)
            log_prob_buffer.append(curr_log_prob_list)
            reward_buffer.append(total_reward)
            value_buffer.append(step_value)
            mask_buffer.append(1.0 - float(done or truncated))
            
            obs = next_obs
            if truncated: done = True
                
        # Update Logic (Every Episode for simplicity in background)
        if len(reward_buffer) > 0:
            # Compute Returns and Advantages (GAE)
            returns = []
            advantages = []
            gae = 0
            next_value = 0 # Assume 0 for terminal
            
            for i in reversed(range(len(reward_buffer))):
                delta = reward_buffer[i] + gamma * next_value * mask_buffer[i] - value_buffer[i]
                gae = delta + gamma * gae_lambda * mask_buffer[i] * gae
                advantages.insert(0, gae)
                next_value = value_buffer[i]
                returns.insert(0, advantages[0] + value_buffer[i])
            
            adv_tensor = torch.FloatTensor(advantages)
            ret_tensor = torch.FloatTensor(returns)
            
            # PPO Update - Advantage Normalization
            adv_tensor = (adv_tensor - adv_tensor.mean()) / (adv_tensor.std() + 1e-8)
            
            # Diagnostic variables
            total_actor_loss = 0
            total_critic_loss = 0
            total_entropy = 0
            
            for _ in range(ppo_epochs):
                indices = np.arange(len(obs_buffer))
                np.random.shuffle(indices)
                
                for start in range(0, len(obs_buffer), mini_batch_size):
                    end = start + mini_batch_size
                    mb_indices = indices[start:end]
                    
                    for i in mb_indices:
                        o_t = torch.FloatTensor(np.array(obs_buffer[i]))
                        a_t = torch.LongTensor(np.array(action_buffer[i]))
                        old_lp = torch.FloatTensor(np.array(log_prob_buffer[i]))
                        
                        # Actor Loss
                        probs = actor(o_t)
                        
                        # NOISE INJECTION: More aggressive threshold (0.6 instead of 0.5)
                        # An entropy of 0.29 is still too "stuck" for a multi-agent network.
                        dist = torch.distributions.Categorical(probs)
                        entropy = dist.entropy().mean()
                        
                        if entropy < 0.6:
                            # Add random noise to kick the policy out of the local minimum
                            noise = torch.ones_like(probs) / probs.size(-1)
                            # Increase randomness: 30% noise if stuck (SHOCK THERAPY)
                            probs = 0.70 * probs + 0.30 * noise
                            dist = torch.distributions.Categorical(probs)
                            # Recalculate entropy after noise injection
                            entropy = dist.entropy().mean()

                        new_lp = dist.log_prob(a_t)
                        ratio = torch.exp(new_lp - old_lp)
                        surr1 = ratio * adv_tensor[i]
                        surr2 = torch.clamp(ratio, 1.0 - clip_param, 1.0 + clip_param) * adv_tensor[i]
                        
                        # High entropy weight to force variety (Up to 0.2)
                        actor_loss = -torch.min(surr1, surr2).mean() - 0.2 * entropy
                        
                        # Critic Loss
                        val_pred = critic(o_t)
                        critic_loss = F.mse_loss(val_pred, ret_tensor[i].view(1, 1))
                        
                        # Optimize
                        actor_opt.zero_grad()
                        actor_loss.backward()
                        actor_opt.step()
                        
                        critic_opt.zero_grad()
                        critic_loss.backward()
                        critic_opt.step()
                        
                        total_actor_loss += actor_loss.item()
                        total_critic_loss += critic_loss.item()
                        total_entropy += entropy.item()
            
            # Diagnostic log (every 10 episodes to avoid clutter)
            if episode % 10 == 0:
                avg_ent = total_entropy / (ppo_epochs * len(obs_buffer))
                logger.info(f"PPO Update - Entropy: {avg_ent:.4f}, Actor Loss: {total_actor_loss:.4f}")
            
            # Clear buffers
            obs_buffer, action_buffer, log_prob_buffer, reward_buffer, value_buffer, mask_buffer = [], [], [], [], [], []

        # Curriculum update logic
        running_reward = 0.9 * running_reward + 0.1 * episode_reward if episode > 0 else episode_reward
        
        if episode == start_episode:
            last_reward = episode_reward
            last_conflicts = info.get('conflicts', 0)
            logger.info(f"🚀 Training Session Started | Level: {current_level} | Baseline Reward: {episode_reward:.2f}")

        # PULISCI FLUSSO: Only log change or every 5th episode
        current_conflicts = info.get('conflicts', 0)
        has_changed = (abs(episode_reward - last_reward) > 0.1) or (current_conflicts != last_conflicts)
        
        if has_changed:
            change_str = "📈 Improvement!" if episode_reward > last_reward else "📉 Variance"
            logger.info(f"✨ Episode {episode} (L{current_level}) | Reward: {episode_reward:.2f} | Conflicts: {current_conflicts} | {change_str}")
            last_reward = episode_reward
            last_conflicts = current_conflicts
        elif episode % 5 == 0:
            logger.info(f"⏳ Episode {episode} (L{current_level}) | Reward: {episode_reward:.2f} (stable) | Conflicts: {current_conflicts}")
            
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
    parser.add_argument("--scenario", type=str, default="scenarios/siena_empoli_realtime.json")
    parser.add_argument("--curriculum", action="store_true", help="Use progressive complexity")
    parser.add_argument("--level", type=int, default=1, help="Start level for curriculum (1-5)")
    parser.add_argument("--episodes", type=int, default=100)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--save_interval", type=int, default=50)
    parser.add_argument("--checkpoint", type=str, default=None)
    parser.add_argument("--out_dir", type=str, default="checkpoints")
    parser.add_argument("--background", action="store_true", help="Running in background mode")
    parser.add_argument("--active_agents", type=str, default=None, help="Comma-separated IDs of agents to train (others will be background)")
    
    args = parser.parse_args()
    train_mappo(args)

