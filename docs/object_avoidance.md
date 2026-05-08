# Object Avoidance And Emergency Stop Plan

## Summary

This document defines how object avoidance should be implemented later, with a specific emergency-stop simulation test where the drone flies toward a building at high speed and must brake into a hover before collision.

This plan is documentation-only. It does not implement avoidance code, Gazebo assets, or automated tests yet.

## Documentation Changes

This plan should stay aligned with:

- `docs/interface_contracts.md`
- `docs/testing_checklist.md`
- `docs/roadmap.md`
- `README.md`

## Object Avoidance Design

Use Depth/LiDAR as the first obstacle sensor strategy.

Treat camera-only avoidance as future work, not the first safety layer.

Add a future `drone_safety` package or safety module with these responsibilities:

- Read obstacle distance and obstacle status.
- Decide when collision risk is critical.
- Override mission commands during emergency stop.
- Command brake and hover behavior.

Package boundaries:

- Keep PX4-specific emergency command publishing inside `drone_vehicle`.
- Keep obstacle detection inside `drone_perception`.
- Keep mission behavior inside `drone_mission`.
- Keep emergency-stop policy inside the future safety layer.

## Planned Topic Contract

All project-owned topics must stay under the `/drone/...` namespace.

Planned topics:

```text
/drone/perception/obstacles/nearest
/drone/perception/obstacles/status
/drone/safety/emergency_stop
/drone/safety/state
/drone/vehicle/command
/drone/vehicle/setpoint
```

External sensor topics, such as LiDAR or depth camera topics, should stay inside `drone_perception`.

Topic constants should be added to:

```text
src/drone_common/drone_common/topics.py
```

## Emergency Stop Test Scenario

Future scenario name:

```text
full_speed_building_stop
```

Scenario behavior:

- Drone starts at a fixed position facing a building.
- Mission commands forward flight at maximum configured test speed.
- Obstacle detector reports decreasing distance to the building.
- Safety layer triggers emergency stop when obstacle distance crosses a configured threshold.
- Drone switches from forward motion to brake and hover.
- Test passes only if the drone stops before the collision boundary.

## Acceptance Criteria

The emergency-stop scenario passes when:

- Emergency stop is triggered before impact.
- Forward velocity command is reduced to zero.
- Drone enters hover or hold behavior.
- No collision with the building occurs.
- Event is logged as an emergency stop.
- Mission does not continue forward until safety clears or an operator resets the mission.

## Future Test Plan

### Unit Tests

- Obstacle distance below threshold triggers emergency stop.
- Obstacle distance above threshold does not trigger emergency stop.
- Emergency stop overrides mission commands.
- Reset and clear behavior requires explicit safety recovery.

### Integration Tests

- Perception obstacle topic feeds safety state.
- Safety command feeds the vehicle command layer.
- Topic names use `drone_common.topics`.

### Gazebo / SITL Test

- Run `full_speed_building_stop`.
- Drone flies toward a building.
- Emergency stop triggers.
- Drone brakes and hovers before collision.

## Assumptions

- First avoidance implementation will use Depth/LiDAR, not camera-only detection.
- Emergency behavior is brake and hover, not immediate landing or return home.
- This is documentation-only for now.
- Implementation will come after the current `vertical_test` smoke mission and teammate control/CV integrations are stable.

## Suggested Next Steps

1. Add object-avoidance topic constants to `drone_common.topics`.
2. Add a `drone_safety` package skeleton.
3. Define the obstacle status message shape.
4. Add a Gazebo scenario config for `full_speed_building_stop`.
5. Implement unit tests for emergency-stop threshold logic.

