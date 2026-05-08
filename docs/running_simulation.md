# Running The Simulation

This document contains repeatable commands for starting PX4 SITL, Gazebo, the DDS agent, and ROS 2 mission nodes.

## Launcher Script

Use the launcher script from the repository root:

```bash
python3 scripts/drone_launcher.py list-missions
```

Show the commands for a mission without starting anything:

```bash
python3 scripts/drone_launcher.py plan --mission simple_delivery
```

Start the full stack:

```bash
python3 scripts/drone_launcher.py start --mission simple_delivery
```

If `--mission` is omitted for `plan` or `start`, the launcher prompts for a mission.

## Configurable Paths

The launcher assumes:

- PX4-Autopilot: `~/PX4-Autopilot`
- ROS 2 workspace: `~/drone_ws`

Override these paths when needed:

```bash
python3 scripts/drone_launcher.py plan \
  --mission simple_delivery \
  --px4-dir ~/PX4-Autopilot \
  --workspace-dir ~/drone_ws
```

## What The Launcher Starts

For `simple_delivery`, the launcher starts:

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
   source install/setup.bash && ros2 run drone_mission offboard_takeoff
   ```

## Mission Selection

Available missions are defined in:

```text
scripts/drone_launcher.py
```

Mission runtime parameters are currently stored in:

```text
src/drone_bringup/config/mission.yaml
```

Add new missions by adding a mission config and registering it in the launcher.
