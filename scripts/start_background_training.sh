#!/bin/bash
# Start background training manager as a service

echo "🤖 Starting Background Training Manager..."
echo ""

# Check if already running
if pgrep -f "background_training_manager.py" > /dev/null; then
    echo "⚠️  Background training manager already running"
    echo "   PID: $(pgrep -f background_training_manager.py)"
    echo ""
    echo "To stop: pkill -f background_training_manager.py"
    exit 1
fi

# Start in background with nohup
nohup python3 python/training/background_training_manager.py \
    --cpu-threshold 30 \
    --memory-threshold 70 \
    --check-interval 60 \
    --batch-size 500 \
    > logs/background_training.log 2>&1 &

PID=$!

echo "✅ Background training manager started"
echo "   PID: $PID"
echo "   Log: logs/background_training.log"
echo ""
echo "📊 Monitor with:"
echo "   tail -f logs/background_training.log"
echo ""
echo "⏸️  Stop with:"
echo "   pkill -f background_training_manager.py"
echo ""
echo "The manager will:"
echo "  • Monitor CPU and RAM usage"
echo "  • Start training when server is idle (CPU < 30%, RAM < 70%)"
echo "  • Stop training when server gets busy"
echo "  • Continuously improve the model"
echo ""
