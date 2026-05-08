# Testing Checklist

Use this checklist before merging feature branches.

## General Checks

- The package imports successfully.
- Unit tests pass.
- No generated files are committed.
- No hard-coded local-only paths are required.
- Documentation is updated for changed behavior.
- Project-owned ROS topics use the `/drone/...` namespace.

## Commands

Run Python syntax validation:

```bash
python3 -m compileall src
```

When ROS 2 is available, run package tests from the workspace root:

```bash
colcon test
colcon test-result --verbose
```

When a package is ready to build with ROS 2:

```bash
colcon build
```

Run lightweight unit tests without ROS 2, PX4, or Gazebo:

```bash
pytest src tests
```

Run only project validation tests:

```bash
pytest tests
```

## GitHub Actions

The repository includes a lightweight CI workflow at `.github/workflows/ci.yml`.

It runs on every push and pull request:

- Python setup
- `python -m compileall src`
- `pytest src tests`

This CI does not run PX4 SITL, Gazebo, or full ROS 2 `colcon` checks. Those remain local or integration-machine validation steps.

## Topic Namespace Validation

Project topic rules are checked by `tests/test_topic_namespace.py`.

The validation enforces:

- Project-owned topics do not use `/landing_pad/...`, `/mission/...`, or `/vehicle/...`.
- PX4 `/fmu/...` topics appear only in `drone_vehicle`.
- Raw camera `/camera/...` topics appear only in `drone_perception`.
- Topic strings are centralized in `src/drone_common/drone_common/topics.py`.

Use `/drone/...` for communication between project packages.

## ArUco / Perception Checks

- Static image test detects the expected marker ID.
- Detector handles no-marker images without crashing.
- Detector documents required raw camera topic and `/drone/perception/...` output topics.
- Camera calibration assumptions are documented.
- Gazebo camera bridge is tested when a machine with Gazebo support is available.

## PX4 / Vehicle Control Checks

- Unit tests cover command creation or command publishing.
- Offboard setpoint streaming behavior is tested with mocks when SITL is unavailable.
- Code documents required PX4 `/fmu/...` topics, project `/drone/vehicle/...` topics, and message types.
- SITL test status is recorded: tested, not tested, or blocked by hardware.
- Manual override and failsafe assumptions are documented.

## Full Simulation Checks

Run these when PX4 SITL and Gazebo are available:

- PX4 starts with the `food_delivery` world.
- Micro XRCE-DDS Agent connects.
- ROS 2 nodes start without import or parameter errors.
- Drone arms and enters Offboard mode.
- Drone completes takeoff, delivery waypoint, landing, wait, return home, and final landing.
- Logs or rosbag output are captured for the run.
