#!/bin/bash
# Start the backup service in background

echo "🔄 Starting Model Backup Service..."

# Kill any existing backup service
pkill -f backup_service.py

# Start new backup service in background
nohup python3 /app/python/training/backup_service.py > /app/logs/backup_service.log 2>&1 &

PID=$!

echo "✅ Backup service started (PID: $PID)"
echo "📝 Logs: /app/logs/backup_service.log"
echo ""
echo "To view logs:"
echo "  tail -f /app/logs/backup_service.log"
echo ""
echo "To stop:"
echo "  pkill -f backup_service.py"
