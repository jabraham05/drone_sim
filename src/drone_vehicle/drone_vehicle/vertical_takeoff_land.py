"""Minimal PX4 Offboard mission: take off, hold, then land."""

from __future__ import annotations

from dataclasses import dataclass


PHASE_PRE_STREAM = "PRE_STREAM"
PHASE_TAKEOFF = "TAKEOFF"
PHASE_HOLD = "HOLD"
PHASE_LAND = "LAND"
PHASE_DONE = "DONE"


@dataclass(frozen=True)
class VerticalMissionConfig:
    altitude_m: float = 5.0
    takeoff_duration_s: float = 8.0
    hold_duration_s: float = 10.0
    landing_command_duration_s: float = 2.0
    timer_period_s: float = 0.1
    pre_stream_setpoint_count: int = 10


class VerticalMissionTimeline:
    """Time-based state helper for the first PX4 smoke-test mission."""

    def __init__(self, config: VerticalMissionConfig) -> None:
        self.config = config

    def phase_for_tick(self, tick_count: int) -> str:
        if tick_count < self.config.pre_stream_setpoint_count:
            return PHASE_PRE_STREAM

        elapsed = self._elapsed_after_pre_stream(tick_count)

        if elapsed < self.config.takeoff_duration_s:
            return PHASE_TAKEOFF

        if elapsed < self.config.takeoff_duration_s + self.config.hold_duration_s:
            return PHASE_HOLD

        if elapsed < (
            self.config.takeoff_duration_s
            + self.config.hold_duration_s
            + self.config.landing_command_duration_s
        ):
            return PHASE_LAND

        return PHASE_DONE

    def should_enter_offboard_and_arm(self, tick_count: int) -> bool:
        return tick_count == self.config.pre_stream_setpoint_count

    def should_send_land_command(self, tick_count: int) -> bool:
        return self.phase_for_tick(tick_count) == PHASE_LAND and self.phase_for_tick(tick_count - 1) != PHASE_LAND

    def setpoint_z_for_phase(self, phase: str) -> float:
        if phase in (PHASE_PRE_STREAM, PHASE_TAKEOFF, PHASE_HOLD):
            return -abs(self.config.altitude_m)
        return 0.0

    def _elapsed_after_pre_stream(self, tick_count: int) -> float:
        return (tick_count - self.config.pre_stream_setpoint_count) * self.config.timer_period_s


def _create_node_class():
    import rclpy
    from rclpy.node import Node

    from drone_common import topics
    from px4_msgs.msg import OffboardControlMode, TrajectorySetpoint, VehicleCommand

    class VerticalTakeoffLandNode(Node):
        def __init__(self) -> None:
            super().__init__("vertical_takeoff_land")

            self.declare_parameter("altitude_m", 5.0)
            self.declare_parameter("takeoff_duration_s", 8.0)
            self.declare_parameter("hold_duration_s", 10.0)
            self.declare_parameter("landing_command_duration_s", 2.0)
            self.declare_parameter("timer_period_s", 0.1)
            self.declare_parameter("pre_stream_setpoint_count", 10)

            self.config = VerticalMissionConfig(
                altitude_m=float(self.get_parameter("altitude_m").value),
                takeoff_duration_s=float(self.get_parameter("takeoff_duration_s").value),
                hold_duration_s=float(self.get_parameter("hold_duration_s").value),
                landing_command_duration_s=float(self.get_parameter("landing_command_duration_s").value),
                timer_period_s=float(self.get_parameter("timer_period_s").value),
                pre_stream_setpoint_count=int(self.get_parameter("pre_stream_setpoint_count").value),
            )
            self.timeline = VerticalMissionTimeline(self.config)
            self.tick_count = 0

            self.offboard_control_mode_pub = self.create_publisher(
                OffboardControlMode,
                topics.PX4_OFFBOARD_CONTROL_MODE,
                10,
            )
            self.trajectory_setpoint_pub = self.create_publisher(
                TrajectorySetpoint,
                topics.PX4_TRAJECTORY_SETPOINT,
                10,
            )
            self.vehicle_command_pub = self.create_publisher(
                VehicleCommand,
                topics.PX4_VEHICLE_COMMAND,
                10,
            )
            self.timer = self.create_timer(self.config.timer_period_s, self._on_timer)
            self.get_logger().info("Vertical takeoff-hold-land mission started.")

        def _on_timer(self) -> None:
            phase = self.timeline.phase_for_tick(self.tick_count)

            if phase == PHASE_DONE:
                self.get_logger().info("Vertical mission complete.")
                self.timer.cancel()
                return

            self._publish_offboard_control_mode()
            self._publish_position_setpoint(self.timeline.setpoint_z_for_phase(phase))

            if self.timeline.should_enter_offboard_and_arm(self.tick_count):
                self._publish_vehicle_command(
                    VehicleCommand.VEHICLE_CMD_DO_SET_MODE,
                    param1=1.0,
                    param2=6.0,
                )
                self._publish_vehicle_command(VehicleCommand.VEHICLE_CMD_COMPONENT_ARM_DISARM, param1=1.0)
                self.get_logger().info("Requested Offboard mode and arm.")

            if self.timeline.should_send_land_command(self.tick_count):
                self._publish_vehicle_command(VehicleCommand.VEHICLE_CMD_NAV_LAND)
                self.get_logger().info("Requested landing.")

            self.tick_count += 1

        def _publish_offboard_control_mode(self) -> None:
            msg = OffboardControlMode()
            msg.position = True
            msg.velocity = False
            msg.acceleration = False
            msg.attitude = False
            msg.body_rate = False
            msg.timestamp = self._timestamp_us()
            self.offboard_control_mode_pub.publish(msg)

        def _publish_position_setpoint(self, z: float) -> None:
            msg = TrajectorySetpoint()
            msg.position = [0.0, 0.0, z]
            msg.yaw = 0.0
            msg.timestamp = self._timestamp_us()
            self.trajectory_setpoint_pub.publish(msg)

        def _publish_vehicle_command(
            self,
            command: int,
            param1: float = 0.0,
            param2: float = 0.0,
        ) -> None:
            msg = VehicleCommand()
            msg.command = command
            msg.param1 = param1
            msg.param2 = param2
            msg.target_system = 1
            msg.target_component = 1
            msg.source_system = 1
            msg.source_component = 1
            msg.from_external = True
            msg.timestamp = self._timestamp_us()
            self.vehicle_command_pub.publish(msg)

        def _timestamp_us(self) -> int:
            return int(self.get_clock().now().nanoseconds / 1000)

    return rclpy, VerticalTakeoffLandNode


def main() -> None:
    rclpy, node_class = _create_node_class()
    rclpy.init()
    node = node_class()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

