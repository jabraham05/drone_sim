# Running The Simulation

This document contains repeatable commands for starting PX4 SITL, Gazebo, the DDS agent, and ROS 2 mission nodes.

Complete `docs/setup.md` before running these commands.

## Launcher Script

Use the launcher script from the repository root:

```bash
python3 scripts/drone_launcher.py list-missions
```

Show the commands for a mission without starting anything:

```bash
python3 scripts/drone_launcher.py plan --mission vertical_test
```

Start the full stack:

```bash
python3 scripts/drone_launcher.py start --mission vertical_test
```

If `--mission` is omitted for `plan` or `start`, the launcher prompts for a mission.

## Configurable Paths

The launcher assumes:

- PX4-Autopilot: `~/PX4-Autopilot`
- ROS 2 workspace: `~/drone_ws`

Override these paths when needed:

```bash
python3 scripts/drone_launcher.py plan \
  --mission vertical_test \
  --px4-dir ~/PX4-Autopilot \
  --workspace-dir ~/drone_ws
```

## What The Launcher Starts

For `vertical_test`, the launcher starts:

1. PX4 SITL with Gazebo:

   ```bash
   PX4_GZ_WORLD=food_delivery make px4_sitl gz_x500
   ```

2. Micro XRCE-DDS Agent:

   ```bash
   micro-xrce-dds-agent udp4 -p 8888
   ```

3. ROS 2 mission node:

   ```bash
   source install/setup.bash && ros2 run drone_vehicle vertical_takeoff_land --ros-args -p altitude_m:=5.0 -p takeoff_duration_s:=8.0 -p hold_duration_s:=10.0 -p landing_command_duration_s:=2.0
   ```

## Mission Selection

Current missions:

- `vertical_test`: implemented PX4 Offboard smoke mission that takes off, holds position, then commands land.
- `simple_delivery`: home-to-delivery-to-home mission definition.

## `vertical_test` Behavior

The `vertical_test` mission runs:

```text
PRE_STREAM -> TAKEOFF -> HOLD -> LAND -> DONE
```

Runtime behavior:

- Pre-streams position setpoints before switching to Offboard mode.
- Requests PX4 Offboard mode.
- Arms the vehicle.
- Publishes a local NED setpoint at `z = -5.0` for takeoff and hold.
- Holds for `10.0` seconds.
- Sends `VEHICLE_CMD_NAV_LAND`.

This first mission is time-based. It does not yet verify altitude using vehicle odometry, so it should be treated as a smoke test for PX4/Gazebo integration rather than a complete autonomous controller.

Available missions are defined in:

```text
scripts/drone_launcher.py
```

Mission runtime parameters are currently stored in:

```text
src/drone_bringup/config/
```

Add new missions by adding a mission config and registering it in the launcher.
