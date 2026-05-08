"""Shared ROS topic names for the drone delivery stack."""

DRONE_NAMESPACE = "/drone"

VEHICLE_STATUS = f"{DRONE_NAMESPACE}/vehicle/status"
VEHICLE_LOCAL_POSITION = f"{DRONE_NAMESPACE}/vehicle/local_position"
VEHICLE_ODOMETRY = f"{DRONE_NAMESPACE}/vehicle/odometry"
VEHICLE_COMMAND = f"{DRONE_NAMESPACE}/vehicle/command"
VEHICLE_SETPOINT = f"{DRONE_NAMESPACE}/vehicle/setpoint"

LANDING_PAD_MARKER_POSE = f"{DRONE_NAMESPACE}/perception/landing_pad/marker_pose"
LANDING_PAD_DETECTION_STATUS = f"{DRONE_NAMESPACE}/perception/landing_pad/detection_status"

PX4_VEHICLE_STATUS = "/fmu/out/vehicle_status"
PX4_VEHICLE_LOCAL_POSITION = "/fmu/out/vehicle_local_position"
PX4_VEHICLE_ODOMETRY = "/fmu/out/vehicle_odometry"
PX4_OFFBOARD_CONTROL_MODE = "/fmu/in/offboard_control_mode"
PX4_TRAJECTORY_SETPOINT = "/fmu/in/trajectory_setpoint"
PX4_VEHICLE_COMMAND = "/fmu/in/vehicle_command"

CAMERA_IMAGE_RAW = "/camera/image_raw"
CAMERA_INFO = "/camera/camera_info"

PROJECT_TOPICS = (
    VEHICLE_STATUS,
    VEHICLE_LOCAL_POSITION,
    VEHICLE_ODOMETRY,
    VEHICLE_COMMAND,
    VEHICLE_SETPOINT,
    LANDING_PAD_MARKER_POSE,
    LANDING_PAD_DETECTION_STATUS,
)

PX4_TOPICS = (
    PX4_VEHICLE_STATUS,
    PX4_VEHICLE_LOCAL_POSITION,
    PX4_VEHICLE_ODOMETRY,
    PX4_OFFBOARD_CONTROL_MODE,
    PX4_TRAJECTORY_SETPOINT,
    PX4_VEHICLE_COMMAND,
)

CAMERA_TOPICS = (
    CAMERA_IMAGE_RAW,
    CAMERA_INFO,
)

