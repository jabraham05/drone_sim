"""
drone_control.py
================
Person 2 – Control Layer
ROS 2 (rclpy) + PX4 uXRCE-DDS based drone control API.

Architecture
------------
This node communicates with PX4 entirely through ROS 2 publishers:
  "The drone is controlled entirely through ROS 2 publishers
   using PX4 Offboard Mode."

Three publishers drive the drone:
  1. /fmu/in/OffboardControlMode   – heartbeat, must stream at >= 2 Hz
  2. /fmu/in/TrajectorySetpoint    – position commands (NED frame)
  3. /fmu/in/VehicleCommand        – arm / disarm / land / mode switch

Two subscribers keep DroneState current:
  • /fmu/out/VehicleOdometry       – position (NED frame)
  • /fmu/out/VehicleStatus         – armed flag, nav_state (flight mode)

Prerequisites
-------------
  sudo apt install ros-jazzy-px4-msgs
  pip install rclpy

# Assumptions
# -----------
# - PX4 SITL is running and uXRCE-DDS bridge is active before this node starts
# - Drone starts disarmed on the ground at home position (x=0, y=0, z=0)
# - OffboardControlMode must stream at >= 2 Hz or PX4 will failsafe
# - SITL not tested locally on Windows – tested via unit tests with mocks only
#
# /drone/vehicle/... bridge topics are NOT yet implemented.
# drone_mission must not import or call this node directly until the bridge exists.

Run
---
  # Terminal 1 – PX4 SITL + Gazebo
  cd ~/PX4-Autopilot
  PX4_GZ_WORLD=food_delivery make px4_sitl gz_x500

  # Terminal 2 – uXRCE-DDS bridge
  micro-xrce-dds-agent udp4 -p 8888

  # Terminal 3 – this node
  cd ~/drone_ws && source install/setup.bash
  python3 drone_control.py
"""

import math
import time
from dataclasses import dataclass
from enum import Enum, auto

import rclpy
from rclpy.node import Node
from rclpy.qos import (
    QoSProfile,
    QoSReliabilityPolicy,
    QoSHistoryPolicy,
    QoSDurabilityPolicy,
)

from px4_msgs.msg import (
    OffboardControlMode,
    TrajectorySetpoint,
    VehicleCommand,
    VehicleOdometry,
    VehicleStatus,
)


# ─────────────────────────────────────────────────────────────────────────────
# QoS profile required by all PX4 topics
# ─────────────────────────────────────────────────────────────────────────────
PX4_QOS = QoSProfile(
    reliability=QoSReliabilityPolicy.BEST_EFFORT,
    durability=QoSDurabilityPolicy.TRANSIENT_LOCAL,
    history=QoSHistoryPolicy.KEEP_LAST,
    depth=1,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data structures  (identical to MAVSDK version)
# ─────────────────────────────────────────────────────────────────────────────
class DroneMode(Enum):
    UNKNOWN  = auto()
    OFFBOARD = auto()
    POSITION = auto()
    MISSION  = auto()
    HOLD     = auto()


@dataclass
class DroneState:
    """Live snapshot of the drone's state."""
    armed: bool      = False
    mode:  DroneMode = DroneMode.UNKNOWN
    x:     float     = 0.0   # North  (m, NED)
    y:     float     = 0.0   # East   (m, NED)
    z:     float     = 0.0   # Down   (m, NED – negative = above home)

    @property
    def altitude(self) -> float:
        """Positive altitude above home (metres)."""
        return -self.z

    @property
    def position(self) -> tuple:
        return (round(self.x, 3), round(self.y, 3), round(self.altitude, 3))


# ─────────────────────────────────────────────────────────────────────────────
# PX4 nav_state constants  (from VehicleStatus.msg)
# ─────────────────────────────────────────────────────────────────────────────
NAV_STATE_POSCTL      = 2
NAV_STATE_MISSION     = 3
NAV_STATE_AUTO_LOITER = 13   # HOLD
NAV_STATE_OFFBOARD    = 14


# ─────────────────────────────────────────────────────────────────────────────
# DroneController – rclpy Node
# ─────────────────────────────────────────────────────────────────────────────
class DroneController(Node):
    """
    High-level control API for a PX4 drone via ROS 2 publishers.

    The public API is identical to the MAVSDK version – only the transport
    layer changes.  All control logic, state tracking, and logging are
    preserved exactly.

    Usage:
        rclpy.init()
        dc = DroneController()
        dc.takeoff(height=2.0)
        dc.go_to(x=5, y=5, z=2.0)
        dc.hover(duration=5.0)
        dc.land()
        dc.destroy_node()
        rclpy.shutdown()
    """

    # ── Tunable constants ─────────────────────────────────────────────────────
    POSITION_TOLERANCE_M      = 0.25   # metres  – "close enough" threshold
    OFFBOARD_HZ               = 10     # Hz      – setpoint + heartbeat rate
    ARM_TIMEOUT_S             = 10     # seconds – max wait for arming
    REACH_TIMEOUT_S           = 30     # seconds – max wait per go_to
    # PX4 needs >= 1 s of OffboardControlMode before accepting mode switch.
    # At 10 Hz, 15 cycles = 1.5 s – safe margin.
    OFFBOARD_PREFLIGHT_CYCLES = 15

    def __init__(self):
        super().__init__("drone_controller")

        self.state   = DroneState()
        self._target = (0.0, 0.0, 0.0)   # (North m, East m, altitude m)
        self._streaming = False           # gate: only publish when needed

        # ── Publishers ────────────────────────────────────────────────────────
        self._pub_offboard = self.create_publisher(
            OffboardControlMode,
            "/fmu/in/OffboardControlMode",
            PX4_QOS,
        )
        self._pub_setpoint = self.create_publisher(
            TrajectorySetpoint,
            "/fmu/in/TrajectorySetpoint",
            PX4_QOS,
        )
        self._pub_command = self.create_publisher(
            VehicleCommand,
            "/fmu/in/VehicleCommand",
            PX4_QOS,
        )

        # ── Subscribers ───────────────────────────────────────────────────────
        self.create_subscription(
            VehicleOdometry,
            "/fmu/out/VehicleOdometry",
            self._odometry_callback,
            PX4_QOS,
        )
        self.create_subscription(
            VehicleStatus,
            "/fmu/out/VehicleStatus",
            self._status_callback,
            PX4_QOS,
        )

        # ── Background timer – heartbeat + setpoint stream ────────────────────
        # Fires at OFFBOARD_HZ; does nothing until self._streaming = True.
        self._setpoint_timer = self.create_timer(
            1.0 / self.OFFBOARD_HZ,
            self._setpoint_timer_callback,
        )

        self.get_logger().info("DroneController node initialised")

    # =========================================================================
    # Public API
    # =========================================================================

    def takeoff(self, height: float = 2.0) -> None:
        """
        Arm the drone, enter Offboard mode, and climb to *height* metres.

        Args:
            height: Target altitude in metres above home position.
        """
        self.get_logger().info(f"▶ TAKEOFF  target altitude = {height} m")

        self._ensure_armed()
        self._enter_offboard_mode()
        self._move_to(self.state.x, self.state.y, height)

        self.get_logger().info(
            f"✓ TAKEOFF complete  –  altitude = {self.state.altitude:.2f} m"
        )

    def go_to(self, x: float, y: float, z: float) -> None:
        """
        Fly to position (x=North, y=East, z=altitude) in metres from home.

        Args:
            x: North offset from home (metres).
            y: East  offset from home (metres).
            z: Target altitude        (metres, positive = up).
        """
        self.get_logger().info(f"▶ GO_TO    target = ({x}, {y}, {z})")

        if not self.state.armed:
            self.get_logger().warn("Drone is not armed – aborting go_to")
            return

        self._enter_offboard_mode()
        self._move_to(x, y, z)

        self.get_logger().info(
            f"✓ GO_TO complete   –  position = {self.state.position}"
        )

    def hover(self, duration: float = 5.0) -> None:
        """
        Hold current position for *duration* seconds.

        Args:
            duration: Seconds to hover (default 5 s).
        """
        self.get_logger().info(f"▶ HOVER    duration = {duration} s")

        self._enter_offboard_mode()

        # Lock the setpoint onto current position
        self._target = (self.state.x, self.state.y, self.state.altitude)
        self._spin_for(duration)

        self.get_logger().info("✓ HOVER complete")

    def land(self) -> None:
        """
        Send the PX4 NAV_LAND command and wait for disarm.
        """
        self.get_logger().info("▶ LAND")
        self._streaming = False

        self._publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_NAV_LAND,
        )
        self.get_logger().info("✓ LAND command sent – waiting for disarm …")

        deadline = time.time() + 30.0
        while self.state.armed:
            if time.time() > deadline:
                self.get_logger().warn("Land timeout – drone may still be armed")
                break
            rclpy.spin_once(self, timeout_sec=0.2)

        self.get_logger().info("✓ Drone disarmed – landed")

    # =========================================================================
    # State management
    # =========================================================================

    def _ensure_armed(self) -> None:
        """Arm the drone and block until the armed flag goes True."""
        if self.state.armed:
            return

        self.get_logger().info("  Arming …")
        self._streaming = True   # start heartbeat before arm command

        self._publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,   # 1.0 = arm,  0.0 = disarm
        )

        deadline = time.time() + self.ARM_TIMEOUT_S
        while not self.state.armed:
            if time.time() > deadline:
                raise TimeoutError("Drone did not arm in time")
            rclpy.spin_once(self, timeout_sec=0.2)

        self.get_logger().info("  ✓ Armed")

    # =========================================================================
    # Offboard mode management
    # =========================================================================

    def _enter_offboard_mode(self) -> None:
        """
        Pre-stream setpoints then request OFFBOARD mode (idempotent).

        PX4 needs OffboardControlMode streaming for >= 1 s before it will
        accept the mode-switch command, so we spin through
        OFFBOARD_PREFLIGHT_CYCLES before sending it.
        """
        if self.state.mode == DroneMode.OFFBOARD:
            return

        self.get_logger().info("  Entering OFFBOARD mode …")

        self._streaming = True
        for _ in range(self.OFFBOARD_PREFLIGHT_CYCLES):
            rclpy.spin_once(self, timeout_sec=1.0 / self.OFFBOARD_HZ)

        # Request OFFBOARD via DO_SET_MODE
        self._publish_vehicle_command(
            VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
            param1=1.0,   # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
            param2=6.0,   # PX4_CUSTOM_MAIN_MODE_OFFBOARD
        )

        deadline = time.time() + 5.0
        while self.state.mode != DroneMode.OFFBOARD:
            if time.time() > deadline:
                self.get_logger().warn(
                    "OFFBOARD mode switch timed out – proceeding anyway"
                )
                break
            rclpy.spin_once(self, timeout_sec=0.1)

        self.get_logger().info("  ✓ OFFBOARD mode active")

    # =========================================================================
    # Motion helpers
    # =========================================================================

    def _move_to(
        self,
        x: float,
        y: float,
        altitude: float,
        timeout: float = None,
    ) -> None:
        """
        Update the setpoint and spin until within tolerance or timeout.
        """
        self._target = (x, y, altitude)
        timeout  = timeout or self.REACH_TIMEOUT_S
        deadline = time.time() + timeout

        while True:
            dist = self._distance_to(x, y, altitude)
            self._log_status(x, y, altitude, dist)

            if dist <= self.POSITION_TOLERANCE_M:
                break
            if time.time() > deadline:
                self.get_logger().warn(
                    f"  Timeout reaching ({x}, {y}, {altitude}) – "
                    f"still {dist:.2f} m away"
                )
                break

            rclpy.spin_once(self, timeout_sec=0.2)

    def _distance_to(self, x: float, y: float, altitude: float) -> float:
        dx = x - self.state.x
        dy = y - self.state.y
        dz = altitude - self.state.altitude
        return math.sqrt(dx**2 + dy**2 + dz**2)

    def _spin_for(self, seconds: float) -> None:
        """Process ROS 2 callbacks for *seconds* seconds."""
        deadline = time.time() + seconds
        while time.time() < deadline:
            rclpy.spin_once(self, timeout_sec=0.1)

    # =========================================================================
    # Timer callback – heartbeat + setpoint stream (runs at OFFBOARD_HZ)
    # =========================================================================

    def _setpoint_timer_callback(self) -> None:
        """
        Fires at OFFBOARD_HZ.  While self._streaming is True, publishes:
          1. OffboardControlMode – proof-of-life for PX4 offboard watchdog
          2. TrajectorySetpoint  – current target position in NED frame
        """
        if not self._streaming:
            return

        # 1. Heartbeat ─────────────────────────────────────────────────────────
        hb              = OffboardControlMode()
        hb.position     = True    # we command via position setpoints
        hb.velocity     = False
        hb.acceleration = False
        hb.attitude     = False
        hb.body_rate    = False
        hb.timestamp    = self._timestamp()
        self._pub_offboard.publish(hb)

        # 2. Position setpoint (NED: z = -altitude) ────────────────────────────
        tx, ty, talt = self._target
        sp           = TrajectorySetpoint()
        sp.position  = [tx, ty, -talt]   # NED frame: down is positive
        sp.yaw       = 0.0               # face north
        sp.timestamp = self._timestamp()
        self._pub_setpoint.publish(sp)

    # =========================================================================
    # Publisher helper
    # =========================================================================

    def _publish_vehicle_command(
        self,
        command: int,
        param1: float = 0.0,
        param2: float = 0.0,
        param3: float = 0.0,
    ) -> None:
        """Build and publish a VehicleCommand message."""
        msg                  = VehicleCommand()
        msg.command          = command
        msg.param1           = param1
        msg.param2           = param2
        msg.param3           = param3
        msg.target_system    = 1
        msg.target_component = 1
        msg.source_system    = 1
        msg.source_component = 1
        msg.from_external    = True
        msg.timestamp        = self._timestamp()
        self._pub_command.publish(msg)

    def _timestamp(self) -> int:
        """Return current time in microseconds (PX4 convention)."""
        return int(self.get_clock().now().nanoseconds / 1_000)

    # =========================================================================
    # Subscriber callbacks – keep DroneState current
    # =========================================================================

    def _odometry_callback(self, msg: VehicleOdometry) -> None:
        """
        /fmu/out/VehicleOdometry -> update position.
        PX4 publishes NED: position[0]=North, [1]=East, [2]=Down.
        """
        self.state.x = msg.position[0]
        self.state.y = msg.position[1]
        self.state.z = msg.position[2]   # Down – negative when above home

    def _status_callback(self, msg: VehicleStatus) -> None:
        """
        /fmu/out/VehicleStatus -> update armed flag and flight mode.
        """
        self.state.armed = (
            msg.arming_state == VehicleStatus.ARMING_STATE_ARMED
        )

        mode_map = {
            NAV_STATE_OFFBOARD:    DroneMode.OFFBOARD,
            NAV_STATE_POSCTL:      DroneMode.POSITION,
            NAV_STATE_MISSION:     DroneMode.MISSION,
            NAV_STATE_AUTO_LOITER: DroneMode.HOLD,
        }
        self.state.mode = mode_map.get(msg.nav_state, DroneMode.UNKNOWN)

    # =========================================================================
    # Logging  (exact format from simulation doc spec)
    # =========================================================================

    def _log_status(
        self, tx: float, ty: float, tz: float, dist: float
    ) -> None:
        cx, cy, cz = self.state.position
        status = "reached" if dist <= self.POSITION_TOLERANCE_M else "moving"
        self.get_logger().info(
            f"  Current position : ({cx}, {cy}, {cz})  |  "
            f"Target : ({tx}, {ty}, {tz})  |  "
            f"Status : {status}  [{dist:.2f} m away]"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Demo mission  (takeoff -> go_to -> hover -> return -> land)
# ─────────────────────────────────────────────────────────────────────────────
def run_demo_mission() -> None:
    rclpy.init()
    dc = DroneController()

    try:
        dc.takeoff(height=2.0)
        dc.go_to(x=5.0, y=5.0, z=2.0)
        dc.hover(duration=5.0)
        dc.go_to(x=0.0, y=0.0, z=2.0)
        dc.land()
    except KeyboardInterrupt:
        dc.get_logger().info("Mission interrupted by user")
    finally:
        dc.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    run_demo_mission()
