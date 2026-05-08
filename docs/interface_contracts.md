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

## Topic Standard

Project-owned ROS topics must use one namespace:

```text
/drone/...
```

Topic names are centralized in:

```text
src/drone_common/drone_common/topics.py
```

Code should import topic constants from `drone_common.topics` instead of hard-coding topic strings.

Use this namespace for communication between project packages. Do not create new top-level project topics such as `/landing_pad/...`, `/mission/...`, or `/vehicle/...`.

External system topics are allowed only at adapter boundaries:

- PX4 bridge topics stay under `/fmu/...` and are owned by `drone_vehicle`.
- Camera driver or Gazebo camera topics may stay under their source namespace and are owned by `drone_perception`.

Other packages should not publish or subscribe directly to external PX4 or raw camera topics unless the interface contract is updated.

## Initial Topic Contract

These names are the initial intended interface. They can change as implementation details become clearer, but changes must update this file and the affected docs.

### Vehicle Interface

External PX4 inputs consumed only by `drone_vehicle`:

- `/fmu/out/vehicle_status`
- `/fmu/out/vehicle_local_position`
- `/fmu/out/vehicle_odometry`

External PX4 outputs published only by `drone_vehicle`:

- `/fmu/in/offboard_control_mode`
- `/fmu/in/trajectory_setpoint`
- `/fmu/in/vehicle_command`

Project-owned vehicle topics:

- `/drone/vehicle/status`
- `/drone/vehicle/local_position`
- `/drone/vehicle/odometry`
- `/drone/vehicle/command`
- `/drone/vehicle/setpoint`

Mission-facing API rule:

- `drone_mission` should communicate through `/drone/vehicle/...` topics or a vehicle abstraction.
- `drone_mission` must not publish raw PX4 `/fmu/in/...` messages directly.

### Perception Interface

External camera inputs consumed only by `drone_perception`:

- `/camera/image_raw`
- `/camera/camera_info`

Project-owned perception topics:

- `/drone/perception/landing_pad/marker_pose`
- `/drone/perception/landing_pad/detection_status`

Initial behavior:

- Publish marker pose only when a valid marker is detected.
- Publish detection status so the mission layer can distinguish detected, lost, and unavailable states.

### Mission Interface

Mission inputs:

- Mission config from `src/drone_bringup/config/mission.yaml`
- Vehicle health and position from `/drone/vehicle/...`
- Landing marker status from `/drone/perception/...` when precision landing is enabled

Mission outputs:

- Vehicle commands through `/drone/vehicle/...`
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
