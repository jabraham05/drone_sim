import importlib.util
import sys
from pathlib import Path


MODULE_FILE = Path(__file__).resolve().parents[1] / "drone_vehicle" / "vertical_takeoff_land.py"
SPEC = importlib.util.spec_from_file_location("vertical_takeoff_land", MODULE_FILE)
vertical_takeoff_land = importlib.util.module_from_spec(SPEC)
sys.modules["vertical_takeoff_land"] = vertical_takeoff_land
SPEC.loader.exec_module(vertical_takeoff_land)

PHASE_DONE = vertical_takeoff_land.PHASE_DONE
PHASE_HOLD = vertical_takeoff_land.PHASE_HOLD
PHASE_LAND = vertical_takeoff_land.PHASE_LAND
PHASE_PRE_STREAM = vertical_takeoff_land.PHASE_PRE_STREAM
PHASE_TAKEOFF = vertical_takeoff_land.PHASE_TAKEOFF
VerticalMissionConfig = vertical_takeoff_land.VerticalMissionConfig
VerticalMissionTimeline = vertical_takeoff_land.VerticalMissionTimeline


def test_vertical_mission_phase_timing():
    config = VerticalMissionConfig(
        altitude_m=5.0,
        takeoff_duration_s=1.0,
        hold_duration_s=1.0,
        landing_command_duration_s=0.5,
        timer_period_s=0.5,
        pre_stream_setpoint_count=2,
    )
    timeline = VerticalMissionTimeline(config)

    assert timeline.phase_for_tick(0) == PHASE_PRE_STREAM
    assert timeline.phase_for_tick(1) == PHASE_PRE_STREAM
    assert timeline.phase_for_tick(2) == PHASE_TAKEOFF
    assert timeline.phase_for_tick(3) == PHASE_TAKEOFF
    assert timeline.phase_for_tick(4) == PHASE_HOLD
    assert timeline.phase_for_tick(5) == PHASE_HOLD
    assert timeline.phase_for_tick(6) == PHASE_LAND
    assert timeline.phase_for_tick(7) == PHASE_DONE


def test_vertical_mission_command_triggers():
    config = VerticalMissionConfig(
        takeoff_duration_s=1.0,
        hold_duration_s=1.0,
        landing_command_duration_s=0.5,
        timer_period_s=0.5,
        pre_stream_setpoint_count=2,
    )
    timeline = VerticalMissionTimeline(config)

    assert not timeline.should_enter_offboard_and_arm(1)
    assert timeline.should_enter_offboard_and_arm(2)
    assert not timeline.should_enter_offboard_and_arm(3)

    assert not timeline.should_send_land_command(5)
    assert timeline.should_send_land_command(6)
    assert not timeline.should_send_land_command(7)


def test_vertical_mission_setpoint_altitudes():
    config = VerticalMissionConfig(altitude_m=5.0)
    timeline = VerticalMissionTimeline(config)

    assert timeline.setpoint_z_for_phase(PHASE_PRE_STREAM) == -5.0
    assert timeline.setpoint_z_for_phase(PHASE_TAKEOFF) == -5.0
    assert timeline.setpoint_z_for_phase(PHASE_HOLD) == -5.0
    assert timeline.setpoint_z_for_phase(PHASE_LAND) == 0.0
    assert timeline.setpoint_z_for_phase(PHASE_DONE) == 0.0
