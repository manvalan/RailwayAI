#!/bin/bash
# Automatic checkpoint backup script
# Run this on the server with cron: */30 * * * * /opt/docker-projects/railway-ai/scripts/backup_checkpoints.sh

set -e

CHECKPOINT_DIR="/opt/docker-projects/railway-ai/models/training"
BACKUP_DIR="/opt/docker-projects/railway-ai/models/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Find all L2+ checkpoints (not L1)
echo "[$(date)] Starting checkpoint backup..."

# Backup L2, L3, L4, L5 checkpoints
for level in 2 3 4 5; do
    latest=$(ls -t "$CHECKPOINT_DIR"/mappo_curriculum_l${level}_ep*.pth 2>/dev/null | head -1)
    if [ -n "$latest" ]; then
        filename=$(basename "$latest")
        backup_name="${filename%.pth}_backup_${TIMESTAMP}.pth"
        cp "$latest" "$BACKUP_DIR/$backup_name"
        echo "  ✅ Backed up L${level}: $filename -> $backup_name"
    fi
done

# Keep only last 10 backups per level to save space
for level in 2 3 4 5; do
    ls -t "$BACKUP_DIR"/mappo_curriculum_l${level}_*_backup_*.pth 2>/dev/null | tail -n +11 | xargs -r rm
done

echo "[$(date)] Backup complete!"
