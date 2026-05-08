# Roadmap

This document will track the project roadmap from simulation baseline through real-drone readiness.

## Phases

1. Repository foundation
2. Reliable SITL mission baseline
3. Gazebo delivery environment
4. ArUco precision landing
5. Safety and real-drone readiness
6. Advanced autonomy

## Design Documents

- `docs/object_avoidance.md`: planned Depth/LiDAR obstacle avoidance and emergency-stop test scenario.

## Next Steps

Current priorities:

1. Commit the repository governance updates: GitHub templates, CI workflow, and documentation updates.
2. Complete `docs/setup.md` on a machine that can run PX4/Gazebo.
3. Run `vertical_test` in PX4/Gazebo as the first smoke test for drone-control integration.
4. Ask teammates to submit their completed ArUco and drone-control work on separate feature branches.
5. Integrate drone-control work into `src/drone_vehicle` first, because mission execution depends on a stable vehicle interface.
6. Integrate ArUco detection into `src/drone_perception` after the control branch is reviewable.
7. Update `docs/interface_contracts.md` if either branch needs a new `/drone/...` topic, message type, or config field.
8. Run lightweight CI checks on each branch with `python3 -m compileall src scripts tests` and `python3 -m pytest src tests`.
9. Schedule PX4/Gazebo SITL validation once the control and perception branches are both merged or ready for integration testing.

## Current Blockers

- Teammate code has not been uploaded to the shared repository yet.
- Full PX4/Gazebo validation requires a machine that has completed `docs/setup.md`.
