#!/usr/bin/env python3
"""
Automatic Model Backup Service

Runs in background and creates backups every 2 hours.
"""

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BACKUP_DIR = Path("/app/models/backups")
BACKUP_INTERVAL = 2 * 60 * 60  # 2 hours in seconds
MAX_BACKUPS = 24  # Keep last 24 backups (2 days)

def create_backup():
    """Create a backup of all models"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"model_backup_{timestamp}"
    
    logger.info(f"🔄 Starting backup: {backup_name}")
    
    # Ensure backup directory exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    
    backups_created = []
    
    # Backup current model
    current_model = Path("/app/models/training/current_model.pth")
    if current_model.exists():
        dest = BACKUP_DIR / f"{backup_name}_current.pth"
        shutil.copy(current_model, dest) # Use copy instead of copy2 to update timestamp
        backups_created.append(dest)
        logger.info(f"✅ Backed up current model")
    
    # Backup best imitation model
    imitation_model = Path("/app/models/imitation/best_imitation_model.pth")
    if imitation_model.exists():
        dest = BACKUP_DIR / f"{backup_name}_imitation.pth"
        shutil.copy(imitation_model, dest)
        backups_created.append(dest)
        logger.info(f"✅ Backed up imitation model")
    
    # Backup latest MAPPO checkpoint
    training_dir = Path("/app/models/training")
    if training_dir.exists():
        mappo_checkpoints = sorted(
            training_dir.glob("mappo_*.pth"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if mappo_checkpoints:
            latest_mappo = mappo_checkpoints[0]
            dest = BACKUP_DIR / f"{backup_name}_mappo.pth"
            shutil.copy(latest_mappo, dest)
            backups_created.append(dest)
            logger.info(f"✅ Backed up MAPPO checkpoint: {latest_mappo.name}")
            
    # Clean old backups
    cleanup_old_backups()
    
    # Create manifest
    manifest_path = BACKUP_DIR / "latest_backup.txt"
    with open(manifest_path, 'w') as f:
        f.write(f"Backup created: {datetime.now()}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write(f"Files backed up:\n")
        for backup in backups_created:
            if backup.exists():
                size = backup.stat().st_size / 1024  # KB
                f.write(f"  - {backup.name} ({size:.1f} KB)\n")
    
    total_backups = len(list(BACKUP_DIR.glob("model_backup_*.pth")))
    logger.info(f"✅ Backup completed: {backup_name}")
    logger.info(f"📊 Total backups: {total_backups}")

def cleanup_old_backups():
    """Keep only the last MAX_BACKUPS backups"""
    all_backups = sorted(
        BACKUP_DIR.glob("model_backup_*.pth"),
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )
    
    if len(all_backups) > MAX_BACKUPS:
        for old_backup in all_backups[MAX_BACKUPS:]:
            old_backup.unlink()
            logger.debug(f"🗑️  Removed old backup: {old_backup.name}")
        
        logger.info(f"🗑️  Cleaned old backups (keeping last {MAX_BACKUPS})")

def run_backup_service():
    """Main service loop"""
    logger.info("="*70)
    logger.info("  🔄 MODEL BACKUP SERVICE STARTED")
    logger.info("="*70)
    logger.info(f"Backup interval: {BACKUP_INTERVAL/3600:.1f} hours")
    logger.info(f"Backup directory: {BACKUP_DIR}")
    logger.info(f"Max backups to keep: {MAX_BACKUPS}")
    logger.info("")
    
    # Create initial backup
    try:
        create_backup()
    except Exception as e:
        logger.error(f"Initial backup failed: {e}")
    
    # Main loop
    while True:
        try:
            logger.info(f"⏰ Next backup in {BACKUP_INTERVAL/3600:.1f} hours...")
            time.sleep(BACKUP_INTERVAL)
            create_backup()
        except KeyboardInterrupt:
            logger.info("\n⏸️  Backup service stopped by user")
            break
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Continue running even if one backup fails

if __name__ == "__main__":
    run_backup_service()
