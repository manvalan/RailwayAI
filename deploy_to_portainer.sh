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
python3 -c "import sys, os; sys.path.append('build/python'); import railway_cpp; print('✓ C++ Backend OK')" || {
    echo -e "${RED}✗ C++ Backend not compiled! Run build first.${NC}"
    exit 1
}
python3 -c "from python.marl_scheduling.env import RailwayGymEnv; print('✓ MARL Env OK')" || {
    echo -e "${RED}✗ MARL Env error!${NC}"
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
    # Core Python files
    git add python/scheduling/*.py
    git add python/marl_scheduling/*.py
    git add api/*.py
    
    # Core C++ files
    git add cpp/include/*.h
    git add cpp/src/*.cpp
    git add CMakeLists.txt
    
    # Doc and scripts
    git add ROUTE_PLANNING_GUIDE.md
    git add *.md
    git add deploy_to_portainer.sh
    git add Dockerfile
    
    git commit -m "feat: Add MARL conflict resolution with C++ accelerated backend

- Implemented Multi-Agent Reinforcement Learning (MAPPO) for conflict resolution
- Added C++ high-performance physics core with pybind11 bindings
- Neuro-symbolic safety constraint layer to prevent collisions
- Updated Dockerfile for C++ compilation and Torch support"
    
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
