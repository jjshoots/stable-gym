# HopperCost gymnasium environment

<div align="center">
    <img src="https://github.com/rickstaa/stable-gym/assets/17570430/e7d31373-3cf9-426d-b4bb-8f745f00971b" alt="Hopper Cost environment" width="200px">
</div>
</br>

An actuated 3-jointed hopper. This environment corresponds to the [Hopper-v4](https://gymnasium.farama.org/environments/mujoco/hopper) environment included in the [gymnasium package](https://gymnasium.farama.org/). It is different in the fact that:

*   The objective was changed to a velocity-tracking task. To do this, the reward is replaced with a cost. This cost is the squared
    difference between the Hopper's forward velocity and a reference value (error).

The rest of the environment is the same as the original Hopper environment. Below, the modified cost is described. For more information about the environment (e.g. observation space, action space, episode termination, etc.), please refer to the [gymnasium library](https://gymnasium.farama.org/environments/mujoco/hopper/).

## Cost function

The cost function of this environment is designed in such a way that it tries to minimize the error between the Hopper's forward velocity and a reference value. The cost function is defined as:

$$
cost = w_{forward} \times (x_{velocity} - x_{reference\_x\_velocity})^2 + w_{ctrl} \times c_{ctrl}
$$

## How to use

This environment is part of the [Stable Gym package](https://github.com/rickstaa/stable-gym). It is therefore registered as the `stable_gym:HopperCost-v1` gymnasium environment when you import the Stable Gym package. If you want to use the environment in stand-alone mode, you can register it yourself.