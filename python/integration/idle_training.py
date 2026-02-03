import asyncio
import time
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class IdleTrainingManager:
    def __init__(self, idle_threshold_seconds: int = 300):
        self.idle_threshold = idle_threshold_seconds
        self.last_activity = time.time()
        self.last_training_time: Optional[datetime] = None
        self.is_training = False
        self.enabled = True  # Auto-training enabled by default
        self.training_process: Optional[subprocess.Popen] = None
        self.check_interval = 30 # Check every 30 seconds
        self.scenario_path: Optional[str] = None  # Scenario to use for training
        self.episodes_per_run = 100  # Episodes per training session
        self._task = None

    def record_activity(self):
        """Notifica che c'è stata attività da parte di un utente."""
        self.last_activity = time.time()
        if self.is_training:
            logger.info("Activity detected! Suspending background training...")
            self.stop_training()

    async def start(self):
        """Avvia il loop di monitoraggio."""
        logger.info(f"Idle Training Manager started (threshold: {self.idle_threshold}s, enabled: {self.enabled})")
        self._task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            try:
                if not self.enabled:
                    await asyncio.sleep(self.check_interval)
                    continue
                    
                idle_time = time.time() - self.last_activity
                if idle_time > self.idle_threshold and not self.is_training:
                    await self._run_training()
                elif idle_time <= self.idle_threshold and self.is_training:
                    self.stop_training()
            except Exception as e:
                logger.error(f"Error in Idle Training loop: {e}")
            
            await asyncio.sleep(self.check_interval)

    async def _run_training(self):
        """Avvia il processo di addestramento in background."""
        if not self.enabled:
            return
            
        # Find a scenario to use
        scenario = self.scenario_path
        if not scenario:
            # Auto-select first available scenario
            scenarios_dir = Path("scenarios")
            if scenarios_dir.exists():
                scenarios = list(scenarios_dir.glob("*.json"))
                if scenarios:
                    scenario = str(scenarios[0])
        
        if not scenario:
            logger.warning("No scenario available for auto-training. Skipping.")
            return
        
        logger.info(f"System is idle. Starting background training on {scenario}...")
        self.is_training = True
        self.last_training_time = datetime.now()
        
        try:
            # Run training with selected scenario
            self.training_process = subprocess.Popen(
                [
                    "python3", "python/marl_scheduling/train_mappo.py",
                    "--scenario", scenario,
                    "--episodes", str(self.episodes_per_run),
                    "--background"
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for completion in background
            await asyncio.create_task(self._wait_for_training())
        except Exception as e:
            logger.error(f"Failed to start training process: {e}")
            self.is_training = False

    async def _wait_for_training(self):
        """Wait for training process to complete."""
        if self.training_process:
            try:
                await asyncio.to_thread(self.training_process.wait)
                logger.info("Background training completed.")
            except Exception as e:
                logger.error(f"Error waiting for training: {e}")
            finally:
                self.is_training = False
                self.training_process = None

    def stop_training(self):
        """Ferma il processo di addestramento."""
        self.is_training = False
        if self.training_process:
            try:
                self.training_process.terminate()
                self.training_process.wait(timeout=5)
                logger.info("Background training suspended.")
            except Exception as e:
                logger.error(f"Error stopping training process: {e}")
                if self.training_process:
                    self.training_process.kill()
            finally:
                self.training_process = None

    def update_config(self, threshold: Optional[int] = None, scenario: Optional[str] = None, 
                     episodes: Optional[int] = None, enabled: Optional[bool] = None):
        """Update auto-training configuration."""
        if threshold is not None:
            self.idle_threshold = threshold
            logger.info(f"Auto-training threshold updated to {threshold}s")
        if scenario is not None:
            self.scenario_path = scenario
            logger.info(f"Auto-training scenario set to {scenario}")
        if episodes is not None:
            self.episodes_per_run = episodes
            logger.info(f"Episodes per run set to {episodes}")
        if enabled is not None:
            self.enabled = enabled
            logger.info(f"Auto-training {'enabled' if enabled else 'disabled'}")

    def get_config(self):
        """Get current configuration."""
        return {
            "enabled": self.enabled,
            "threshold_seconds": self.idle_threshold,
            "scenario_path": self.scenario_path,
            "episodes_per_run": self.episodes_per_run
        }

    def stop(self):
        if self._task:
            self._task.cancel()
        self.stop_training()

# Istanza globale
idle_manager = IdleTrainingManager()
