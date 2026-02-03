import asyncio
import sys
import time
import subprocess
import logging
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path
import os

logger = logging.getLogger(__name__)

class IdleTrainingManager:
    def __init__(self, idle_threshold_seconds: int = 300):
        self.idle_threshold = idle_threshold_seconds
        self.last_activity = time.time()
        self.last_training_time: Optional[datetime] = None
        self.is_training = False
        self.enabled = True
        self.training_process: Optional[subprocess.Popen] = None
        self.check_interval = 30
        self.scenario_path: Optional[str] = None
        self.episodes_per_run = 100
        self._task = None
        
        # New: History and Rotation
        self.history: List[Dict[str, Any]] = []  # List of past sessions
        self.last_logs: List[str] = []           # Output of the last run
        self.current_scenario_index = 0          # For rotation
        
        # Determine available scenarios
        self.available_scenarios: List[str] = []
        self._refresh_scenarios()

    def _refresh_scenarios(self):
        """Refresh list of available scenarios."""
        scenarios_dir = Path("scenarios")
        if scenarios_dir.exists():
            self.available_scenarios = sorted([str(p) for p in scenarios_dir.glob("*.json")])

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

    def _get_next_scenario(self) -> Optional[str]:
        """Selects the next scenario based on config or rotation."""
        self._refresh_scenarios()
        
        if not self.available_scenarios:
            return None
            
        # 1. If explicit scenario set
        if self.scenario_path:
             if self.scenario_path in self.available_scenarios:
                 return self.scenario_path
             # Fallback if file deleted
        
        # 2. Rotation
        if not self.available_scenarios:
            return None
            
        scenario = self.available_scenarios[self.current_scenario_index % len(self.available_scenarios)]
        # Prepare for next time
        self.current_scenario_index = (self.current_scenario_index + 1) % len(self.available_scenarios)
        return scenario

    async def _run_training(self):
        """Select scenario and start training."""
        if not self.enabled or self.is_training:
            return
            
        scenario = self._get_next_scenario()
        if not scenario:
            logger.warning("No scenarios found for training.")
            return
            
        await self._run_background_training(scenario)

    async def _run_background_training(self, scenario: str):
        """Execute the training script in a non-blocking background process."""
        if not self.enabled or self.is_training: # Added self.is_training check
            return
            
        logger.info(f"System is idle. Starting background training on {scenario}...")
        self.is_training = True
        self.last_training_time = datetime.now()
        self.last_logs = [] # Clear logs
        
        try:
            # Prepare command
            cmd = [
                sys.executable, "-u", "python/marl_scheduling/train_mappo.py",
                "--scenario", scenario,
                "--episodes", str(self.episodes_per_run),
                "--background"
            ]
            
            # Immediate feedback
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing training process on {Path(scenario).name}...")
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Executing: {' '.join(cmd)}")
            
            # Start process using asyncio for non-blocking IO
            env = os.environ.copy()
            env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":" + str(Path(__file__).parent.parent.parent)
            env["PYTHONUNBUFFERED"] = "1"
            
            try:
                self.training_process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env=env
                )
                self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Process started successfully (PID: {self.training_process.pid})")
            except Exception as startup_err:
                self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] CRITICAL: Could not execute python3: {startup_err}")
                raise startup_err
            
            # Start monitoring in a separate background task so we don't block the loop
            asyncio.create_task(self._monitor_process_output(scenario))
            
        except Exception as e:
            logger.error(f"Failed to start training process: {e}")
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] STARTUP ERROR: {e}")
            self.is_training = False
            self._add_history_entry(scenario, "failed", str(e))

    async def _monitor_process_output(self, scenario: str):
        """Read stdout from the training process without blocking the event loop."""
        start_time = time.time()
        status = "completed"
        error_msg = None

        if not self.training_process:
            self.is_training = False
            return

        try:
            # Read line by line asynchronously
            while True:
                line_bytes = await self.training_process.stdout.readline()
                if not line_bytes:
                    self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] End of process stream reached.")
                    break
                
                line = line_bytes.decode('utf-8').strip()
                if line:
                    self.last_logs.append(line)
                    if len(self.last_logs) > 1000:
                         self.last_logs.pop(0)

            # Wait for completion
            return_code = await self.training_process.wait()
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Process exited with code: {return_code}")
            if return_code != 0:
                 status = "error" if return_code != -15 else "suspended"
                 error_msg = f"Exit code {return_code}"
                 self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Training process {status}: {error_msg}")
            else:
                 self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Training process completed successfully.")

        except Exception as e:
            logger.error(f"Error monitoring training output: {e}")
            status = "error"
            error_msg = str(e)
        finally:
            duration = time.time() - start_time
            self._add_history_entry(scenario, status, error_msg, duration)
            self.is_training = False
            self.training_process = None
            logger.info(f"Background training finished: {status}")

    def _add_history_entry(self, scenario: str, status: str, details: str = None, duration: float = 0):
        """Add entry to history log."""
        self.history.insert(0, {
            "timestamp": datetime.now().isoformat(),
            "scenario": Path(scenario).name,
            "status": status,
            "duration_seconds": round(duration, 1),
            "details": details
        })
        # Keep last 50 entries
        self.history = self.history[:50]

    def stop_training(self):
        """Ferma il processo."""
        if self.is_training and self.training_process:
            logger.info("Stopping background training...")
            try:
                self.training_process.terminate() 
                # Monitoring loop will handle cleanup
            except Exception as e:
                logger.error(f"Error killing process: {e}")

    def update_config(self, threshold: Optional[int] = None, scenario: Optional[str] = None, 
                     episodes: Optional[int] = None, enabled: Optional[bool] = None):
        """Update configuration."""
        if threshold is not None:
            self.idle_threshold = threshold
        if scenario is not None:
            self.scenario_path = scenario
        if episodes is not None:
            self.episodes_per_run = episodes
        if enabled is not None:
            self.enabled = enabled
        logger.info(f"Config updated: {self.get_config()}")

    def get_config(self):
        """Get config."""
        return {
            "enabled": self.enabled,
            "threshold_seconds": self.idle_threshold,
            "scenario_path": self.scenario_path,
            "episodes_per_run": self.episodes_per_run
        }

    def get_status_report(self):
        """Get full status report for dashboard."""
        self._refresh_scenarios()
        next_scenario = self._get_next_scenario() if not self.scenario_path else self.scenario_path
        
        idle_time = time.time() - self.last_activity
        remaining = max(0, self.idle_threshold - idle_time)
        
        return {
            "status": "training" if self.is_training else "idle",
            "current_scenario": Path(next_scenario).name if next_scenario else None,
            "last_run": self.last_training_time.isoformat() if self.last_training_time else None,
            "history": self.history[:10], # Last 10 runs
            "queued_scenario": Path(next_scenario).name if next_scenario else "None",
            "available_scenarios_count": len(self.available_scenarios),
            "logs_preview": self.last_logs[-20:] if self.last_logs else ["No recent logs"],
            "seconds_until_next_run": round(remaining)
        }
        
    def stop(self):
        if self._task:
            self._task.cancel()
        self.stop_training()

# Istanza globale
idle_manager = IdleTrainingManager()
