# Interface Contracts

This document defines the intended boundaries between ROS 2 packages. These contracts should stay stable enough that teammates can work in parallel without tightly coupling every module.

## Package Responsibilities

### `drone_mission`

Owns delivery mission behavior.

Responsibilities:

- Mission state machine
- Delivery waypoint sequencing
- Return-to-home behavior
- Mission timeout and failsafe decisions
- High-level commands to the vehicle interface

Should not own:

- Raw PX4 topic details
- OpenCV image processing
- Gazebo world assets

### `drone_vehicle`

Owns PX4 vehicle communication.

Responsibilities:

- PX4 Offboard mode setup
- Arming and mode commands
- Setpoint publishing
- Vehicle status and health tracking
- Local position and odometry subscriptions

Should not own:

- Delivery mission policy
- Landing marker detection
- Simulation-only world logic

### `drone_perception`

Owns camera perception.

Responsibilities:

- Camera image subscription
- ArUco marker detection
- Landing pad pose estimation
- Marker confidence/status publishing

Should not own:

- Vehicle arming or mode changes
- Mission state transitions
- Gazebo world generation

### `drone_simulation`

Owns simulation assets.

Responsibilities:

- Gazebo worlds
- Models and landing pads
- Scenario definitions
- Simulation sensor placement

Should not own:

- Mission state machine logic
- PX4 command logic

### `drone_bringup`

Owns launch and runtime configuration.

Responsibilities:

- Launch files
- Mission YAML configs
- Node composition and parameter wiring
- Repeatable simulation startup entrypoints

## Initial Topic Contract

These names are the initial intended interface. They can change as implementation details become clearer, but changes must update this file and the affected docs.

### Vehicle Interface

Inputs consumed by `drone_vehicle`:

- `/fmu/out/vehicle_status`
- `/fmu/out/vehicle_local_position`
- `/fmu/out/vehicle_odometry`

Outputs published by `drone_vehicle`:

- `/fmu/in/offboard_control_mode`
- `/fmu/in/trajectory_setpoint`
- `/fmu/in/vehicle_command`

Mission-facing API target:

- The mission layer should call a vehicle abstraction rather than publishing raw PX4 messages directly.
- The first implementation may be an in-process Python class.
- A later implementation may expose ROS services/actions if separate mission and vehicle nodes are needed.

### Perception Interface

Inputs consumed by `drone_perception`:

- `/camera/image_raw`
- `/camera/camera_info`

Outputs published by `drone_perception`:

- `/landing_pad/marker_pose`
- `/landing_pad/detection_status`

Initial behavior:

- Publish marker pose only when a valid marker is detected.
- Publish detection status so the mission layer can distinguish detected, lost, and unavailable states.

### Mission Interface

Mission inputs:

- Mission config from `src/drone_bringup/config/mission.yaml`
- Vehicle health and position from `drone_vehicle`
- Landing marker status from `drone_perception` when precision landing is enabled

Mission outputs:

- Vehicle commands through `drone_vehicle`
- Mission state logs through ROS 2 logging
- Structured mission event logs in a future logging module

## Configuration Contract

Runtime configuration belongs in YAML under `src/drone_bringup/config`.

Current baseline config:

```text
src/drone_bringup/config/mission.yaml
```

Expected mission fields:

- Home position
- Delivery position
- Cruise altitude
- Acceptance radius
- Delivery wait duration

