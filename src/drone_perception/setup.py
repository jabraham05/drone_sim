from setuptools import setup

package_name = "drone_perception"

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
    description="Perception modules for landing pad detection and future navigation features.",
    license="MIT",
    entry_points={
        "console_scripts": [
            "aruco_landing_detector = drone_perception.aruco_landing_detector:main",
        ],
    },
)

