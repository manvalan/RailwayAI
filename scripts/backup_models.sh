#!/bin/bash
# Automatic Model Backup Script
# Runs every 2 hours via cron to backup trained models

BACKUP_DIR="/app/models/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="model_backup_${TIMESTAMP}"

# Create backup directory if not exists
mkdir -p "$BACKUP_DIR"

echo "🔄 Starting model backup at $(date)"

# Backup current model
if [ -f "/app/models/training/current_model.pth" ]; then
    cp "/app/models/training/current_model.pth" "$BACKUP_DIR/${BACKUP_NAME}_current.pth"
    echo "✅ Backed up current model"
fi

# Backup best imitation model
if [ -f "/app/models/imitation/best_imitation_model.pth" ]; then
    cp "/app/models/imitation/best_imitation_model.pth" "$BACKUP_DIR/${BACKUP_NAME}_imitation.pth"
    echo "✅ Backed up imitation model"
fi

# Backup latest MAPPO checkpoint (if exists)
LATEST_MAPPO=$(ls -t /app/models/training/mappo_*.pth 2>/dev/null | head -1)
if [ -n "$LATEST_MAPPO" ]; then
    cp "$LATEST_MAPPO" "$BACKUP_DIR/${BACKUP_NAME}_mappo.pth"
    echo "✅ Backed up MAPPO checkpoint"
fi

# Keep only last 24 backups (2 days worth at 2-hour intervals)
cd "$BACKUP_DIR"
ls -t model_backup_*.pth 2>/dev/null | tail -n +25 | xargs -r rm
echo "🗑️  Cleaned old backups (keeping last 24)"

# Create backup manifest
cat > "$BACKUP_DIR/latest_backup.txt" <<EOF
Backup created: $(date)
Timestamp: $TIMESTAMP
Files backed up:
$(ls -lh $BACKUP_DIR/${BACKUP_NAME}_*.pth 2>/dev/null)
EOF

echo "✅ Backup completed: $BACKUP_NAME"
echo "📊 Total backups: $(ls -1 $BACKUP_DIR/model_backup_*.pth 2>/dev/null | wc -l)"
