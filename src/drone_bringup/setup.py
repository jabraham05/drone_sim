from setuptools import setup

package_name = "drone_bringup"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", ["launch/sitl_delivery.launch.py"]),
        (f"share/{package_name}/config", ["config/mission.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TODO",
    maintainer_email="todo@example.com",
    description="Launch and configuration orchestration for the autonomous drone delivery simulation.",
    license="MIT",
)

