from setuptools import setup

package_name = "drone_simulation"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/worlds", ["worlds/food_delivery.sdf"]),
        (f"share/{package_name}/models", ["models/.gitkeep"]),
        (f"share/{package_name}/scenarios", ["scenarios/simple_delivery.yaml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="TODO",
    maintainer_email="todo@example.com",
    description="Gazebo worlds, models, and simulation scenarios for drone delivery.",
    license="MIT",
)

