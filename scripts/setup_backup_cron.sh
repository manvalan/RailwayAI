#!/bin/bash
# Setup cron job for automatic model backups

echo "⚙️ Setting up automatic model backups..."

# Make backup script executable
chmod +x /app/scripts/backup_models.sh

# Add cron job (every 2 hours)
CRON_JOB="0 */2 * * * /app/scripts/backup_models.sh >> /app/logs/backup.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "backup_models.sh"; then
    echo "⚠️  Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
    echo "✅ Cron job added: Backups every 2 hours"
fi

# Create logs directory
mkdir -p /app/logs

# Run initial backup
echo "🔄 Running initial backup..."
/app/scripts/backup_models.sh

echo ""
echo "✅ Backup system configured!"
echo "📅 Schedule: Every 2 hours"
echo "📁 Location: /app/models/backups/"
echo "📝 Logs: /app/logs/backup.log"
echo ""
echo "To view backups:"
echo "  ls -lh /app/models/backups/"
echo ""
echo "To restore a backup:"
echo "  cp /app/models/backups/model_backup_YYYYMMDD_HHMMSS_current.pth /app/models/training/current_model.pth"
