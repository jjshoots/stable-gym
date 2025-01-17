.. _envs:

============
Environments
============

The :stable_gym:`Stable Gym package <>` provides a variety of environments for training and testing
:stable_learning_control:`(stable) reinforcement learning (RL) algorithms <>`.

Biological environments
-----------------------

Gym environments that are based on Biological systems.

.. toctree::
    :maxdepth: 1

    ./biological/oscillator.rst
    ./biological/oscillator_complicated.rst

Classic control environments
----------------------------

Environments that are based on classical control problems or `classical control`_
environments found in the :gymnasium:`gymnasium <>` library.

.. _`classical control`: https://gymnasium.farama.org/environments/classic_control

.. toctree::
    :maxdepth: 1

    ./classic_control/ex3_ekf.rst
    ./classic_control/cartpole_cost.rst
    ./classic_control/cartpole_tracking_cost.rst

.. _`classical control gymnasium environments`: https://gymnasium.farama.org/environments/classic_control

Mujoco environments
-------------------

Environments that are based on the on `Mujoco`_ or `Mujoco gymnasium`_ environments.

.. toctree::
    :maxdepth: 1

    ./mujoco/ant_cost.rst
    ./mujoco/half_cheetah_cost.rst
    ./mujoco/hopper_cost.rst
    ./mujoco/humanoid_cost.rst
    ./mujoco/swimmer_cost.rst
    ./mujoco/walker2d_cost.rst

.. _`Mujoco`: https://mujoco.org/
.. _`mujoco gymnasium`: https://gymnasium.farama.org/environments/mujoco

Robotics environment
--------------------

.. toctree::
    :maxdepth: 1

    ./robotics/fetch_reach_cost.rst
    ./robotics/minitaur_bullet_cost.rst
    ./robotics/quadx_hover_cost.rst
    ./robotics/quadx_tracking_cost.rst
    ./robotics/quadx_waypoints_cost.rst

.. note::

    The ROS robotics environments of the Stable Gym package were moved into a separate package
    called :ros_gazebo_gym:`Ros Gazebo Gym <>`.
