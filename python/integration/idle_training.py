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
        self.curriculum_enabled = False  # New: Curriculum mode
        self.curriculum_level = 1
        self.active_agent_ids: Optional[str] = None # Comma-separated IDs for selective training
        self._task = None
        
        # New: History and Rotation
        self.history: List[Dict[str, Any]] = []  # List of past sessions
        self.last_logs: List[str] = []           # Output of the last run
        self.current_scenario_index = 0          # For rotation
        
        # Determine available scenarios
        self.available_scenarios: List[str] = []
        self._refresh_scenarios()
        self._initialize_level()


    def _refresh_scenarios(self):
        """Refresh list of available scenarios."""
        scenarios_dir = Path("scenarios")
        if scenarios_dir.exists():
            self.available_scenarios = sorted([p.name for p in scenarios_dir.glob("*.json")])

    def _initialize_level(self):
        """Attempts to recover the last curriculum level from the models/training directory."""
        try:
            out_dir = Path("models/training")
            ckpt = self._find_latest_checkpoint(out_dir)
            if ckpt:
                # We use a simple name-based heuristic if we don't want to load with torch
                # mappo_curriculum_l{level}_ep{episode}.pth
                name = ckpt.name
                if "curriculum_l" in name:
                    try:
                        level_part = name.split("curriculum_l")[1]
                        level = int(level_part.split("_")[0])
                        self.curriculum_level = level
                        logger.info(f"Recovered Curriculum Level from checkpoint name: {level}")
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Failed to initialize level from checkpoint: {e}")


    def record_activity(self, source: str = "User Action"):
        """Notifica che c'è stata attività reale. Ignora le letture di monitoraggio."""
        # Se la sorgente è una di quelle che vogliamo ignorare (facoltativo, 
        # ma qui lo rendiamo esplicito via chiamate nel server.py)
        self.last_activity = time.time()
        if self.is_training:
            logger.info(f"Activity detected: {source}. Suspending training to prioritize user.")
            self.stop_training()

    async def start(self):
        """Avvia il loop di monitoraggio."""
        logger.info(f"Idle Training Manager started (threshold: {self.idle_threshold}s)")
        self._task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            try:
                if not self.enabled:
                    await asyncio.sleep(self.check_interval)
                    continue
                    
                idle_time = time.time() - self.last_activity
                if self.is_training:
                    # Se l'attività è tornata sotto la soglia (es. utente è tornato attivo)
                    if idle_time <= self.idle_threshold:
                        logger.info(f"Activity detected ({idle_time:.1f}s ago). Stopping background training.")
                        self.stop_training()
                elif idle_time > self.idle_threshold:
                    # Sistema a riposo, possiamo allenare
                    logger.info(f"System idle for {idle_time:.1f}s (Threshold: {self.idle_threshold}s). Triggering training.")
                    await self._run_training()
            except Exception as e:
                logger.error(f"Error in Idle Training loop: {e}")
            
            await asyncio.sleep(self.check_interval)

    def _peek_next_scenario(self) -> Optional[str]:
        """Returns the next scenario in the rotation without advancing the index."""
        self._refresh_scenarios()
        if not self.available_scenarios:
            return None
            
        if self.scenario_path:
             if self.scenario_path in self.available_scenarios:
                 return f"scenarios/{self.scenario_path}"
        
        fname = self.available_scenarios[self.current_scenario_index % len(self.available_scenarios)]
        return f"scenarios/{fname}"

    async def _run_training(self):
        """Select scenario, advance rotation, and start training."""
        if not self.enabled or self.is_training:
            return
            
        scenario = self._peek_next_scenario()
        if not scenario:
            logger.warning("No scenarios found for training.")
            return
            
        # Only advance rotation here, when we actually start
        if not self.scenario_path:
            self.current_scenario_index = (self.current_scenario_index + 1) % len(self.available_scenarios)
            
        await self._run_background_training(scenario)


    async def _run_background_training(self, scenario: str):
        """Execute the training script in a non-blocking background process."""
        if not self.enabled or self.is_training:
            return
            
        logger.info(f"System is idle. Starting background training on {scenario}...")
        self.is_training = True
        self.last_training_time = datetime.now()
        self.last_logs = [] # Clear logs
        
        try:
            # Ensure models/training directory exists for persistent checkpoints
            out_dir = Path("models/training")
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare command
            cmd = [
                "python3", "-u", "python/marl_scheduling/train_mappo.py",
                "--episodes", str(self.episodes_per_run),
                "--background",
                "--out_dir", str(out_dir)
            ]
            
            # Try to find the latest checkpoint to RESUME training
            checkpoint = self._find_latest_checkpoint(out_dir)
            if checkpoint:
                cmd.extend(["--checkpoint", str(checkpoint)])
                self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Resuming from checkpoint: {checkpoint.name}")
            else:
                self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] No checkpoint found. Starting from scratch.")

            if self.curriculum_enabled:
                cmd.extend(["--curriculum", "--level", str(self.curriculum_level)])
            else:
                cmd.extend(["--scenario", scenario])
            
            if self.active_agent_ids:
                cmd.extend(["--active_agents", self.active_agent_ids])
            
            # Immediate feedback
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Initializing training process on {Path(scenario).name}...")
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Executing: {' '.join(cmd)}")
            
            # Start process using asyncio
            env = os.environ.copy()
            env["PYTHONPATH"] = env.get("PYTHONPATH", "") + ":" + str(Path(__file__).parent.parent.parent)
            env["PYTHONUNBUFFERED"] = "1"
            
            self.training_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=env
            )
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Process started (PID: {self.training_process.pid})")
            
            # Monitoring task
            self._monitor_task = asyncio.create_task(self._monitor_process_output(scenario))
            
        except Exception as e:
            logger.error(f"Failed to start training process: {e}", exc_info=True)
            self.last_logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] STARTUP ERROR: {e}")
            self.is_training = False
            self._add_history_entry(scenario, "failed", str(e))

    def _find_latest_checkpoint(self, directory: Path) -> Optional[Path]:
        """Find the most recent .pth checkpoint in the directory."""
        if not directory.exists():
            return None
        checkpoints = sorted(directory.glob("*.pth"), key=os.path.getmtime, reverse=True)
        return checkpoints[0] if checkpoints else None


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
                    
                    # Log parsing for curriculum updates
                    if "Network complexity increased to Level" in line:
                         try:
                             parts = line.split("Level")
                             if len(parts) > 1:
                                 new_lvl = int(parts[1].strip().split()[0])
                                 self.curriculum_level = new_lvl
                                 logger.info(f"IdleManager captured level update from logs: Level {new_lvl}")
                         except Exception as parse_err:
                             logger.warning(f"Failed to parse level from log: {line} -> {parse_err}")

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
                     episodes: Optional[int] = None, enabled: Optional[bool] = None, **kwargs):
        """Update configuration."""
        if threshold is not None:
            self.idle_threshold = threshold
        if scenario is not None:
            self.scenario_path = scenario
        if episodes is not None:
            self.episodes_per_run = episodes
        if enabled is not None:
            self.enabled = enabled
        if kwargs.get('curriculum') is not None:
            self.curriculum_enabled = kwargs.get('curriculum')
        if kwargs.get('level') is not None:
            self.curriculum_level = kwargs.get('level')
        if kwargs.get('active_agents') is not None:
            self.active_agent_ids = kwargs.get('active_agents')
        logger.info(f"Config updated: {self.get_config()}")

    @property
    def current_scenario(self) -> Optional[str]:
        """Returns the scenario that is either training or queued to train."""
        # If we are training, use that. Otherwise peek at next.
        return self._peek_next_scenario()

    def get_config(self):
        """Get config."""
        return {
            "enabled": self.enabled,
            "threshold_seconds": self.idle_threshold,
            "scenario_path": self.scenario_path,
            "episodes_per_run": self.episodes_per_run,
            "curriculum_enabled": self.curriculum_enabled,
            "curriculum_level": self.curriculum_level,
            "active_agent_ids": self.active_agent_ids
        }

    def get_status_report(self):
        """Get full status report for dashboard."""
        self._refresh_scenarios()
        next_scenario = self._peek_next_scenario()
        
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
            "seconds_until_next_run": round(remaining),
            "curriculum_level": self.curriculum_level,
            "curriculum_enabled": self.curriculum_enabled,
            "active_agent_ids": self.active_agent_ids
        }
        
    def stop(self):
        if self._task:
            self._task.cancel()
        self.stop_training()

# Istanza globale
idle_manager = IdleTrainingManager()
