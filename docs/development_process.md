# Development Process

This project uses a documentation-first and documentation-last workflow. Every code change should keep the repository understandable, structured, and aligned with the current architecture.

## Required Workflow

Before making a code change:

1. Read the relevant documentation.
2. Check the current implementation.
3. Create a short update plan.
4. Make the code changes.
5. Update the documentation affected by the change.
6. Run the relevant validation checks.

## Documentation Rule

Code changes are not complete until the documentation is updated.

Update documentation when a change affects:

- Setup or installation steps
- Launch commands
- Package structure
- ROS topics, services, actions, parameters, or message flow
- Mission behavior or state transitions
- Simulation worlds, models, or scenarios
- Logging, testing, or troubleshooting steps
- Roadmap status or feature scope

## Planning Rule

Each non-trivial change should start with a short plan that states:

- What behavior or structure will change
- Which packages or docs are affected
- How the change will be validated

## Documentation Locations

- `README.md`: Project overview, quick start, and repository structure
- `docs/architecture.md`: System architecture and package responsibilities
- `docs/setup.md`: Installation and environment setup
- `docs/running_simulation.md`: Commands for running SITL, Gazebo, DDS, and mission nodes
- `docs/roadmap.md`: Planned phases and feature status
- `docs/troubleshooting.md`: Known issues and fixes

