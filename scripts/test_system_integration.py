import os
import sys
import unittest
import json
import numpy as np
import torch

# Setup paths
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(PROJECT_ROOT, "python/marl_scheduling"))

class TestRailwayAISystem(unittest.TestCase):

    def setUp(self):
        self.scenario_file = os.path.join(PROJECT_ROOT, "actual_problem_scenario.json")
        with open(self.scenario_file, 'r') as f:
            self.scenario_data = json.load(f)

    def test_01_scenario_loader(self):
        """Test if ScenarioLoader correctly parses and validates the JSON."""
        print("\n[Test] ScenarioLoader...")
        from scenario_loader import ScenarioLoader
        data = ScenarioLoader.load_scenario(self.scenario_file)
        self.assertIn('tracks', data)
        self.assertIn('stations', data)
        self.assertIn('trains', data)
        self.assertGreater(len(data['trains']), 0)
        print("✓ ScenarioLoader OK")

    def test_02_cpp_backend_integration(self):
        """Test if the Gymnasium environment can load and use the C++ backend."""
        print("\n[Test] C++ Backend Integration...")
        from env import RailwayGymEnv, HAS_CPP
        self.assertTrue(HAS_CPP, "C++ backend (railway_cpp) not found! Ensure it is built.")
        
        env = RailwayGymEnv(
            self.scenario_data['tracks'], 
            self.scenario_data['stations'], 
            self.scenario_data['trains']
        )
        obs, _ = env.reset()
        self.assertGreater(len(obs), 0)
        
        # Take a step
        actions = {aid: 0 for aid in env.agent_ids} # All cruise
        next_obs, rewards, done, truncated, info = env.step(actions)
        
        self.assertEqual(len(next_obs), len(env.agent_ids))
        self.assertIn('conflicts', info)
        print("✓ C++ Backend & Env STEP OK")

    def test_03_mappo_networks(self):
        """Test if the Actor and Critic networks handle universal observations."""
        print("\n[Test] MAPPO Universal Networks...")
        from models import ActorNetwork, CriticNetwork
        obs_dim = 8
        actor = ActorNetwork(obs_dim)
        critic = CriticNetwork(obs_dim)
        
        # Dummy batch of observations
        sample_obs = torch.randn(5, obs_dim) 
        
        probs = actor(sample_obs)
        self.assertEqual(probs.shape, (5, 3))
        
        value = critic(sample_obs)
        self.assertEqual(value.shape, (1, 1))
        print("✓ MAPPO Models OK")

    def test_04_dashboard_assets(self):
        """Verify that all dashboard files are present."""
        print("\n[Test] Dashboard Assets...")
        assets = [
            "api/static/index.html",
            "api/static/css/style.css",
            "api/static/js/dashboard.js"
        ]
        for asset in assets:
            path = os.path.join(PROJECT_ROOT, asset)
            self.assertTrue(os.path.exists(path), f"Missing asset: {asset}")
        print("✓ Dashboard Assets Present")

    def test_05_osm_fetcher_logic(self):
        """Test if OSM fetcher script is syntactically correct and can be imported."""
        print("\n[Test] OSM Fetcher Logic...")
        sys.path.append(os.path.join(PROJECT_ROOT, "scripts"))
        try:
            import fetch_osm_rail
            self.assertTrue(hasattr(fetch_osm_rail, 'haversine'))
            print("✓ OSM Fetcher Import OK")
        except ImportError as e:
            self.fail(f"Could not import fetch_osm_rail: {e}")

if __name__ == "__main__":
    unittest.main(verbosity=1)
