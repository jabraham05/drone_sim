# Setup

This project targets Ubuntu 24.04, ROS 2 Jazzy, PX4 SITL, Gazebo Harmonic, and Micro XRCE-DDS Agent.

Use this document before running `docs/running_simulation.md`.

## Expected Layout

The launcher assumes this layout by default:

```text
~/PX4-Autopilot
~/drone_ws
  src/
    drone_sim/
```

If your paths are different, pass overrides to the launcher:

```bash
python3 scripts/drone_launcher.py plan \
  --mission vertical_test \
  --px4-dir /path/to/PX4-Autopilot \
  --workspace-dir /path/to/drone_ws
```

## System Packages

Install common development tools:

```bash
sudo apt update
sudo apt install -y git curl wget lsb-release gnupg build-essential cmake python3-pip python3-venv
```

## ROS 2 Jazzy

Install ROS 2 Jazzy for Ubuntu 24.04 using the official ROS 2 Debian package instructions.

Minimum packages for this repo:

```bash
sudo apt install -y \
  ros-jazzy-desktop \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool
```

Source ROS 2 in every terminal that runs ROS commands:

```bash
source /opt/ros/jazzy/setup.bash
```

Optional shell setup:

```bash
echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
```

Initialize `rosdep` if needed:

```bash
sudo rosdep init
rosdep update
```

If `sudo rosdep init` reports that rosdep is already initialized, continue with `rosdep update`.

## Gazebo Harmonic

Install Gazebo Harmonic from OSRF packages:

```bash
sudo apt update
sudo apt install -y gz-harmonic
```

Check Gazebo:

```bash
gz sim --versions
```

## PX4 Autopilot

Clone PX4:

```bash
cd ~
git clone https://github.com/PX4/PX4-Autopilot.git
cd ~/PX4-Autopilot
git submodule update --init --recursive
```

Install PX4 development dependencies:

```bash
bash ./Tools/setup/ubuntu.sh
```

Restart the terminal after the PX4 setup script completes.

Check PX4 SITL:

```bash
cd ~/PX4-Autopilot
make px4_sitl gz_x500
```

Stop it with `Ctrl+C` after confirming Gazebo opens.

## Micro XRCE-DDS Agent

Install or build the Micro XRCE-DDS Agent so ROS 2 can communicate with PX4.

Check the command name available on your machine:

```bash
which MicroXRCEAgent || which micro-xrce-dds-agent
```

This repo's launcher currently uses:

```bash
micro-xrce-dds-agent udp4 -p 8888
```

If your install provides `MicroXRCEAgent` instead, either create an alias or update `scripts/drone_launcher.py`.

## Project Workspace

Create a ROS workspace:

```bash
mkdir -p ~/drone_ws/src
cd ~/drone_ws/src
git clone <this-repository-url> drone_sim
```

Install ROS dependencies:

```bash
cd ~/drone_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
```

Build the workspace:

```bash
colcon build
```

Source the workspace:

```bash
source ~/drone_ws/install/setup.bash
```

## Local Validation

From the repository root:

```bash
python3 -m compileall src scripts tests
python3 -m pytest src tests
```

From the ROS workspace root:

```bash
cd ~/drone_ws
source /opt/ros/jazzy/setup.bash
colcon build
colcon test
colcon test-result --verbose
```

## Preflight Checklist

Before running the simulation:

- ROS 2 Jazzy is sourced.
- `~/PX4-Autopilot` exists or a launcher override is provided.
- `~/drone_ws` exists or a launcher override is provided.
- `colcon build` has completed successfully.
- `source ~/drone_ws/install/setup.bash` has been run.
- Micro XRCE-DDS Agent is installed.
- Gazebo Harmonic is installed.
- PX4 SITL can start with `make px4_sitl gz_x500`.

After setup is complete, continue with `docs/running_simulation.md`.

## References

- ROS 2 Jazzy installation: https://docs.ros.org/en/jazzy/Installation.html
- ROS 2 Jazzy Ubuntu packages: https://docs.ros.org/en/jazzy/Installation/Ubuntu-Install-Debs.html
- Gazebo Harmonic install: https://gazebosim.org/docs/harmonic/install_ubuntu/
- PX4 ROS 2 guide: https://docs.px4.io/main/en/ros2/user_guide
