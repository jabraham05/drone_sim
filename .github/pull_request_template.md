## Summary

Describe the change and why it is needed.

## Package Area

- [ ] `drone_mission`
- [ ] `drone_vehicle`
- [ ] `drone_perception`
- [ ] `drone_simulation`
- [ ] `drone_bringup`
- [ ] `drone_common`
- [ ] Documentation
- [ ] CI/testing

## Interface Or Behavior Changes

List any changed ROS topics, services, actions, parameters, launch files, configs, mission states, or simulation assumptions.

- [ ] Project-owned ROS topics use `/drone/...`.
- [ ] Topic names are imported from `drone_common.topics`.
- [ ] PX4 `/fmu/...` topics are isolated to `drone_vehicle`.
- [ ] Raw camera topics are isolated to `drone_perception`.

## Tests Run

- [ ] `python3 -m compileall src`
- [ ] `pytest src tests`
- [ ] `pytest tests`
- [ ] `colcon build`
- [ ] `colcon test`
- [ ] PX4 SITL
- [ ] Gazebo simulation

## Not Tested

List anything that was not tested and why.

## Documentation

- [ ] Relevant docs were read before implementation.
- [ ] Affected docs were updated after implementation.
- [ ] No documentation update needed because:
