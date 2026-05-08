# Integration Guide

Use this guide when adding teammate work into the shared repository.

## Branches

Create a separate branch for each workstream:

```bash
git checkout main
git pull
git checkout -b feature/aruco-detection
```

```bash
git checkout main
git pull
git checkout -b feature/drone-control
```

Keep each branch focused. Do not mix perception, vehicle control, simulation world edits, and documentation cleanup in the same branch unless the changes are required for one feature to work.

## Where Code Goes

- ArUco/OpenCV detection code goes in `src/drone_perception`.
- PX4 Offboard control code goes in `src/drone_vehicle`.
- Mission state machine code goes in `src/drone_mission`.
- Gazebo worlds, models, camera setup, and scenarios go in `src/drone_simulation`.
- Launch files and runtime YAML configs go in `src/drone_bringup`.
- Shared helpers that are truly reused by more than one package go in `src/drone_common`.

## What To Include

Every feature branch should include:

- Source code in the correct package
- Tests that can run without PX4/Gazebo when possible
- Example config or launch changes when needed
- Documentation updates for changed behavior, commands, topics, or assumptions
- Notes about anything that was not tested locally

## Topic Naming Rule

Project-owned ROS topics must use the `/drone/...` namespace defined in `docs/interface_contracts.md`.

Do not add new project-level topics like `/landing_pad/...`, `/mission/...`, or `/vehicle/...`.

Allowed external topic exceptions:

- PX4 bridge topics under `/fmu/...` belong only inside `src/drone_vehicle`.
- Raw camera topics such as `/camera/image_raw` belong only inside `src/drone_perception`.

## CV Workstream Checklist

For ArUco detection work, include:

- Detector source code
- Static test image or generated fixture
- Test that verifies marker detection from a known image
- Expected camera topic name
- Expected `/drone/perception/...` output topic name and message type
- Camera calibration assumptions
- OpenCV version or dependency notes

Initial target package:

```text
src/drone_perception/
```

## Drone Control Workstream Checklist

For PX4 control work, include:

- Vehicle interface source code
- Unit tests with mocked PX4 messages or mocked publishers/subscribers
- Expected PX4 ROS 2 topics
- Expected `/drone/vehicle/...` project topics
- Required PX4 message types
- Assumptions about arming, Offboard mode, and setpoint streaming
- Notes if Gazebo/PX4 SITL was not tested locally

Initial target package:

```text
src/drone_vehicle/
```

## Review Criteria

Before merging a branch:

- The code is in the correct package.
- The branch does not introduce unrelated rewrites.
- Tests pass locally where possible.
- Topic namespace validation passes.
- Documentation is updated.
- Any untested PX4/Gazebo behavior is clearly documented.
- The feature can be launched, tested, or imported without hidden local-only paths.
