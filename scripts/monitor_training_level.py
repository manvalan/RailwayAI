#!/usr/bin/env python3
"""
Training Level Monitor
Monitors the current training level and alerts if it regresses unexpectedly.
Can be run locally or on the server.
"""

import subprocess
import time
import sys
from datetime import datetime

# Configuration
SSH_HOST = "root@railway-ai.michelebigi.it"
DOCKER_CONTAINER = "railway-ai"
CHECK_INTERVAL = 300  # Check every 5 minutes
ALERT_ON_REGRESSION = True

def get_current_level_remote():
    """Get current training level from remote server via SSH"""
    try:
        cmd = f'ssh {SSH_HOST} "docker exec {DOCKER_CONTAINER} ps aux | grep train_mappo.py"'
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return None, "Training process not found"
        
        # Parse checkpoint filename from command line
        output = result.stdout
        if "checkpoint" in output:
            # Extract checkpoint path
            parts = output.split("--checkpoint")
            if len(parts) > 1:
                ckpt_path = parts[1].split()[0]
                # Extract level from filename (e.g., mappo_curriculum_l2_ep100.pth -> 2)
                if "_l" in ckpt_path:
                    level_str = ckpt_path.split("_l")[1].split("_")[0]
                    try:
                        level = int(level_str)
                        return level, ckpt_path
                    except ValueError:
                        pass
        
        return None, "Could not parse level from checkpoint"
    
    except subprocess.TimeoutExpired:
        return None, "SSH timeout"
    except Exception as e:
        return None, f"Error: {str(e)}"

def get_current_level_local():
    """Get current training level from local training_realtime.log"""
    try:
        with open("/Users/michelebigi/RailwayAI/training_realtime.log", "r") as f:
            # Read last 100 lines
            lines = f.readlines()[-100:]
            for line in reversed(lines):
                if "(L" in line and "Episode" in line:
                    # Extract level from log line like "Episode 123 (L2)"
                    level_str = line.split("(L")[1].split(")")[0]
                    try:
                        return int(level_str), "local log"
                    except ValueError:
                        pass
        return None, "No level info in recent logs"
    except FileNotFoundError:
        return None, "Log file not found"
    except Exception as e:
        return None, f"Error: {str(e)}"

def main():
    print("🔍 Training Level Monitor Started")
    print(f"   Checking every {CHECK_INTERVAL}s")
    print(f"   Alert on regression: {ALERT_ON_REGRESSION}")
    print("-" * 50)
    
    last_level = None
    mode = "remote"  # or "local"
    
    # Detect if we can reach remote server
    try:
        subprocess.run(f"ssh {SSH_HOST} echo test", shell=True, capture_output=True, timeout=5, check=True)
        mode = "remote"
        print("✅ Connected to remote server")
    except:
        mode = "local"
        print("⚠️  Cannot reach remote server, using local logs")
    
    while True:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if mode == "remote":
            level, info = get_current_level_remote()
        else:
            level, info = get_current_level_local()
        
        if level is not None:
            status = "📊"
            if last_level is not None:
                if level > last_level:
                    status = "📈 LEVEL UP!"
                elif level < last_level:
                    status = "🚨 REGRESSION!"
                    if ALERT_ON_REGRESSION:
                        print(f"\n{'='*50}")
                        print(f"⚠️  ALERT: Training regressed from L{last_level} to L{level}!")
                        print(f"   Checkpoint: {info}")
                        print(f"   Time: {timestamp}")
                        print(f"{'='*50}\n")
            
            print(f"[{timestamp}] {status} Level {level} | {info}")
            last_level = level
        else:
            print(f"[{timestamp}] ❌ Could not determine level: {info}")
        
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Monitor stopped by user")
        sys.exit(0)
