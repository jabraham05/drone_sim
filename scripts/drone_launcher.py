#!/usr/bin/env python3
"""Launch helper for the drone delivery simulation stack."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PX4_DIR = Path.home() / "PX4-Autopilot"
DEFAULT_WORKSPACE_DIR = Path.home() / "drone_ws"


@dataclass(frozen=True)
class Mission:
    name: str
    description: str
    config_path: Path
    world: str
    ros_entrypoint: str


@dataclass(frozen=True)
class LaunchCommand:
    name: str
    command: str
    cwd: Path | None = None


MISSIONS = {
    "simple_delivery": Mission(
        name="simple_delivery",
        description="Baseline home-to-delivery-to-home mission.",
        config_path=REPO_ROOT / "src" / "drone_bringup" / "config" / "mission.yaml",
        world="food_delivery",
        ros_entrypoint="ros2 run drone_mission offboard_takeoff",
    ),
}


def build_launch_commands(mission: Mission, px4_dir: Path, workspace_dir: Path) -> list[LaunchCommand]:
    return [
        LaunchCommand(
            name="PX4 + Gazebo",
            command=f"PX4_GZ_WORLD={mission.world} make px4_sitl gz_x500",
            cwd=px4_dir,
        ),
        LaunchCommand(
            name="Micro XRCE-DDS Agent",
            command="micro-xrce-dds-agent udp4 -p 8888",
        ),
        LaunchCommand(
            name="ROS 2 mission node",
            command=f"source install/setup.bash && {mission.ros_entrypoint}",
            cwd=workspace_dir,
        ),
    ]


def print_missions() -> None:
    for mission in MISSIONS.values():
        print(f"{mission.name}: {mission.description}")
        print(f"  config: {mission.config_path.relative_to(REPO_ROOT)}")
        print(f"  world: {mission.world}")


def print_launch_plan(commands: list[LaunchCommand]) -> None:
    for index, launch_command in enumerate(commands, start=1):
        cwd = str(launch_command.cwd) if launch_command.cwd else "current shell"
        print(f"{index}. {launch_command.name}")
        print(f"   cwd: {cwd}")
        print(f"   cmd: {launch_command.command}")


def start_commands(commands: list[LaunchCommand]) -> list[subprocess.Popen]:
    processes = []
    for launch_command in commands:
        print(f"Starting {launch_command.name}...")
        process = subprocess.Popen(
            launch_command.command,
            cwd=launch_command.cwd,
            shell=True,
            executable="/bin/bash",
        )
        processes.append(process)
    return processes


def choose_mission_interactively() -> Mission:
    mission_names = list(MISSIONS)
    print("Available missions:")
    for index, mission_name in enumerate(mission_names, start=1):
        print(f"{index}. {mission_name}")

    choice = input("Select mission: ").strip()
    if choice.isdigit():
        selected_index = int(choice) - 1
        if 0 <= selected_index < len(mission_names):
            return MISSIONS[mission_names[selected_index]]

    if choice in MISSIONS:
        return MISSIONS[choice]

    raise SystemExit(f"Unknown mission selection: {choice}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drone simulation launcher")
    parser.add_argument(
        "command",
        choices=("list-missions", "plan", "start"),
        help="Action to run.",
    )
    parser.add_argument(
        "--mission",
        choices=tuple(MISSIONS),
        help="Mission to use. If omitted for plan/start, the launcher prompts for a mission.",
    )
    parser.add_argument(
        "--px4-dir",
        type=Path,
        default=DEFAULT_PX4_DIR,
        help=f"PX4-Autopilot directory. Default: {DEFAULT_PX4_DIR}",
    )
    parser.add_argument(
        "--workspace-dir",
        type=Path,
        default=DEFAULT_WORKSPACE_DIR,
        help=f"ROS 2 workspace directory. Default: {DEFAULT_WORKSPACE_DIR}",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    if args.command == "list-missions":
        print_missions()
        return 0

    mission = MISSIONS[args.mission] if args.mission else choose_mission_interactively()
    commands = build_launch_commands(mission, args.px4_dir, args.workspace_dir)

    if args.command == "plan":
        print_launch_plan(commands)
        return 0

    print_launch_plan(commands)
    confirm = input("Start all commands? [y/N] ").strip().lower()
    if confirm != "y":
        print("Launch cancelled.")
        return 1

    processes = start_commands(commands)
    print("Launch commands started. Press Ctrl+C to stop this launcher.")
    try:
        for process in processes:
            process.wait()
    except KeyboardInterrupt:
        print("Stopping launched processes...")
        for process in processes:
            process.terminate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

