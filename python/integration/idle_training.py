import asyncio
import time
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

class IdleTrainingManager:
    def __init__(self, idle_threshold_seconds: int = 300):
        self.idle_threshold = idle_threshold_seconds
        self.last_activity = time.time()
        self.is_training = False
        self.training_process: Optional[subprocess.Popen] = None
        self.check_interval = 30 # Check every 30 seconds
        self._task = None

    def record_activity(self):
        """Notifica che c'è stata attività da parte di un utente."""
        self.last_activity = time.time()
        if self.is_training:
            logger.info("Activity detected! Suspending background training...")
            self.stop_training()

    async def start(self):
        """Avvia il loop di monitoraggio."""
        logger.info(f"Idle Training Manager started (threshold: {self.idle_threshold}s)")
        self._task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        while True:
            try:
                idle_time = time.time() - self.last_activity
                if idle_time > self.idle_threshold and not self.is_training:
                    # Controlla se ci sono scenari disponibili prima di avviare
                    self.start_training()
                elif idle_time <= self.idle_threshold and self.is_training:
                    self.stop_training()
            except Exception as e:
                logger.error(f"Error in Idle Training loop: {e}")
            
            await asyncio.sleep(self.check_interval)

    def start_training(self):
        """Avvia il processo di addestramento in background."""
        logger.info("System is idle. Starting background training...")
        self.is_training = True
        
        # In una versione reale, dovresti scegliere uno scenario o parametri di default
        # Per ora usiamo un placeholder o il comando standard
        try:
            # Esempio: addestra sull'area predefinita o l'ultima usata
            self.training_process = subprocess.Popen(
                ["python3", "python/marl_scheduling/train_mappo.py", "--episodes", "1000", "--background"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception as e:
            logger.error(f"Failed to start training process: {e}")
            self.is_training = False

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

    def stop(self):
        if self._task:
            self._task.cancel()
        self.stop_training()

# Istanza globale
idle_manager = IdleTrainingManager()
