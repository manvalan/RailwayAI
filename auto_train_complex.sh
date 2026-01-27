#!/bin/bash
set -e

# Master script for Automated European Training
# Usage: ./auto_train_complex.sh "Area Name" [episodes]

AREA=${1:-"Toscana"}
EPISODES=${2:-200}
OUTPUT_FILE="scenarios/${AREA// /_}_complex.json"

echo "===================================================="
echo "🚀 Starting Automated Complex Training: $AREA"
echo "===================================================="

mkdir -p scenarios

# 1. Fetch Real Data from OSM
echo "🔗 Step 1: Fetching infrastructure for $AREA..."
python3 scripts/fetch_osm_rail.py --area "$AREA" --output "$OUTPUT_FILE"

# 2. Start Training
echo "🧠 Step 2: Training MARL agent on $AREA ($EPISODES episodes)..."
python3 python/marl_scheduling/train_mappo.py \
    --scenario "$OUTPUT_FILE" \
    --episodes "$EPISODES" \
    --out_dir "checkpoints/$AREA"

echo ""
echo "✅ Training Complete!"
echo "📍 Scenario: $OUTPUT_FILE"
echo "📍 Model: checkpoints/$AREA/mappo_universal_ep$EPISODES.pth"
echo "===================================================="
