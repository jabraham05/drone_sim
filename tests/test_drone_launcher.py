import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCHER_FILE = REPO_ROOT / "scripts" / "drone_launcher.py"
SPEC = importlib.util.spec_from_file_location("drone_launcher", LAUNCHER_FILE)
drone_launcher = importlib.util.module_from_spec(SPEC)
sys.modules["drone_launcher"] = drone_launcher
SPEC.loader.exec_module(drone_launcher)


def test_default_mission_exists():
    assert "simple_delivery" in drone_launcher.MISSIONS


def test_launch_commands_include_required_stack_parts():
    mission = drone_launcher.MISSIONS["simple_delivery"]
    commands = drone_launcher.build_launch_commands(
        mission,
        Path("/tmp/PX4-Autopilot"),
        Path("/tmp/drone_ws"),
    )

    command_text = "\n".join(command.command for command in commands)

    assert "PX4_GZ_WORLD=food_delivery" in command_text
    assert "micro-xrce-dds-agent udp4 -p 8888" in command_text
    assert "ros2 run drone_mission offboard_takeoff" in command_text


def test_plan_command_does_not_start_processes(capsys):
    result = drone_launcher.main(
        [
            "plan",
            "--mission",
            "simple_delivery",
            "--px4-dir",
            "/tmp/PX4-Autopilot",
            "--workspace-dir",
            "/tmp/drone_ws",
        ]
    )

    output = capsys.readouterr().out

    assert result == 0
    assert "PX4 + Gazebo" in output
    assert "ROS 2 mission node" in output
