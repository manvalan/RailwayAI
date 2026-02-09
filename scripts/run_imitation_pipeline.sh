#!/bin/bash
set -e

echo "🚀 RailwayAI - Imitation Learning Pipeline"
echo "=========================================="
echo ""

# Step 1: Download GTFS data (if not already done)
if [ ! -d "data/gtfs" ]; then
    echo "📥 Step 1: Downloading European GTFS data..."
    python3 scripts/download_gtfs_europe.py --output data/gtfs
    echo "✅ GTFS data downloaded"
    echo ""
else
    echo "✓ GTFS data already present"
    echo ""
fi

# Step 2: Generate expert dataset from GA
echo "🎯 Step 2: Generating expert demonstrations from GA..."
python3 python/training/generate_expert_dataset.py \
    --examples 10000 \
    --output data/expert_demonstrations

if [ $? -ne 0 ]; then
    echo "❌ Failed to generate dataset"
    exit 1
fi

DATASET_PATH="data/expert_demonstrations/expert_dataset.pt"
echo "✅ Dataset generated: $DATASET_PATH"
echo ""

# Step 3: Train with imitation learning
echo "🎓 Step 3: Training neural network with imitation learning..."
python3 python/training/train_imitation.py \
    --dataset "$DATASET_PATH" \
    --output models/imitation \
    --epochs 50 \
    --batch-size 256 \
    --lr 0.0003

if [ $? -ne 0 ]; then
    echo "❌ Training failed"
    exit 1
fi

echo ""
echo "✅ Imitation learning complete!"
echo ""

# Step 4: Fine-tune with RL (optional)
read -p "🤔 Fine-tune with reinforcement learning? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🏃 Step 4: Fine-tuning with MAPPO..."
    python3 python/marl_scheduling/train_mappo.py \
        --checkpoint models/imitation/best_imitation_model.pth \
        --curriculum \
        --level 2 \
        --episodes 1000 \
        --out_dir models/imitation_finetuned
    
    echo "✅ Fine-tuning complete!"
fi

echo ""
echo "=========================================="
echo "🎉 Pipeline completed successfully!"
echo "=========================================="
echo ""
echo "📊 Results:"
echo "  • Expert dataset: $DATASET_PATH"
echo "  • Trained model: models/imitation/best_imitation_model.pth"
echo ""
echo "🚀 Next steps:"
echo "  1. Test the model with real scenarios"
echo "  2. Deploy to production API"
echo "  3. Monitor performance and collect feedback"
echo ""
