# RailwayAI Integration Specifications for FDC
**Document Version**: 1.0  
**Date**: November 19, 2025  
**Target**: RailwayAI Development Team

---

## Executive Summary

This document specifies the JSON data format that **RailwayAI must return** to enable seamless integration with the FDC (Ferrovie della Contea) railway management system. The current implementation returns only generic delay values, which are insufficient for sophisticated conflict resolution.

---

## Current Implementation (Insufficient)

### What RailwayAI Returns Now
```json
{
  "success": true,
  "modifications": [
    {
      "train_id": "TRAIN_024",
      "delay_minutes": -3,
      "new_route": [],
      "reason": "Anticipo per evitare conflitto"
    }
  ],
  "total_delay_minutes": 3.0,
  "ml_confidence": 0.85,
  "error_message": ""
}
```

### The Problem
- ✅ **train_id**: Good - identifies the train
- ✅ **delay_minutes**: Good - indicates time shift (negative = advance, positive = delay)
- ❌ **Missing critical details**: HOW to achieve this delay (speed change? platform change? dwell time adjustment?)
- ❌ **No station/section information**: WHERE to apply modifications
- ❌ **No action-specific parameters**: What speed? Which platform? Which station?

This forces FDC to apply delays by **blindly shifting all stop times**, which:
- Wastes optimization potential (e.g., platform changes could resolve conflicts without delays)
- Propagates delays to all subsequent stops unnecessarily
- Doesn't leverage intelligent track switching capabilities

---

## Required JSON Format (Enhanced)

### Option 1: Detailed Modifications (RECOMMENDED)

RailwayAI should return **specific, actionable modifications** with all necessary details:

```json
{
  "success": true,
  "optimization_type": "multi_train_coordination",
  "total_impact_minutes": 5,
  "ml_confidence": 0.92,
  "modifications": [
    {
      "train_id": "IC101",
      "modification_type": "speed_reduction",
      "section": {
        "from_station": "MILANO_CENTRALE",
        "to_station": "MONZA"
      },
      "parameters": {
        "new_speed_kmh": 100,
        "original_speed_kmh": 140
      },
      "impact": {
        "time_increase_seconds": 180,
        "affected_stations": ["MONZA", "COMO"]
      },
      "reason": "Riduzione velocità per coordinamento con R203",
      "confidence": 0.95
    },
    {
      "train_id": "R203",
      "modification_type": "platform_change",
      "section": {
        "station": "MONZA"
      },
      "parameters": {
        "new_platform": 2,
        "original_platform": 1
      },
      "impact": {
        "time_increase_seconds": 0,
        "affected_stations": ["MONZA"]
      },
      "reason": "Cambio binario per evitare conflitto con IC101",
      "confidence": 0.98
    },
    {
      "train_id": "R205",
      "modification_type": "dwell_time_increase",
      "section": {
        "station": "COMO"
      },
      "parameters": {
        "additional_seconds": 120,
        "original_dwell_seconds": 180
      },
      "impact": {
        "time_increase_seconds": 120,
        "affected_stations": ["MONZA", "MILANO_CENTRALE"]
      },
      "reason": "Aumento sosta per separazione temporale",
      "confidence": 0.88
    }
  ],
  "alternatives": [
    {
      "description": "Alternativa con ritardo distribuito",
      "total_impact_minutes": 7,
      "confidence": 0.85,
      "modifications": [
        {
          "train_id": "IC101",
          "modification_type": "departure_delay",
          "section": {
            "station": "MILANO_CENTRALE"
          },
          "parameters": {
            "delay_seconds": 240
          },
          "impact": {
            "time_increase_seconds": 240,
            "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"]
          },
          "reason": "Ritardo partenza come alternativa",
          "confidence": 0.85
        }
      ]
    }
  ],
  "conflict_analysis": {
    "original_conflicts": [
      {
        "type": "platform_conflict",
        "location": "MONZA",
        "trains": ["IC101", "R203"],
        "severity": "high"
      }
    ],
    "resolved_conflicts": 1,
    "remaining_conflicts": 0
  }
}
```

---

## Modification Types and Required Parameters

### 1. `speed_reduction` / `speed_increase`

**Purpose**: Change train speed on a specific section

**Required Fields**:
```json
{
  "modification_type": "speed_reduction",
  "section": {
    "from_station": "STATION_A",  // Station ID (string)
    "to_station": "STATION_B"      // Station ID (string)
  },
  "parameters": {
    "new_speed_kmh": 100.0,        // Target speed (double)
    "original_speed_kmh": 140.0    // Original speed (double, optional)
  }
}
```

**FDC Processing**:
- Recalculates travel time between stations
- Updates arrival/departure times for affected stations
- Propagates delay to subsequent stops

---

### 2. `platform_change`

**Purpose**: Change platform assignment at a station

**Required Fields**:
```json
{
  "modification_type": "platform_change",
  "section": {
    "station": "MONZA"              // Station ID (string)
  },
  "parameters": {
    "new_platform": 2,              // Target platform number (integer)
    "original_platform": 1          // Original platform (integer, optional)
  }
}
```

**FDC Processing**:
- Updates platform assignment for specified station
- Validates platform availability
- Checks for platform conflicts with other trains

**Important**: Platform changes can often resolve conflicts **without adding delays**!

---

### 3. `dwell_time_increase` / `dwell_time_decrease`

**Purpose**: Modify stop duration at a station

**Required Fields**:
```json
{
  "modification_type": "dwell_time_increase",
  "section": {
    "station": "COMO"                // Station ID (string)
  },
  "parameters": {
    "additional_seconds": 120,       // Time change in seconds (integer, can be negative)
    "original_dwell_seconds": 180    // Original dwell time (integer, optional)
  }
}
```

**FDC Processing**:
- Adjusts departure time at specified station
- Propagates time shift to subsequent stops
- Maintains arrival time at the station

---

### 4. `departure_delay` / `departure_advance`

**Purpose**: Shift entire schedule by delaying/advancing departure from origin

**Required Fields**:
```json
{
  "modification_type": "departure_delay",
  "section": {
    "station": "MILANO_CENTRALE"    // Origin station ID (string)
  },
  "parameters": {
    "delay_seconds": 240            // Time shift in seconds (integer, negative = advance)
  }
}
```

**FDC Processing**:
- Shifts all stop times by specified amount
- Simple global time adjustment
- Use this when no more sophisticated optimization is available

---

### 5. `stop_skip` (Advanced)

**Purpose**: Skip a scheduled stop

**Required Fields**:
```json
{
  "modification_type": "stop_skip",
  "section": {
    "station": "MONZA"              // Station to skip (string)
  },
  "parameters": {
    "reason": "optimization"        // Why skip this stop (string)
  }
}
```

**FDC Processing**:
- Removes stop from schedule
- Recalculates direct travel time
- Updates subsequent stop times

⚠️ **Use carefully**: Skipping stops affects service quality!

---

### 6. `route_change` (Advanced)

**Purpose**: Reroute train through different stations

**Required Fields**:
```json
{
  "modification_type": "route_change",
  "section": {
    "from_station": "MILANO_CENTRALE",
    "to_station": "COMO"
  },
  "parameters": {
    "new_route": ["MILANO_CENTRALE", "SARONNO", "COMO"],  // New station sequence
    "original_route": ["MILANO_CENTRALE", "MONZA", "COMO"]
  }
}
```

**FDC Processing**:
- Replaces route segment
- Recalculates all timings
- Validates track availability

⚠️ **Complex**: Requires extensive network knowledge!

---

## Impact Information (Required for All Modifications)

Each modification must include an `impact` object:

```json
"impact": {
  "time_increase_seconds": 180,           // Total delay added (integer)
  "affected_stations": ["MONZA", "COMO"], // List of stations with changed times
  "passenger_impact_score": 0.3           // Optional: 0-1 scale, passenger inconvenience
}
```

This helps FDC:
- Display impact to users
- Prioritize between alternatives
- Validate modifications

---

## Alternative Solutions

RailwayAI should provide **multiple solutions** ranked by quality:

```json
"alternatives": [
  {
    "description": "Soluzione con cambio binario (preferita)",
    "total_impact_minutes": 2,
    "confidence": 0.95,
    "modifications": [ /* ... */ ]
  },
  {
    "description": "Soluzione con ritardo distribuito",
    "total_impact_minutes": 5,
    "confidence": 0.88,
    "modifications": [ /* ... */ ]
  },
  {
    "description": "Soluzione con riduzione velocità",
    "total_impact_minutes": 3,
    "confidence": 0.92,
    "modifications": [ /* ... */ ]
  }
]
```

**Benefits**:
- FDC can try alternatives if primary solution fails validation
- Users can choose based on preferences (minimal delay vs. no speed changes)
- System resilience improves

---

## Validation and Error Handling

### Success Response
```json
{
  "success": true,
  "modifications": [ /* ... */ ],
  "conflict_analysis": {
    "original_conflicts": 3,
    "resolved_conflicts": 3,
    "remaining_conflicts": 0
  }
}
```

### Partial Success
```json
{
  "success": true,
  "modifications": [ /* ... */ ],
  "conflict_analysis": {
    "original_conflicts": 5,
    "resolved_conflicts": 4,
    "remaining_conflicts": 1,
    "unresolved_details": [
      {
        "type": "capacity_limit",
        "description": "Binario 1 saturo alle 08:15",
        "affected_trains": ["IC101", "R203"]
      }
    ]
  }
}
```

### Failure Response
```json
{
  "success": false,
  "error_message": "Impossibile risolvere conflitti senza violare vincoli di capacità",
  "error_code": "CAPACITY_EXCEEDED",
  "conflict_analysis": {
    "original_conflicts": 3,
    "resolved_conflicts": 0,
    "remaining_conflicts": 3
  },
  "suggestions": [
    "Ridurre il numero di treni nella finestra oraria 08:00-09:00",
    "Aumentare capacità binari alla stazione MONZA"
  ]
}
```

---

## Minimal Backward-Compatible Implementation

If full implementation is too complex initially, RailwayAI can start with this minimal format:

```json
{
  "success": true,
  "modifications": [
    {
      "train_id": "IC101",
      "modification_type": "departure_delay",
      "section": {
        "station": "MILANO_CENTRALE"
      },
      "parameters": {
        "delay_seconds": 180
      },
      "impact": {
        "time_increase_seconds": 180,
        "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"]
      },
      "reason": "Ritardo partenza per evitare conflitto",
      "confidence": 0.85
    }
  ],
  "total_impact_minutes": 3,
  "ml_confidence": 0.85
}
```

This provides:
- ✅ Station information (where to apply modification)
- ✅ Explicit modification type
- ✅ All required parameters
- ✅ Impact assessment
- ✅ Can be extended to more sophisticated types later

---

## Integration Testing Checklist

Before deployment, RailwayAI should test:

- [ ] **Speed changes**: Return valid station pairs and speed values
- [ ] **Platform changes**: Return valid station IDs and platform numbers
- [ ] **Dwell time changes**: Return valid station IDs and time adjustments
- [ ] **Departure delays**: Return valid origin station and delay amount
- [ ] **Multiple modifications**: Test coordinated multi-train solutions
- [ ] **Alternatives**: Provide 2-3 ranked alternatives per conflict
- [ ] **Error cases**: Return proper error messages when optimization fails
- [ ] **JSON validation**: Ensure all required fields are present
- [ ] **Station ID matching**: Use exact station IDs from input network
- [ ] **Confidence scores**: Return realistic 0.0-1.0 values

---

## Expected Benefits

With this enhanced format, FDC can:

✅ **Apply sophisticated optimizations**:
- Platform changes without delays
- Targeted speed adjustments on specific sections
- Minimal passenger impact through dwell time tuning

✅ **Provide better user experience**:
- Show detailed explanation of each modification
- Display impact per station
- Let users choose between alternatives

✅ **Improve conflict resolution**:
- Try alternatives if primary solution fails validation
- Combine multiple modification types
- Minimize total delay while respecting constraints

✅ **Leverage RailwayAI's ML capabilities**:
- Use intelligent track switching
- Optimize across multiple trains simultaneously
- Learn from past conflicts

---

## Contact and Support

**FDC Integration Team**:
- Repository: https://github.com/manvalan/FDC
- Branch: cpp-rewrite
- Integration Point: `cpp/src/ai_scheduler.cpp` (resolve_conflict_with_railway_ai)

**Questions?**
Please open an issue in the FDC repository with tag `[RailwayAI Integration]`

---

## Appendix: Example Scenario

### Input Conflict
```json
{
  "conflict_type": "platform_conflict",
  "location": "MONZA",
  "trains": [
    {
      "train_id": "IC101",
      "arrival": "2025-11-16T08:08:00",
      "departure": "2025-11-16T08:10:00",
      "platform": 1
    },
    {
      "train_id": "R203",
      "arrival": "2025-11-16T08:15:00",
      "departure": "2025-11-16T08:17:00",
      "platform": 1
    }
  ],
  "severity": "high",
  "time_overlap_seconds": 300
}
```

### Expected RailwayAI Response
```json
{
  "success": true,
  "optimization_type": "platform_reassignment",
  "total_impact_minutes": 0,
  "ml_confidence": 0.96,
  "modifications": [
    {
      "train_id": "R203",
      "modification_type": "platform_change",
      "section": {
        "station": "MONZA"
      },
      "parameters": {
        "new_platform": 2,
        "original_platform": 1
      },
      "impact": {
        "time_increase_seconds": 0,
        "affected_stations": ["MONZA"]
      },
      "reason": "Cambio binario risolve conflitto senza ritardi",
      "confidence": 0.96
    }
  ],
  "alternatives": [
    {
      "description": "Ritardo IC101 di 3 minuti",
      "total_impact_minutes": 3,
      "confidence": 0.88,
      "modifications": [
        {
          "train_id": "IC101",
          "modification_type": "departure_delay",
          "section": {
            "station": "MILANO_CENTRALE"
          },
          "parameters": {
            "delay_seconds": 180
          },
          "impact": {
            "time_increase_seconds": 180,
            "affected_stations": ["MILANO_CENTRALE", "MONZA", "COMO"]
          },
          "reason": "Ritardo partenza alternativo",
          "confidence": 0.88
        }
      ]
    }
  ],
  "conflict_analysis": {
    "original_conflicts": 1,
    "resolved_conflicts": 1,
    "remaining_conflicts": 0
  }
}
```

**Result**: Conflict resolved with **zero delay** by intelligent platform reassignment! 🎯

---

*End of Specifications Document*
