# 🤖 Railway AI: Master Agent Mission Briefing (v3.0.0)

This is the definitive document for the AI agent or developer responsible for the "FdC Railway Manager" client application. It contains the complete technical specifications, logic rules, and integration patterns for the Railway AI backend.

---

## 1. System Architecture & High-Resolution Logic
The backend is a hybrid C++/Python system designed for high-precision rail simulation.

*   **Time Resolution**: **30 seconds (0.5m)**. All calculations (conflicts, travel times) use this granularity to ensure 100% synchronization with real-world movement.
*   **Safety Buffer (Headway)**: **2 minutes**. The optimization engine enforces a mandatory 2-minute separation between trains in the same section to prevent "theoretical-only" solutions.
*   **Dwell Time**: Base stop time is **3 minutes** (unless overridden by `base_dwell_time`).

---

## 2. Authentication Protocol
Every request MUST be authenticated.

*   **Header**: `X-API-Key: rw-ABC123XYZ...`
*   **Validity**: 60 days.
*   **Lifecycle**: Verify status via `GET /api/v1/key-info`. If `remaining_days < 5`, prompt user for re-login via `POST /token`.

---

## 3. Core API Reference

### 🚀 Optimization (`POST /api/v1/optimize`)
Used for real-time conflict resolution.
- **Strategy**: If > 100 trains, the server uses **Selective Focus**.
    - **Active Trains**: Top 100 based on $Delay \times Priority$. AI modifies these.
    - **Passive Trains**: The remainder. AI treats them as static obstacles (immutable).
- **Critical Params**: `max_iterations` (Time horizon in minutes).

### 📈 Line Axis Analysis (`POST /api/v1/analyze_line`) - *NEW*
Strategic planning for a single line (A-to-B axis).
- **Inputs**: Ordered array of `tracks`.
- **Outputs**:
    *   `min_headway_min`: Hard physical saturation limit (Max capacity).
    *   `optimal_headway_min`: Suggested user-facing cadence (15/30/60 min).
    *   **`optimal_offset_min`**: Essential! Tells the client the exact minute offset for the return direction (B-A) to ensure meetings happen at double-track stations.
    *   `reliability_index`: Score (0-1) indicating infrastructure vulnerability.

### ⚡ Fast Propose (`POST /api/v1/propose_schedule`)
Used to generate entirely new logical lines from a raw graph. Response time < 0.5s.

---

## 4. Resource & Training Management
The backend is **self-improving**.

*   **Idle Training**: If no API activity occurs for 300 seconds, the server starts background MARL (Multi-Agent Reinforcement Learning) training.
*   **Pre-emption**: Background training is instantly terminated upon receiving a user request to ensure 100% responsiveness.

---

## 5. Compliance & Store Readiness (Apple/GDPR)

### Account Deletion (Apple Rule 5.1.1)
- **Endpoint**: `DELETE /api/v1/user/me`
- **Action**: Completely purges the user profile. Must be triggered from a "Danger Zone" in the App's settings.

### Terms & Privacy
- **Policy URL**: `http://railway-ai.michelebigi.it:8080/static/terms.html`
- **Registration**: You MUST include `accept_terms: true` in the request to `/api/v1/register/request`.

---

## 6. Optimization "Rules of Thumb" for the Agent
- **Uniqueness**: Every `train_id` in the `trains` array must be unique.
- **Pathfinding**: If `planned_route` is `null`, the server will perform A* pathfinding between `origin_station` and `destination_station` automatically.
- **Priority**: A priority of `10` forces a train into the "Active" category during large-scale network optimizations.

---

**Manual Last Updated**: February 2, 2026  
**Status**: Production Ready  
**Engine Precision**: 30s Step / 2m Buffer
