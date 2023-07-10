# AntCost gymnasium environment

<div align="center">
    <img src="https://github.com/rickstaa/stable-gym/assets/17570430/c9f6d7f9-586e-4236-91d3-fa2d0ce4aadc" alt="Ant Cost environment" width="200px">
</div>
</br>

An actuated 8-jointed ant. This environment corresponds to the [Ant-v4](https://gymnasium.farama.org/environments/mujoco/ant) environment included in the [gymnasium package](https://gymnasium.farama.org/). It is different in the fact that:

*   The objective was changed to a velocity-tracking task. To do this, the reward is replaced with a cost. This cost is the squared
    difference between the Ant's forward velocity and a reference value (error).

The rest of the environment is the same as the original Ant environment. Below, the modified cost is described. For more information about the environment (e.g. observation space, action space, episode termination, etc.), please refer to the [gymnasium library](https://gymnasium.farama.org/environments/mujoco/ant/).

## Cost function

The cost function of this environment is designed in such a way that it tries to minimize the error between the Ant's forward velocity and a reference value. The cost function is defined as:

$$
cost = w_{forward} \times (x_{velocity} - x_{reference\_x\_velocity})^2 + w_{ctrl} \times c_{ctrl}
$$

## How to use

This environment is part of the [Stable Gym package](https://github.com/rickstaa/stable-gym). It is therefore registered as the `stable_gym:AntCost-v1` gymnasium environment when you import the Stable Gym package. If you want to use the environment in stand-alone mode, you can register it yourself.