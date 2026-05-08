# Autonomous Drone Delivery Simulation

A full-stack autonomous drone delivery simulation platform built with ROS 2, PX4, and Gazebo.

This project simulates an autonomous food delivery drone capable of:

- Autonomous takeoff and landing
- Waypoint navigation
- Offboard flight control through ROS 2
- Delivery mission state machines
- Return-to-home behavior
- Custom Gazebo simulation environments
- Future vision-based precision landing with OpenCV

## Tech Stack

- ROS 2 Jazzy
- PX4 Autopilot (SITL)
- Gazebo Harmonic / Gazebo Sim
- Python
- OpenCV (planned)
- QGroundControl

## Current Features

### Autonomous Mission State Machine

The drone currently performs a complete autonomous delivery mission:

```text
TAKEOFF_HOME
-> GO_TO_DELIVERY
-> LAND_DELIVERY
-> WAIT_AT_DELIVERY
-> TAKEOFF_DELIVERY
-> RETURN_HOME
-> LAND_HOME
-> DONE
```

### Offboard Control

The drone is controlled entirely through ROS 2 publishers using PX4 Offboard Mode.

### Custom Gazebo World

The custom simulation environment includes:

- Roads
- Buildings
- Delivery landing pad
- Realistic delivery environment layout

## System Architecture

```text
ROS 2 Mission Node
        |
        v
PX4 Offboard Control
        |
        v
Gazebo Drone Simulation
        |
        v
Custom World + Sensors
```

## Project Structure

```text
docs/
  architecture.md
  development_process.md
  roadmap.md
  running_simulation.md
  setup.md
  troubleshooting.md
src/
  drone_bringup/      # Launch files and runtime configuration
  drone_common/       # Shared utilities and configuration helpers
  drone_mission/      # Delivery mission state machines
  drone_perception/   # Camera and landing pad perception
  drone_simulation/   # Gazebo worlds, models, and scenarios
  drone_vehicle/      # PX4 Offboard interface and vehicle health checks
```

## Development Process

This project follows a documentation-first and documentation-last workflow:

1. Read the relevant documentation.
2. Create a short plan for the change.
3. Make the code changes.
4. Update affected documentation.
5. Run relevant validation checks.

Code changes are not complete until the docs are updated. See `docs/development_process.md` for the full workflow.

## Repository Goals

This project aims to evolve into a realistic autonomous drone delivery platform with:

- Precision landing
- Vision-based navigation
- OpenCV landing pad detection
- Obstacle avoidance
- Dynamic mission planning
- Multi-drone coordination
- Real-world deployment pipeline

## Setup

### Dependencies

- Ubuntu 24.04
- ROS 2 Jazzy
- PX4-Autopilot
- Gazebo Sim
- Micro XRCE-DDS Agent

## Running the Simulation

### Start PX4 + Gazebo

```bash
cd ~/PX4-Autopilot
PX4_GZ_WORLD=food_delivery make px4_sitl gz_x500
```

### Start DDS Agent

```bash
micro-xrce-dds-agent udp4 -p 8888
```

### Run Mission Node

```bash
cd ~/drone_ws
source install/setup.bash

ros2 run drone_mission offboard_takeoff
```

## Planned Features

- Downward-facing camera integration
- OpenCV precision landing
- ArUco marker detection
- Realistic delivery zones
- Path planning
- Obstacle avoidance
- Wind simulation
- GPS-denied navigation
- Reinforcement learning experiments

## Inspiration

This project explores the future of autonomous aerial delivery systems and robotics infrastructure.

## License

MIT License
