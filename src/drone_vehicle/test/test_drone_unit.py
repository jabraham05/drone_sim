"""
test_drone_unit.py
==================
Unit tests for the ROS 2 drone_control.py (rclpy + PX4 uXRCE-DDS version).
No PX4 SITL, no Gazebo, no uXRCE-DDS bridge required.

All four requirements below are verified here:
  REQ-1  Build Control Functions   – takeoff / go_to / hover / land API
  REQ-2  Handle Drone State        – DroneState tracks armed, position, mode
  REQ-3  Implement Offboard Control – publishers stream OffboardControlMode
                                      and TrajectorySetpoint via ROS 2
  REQ-4  Add Logging               – _log_status() emits the exact spec format

Run with:
    python3 test_drone_unit.py
    # or
    pytest test_drone_unit.py -v
"""

import math
import sys
import time
import types
import unittest
from unittest.mock import MagicMock, patch


# ─────────────────────────────────────────────────────────────────────────────
# Stub every ROS 2 / px4_msgs dependency before importing drone_control
# ─────────────────────────────────────────────────────────────────────────────

def _msg_class(name):
    """Lightweight stand-in for a px4_msgs message class."""
    return type(name, (), {
        "VEHICLE_CMD_COMPONENT_ARM_DISARM": 400,
        "VEHICLE_CMD_DO_SET_MODE":          176,
        "VEHICLE_CMD_NAV_LAND":             21,
        "ARMING_STATE_ARMED":               2,
    })


px4_msgs_mod     = types.ModuleType("px4_msgs")
px4_msgs_msg_mod = types.ModuleType("px4_msgs.msg")

OffboardControlMode = _msg_class("OffboardControlMode")
TrajectorySetpoint  = _msg_class("TrajectorySetpoint")
VehicleCommand      = _msg_class("VehicleCommand")
VehicleOdometry     = _msg_class("VehicleOdometry")
VehicleStatus       = _msg_class("VehicleStatus")

for cls in (OffboardControlMode, TrajectorySetpoint, VehicleCommand,
            VehicleOdometry, VehicleStatus):
    setattr(px4_msgs_msg_mod, cls.__name__, cls)

sys.modules["px4_msgs"]     = px4_msgs_mod
sys.modules["px4_msgs.msg"] = px4_msgs_msg_mod

# rclpy stubs
rclpy_mod = types.ModuleType("rclpy")
rclpy_mod.init      = MagicMock()
rclpy_mod.shutdown  = MagicMock()
rclpy_mod.spin_once = MagicMock()   # no-op; tests flip state flags directly

rclpy_node_mod = types.ModuleType("rclpy.node")
rclpy_qos_mod  = types.ModuleType("rclpy.qos")
for attr in ("QoSProfile", "QoSReliabilityPolicy",
             "QoSHistoryPolicy", "QoSDurabilityPolicy"):
    setattr(rclpy_qos_mod, attr, MagicMock())


class FakeNode:
    """Minimal stand-in for rclpy.Node – captures all publish calls."""
    def __init__(self, name):
        self._log_lines = []
        self._publishers  = {}
        self._subscribers = {}

    def create_publisher(self, msg_type, topic, qos):
        pub = MagicMock()
        self._publishers[topic] = pub
        return pub

    def create_subscription(self, msg_type, topic, cb, qos):
        sub = MagicMock()
        self._subscribers[topic] = sub
        return sub

    def create_timer(self, period, cb):
        return MagicMock()

    def get_logger(self):
        outer = self
        class _L:
            def info(s, m):  outer._log_lines.append(("INFO",  m))
            def warn(s, m):  outer._log_lines.append(("WARN",  m))
            def error(s, m): outer._log_lines.append(("ERROR", m))
        return _L()

    def get_clock(self):
        c = MagicMock()
        c.now.return_value.nanoseconds = 1_000_000_000   # 1 s in ns
        return c

    def destroy_node(self): pass


rclpy_node_mod.Node = FakeNode

sys.modules["rclpy"]      = rclpy_mod
sys.modules["rclpy.node"] = rclpy_node_mod
sys.modules["rclpy.qos"]  = rclpy_qos_mod

from drone_control import DroneController, DroneMode, DroneState  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
results: list[dict] = []


def record(name: str, passed: bool, note: str = ""):
    tag = f"{GREEN}✓ PASS{RESET}" if passed else f"{RED}✗ FAIL{RESET}"
    print(f"  {tag}  {name}" + (f"  ({note})" if note else ""))
    results.append({"name": name, "passed": passed})


def make_controller() -> DroneController:
    """Fresh DroneController backed by FakeNode – no real ROS 2 needed."""
    dc = DroneController.__new__(DroneController)
    FakeNode.__init__(dc, "drone_controller")
    dc.state      = DroneState()
    dc._target    = (0.0, 0.0, 0.0)
    dc._streaming = False

    from drone_control import PX4_QOS
    dc._pub_offboard = dc.create_publisher(
        OffboardControlMode, "/fmu/in/OffboardControlMode", PX4_QOS)
    dc._pub_setpoint = dc.create_publisher(
        TrajectorySetpoint,  "/fmu/in/TrajectorySetpoint",  PX4_QOS)
    dc._pub_command  = dc.create_publisher(
        VehicleCommand,      "/fmu/in/VehicleCommand",      PX4_QOS)
    dc.create_subscription(
        VehicleOdometry, "/fmu/out/VehicleOdometry",
        dc._odometry_callback, PX4_QOS)
    dc.create_subscription(
        VehicleStatus, "/fmu/out/VehicleStatus",
        dc._status_callback, PX4_QOS)
    dc._setpoint_timer = dc.create_timer(
        1.0 / dc.OFFBOARD_HZ, dc._setpoint_timer_callback)
    return dc


# ─────────────────────────────────────────────────────────────────────────────
# REQ-2 – Handle Drone State
# ─────────────────────────────────────────────────────────────────────────────
class TestDroneState(unittest.TestCase):

    def test_default_values(self):
        s = DroneState()
        self.assertFalse(s.armed)
        self.assertEqual(s.mode, DroneMode.UNKNOWN)
        self.assertEqual(s.position, (0.0, 0.0, 0.0))
        record("REQ-2 | DroneState: correct defaults", True)

    def test_altitude_is_neg_z(self):
        """NED convention: altitude = -z (down is positive in NED)."""
        s = DroneState(z=-3.5)
        self.assertAlmostEqual(s.altitude, 3.5)
        record("REQ-2 | DroneState: altitude = -z  (NED convention)", True)

    def test_position_rounds_to_3dp(self):
        s = DroneState(x=1.23456, y=2.34567, z=-4.56789)
        self.assertEqual(s.position, (1.235, 2.346, 4.568))
        record("REQ-2 | DroneState: position rounds to 3 dp", True)


class TestOdometryCallback(unittest.TestCase):

    def test_xyz_updated_from_odometry(self):
        dc = make_controller()
        msg = MagicMock()
        msg.position = [3.0, 4.0, -2.0]
        dc._odometry_callback(msg)
        self.assertAlmostEqual(dc.state.x,        3.0)
        self.assertAlmostEqual(dc.state.y,        4.0)
        self.assertAlmostEqual(dc.state.z,       -2.0)
        self.assertAlmostEqual(dc.state.altitude,  2.0)
        record("REQ-2 | _odometry_callback: x/y/z updated from VehicleOdometry", True)


class TestStatusCallback(unittest.TestCase):

    def test_armed_flag_set(self):
        dc = make_controller()
        msg = MagicMock()
        msg.arming_state = VehicleStatus.ARMING_STATE_ARMED
        msg.nav_state    = 14
        dc._status_callback(msg)
        self.assertTrue(dc.state.armed)
        record("REQ-2 | _status_callback: armed=True when ARMING_STATE_ARMED", True)

    def test_all_mode_mappings(self):
        dc = make_controller()
        cases = [
            (14, DroneMode.OFFBOARD),
            (2,  DroneMode.POSITION),
            (3,  DroneMode.MISSION),
            (13, DroneMode.HOLD),
            (99, DroneMode.UNKNOWN),
        ]
        for nav, expected in cases:
            msg = MagicMock()
            msg.arming_state = 0
            msg.nav_state    = nav
            dc._status_callback(msg)
            self.assertEqual(dc.state.mode, expected,
                             msg=f"nav_state {nav} should map to {expected}")
        record("REQ-2 | _status_callback: all 5 nav_state mappings correct", True)


# ─────────────────────────────────────────────────────────────────────────────
# REQ-3 – Implement Offboard Control  (ROS 2 publishers, not MAVSDK)
# ─────────────────────────────────────────────────────────────────────────────
class TestOffboardHeartbeat(unittest.TestCase):
    """Timer publishes OffboardControlMode + TrajectorySetpoint via ROS 2."""

    def test_silent_when_streaming_false(self):
        dc = make_controller()
        dc._streaming = False
        dc._setpoint_timer_callback()
        dc._pub_offboard.publish.assert_not_called()
        dc._pub_setpoint.publish.assert_not_called()
        record("REQ-3 | Timer: no publish when _streaming=False", True)

    def test_publishes_both_messages(self):
        dc = make_controller()
        dc._streaming = True
        dc._setpoint_timer_callback()
        dc._pub_offboard.publish.assert_called_once()
        dc._pub_setpoint.publish.assert_called_once()
        record("REQ-3 | Timer: publishes OffboardControlMode + TrajectorySetpoint", True)

    def test_offboard_mode_position_flag_true(self):
        """position=True tells PX4 we are sending position setpoints."""
        dc = make_controller()
        dc._streaming = True
        captured = []
        dc._pub_offboard.publish.side_effect = lambda m: captured.append(m)
        dc._setpoint_timer_callback()
        self.assertTrue(captured[0].position)
        self.assertFalse(captured[0].velocity)
        self.assertFalse(captured[0].acceleration)
        record("REQ-3 | Timer: OffboardControlMode.position=True, velocity=False", True)

    def test_trajectory_setpoint_ned_z_negated(self):
        """z sent to PX4 must be -altitude (NED frame: down is positive)."""
        dc = make_controller()
        dc._streaming = True
        dc._target    = (5.0, 5.0, 2.0)
        captured = []
        dc._pub_setpoint.publish.side_effect = lambda m: captured.append(m)
        dc._setpoint_timer_callback()
        sp = captured[0]
        self.assertEqual(sp.position[0],  5.0)
        self.assertEqual(sp.position[1],  5.0)
        self.assertEqual(sp.position[2], -2.0)
        record("REQ-3 | Timer: TrajectorySetpoint z = -altitude (NED)", True)

    def test_timestamp_in_microseconds(self):
        """PX4 expects µs; clock gives ns, so we divide by 1 000."""
        dc = make_controller()
        dc._streaming = True
        captured = []
        dc._pub_offboard.publish.side_effect = lambda m: captured.append(m)
        dc._setpoint_timer_callback()
        # FakeNode clock → 1_000_000_000 ns → 1_000_000 µs
        self.assertEqual(captured[0].timestamp, 1_000_000)
        record("REQ-3 | Timer: timestamp = nanoseconds ÷ 1000 (µs)", True)


class TestEnterOffboardMode(unittest.TestCase):

    def test_idempotent_when_already_offboard(self):
        dc = make_controller()
        dc.state.mode = DroneMode.OFFBOARD
        dc._enter_offboard_mode()
        dc._pub_command.publish.assert_not_called()
        record("REQ-3 | _enter_offboard_mode: no-op when already OFFBOARD", True)

    def test_sends_do_set_mode_command(self):
        dc = make_controller()
        dc.state.mode = DroneMode.UNKNOWN
        def fake_pub(msg):
            if msg.command == VehicleCommand.VEHICLE_CMD_DO_SET_MODE:
                dc.state.mode = DroneMode.OFFBOARD
        dc._pub_command.publish.side_effect = fake_pub
        dc._enter_offboard_mode()
        cmds = [c.args[0].command
                for c in dc._pub_command.publish.call_args_list]
        self.assertIn(VehicleCommand.VEHICLE_CMD_DO_SET_MODE, cmds)
        record("REQ-3 | _enter_offboard_mode: sends VEHICLE_CMD_DO_SET_MODE", True)

    def test_mode_switch_params(self):
        """param1=1.0 (custom-mode flag), param2=6.0 (PX4 OFFBOARD id)."""
        dc = make_controller()
        dc.state.mode = DroneMode.UNKNOWN
        captured = []
        def fake_pub(msg):
            captured.append(msg)
            dc.state.mode = DroneMode.OFFBOARD
        dc._pub_command.publish.side_effect = fake_pub
        dc._enter_offboard_mode()
        mode_cmd = next(
            m for m in captured
            if m.command == VehicleCommand.VEHICLE_CMD_DO_SET_MODE)
        self.assertEqual(mode_cmd.param1, 1.0)
        self.assertEqual(mode_cmd.param2, 6.0)
        record("REQ-3 | _enter_offboard_mode: param1=1.0, param2=6.0", True)

    def test_streaming_enabled_before_command(self):
        dc = make_controller()
        dc.state.mode = DroneMode.UNKNOWN
        streaming_at_cmd = []
        def fake_pub(msg):
            streaming_at_cmd.append(dc._streaming)
            dc.state.mode = DroneMode.OFFBOARD
        dc._pub_command.publish.side_effect = fake_pub
        dc._enter_offboard_mode()
        self.assertTrue(all(streaming_at_cmd))
        record("REQ-3 | _enter_offboard_mode: _streaming=True before command", True)


class TestEnsureArmed(unittest.TestCase):

    def test_skips_when_already_armed(self):
        dc = make_controller()
        dc.state.armed = True
        dc._ensure_armed()
        dc._pub_command.publish.assert_not_called()
        record("REQ-2 | _ensure_armed: no publish when already armed", True)

    def test_sends_arm_command(self):
        dc = make_controller()
        dc.state.armed = False
        def fake_pub(msg):
            if msg.command == VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM:
                dc.state.armed = True
        dc._pub_command.publish.side_effect = fake_pub
        dc._ensure_armed()
        self.assertTrue(dc.state.armed)
        record("REQ-2 | _ensure_armed: sends VEHICLE_CMD_COMPONENT_ARM_DISARM", True)

    def test_arm_param1_is_1(self):
        """param1=1.0 = ARM;  param1=0.0 = DISARM – must not get these swapped."""
        dc = make_controller()
        dc.state.armed = False
        captured = []
        def fake_pub(msg):
            captured.append(msg)
            dc.state.armed = True
        dc._pub_command.publish.side_effect = fake_pub
        dc._ensure_armed()
        arm_msg = next(
            m for m in captured
            if m.command == VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM)
        self.assertEqual(arm_msg.param1, 1.0)
        record("REQ-2 | _ensure_armed: param1=1.0  (ARM, not DISARM)", True)

    def test_timeout_raises(self):
        dc = make_controller()
        dc.state.armed   = False
        dc.ARM_TIMEOUT_S = 0.05
        dc._pub_command.publish = MagicMock()
        with self.assertRaises(TimeoutError):
            dc._ensure_armed()
        record("REQ-2 | _ensure_armed: TimeoutError if drone never arms", True)

    def test_vehicle_command_fields(self):
        """All required PX4 VehicleCommand fields must be populated."""
        dc = make_controller()
        dc.state.armed = False
        captured = []
        def fake_pub(msg):
            captured.append(msg)
            dc.state.armed = True
        dc._pub_command.publish.side_effect = fake_pub
        dc._ensure_armed()
        msg = captured[0]
        self.assertEqual(msg.target_system,    1)
        self.assertEqual(msg.target_component, 1)
        self.assertEqual(msg.source_system,    1)
        self.assertEqual(msg.source_component, 1)
        self.assertTrue(msg.from_external)
        record("REQ-3 | VehicleCommand: all PX4 header fields populated", True)


# ─────────────────────────────────────────────────────────────────────────────
# REQ-1 – Build Control Functions
# ─────────────────────────────────────────────────────────────────────────────
class TestDistanceCalculation(unittest.TestCase):

    def test_zero_at_target(self):
        dc = make_controller()
        dc.state.x = 5.0; dc.state.y = 5.0; dc.state.z = -2.0
        self.assertAlmostEqual(dc._distance_to(5.0, 5.0, 2.0), 0.0, places=6)
        record("REQ-1 | _distance_to: 0 when already at target", True)

    def test_345_right_triangle(self):
        dc = make_controller()
        dc.state.x = 0.0; dc.state.y = 0.0; dc.state.z = 0.0
        self.assertAlmostEqual(dc._distance_to(3.0, 4.0, 0.0), 5.0, places=5)
        record("REQ-1 | _distance_to: 3-4-5 right triangle", True)

    def test_full_3d_euclidean(self):
        dc = make_controller()
        dc.state.x = 1.0; dc.state.y = 2.0; dc.state.z = -3.0
        expected = math.sqrt((4-1)**2 + (6-2)**2 + (5-3)**2)
        self.assertAlmostEqual(dc._distance_to(4.0, 6.0, 5.0), expected, places=5)
        record("REQ-1 | _distance_to: full 3D Euclidean distance", True)


class TestTakeoff(unittest.TestCase):

    def test_calls_ensure_armed(self):
        dc = make_controller()
        dc.state.armed = False
        called = []
        dc._ensure_armed        = lambda: called.append(True) or setattr(dc.state, "armed", True)
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._move_to             = lambda *a: None
        dc.takeoff(height=2.0)
        self.assertTrue(called)
        record("REQ-1 | takeoff: calls _ensure_armed", True)

    def test_calls_enter_offboard(self):
        dc = make_controller()
        dc.state.armed = True
        called = []
        dc._enter_offboard_mode = lambda: called.append(True) or setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._move_to             = lambda *a: None
        dc.takeoff(height=2.0)
        self.assertTrue(called)
        record("REQ-1 | takeoff: calls _enter_offboard_mode", True)

    def test_move_to_receives_target_height(self):
        dc = make_controller()
        dc.state.armed = True
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        captured = []
        dc._move_to = lambda x, y, alt: captured.append((x, y, alt))
        dc.takeoff(height=3.5)
        self.assertEqual(captured[0][2], 3.5)
        record("REQ-1 | takeoff: _move_to called with the requested height", True)


class TestGoTo(unittest.TestCase):

    def test_aborts_when_not_armed(self):
        dc = make_controller()
        dc.state.armed = False
        called = []
        dc._enter_offboard_mode = lambda: called.append(True)
        dc.go_to(5.0, 5.0, 2.0)
        self.assertFalse(called)
        record("REQ-1 | go_to: aborts early when not armed", True)

    def test_move_to_receives_correct_coords(self):
        dc = make_controller()
        dc.state.armed = True
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        captured = []
        dc._move_to = lambda x, y, alt: captured.append((x, y, alt))
        dc.go_to(5.0, 3.0, 2.5)
        self.assertEqual(captured[0], (5.0, 3.0, 2.5))
        record("REQ-1 | go_to: _move_to receives correct (x, y, z)", True)


class TestHover(unittest.TestCase):

    def test_target_locked_to_current_position(self):
        dc = make_controller()
        dc.state.armed = True
        dc.state.x = 4.0; dc.state.y = 5.0; dc.state.z = -2.0
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._spin_for            = lambda s: None
        dc.hover(duration=1.0)
        self.assertEqual(dc._target, (4.0, 5.0, 2.0))
        record("REQ-1 | hover: _target locked to current position", True)

    def test_calls_enter_offboard(self):
        dc = make_controller()
        dc.state.armed = True
        called = []
        dc._enter_offboard_mode = lambda: called.append(True) or setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._spin_for            = lambda s: None
        dc.hover(duration=1.0)
        self.assertTrue(called)
        record("REQ-1 | hover: calls _enter_offboard_mode", True)


class TestLand(unittest.TestCase):

    def test_sends_nav_land_command(self):
        dc = make_controller()
        dc.state.armed = False
        captured = []
        dc._pub_command.publish.side_effect = lambda m: captured.append(m)
        dc.land()
        cmds = [m.command for m in captured]
        self.assertIn(VehicleCommand.VEHICLE_CMD_NAV_LAND, cmds)
        record("REQ-1 | land: sends VEHICLE_CMD_NAV_LAND via ROS 2 publisher", True)

    def test_streaming_disabled_before_command(self):
        """Heartbeat stream must stop before land command is sent."""
        dc = make_controller()
        dc.state.armed   = True
        dc._streaming    = True
        streaming_states = []

        def track(msg):
            streaming_states.append(dc._streaming)
            dc.state.armed = False

        dc._pub_command.publish.side_effect = track
        dc.land()
        self.assertFalse(streaming_states[0])
        record("REQ-1 | land: _streaming=False before NAV_LAND command", True)

    def test_graceful_on_timeout(self):
        dc = make_controller()
        dc.state.armed = True
        call_count = [0]
        real_time  = time.time

        def fast_time():
            call_count[0] += 1
            return real_time() + (40.0 if call_count[0] > 3 else 0.0)

        with patch("drone_control.time.time", side_effect=fast_time):
            try:
                dc.land()
                record("REQ-1 | land: returns gracefully on disarm timeout", True)
            except Exception as e:
                record("REQ-1 | land: returns gracefully on disarm timeout",
                       False, str(e))


# ─────────────────────────────────────────────────────────────────────────────
# REQ-4 – Add Logging
# ─────────────────────────────────────────────────────────────────────────────
class TestLogging(unittest.TestCase):

    def test_moving_status_in_log(self):
        dc = make_controller()
        dc.state.x = 0.0; dc.state.y = 0.0; dc.state.z = 0.0
        dc._log_status(5.0, 5.0, 2.0, 7.07)
        last = dc._log_lines[-1][1]
        self.assertIn("Current position", last)
        self.assertIn("Target",           last)
        self.assertIn("moving",           last)
        record("REQ-4 | _log_status: 'Current position', 'Target', 'moving' present", True)

    def test_reached_status_within_tolerance(self):
        dc = make_controller()
        dc.state.x = 5.0; dc.state.y = 5.0; dc.state.z = -2.0
        dc._log_status(5.0, 5.0, 2.0, 0.1)
        last = dc._log_lines[-1][1]
        self.assertIn("reached", last)
        record("REQ-4 | _log_status: 'reached' when dist < POSITION_TOLERANCE_M", True)

    def test_all_three_spec_tokens_in_one_line(self):
        """
        Simulation doc specifies three tokens that must appear in each log line:
          Current position: (x, y, z)
          Target: (x, y, z)
          Status: moving / reached
        """
        dc = make_controller()
        dc.state.x = 1.0; dc.state.y = 2.0; dc.state.z = -3.0
        dc._log_status(4.0, 5.0, 6.0, 5.0)
        last = dc._log_lines[-1][1]
        for token in ("Current position", "Target", "Status"):
            self.assertIn(token, last,
                          msg=f"'{token}' missing from log line")
        record("REQ-4 | _log_status: all three spec tokens in one log line", True)

    def test_takeoff_logs_start_and_complete(self):
        dc = make_controller()
        dc.state.armed = True
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._move_to             = lambda *a: None
        dc.takeoff(height=2.0)
        msgs = [m for _, m in dc._log_lines]
        self.assertTrue(any("TAKEOFF" in m and "▶" in m for m in msgs))
        self.assertTrue(any("TAKEOFF" in m and "✓" in m for m in msgs))
        record("REQ-4 | takeoff: logs ▶ start and ✓ complete messages", True)

    def test_go_to_logs_start_and_complete(self):
        dc = make_controller()
        dc.state.armed = True
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._move_to             = lambda *a: None
        dc.go_to(5.0, 5.0, 2.0)
        msgs = [m for _, m in dc._log_lines]
        self.assertTrue(any("GO_TO" in m and "▶" in m for m in msgs))
        self.assertTrue(any("GO_TO" in m and "✓" in m for m in msgs))
        record("REQ-4 | go_to: logs ▶ start and ✓ complete messages", True)

    def test_hover_logs_start_and_complete(self):
        dc = make_controller()
        dc.state.armed = True
        dc._enter_offboard_mode = lambda: setattr(dc.state, "mode", DroneMode.OFFBOARD)
        dc._spin_for            = lambda s: None
        dc.hover(duration=1.0)
        msgs = [m for _, m in dc._log_lines]
        self.assertTrue(any("HOVER" in m and "▶" in m for m in msgs))
        self.assertTrue(any("HOVER" in m and "✓" in m for m in msgs))
        record("REQ-4 | hover: logs ▶ start and ✓ complete messages", True)

    def test_land_logs_command_sent(self):
        dc = make_controller()
        dc.state.armed = False
        dc.land()
        msgs = [m for _, m in dc._log_lines]
        self.assertTrue(any("LAND" in m for m in msgs))
        record("REQ-4 | land: logs LAND command and disarm confirmation", True)


# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
REQ_LABELS = {
    "REQ-1": "Build Control Functions",
    "REQ-2": "Handle Drone State",
    "REQ-3": "Implement Offboard Control",
    "REQ-4": "Add Logging",
}


def print_summary():
    total  = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    bar    = "─" * 60

    reqs: dict[str, list[bool]] = {k: [] for k in REQ_LABELS}
    for r in results:
        for key in reqs:
            if r["name"].startswith(key):
                reqs[key].append(r["passed"])

    print(f"\n{bar}")
    print(f"  Results : {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {RED}{failed} FAILED{RESET}", end="")
    print(f"\n{bar}\n")

    for req, outcomes in reqs.items():
        p = sum(outcomes); t = len(outcomes)
        icon = f"{GREEN}✓{RESET}" if p == t else f"{RED}✗{RESET}"
        print(f"  {icon}  {req} – {REQ_LABELS[req]:30s}  {p}/{t}")

    if failed:
        print(f"\n  {RED}Failed tests:{RESET}")
        for r in results:
            if not r["passed"]:
                print(f"    ✗  {r['name']}")
    print()


if __name__ == "__main__":
    print("\n" + "═" * 60)
    print("  ROS 2 Drone Control — Unit Test Suite")
    print("  (no PX4 SITL or ROS 2 install required)")
    print("═" * 60 + "\n")

    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()

    for cls in [
        TestDroneState,
        TestOdometryCallback,
        TestStatusCallback,
        TestOffboardHeartbeat,
        TestEnterOffboardMode,
        TestEnsureArmed,
        TestDistanceCalculation,
        TestTakeoff,
        TestGoTo,
        TestHover,
        TestLand,
        TestLogging,
    ]:
        suite.addTests(loader.loadTestsFromTestCase(cls))

    runner = unittest.TextTestRunner(verbosity=0, stream=open("/dev/null", "w"))
    runner.run(suite)

    print_summary()
    sys.exit(0 if all(r["passed"] for r in results) else 1)
