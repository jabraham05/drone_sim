from setuptools import setup

package_name = "drone_mission"

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
    description="Mission state machines for autonomous drone delivery.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "offboard_takeoff = drone_mission.offboard_takeoff:main",
        ],
    },
)

