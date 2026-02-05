---
description: How to perform selective training (focus on specific line) with isolated background traffic
---

## Selective AI Training Workflow

This workflow describes how to optimize a specific railway line while treating the rest of the network's traffic as static/background obstacles.

### 1. Identify Target Agents
Find the `id` of the trains belonging to the line you want to optimize. You can find these in the `scenario.json` file.

### 2. Launch Training with Isolation
Run the `train_mappo.py` script using the `--active_agents` flag followed by a comma-separated list of IDs.

```bash
# Example: Optimize only trains 101, 102, 103 on Roma scenario
python3 python/marl_scheduling/train_mappo.py \
    --scenario scenarios/roma.json \
    --active_agents 101,102,103 \
    --episodes 200 \
    --out_dir models/roma_line_A
```

### 3. Key Concepts
- **Active Agents**: These trains are controlled by the Neural Network. They learn to avoid conflicts and minimize delays.
- **Background Traffic**: All other trains in the scenario. They follow their default paths but ARE perceived by the active agents as obstacles.
- **Benefits**: 
  - Faster convergence (smaller observation/action space).
  - Memory efficiency (avoids OOM on large graphs like Roma).
  - Targeted optimization for problematic sections.

### 4. Selective Inference (API)
When calling the `/api/v1/optimize` endpoint, you can pass `active_agent_ids` in the request body:

```json
{
  "trains": [...],
  "active_agent_ids": [101, 102, 103],
  "max_iterations": 100
}
```
The AI will return resolutions ONLY for the specified trains, considering others as obstacles.
