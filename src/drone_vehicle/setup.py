from setuptools import setup

package_name = "drone_vehicle"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TODO",
    maintainer_email="todo@example.com",
    description="PX4 vehicle interface for Offboard control, health checks, and setpoint commands.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "px4_offboard_interface = drone_vehicle.px4_offboard_interface:main",
        ],
    },
)

