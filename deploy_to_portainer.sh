#!/bin/bash
# Quick deployment script for Portainer update

set -e  # Exit on error

echo "=================================="
echo "Railway AI - Portainer Deployment"
echo "=================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Verify local setup
echo -e "${YELLOW}Step 1: Verifying local setup...${NC}"
python3 -c "from python.scheduling.route_planner import RoutePlanner; from python.scheduling.temporal_simulator import TemporalSimulator; print('✓ Imports OK')" || {
    echo -e "${RED}✗ Import error! Check your Python files.${NC}"
    exit 1
}
echo -e "${GREEN}✓ Local setup verified${NC}"
echo ""

# Step 2: Git status
echo -e "${YELLOW}Step 2: Checking git status...${NC}"
git status --short
echo ""

# Step 3: Confirm commit
read -p "Do you want to commit and push these changes? (y/n) " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo -e "${YELLOW}Step 3: Committing changes...${NC}"
    git add python/scheduling/route_planner.py
    git add python/scheduling/temporal_simulator.py
    git add api/server.py
    git add test_scheduled_optimization.py
    git add ROUTE_PLANNING_GUIDE.md
    git add PORTAINER_DEPLOYMENT.md
    git add deploy_to_portainer.sh
    
    git commit -m "feat: Add route planning and temporal simulation

- Implemented Dijkstra's algorithm for automatic route planning
- Added temporal simulator for future conflict detection
- New endpoint /api/v1/optimize_scheduled for scheduled trains
- Extended Train model with origin_station, planned_route fields
- Support for opposite-direction trains on single tracks"
    
    echo -e "${GREEN}✓ Changes committed${NC}"
    echo ""
    
    echo -e "${YELLOW}Step 4: Pushing to remote...${NC}"
    git push origin main || {
        echo -e "${RED}✗ Push failed! Check your git remote.${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Pushed to remote${NC}"
    echo ""
else
    echo -e "${YELLOW}Skipping commit and push${NC}"
    echo ""
fi

# Step 5: Instructions for Portainer
echo "=================================="
echo -e "${GREEN}Next Steps on Portainer:${NC}"
echo "=================================="
echo ""
echo "1. Go to your Portainer dashboard"
echo "2. Navigate to Containers"
echo "3. Find your railway-ai container"
echo "4. Click '⟳ Recreate'"
echo "5. Enable 'Pull latest image'"
echo "6. Click 'Recreate'"
echo ""
echo "=================================="
echo -e "${GREEN}Verification:${NC}"
echo "=================================="
echo ""
echo "After recreation, verify with:"
echo ""
echo "  curl http://your-server:8002/api/v1/health"
echo ""
echo "Check logs for:"
echo "  - 'Initializing route planner and temporal simulator'"
echo "  - 'Starting Railway AI Scheduler API v2.0.0...'"
echo ""
echo -e "${GREEN}Deployment preparation complete!${NC}"
