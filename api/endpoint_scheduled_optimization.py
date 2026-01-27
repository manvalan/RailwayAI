"""
New API endpoint for scheduled train optimization with route planning.
Add this code to api/server.py after the existing /api/v1/optimize endpoint.
"""

@app.post("/api/v1/optimize_scheduled", response_model=OptimizationResponse, tags=["Optimization"])
async def optimize_scheduled_trains(
    request: OptimizationRequest,
    background_tasks: BackgroundTasks,
    current_user: str = Depends(get_current_user)
):
    """
    Optimize train schedule with route planning and temporal simulation.
    
    Supports:
    - Scheduled departure times
    - Automatic route planning between origin and destination
    - Future conflict detection over time horizon
    - Optimal departure time adjustments
    
    Example request:
    ```json
    {
      "trains": [
        {
          "id": 0,
          "origin_station": 11,
          "destination_station": 1,
          "scheduled_departure_time": "12:00:00",
          "velocity_kmh": 160,
          "priority": 5,
          "position_km": 0,
          "current_track": 18
        }
      ],
      "tracks": [...],
      "stations": [...],
      "max_iterations": 60
    }
    ```
    """
    global route_planner, temporal_simulator
    
    start_time = time.time()
    metrics['total_requests'] += 1
    
    if model is None:
        metrics['failed_optimizations'] += 1
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Initialize route planner and simulator if needed
        if (route_planner is None or temporal_simulator is None) and request.tracks and request.stations:
            logger.info("Initializing route planner and temporal simulator")
            route_planner = RoutePlanner(
                [t.dict() for t in request.tracks],
                [s.dict() for s in request.stations]
            )
            temporal_simulator = TemporalSimulator(
                {t.id: t.dict() for t in request.tracks}
            )
        
        if route_planner is None or temporal_simulator is None:
            raise HTTPException(
                status_code=400,
                detail="Route planner not initialized. Please provide tracks and stations."
            )
        
        # Plan routes for trains that need it
        trains_with_routes = []
        for train in request.trains:
            train_dict = train.dict()
            
            # Auto-plan route if origin and destination provided but no planned_route
            if train.planned_route is None and train.origin_station is not None:
                logger.info(f"Planning route for train {train.id} from station {train.origin_station} "
                           f"to {train.destination_station}")
                
                route_plan = route_planner.plan_route(
                    train.origin_station,
                    train.destination_station,
                    avg_speed_kmh=train.velocity_kmh if train.velocity_kmh > 0 else 120.0
                )
                
                if route_plan:
                    train_dict['planned_route'] = route_plan['track_ids']
                    logger.info(f"Route planned for train {train.id}: {len(route_plan['track_ids'])} tracks, "
                               f"{route_plan['total_distance_km']:.1f} km, "
                               f"{route_plan['total_time_minutes']:.1f} min")
                else:
                    logger.warning(f"Could not plan route for train {train.id} from {train.origin_station} "
                                 f"to {train.destination_station}")
                    # Continue without route - will use current_track only
            
            trains_with_routes.append(train_dict)
        
        # Detect future conflicts using temporal simulation
        time_horizon = request.max_iterations  # Use max_iterations as time horizon in minutes
        logger.info(f"Detecting future conflicts over {time_horizon} minute horizon")
        
        future_conflicts = temporal_simulator.detect_future_conflicts(
            trains_with_routes,
            time_horizon_minutes=float(time_horizon),
            time_step_minutes=1.0
        )
        
        logger.info(f"Detected {len(future_conflicts)} future conflicts")
        
        # Generate resolutions for conflicts
        resolutions = []
        processed_trains = set()
        
        for conflict in future_conflicts[:10]:  # Limit to first 10 conflicts
            train1_id = conflict['train1_id']
            train2_id = conflict['train2_id']
            
            # Skip if we've already adjusted one of these trains
            if train1_id in processed_trains and train2_id in processed_trains:
                continue
            
            # Find the trains
            train1 = next((t for t in request.trains if t.id == train1_id), None)
            train2 = next((t for t in request.trains if t.id == train2_id), None)
            
            if not train1 or not train2:
                continue
            
            # Determine which train to delay based on priority
            if train1.priority < train2.priority:
                lower_priority_train = train1
                higher_priority_train = train2
            elif train2.priority < train1.priority:
                lower_priority_train = train2
                higher_priority_train = train1
            else:
                # Equal priority - use ID as tie-breaker
                lower_priority_train = train1 if train1.id > train2.id else train2
                higher_priority_train = train2 if train1.id > train2.id else train1
            
            # Skip if already processed
            if lower_priority_train.id in processed_trains:
                continue
            
            # Calculate delay needed
            # Add buffer time to the conflict time
            delay_minutes = conflict['time_offset_minutes'] + 10.0
            
            # For single-track conflicts, add more delay
            if conflict['conflict_type'] == 'single_track':
                delay_minutes += 5.0
            
            resolutions.append(Resolution(
                train_id=lower_priority_train.id,
                time_adjustment_min=delay_minutes,
                track_assignment=conflict['track_id'],
                confidence=0.85 if conflict['conflict_type'] == 'single_track' else 0.75
            ))
            
            processed_trains.add(lower_priority_train.id)
            
            logger.info(f"Resolution: Delay train {lower_priority_train.id} by {delay_minutes:.1f} min "
                       f"to avoid {conflict['conflict_type']} conflict at t={conflict['time_offset_minutes']:.1f} min")
        
        # Calculate metrics
        inference_time = (time.time() - start_time) * 1000.0
        total_delay = sum(r.time_adjustment_min for r in resolutions)
        
        # Update global metrics
        metrics['successful_optimizations'] += 1
        metrics['total_inference_time_ms'] += inference_time
        metrics['avg_inference_time_ms'] = (
            metrics['total_inference_time_ms'] / metrics['successful_optimizations']
        )
        
        logger.info(f"Scheduled optimization completed: {len(request.trains)} trains, "
                   f"{len(future_conflicts)} conflicts detected, {len(resolutions)} resolutions, "
                   f"{inference_time:.2f}ms")
        
        return OptimizationResponse(
            success=True,
            resolutions=resolutions,
            total_delay_minutes=total_delay,
            inference_time_ms=inference_time,
            conflicts_detected=len(future_conflicts),
            conflicts_resolved=len(resolutions),
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        metrics['failed_optimizations'] += 1
        logger.error(f"Scheduled optimization failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
