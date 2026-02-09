#!/bin/bash
set -e

echo "🚀 RailwayAI - Imitation Learning Pipeline (LIGHT VERSION)"
echo "=========================================="
echo "Optimized for CPU-only servers with limited RAM"
echo ""

# Configuration for low-resource server
EXAMPLES=2000        # Reduced from 10k
BATCH_SIZE=64        # Reduced from 256
EPOCHS=30            # Reduced from 50
NUM_WORKERS=2        # Limited workers to save RAM

# Step 1: Check available scenarios
echo "📊 Checking available scenarios..."
SCENARIO_COUNT=$(ls scenarios/*real*.json 2>/dev/null | wc -l || echo "0")

if [ "$SCENARIO_COUNT" -eq "0" ]; then
    echo "⚠️  No real scenarios found. Using existing scenarios..."
    SCENARIO_COUNT=$(ls scenarios/*.json 2>/dev/null | wc -l || echo "0")
    
    if [ "$SCENARIO_COUNT" -eq "0" ]; then
        echo "❌ No scenarios available. Please add scenarios first."
        exit 1
    fi
fi

echo "✓ Found $SCENARIO_COUNT scenarios"
echo ""

# Step 2: Generate expert dataset (reduced size)
echo "🎯 Step 1: Generating expert demonstrations..."
echo "  Examples: $EXAMPLES (reduced for CPU)"
echo "  This will take ~15-30 minutes..."
echo ""

python3 python/training/generate_expert_dataset.py \
    --examples $EXAMPLES \
    --output data/expert_demonstrations

if [ $? -ne 0 ]; then
    echo "❌ Failed to generate dataset"
    exit 1
fi

DATASET_PATH="data/expert_demonstrations/expert_dataset.pt"
echo "✅ Dataset generated: $DATASET_PATH"
echo ""

# Step 3: Train with imitation learning (CPU-optimized)
echo "🎓 Step 2: Training neural network (CPU mode)..."
echo "  Batch size: $BATCH_SIZE"
echo "  Epochs: $EPOCHS"
echo "  Workers: $NUM_WORKERS"
echo "  Estimated time: 2-4 hours on CPU"
echo ""

# Run in background with nohup so it survives SSH disconnection
nohup python3 python/training/train_imitation.py \
    --dataset "$DATASET_PATH" \
    --output models/imitation \
    --epochs $EPOCHS \
    --batch-size $BATCH_SIZE \
    --lr 0.0003 \
    > training_imitation.log 2>&1 &

TRAIN_PID=$!
echo "✓ Training started in background (PID: $TRAIN_PID)"
echo "  Log file: training_imitation.log"
echo ""
echo "📊 Monitor progress with:"
echo "  tail -f training_imitation.log"
echo ""
echo "🔍 Check if still running:"
echo "  ps aux | grep train_imitation"
echo ""
echo "=========================================="
echo "🎉 Pipeline started successfully!"
echo "=========================================="
echo ""
echo "The training will continue even if you disconnect."
echo "Check back in 2-4 hours for results."
echo ""
