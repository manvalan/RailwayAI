# 🤖 Advanced Agent Manual: Railway AI API v2.2

This comprehensive guide is the definitive reference for agents and developers integrating with the Railway AI backend. It covers authentication, optimization strategies for complex networks, and background system behavior.

---

## 1. Authentication & Security (Mandatory)

The system uses **long-lived API Keys** for all authenticated requests.

- **Header**: `X-API-Key: <your_api_key>`
- **Token Acquisition**: Via `POST /token` (returns a 60-day key).
- **Key Validation**: Always check `GET /api/v1/key-info` on app startup to verify `privilege` level and `remaining_days`.

---

## 2. Optimization Strategy: Complex Networks

The backend implements a **Selective Focus Strategy** to handle large-scale railway networks efficiently.

### The "Top 100" Rule
When an optimization request contains more than 100 trains, the server automatically:
1.  **Prioritizes**: Calculates a "Criticality Score" ($Score = Delay \times Priority$).
2.  **Segments**:
    *   **Active Trains (Top 100)**: These are the only trains the AI will attempt to reschedule/reroute.
    *   **Passive Trains (The rest)**: These are treated as **Static Constraints**. They appear in the simulation and cause conflicts if they block a track, but the AI will NOT modify their schedules.

### How to Declare Passive/Active Trains (Implicit vs Explicit)
- **Implicit (Recommended)**: Send all trains in the `trains` array. The server will decide which 100 are active based on the $Delay \times Priority$ score.
- **Explicit control**: If you want a specific train to be "Active" despite having low delay, ensure its `priority` is set to `10`. To make a train more likely to be "Passive", set its `priority` to `1` and `delay_minutes` to `0`.

---

## 3. Preparing Optimization Requests

**Endpoint**: `POST /api/v1/optimize`

### Payload Structure
```json
{
  "trains": [
    {
      "id": 1024,
      "origin_station": 5,           // Required for auto-routing
      "destination_station": 12,    // Required for auto-routing
      "velocity_kmh": 140,
      "priority": 8,                 // 1 (low) to 10 (high)
      "delay_minutes": 5.2,
      "is_delayed": true,
      "planned_route": null          // Leave null for server-side pathfinding
    }
  ],
  "max_iterations": 120,             // Also acts as the time horizon in minutes
  "ga_max_iterations": 200           // Complexity of the resolution algorithm
}
```

---

## 4. Background System Behavior: Idle Training

The system is designed to be **Self-Improving**.

- **Idle Mode**: If no API activity is detected for **5 minutes**, the server starts background MARL training.
- **Auto-Suspension**: Background training is **instantly killed** when a user request (like `/optimize`) is received.
- **Impact on Client**: None. The process management is server-side, ensuring full CPU/GPU availability for user requests.

---

## 5. Compliance & Regulatory Standards

If publishing to the App Store or operating in the EU, use the following:

- **Privacy URL**: Link to `/static/terms.html`.
- **Account Deletion**: Use `DELETE /api/v1/user/me` in the user's settings profile.
- **Terms Acceptance**: Ensure your registration UI includes the `accept_terms: true` boolean in the request to `/api/v1/register/request`.

---

## 6. Error Handling Strategy

- **401 Unauthorized**: Key expired or missing. Trigger login flow.
- **403 Forbidden**: User has `normal` privilege but tried an `admin` operation (e.g., `/train`).
- **422 Unprocessable Entity**: JSON schema mismatch. Validate `train_id` uniqueness.
- **504 Gateway Timeout**: Network too complex for the requested `max_iterations`. Reduce complexity or increase timeout.

---

## 7. Line Axis Analysis (Strategic Planning)

**Endpoint**: `POST /api/v1/analyze_line`

This API analyzes a linear sequence of tracks (an "axis") to determine the best service frequency and synchronization between opposing ends (A vs B).

### Payload
- `tracks`: The chain of track objects.
- `avg_speed_kmh`: Planned speed for the analysis.
- `min_dwell_time_min`: Minimum stop time at intermediate points.

### Key Outputs
- `min_headway_min`: The "Saturation Point". Minimum minutes between trains to avoid blockage.
- `optimal_headway_min`: Suggested frequency (15, 30, 60 min) for regular service.
- `optimal_offset_min`: **Synchronization Minute**. The shift (in minutes) for the B-to-A direction to ensure optimal encounters at stations or double-track sections.
- `reliability_index`: A score (0-1) indicating how resilient the line is to delays based on single-track bottlenecks.

---

**Manual Version**: 2.3.0  
**Compliance**: GDPR & Apple Guideline 5.1.1 compliant.
