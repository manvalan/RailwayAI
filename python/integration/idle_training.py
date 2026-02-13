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
    def __init__(self, idle_threshold_seconds: int = 120):
        self.idle_threshold = idle_threshold_seconds
        self.last_activity = time.time()
        self.last_training_time: Optional[datetime] = None
        self.is_training = False
        self.enabled = True
        self.training_process: Optional[subprocess.Popen] = None
        self.check_interval = 30
        self.scenario_path = "scenarios/siena_empoli_real.json"
        self.episodes_per_run = 1000
        self.curriculum_enabled = True  # Auto-progression enabled
        self.curriculum_level = 2
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
        """Attempts to recover the last curriculum level from the checkpoints directory using robust metadata."""
        out_dir = Path("checkpoints")
        self.curriculum_level = 2 # Default fallback
        
        # 1. Try JSON Metadata (The Source of Truth)
        try:
            meta_path = out_dir / "LATEST_SUCCESSFUL_LEVEL.json"
            if meta_path.exists():
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                    self.curriculum_level = int(data.get('level', 2))
                    logger.info(f"✅ Recovered Level from Metadata: {self.curriculum_level} (Source: JSON)")
                    return
        except Exception as e:
            logger.warning(f"Metadata read failed: {e}")

        # 2. Fallback to Filename Parsing
        try:
            ckpt = self._find_latest_checkpoint(out_dir)
            if ckpt:
                name = ckpt.name
                if "curriculum_l" in name:
                    try:
                        level_part = name.split("curriculum_l")[1]
                        level = int(level_part.split("_")[0])
                        self.curriculum_level = level
                        logger.info(f"⚠️ Recovered Level from Filename: {self.curriculum_level} (Source: PTH)")
                    except:
                        pass
        except Exception as e:
            logger.warning(f"Failed to initialize level from checkpoint: {e}")
        
        logger.info(f"AI Curriculum Mode: {'ENABLED' if self.curriculum_enabled else 'DISABLED'} | Current Level: {self.curriculum_level}")

    def record_activity(self, source: str = "User Action"):
        """Notifica che c'è stata attività reale. Ignora le letture di monitoraggio."""
        
        # KEY FIX: Se è solo monitoraggio (GET), usciamo PRIMA di aggiornare il timer!
        if "GET" in source or "status" in source.lower() or "monitoring" in source.lower():
            return

        # Logghiamo per debug capire CHI interrompe
        if self.is_training:
            logger.info(f"Activity detected: {source}. IGNORING STOP SIGNAL to force training.")
            # self.stop_training() # TEMPORARILY DISABLED FOR INTENSIVE TRAINING
        
        self.last_activity = time.time()

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
             # Strip prefix if present for the check
             name_only = os.path.basename(self.scenario_path)
             if name_only in self.available_scenarios:
                 return f"scenarios/{name_only}"
        
        # Fallback to rotation if specific scenario not found
        if not self.available_scenarios: return None
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
        
        # Refresh curriculum level from latest checkpoints before starting
        self._initialize_level()
            
        logger.info(f"System is idle. Starting background training (Curriculum L{self.curriculum_level})...")
        self.is_training = True
        self.last_training_time = datetime.now()
        self.last_logs = [] # Clear logs
        
        try:
            # Ensure models/training directory exists for persistent checkpoints
            out_dir = Path("checkpoints")
            out_dir.mkdir(parents=True, exist_ok=True)
            
            # Prepare command
            cmd = [
                "python3", "-u", "python/marl_scheduling/train_mappo.py",
                "--episodes", str(self.episodes_per_run),
                "--background",
                "--out_dir", str(out_dir)
            ]
            
            # Try to find the latest checkpoint up to date (MARL)
            checkpoint = self._find_latest_checkpoint(out_dir)
            
            # Fallback a modello Imitation se siamo all'inizio (o ricominciamo)
            if not checkpoint:
                imitation_path = Path("models/imitation/best_imitation_model.pth")
                if imitation_path.exists():
                    checkpoint = imitation_path
                    self.last_logs.append(f"🎓 No MARL checkpoint found. Using IMITATION baseline as starting point.")
            
            self.last_logs.append(f"═════════════════════════════════════════════════════════════")
            self.last_logs.append(f"🤖 AI AGENT DEPLOYMENT | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.last_logs.append(f"═════════════════════════════════════════════════════════════")
            
            if checkpoint:
                cmd.extend(["--checkpoint", str(checkpoint)])
                self.last_logs.append(f"📦 Starting with: {checkpoint.name}")
            else:
                self.last_logs.append(f"🆕 Starting fresh training (no checkpoint or baseline found)")

            if self.curriculum_enabled:
                 cmd.extend(["--curriculum", "--level", str(self.curriculum_level)])
                 # Force the correct base scenario for map loaded
                 cmd.extend(["--scenario", "scenarios/siena_empoli_real.json"]) 
                 self.last_logs.append(f"🎓 Curriculum Level: {self.curriculum_level} (Map: siena_empoli_real.json)")
            else:
                cmd.extend(["--scenario", scenario])
            
            if self.active_agent_ids:
                cmd.extend(["--active_agents", self.active_agent_ids])
            
            self.last_logs.append(f"🌍 Scenario: {Path(scenario).name}")
            
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
            self.last_logs.append(f"🚀 Process started (PID: {self.training_process.pid})")
            self.last_logs.append(f"─────────────────────────────────────────────────────────────")
            
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
