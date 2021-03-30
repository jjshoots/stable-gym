"""Noisy master slave system (Ex3EKF) gym environment.

The dynamic system whose state is to be estimated:

.. math::
    x(k+1)=Ax(k)+w(k)
    x_1: angle
    x_2: frequency
    x_3: amplitude

    y(k)=x_3(k)*sin(x_1(k))+v(k)
    A=[1,dt,0;0,1,0;0,0,1]
    x(0)~N([0;10;1],[3,0,0;0,3,0;0,0,3])
    w(k)~N([0;0;0],[1/3*(dt)^3*q_1,1/2*(dt)^2*q_1,0;1/2*(dt)^2*q_1,dt*q_1,0;0,0,dt*q_2])
    v(k)~N(0,1)

Estimator design:

.. math::

    \\hat(x)(k+1)=A\\hat(x)(k)+u
    where u=[u1,u2,u3]', u=l(\\hat(x)(k),y(k)) come from the policy network l(.,.)
"""
__VERSION__ = "0.6.3"  # Ex3EKF version

import importlib
import sys

import gym
import matplotlib.pyplot as plt
import numpy as np
from gym import spaces
from gym.utils import seeding

# Try to import the disturber class
# NOTE: Only works if the simzoo or bayesian learning control package is installed.
# fallback to object if not successfull.
if "simzoo" in sys.modules:
    from simzoo.common.disturber import Disturber
elif importlib.util.find_spec("simzoo") is not None:
    Disturber = getattr(importlib.import_module("simzoo.common.disturber"), "Disturber")
else:
    try:
        Disturber = getattr(
            importlib.import_module(
                "bayesian_learning_control.simzoo.simzoo.common.disturber"
            ),
            "Disturber",
        )
    except AttributeError:
        Disturber = object

RANDOM_STEP = False  # Use random steps in __main__

# Disturber config used to overwrite the default config
# NOTE: Merged with the default config
DISTURBER_CFG = {
    # Disturbance applied to environment variables
    "env_disturbance": {
        "description": "Lacl mRNA decay rate disturbance",
        # The env variable which you want to disturb
        "variable": "_c1",
        # The range of values you want to use for each disturbance iteration
        "variable_range": np.linspace(1.0, 3.0, num=5, dtype=np.float32),
        # Label used in robustness plots.
        "label": "r: %s",
    },
}


class Ex3EKF(gym.Env, Disturber):
    """Noisy master slave system
    The goal of the agent in the Ex3EKF environment is to act in such a way that
    estimator perfectly estimated the original noisy system. By doing this it serves
    as a RL based stationary Kalman filter.

    .. note::
        This gym environment inherits from the
        :class:`~bayesian_learning_control.simzoo.simzoo.common.disturber.Disturber`
        in order to be able to use it with the Robustness Evaluation tool of the
        Bayesian Learning Control package (BLC). For more information see
        `the BLC documentation <https://rickstaa.github.io/bayesian-learning-control/control/robustness_eval.html>`_.
    """

    def __init__(self, seed=400):
        """Constructs all the necessary attributes for the oscillator object.

        Args:
            seed (int, optional): A random seed for the environment. By default
                `None``.
        """
        super().__init__()

        self.t = 0
        self.dt = 0.1

        # Setup Ex3EKF parameters
        self.q1 = 0.01
        self.g = 9.81
        self.l_net = 1.0
        self.mean1 = [0, 0]
        self.cov1 = np.array(
            [
                [1 / 3 * (self.dt) ** 3 * self.q1, 1 / 2 * (self.dt) ** 2 * self.q1],
                [1 / 2 * (self.dt) ** 2 * self.q1, self.dt * self.q1],
            ]
        )
        self.mean2 = 0
        self.cov2 = 1e-2
        self.missing_rate = 0
        self.sigma = 0

        # Displacement limit set to be [-high, high]
        high = np.array([10000, 10000, 10000, 10000], dtype=np.float32)

        self.action_space = spaces.Box(
            low=np.array([-10.0, -10.0], dtype=np.float32),
            high=np.array([10.0, 10.0], dtype=np.float32),
            dtype=np.float32,
        )
        self.observation_space = spaces.Box(-high, high, dtype=np.float32)
        self.reward_range = spaces.Box(
            np.array([0.0], dtype=np.float32),
            np.array([100], dtype=np.float32),
            dtype=np.float32,
        )

        self.seed(seed)
        self.viewer = None
        self.state = None
        self.output = None
        self.steps_beyond_done = None

    def seed(self, seed=None):
        """Return random seed."""
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def step(self, action):
        """Take step into the environment.

        Args:
            action (numpy.ndarray): The action we want to perform in the environment.

        Returns:
            (tuple): tuple containing:

                - obs (:obj:`numpy.ndarray`): The current state
                - cost (:obj:`numpy.float64`): The current cost.
                - done (:obj:`bool`): Whether the episode was done.
                - info_dict (:obj:`dict`): Dictionary with additional information.
        """

        # Perform action in the environment and return the new state
        u1, u2 = action
        t = self.t
        input = 0 * np.cos(t) * self.dt

        # Retrieve slave state
        hat_x_1, hat_x_2, x_1, x_2 = self.state

        # Retrieve master state
        x_1 = x_1 + self.dt * x_2
        x_2 = x_2 - self.g * self.l_net * np.sin(x_1) * self.dt + input
        state = np.array([x_1, x_2])
        state = (
            state + self.np_random.multivariate_normal(self.mean1, self.cov1).flatten()
        )  # Add process noise
        x_1, x_2 = state
        y_1 = np.sin(x_1) + self.np_random.normal(self.mean2, np.sqrt(self.cov2))
        hat_y_1 = np.sin(hat_x_1 + self.dt * hat_x_2)
        # flag=1: received
        # flag=0: dropout
        (flag,) = self.np_random.binomial(1, 1 - self.missing_rate, 1)
        # drop_rate = 1
        # to construct cost
        if flag == 1:
            hat_x_1 = hat_x_1 + self.dt * hat_x_2 + self.dt * u1 * (y_1 - hat_y_1)
            hat_x_2 = (
                hat_x_2
                - self.g * np.sin(hat_x_1) * self.dt
                + self.dt * u2 * (y_1 - hat_y_1)
                + input
            )
        else:
            hat_x_1 = hat_x_1 + self.dt * hat_x_2
            hat_x_2 = hat_x_2 - self.g * np.sin(hat_x_1) * self.dt + input

        # Calculate cost
        cost = np.square(hat_x_1 - x_1) + np.square(hat_x_2 - x_2)
        # cost = np.abs(hat_x_1 - x_1)**1 + np.abs(hat_x_2 - x_2)**1

        # Define stopping criteria
        if cost > self.reward_range.high or cost < self.reward_range.low:
            done = True
        else:
            done = False

        # Update state
        self.state = np.array([hat_x_1, hat_x_2, x_1, x_2])
        self.output = y_1
        self.t = self.t + self.dt

        # Return state, cost, done and reference
        return (
            np.array([hat_x_1, hat_x_2, x_1, x_2]),
            cost,
            done,
            dict(
                reference=y_1,
                state_of_interest=np.array([hat_x_1 - x_1, hat_x_2 - x_2]),
            ),
        )

    def reset(self):
        """Reset gym environment.

        Args:
            action (bool, optional): Whether we want to randomly initialize the
            environment. By default True.

        Returns:
            numpy.ndarray: Array containing the current observations.
        """
        x_1 = self.np_random.uniform(-np.pi / 2, np.pi / 2)
        x_2 = self.np_random.uniform(-np.pi / 2, np.pi / 2)
        hat_x_1 = x_1 + self.np_random.uniform(-np.pi / 4, np.pi / 4)
        hat_x_2 = x_2 + self.np_random.uniform(-np.pi / 4, np.pi / 4)
        self.state = np.array([hat_x_1, hat_x_2, x_1, x_2])
        self.output = np.sin(x_1) + self.np_random.normal(
            self.mean2, np.sqrt(self.cov2)
        )
        # y_1 = self.output
        # y_2 = np.sin(x_2) + self.np_random.normal(self.mean2, np.sqrt(self.cov2))
        return np.array([hat_x_1, hat_x_2, x_1, x_2])

    def render(self, mode="human"):
        """Render one frame of the environment.

        Args:
            mode (str, optional): Gym rendering mode. The default mode will do something
                human friendly, such as pop up a window.

        NotImplementedError: Will throw a NotImplimented error since the render method
            has not yet been implemented.

        Note:
            This currently is not yet implemented.
        """
        raise NotImplementedError(
            "No render method was implemented yet for the Ex3EKF environment."
        )


if __name__ == "__main__":

    print("Settting up Ex3EKF environment.")
    env = Ex3EKF()

    # Take T steps in the environment
    T = 10
    path = []
    t1 = []
    s = env.reset()
    print(f"Taking {T} steps in the Ex3EKF environment.")
    for i in range(int(T / env.dt)):
        action = (
            env.np_random.uniform(
                env.action_space.low, env.action_space.high, env.action_space.shape
            )
            if RANDOM_STEP
            else np.zeros(env.action_space.shape)
        )
        s, r, info, done = env.step(action)
        path.append(s)
        t1.append(i * env.dt)

    # Plot results
    print("Plot results.")
    fig = plt.figure(figsize=(9, 6))
    ax = fig.add_subplot(111)
    ax.plot(t1, np.array(path)[:, 0], color="blue", label="x1")
    ax.plot(t1, np.array(path)[:, 1], color="green", label="x2")
    # ax.plot(t1, np.array(path)[:, 2], color='black', label='measurement')
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc=2, fancybox=False, shadow=False)
    plt.show()
    print("done")